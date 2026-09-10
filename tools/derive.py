#!/usr/bin/env python3
"""Derive a JSON graph from docs-apk/ and detect drift.

Every doc in docs-apk/ declares, in YAML frontmatter, what it derives from
(`apk_refs`) and what it builds on (`depends_on`). Integration code cites docs
with a `doc: <id>` comment. This walks all three and answers two questions:

  1. How is the information connected?   -> graph.json
  2. Has anything gone stale?            -> drift report

Usage:
    python3 tools/derive.py                  # verify + write docs-apk/graph.json
    python3 tools/derive.py --update-hashes  # (re)compute apk_ref sha256 values
    python3 tools/derive.py --quiet          # only report problems

Exit status is 1 if drift or a broken link was found, else 0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs-apk"
APK_SRC = ROOT / "nocommit" / "jadx" / "sources"
CODE_ROOTS = [ROOT / "custom_components", ROOT / "tests"]
GRAPH_OUT = DOCS / "graph.json"

# `doc: some.id`, or `doc: some.id#anchor` to cite a specific section.
# Several may be comma-separated. Matched anywhere a module docstring or a
# `#`/`//` comment can carry it.
CITE_RE = re.compile(r"\bdoc:\s*([A-Za-z0-9_.#\-, ]+)")

# Docs declare stable section anchors with `<!-- anchor: name -->`, placed
# under the heading. Anchors rather than heading text, so retitling a section
# does not break citations while deleting one does.
ANCHOR_RE = re.compile(r"<!--\s*anchor:\s*([A-Za-z0-9_.-]+)\s*-->")

# `## 3. Some heading` -> the "3", to catch duplicated section numbers.
HEADING_NUM_RE = re.compile(r"^##\s+(\d+)\.", re.MULTILINE)


# --------------------------------------------------------------------------
# Minimal frontmatter parsing.
#
# Deliberately hand-rolled rather than pulling in PyYAML: the schema is fixed
# and tiny (scalars, a list of ids, and a list of 3-key mappings), and this
# script must run with no dependencies in CI or on a fresh clone.
# --------------------------------------------------------------------------
def parse_frontmatter(text: str) -> tuple[dict, int]:
    """Return (fields, line_offset_of_body). Raises ValueError if malformed."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---' frontmatter fence")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("missing closing '---' frontmatter fence") from None

    out: dict = {}
    key = None          # current top-level key
    cur: dict | None = None   # current apk_refs mapping being filled

    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        s = raw.strip()

        if indent == 0 and ":" in s and not s.startswith("- "):
            key, _, val = s.partition(":")
            key, val = key.strip(), val.strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                out[key] = [x.strip() for x in inner.split(",") if x.strip()]
            elif val:
                out[key] = val.strip("'\"")
            else:
                out[key] = []
            cur = None
        elif s.startswith("- "):
            item = s[2:].strip()
            if ":" in item:                       # start of a mapping entry
                cur = {}
                k, _, v = item.partition(":")
                cur[k.strip()] = v.strip().strip("'\"")
                out.setdefault(key, []).append(cur)
            else:                                 # plain list scalar
                out.setdefault(key, []).append(item.strip("'\""))
                cur = None
        elif cur is not None and ":" in s:        # continuation of a mapping
            k, _, v = s.partition(":")
            cur[k.strip()] = v.strip().strip("'\"")

    return out, end + 1


#: Lines of context hashed either side of a symbol match.
#:
#: Hashing only the matching line is not enough. In a decompiled Retrofit
#: interface the method name sits on the signature line, but the HTTP verb,
#: the path template and any pinned query string are on the line *above* it:
#:
#:     @GET("/v1/p/routeServiceBundle?withScheduledRides=true&embedStops=true")
#:     Observable<RouteServiceBundle> getRouteServiceBundlePublic(...);
#:
#: With a zero-width window, rewriting that path — or flipping those pinned
#: flags, which api.py explicitly relies on — reported "no drift". The window
#: covers the annotation and the immediate body while still ignoring churn
#: elsewhere in a thousand-line file.
CONTEXT_LINES = 3


def ref_hash(path: str, symbol: str) -> tuple[str | None, str]:
    """Hash the lines of `path` that mention `symbol`, plus their context.

    Returns (hexdigest, status).
    """
    if not APK_SRC.exists():
        return None, "unverifiable"
    f = APK_SRC / path
    if not f.exists():
        return None, "missing-file"
    try:
        content = f.read_text(errors="replace")
    except OSError:
        return None, "unreadable"
    lines = content.splitlines()
    matched = [i for i, ln in enumerate(lines) if symbol in ln]
    if not matched:
        return None, "missing-symbol"

    # Union of context windows, so overlapping matches are not double-counted.
    wanted: set[int] = set()
    for i in matched:
        wanted.update(
            range(max(0, i - CONTEXT_LINES),
                  min(len(lines), i + CONTEXT_LINES + 1)))
    body = "\n".join(lines[i].rstrip() for i in sorted(wanted))
    return hashlib.sha256(body.encode()).hexdigest(), "ok"


def load_docs() -> tuple[list[dict], list[str]]:
    docs, problems = [], []
    for md in sorted(DOCS.glob("*.md")):
        text = md.read_text()
        try:
            fm, _ = parse_frontmatter(text)
        except ValueError as e:
            problems.append(f"{md.name}: {e}")
            continue
        if "id" not in fm:
            problems.append(f"{md.name}: frontmatter has no 'id'")
            continue
        fm["_file"] = md.name

        anchors = ANCHOR_RE.findall(text)
        for dup in {a for a in anchors if anchors.count(a) > 1}:
            problems.append(f"{md.name}: duplicate anchor '{dup}'")
        fm["_anchors"] = set(anchors)

        numbers = HEADING_NUM_RE.findall(text)
        for dup in sorted({n for n in numbers if numbers.count(n) > 1}):
            problems.append(
                f"{md.name}: duplicate section number '## {dup}.' "
                f"(sections were renumbered or inserted without renumbering)")

        docs.append(fm)
    return docs, problems


def scan_code_citations() -> dict[str, list[str]]:
    """Map doc id -> list of source files citing it."""
    cites: dict[str, list[str]] = {}
    for root in CODE_ROOTS:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.py")):
            try:
                text = p.read_text(errors="replace")
            except OSError:
                continue
            for m in CITE_RE.finditer(text):
                for did in (x.strip() for x in m.group(1).split(",")):
                    if did:
                        cites.setdefault(did, []).append(
                            str(p.relative_to(ROOT))
                        )
    return {k: sorted(set(v)) for k, v in cites.items()}


def split_ref(ref: str) -> tuple[str, str | None]:
    """Split "id#anchor" into (id, anchor)."""
    doc_id, _, anchor = ref.partition("#")
    return doc_id, (anchor or None)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update-hashes", action="store_true",
                    help="write computed sha256 values back into frontmatter")
    ap.add_argument("--quiet", action="store_true", help="only print problems")
    args = ap.parse_args()

    docs, problems = load_docs()
    if not docs and not problems:
        print("no docs found in docs-apk/", file=sys.stderr)
        return 1

    ids = [d["id"] for d in docs]
    for dup in {i for i in ids if ids.count(i) > 1}:
        problems.append(f"duplicate doc id: {dup}")
    known = set(ids)

    nodes: list[dict] = []
    edges: list[dict] = []
    drift: list[str] = []
    unverifiable = 0
    cites = scan_code_citations()

    for d in docs:
        did = d["id"]
        nodes.append({
            "id": did,
            "type": "doc",
            "kind": d.get("kind", "?"),
            "title": d.get("title", ""),
            "file": f"docs-apk/{d['_file']}",
        })

        for dep in d.get("depends_on", []) or []:
            if dep not in known:
                problems.append(f"{d['_file']}: depends_on unknown id '{dep}'")
            edges.append({"from": did, "to": dep, "rel": "depends_on"})

        for ref in d.get("apk_refs", []) or []:
            if not isinstance(ref, dict):
                problems.append(
                    f"{d['_file']}: malformed apk_ref entry {ref!r} "
                    f"(expected path/symbol/sha256 keys)")
                continue
            path, symbol = ref.get("path"), ref.get("symbol")
            if not path or not symbol:
                problems.append(f"{d['_file']}: apk_ref missing path/symbol")
                continue
            node_id = f"apk:{path}#{symbol}"
            digest, status = ref_hash(path, symbol)
            recorded = ref.get("sha256", "TBD")

            if status == "unverifiable":
                unverifiable += 1
            elif status != "ok":
                drift.append(f"{d['_file']}: {status} for {path}#{symbol}")
            elif recorded == "TBD":
                if not args.update_hashes:
                    drift.append(
                        f"{d['_file']}: unhashed ref {path}#{symbol} "
                        f"(run --update-hashes)")
            elif recorded != digest:
                drift.append(
                    f"{d['_file']}: DRIFT {path}#{symbol}\n"
                    f"    recorded {recorded[:16]}…  actual {digest[:16]}…")

            nodes.append({"id": node_id, "type": "apk_ref", "path": path,
                          "symbol": symbol, "status": status})
            edges.append({"from": did, "to": node_id, "rel": "derived_from"})

        for ref, srcs in cites.items():
            ref_id, anchor = split_ref(ref)
            if ref_id != did:
                continue
            for src in srcs:
                nodes.append({"id": src, "type": "code", "path": src})
                edge = {"from": src, "to": did, "rel": "cites"}
                if anchor:
                    edge["anchor"] = anchor
                edges.append(edge)

    anchors_by_id = {d["id"]: d.get("_anchors", set()) for d in docs}
    for ref, srcs in cites.items():
        ref_id, anchor = split_ref(ref)
        where = ", ".join(srcs)
        if ref_id not in known:
            problems.append(f"code cites unknown doc id '{ref_id}' (in {where})")
        elif anchor and anchor not in anchors_by_id[ref_id]:
            problems.append(
                f"code cites unknown anchor '{ref_id}#{anchor}' (in {where}); "
                f"known anchors: "
                f"{', '.join(sorted(anchors_by_id[ref_id])) or 'none'}")

    # Deduplicate nodes, keeping first occurrence.
    seen, uniq = set(), []
    for n in nodes:
        if n["id"] not in seen:
            seen.add(n["id"])
            uniq.append(n)

    cited_ids = {split_ref(r)[0] for r in cites}
    uncited = sorted(d["id"] for d in docs
                     if d.get("kind") not in ("meta",) and d["id"] not in cited_ids)

    graph = {
        "generated_by": "tools/derive.py",
        "apk_tree_present": APK_SRC.exists(),
        "counts": {
            "docs": len(docs),
            "apk_refs": sum(1 for n in uniq if n["type"] == "apk_ref"),
            "code_files": sum(1 for n in uniq if n["type"] == "code"),
            "anchored_citations": sum(1 for e in edges if e.get("anchor")),
            "edges": len(edges),
        },
        "nodes": uniq,
        "edges": edges,
        "uncited_docs": uncited,
        "problems": problems,
        "drift": drift,
    }

    if args.update_hashes:
        changed: list[str] = []
        for d in docs:
            md = DOCS / d["_file"]
            lines = md.read_text().splitlines()
            targets = {
                (r["path"], r["symbol"]): ref_hash(r["path"], r["symbol"])[0]
                for r in (d.get("apk_refs") or [])
                if isinstance(r, dict) and r.get("path") and r.get("symbol")
            }
            # Walk the frontmatter line by line rather than pattern-matching a
            # fixed key order: the parser accepts any order, so a regex that
            # assumed path/symbol/sha256 silently skipped reordered entries and
            # left real drift in place while reporting success.
            block: dict[str, str] = {}
            sha_line: int | None = None
            out = list(lines)

            def flush(block, sha_line):
                key = (block.get("path"), block.get("symbol"))
                digest = targets.get(key)
                if digest is None or sha_line is None:
                    return
                old = block.get("sha256", "TBD")
                if old == digest:
                    return
                indent = out[sha_line][:len(out[sha_line])
                                       - len(out[sha_line].lstrip())]
                out[sha_line] = f"{indent}sha256: {digest}"
                changed.append(
                    f"{d['_file']}: {key[0]}#{key[1]}\n"
                    f"    {old[:16]}… -> {digest[:16]}…")

            for i, raw in enumerate(lines):
                stripped = raw.strip()
                if stripped == "---" and i > 0:
                    break
                if stripped.startswith("- "):
                    flush(block, sha_line)
                    block, sha_line = {}, None
                    stripped = stripped[2:].strip()
                if ":" in stripped:
                    k, _, v = stripped.partition(":")
                    k, v = k.strip(), v.strip().strip("'\"")
                    if k in ("path", "symbol", "sha256"):
                        block[k] = v
                        if k == "sha256":
                            sha_line = i
            flush(block, sha_line)
            md.write_text("\n".join(out) + "\n")

        if changed:
            print(f"updated {len(changed)} hash(es):")
            for line in changed:
                print(f"  {line}")
            print("\nReview each change above: a hash moving means the cited "
                  "APK code changed.")
        else:
            print("all hashes already current")

    if not args.update_hashes:
        GRAPH_OUT.write_text(json.dumps(graph, indent=2) + "\n")

    if not args.quiet and not args.update_hashes:
        c = graph["counts"]
        print(f"graph -> {GRAPH_OUT.relative_to(ROOT)}")
        print(f"  {c['docs']} docs, {c['apk_refs']} apk refs, "
              f"{c['code_files']} code files, {c['edges']} edges")
        if not APK_SRC.exists():
            print(f"  apk tree absent -> {unverifiable} refs unverifiable "
                  f"(expected on a fresh clone)")
        if uncited:
            print(f"  note: {len(uncited)} doc(s) not cited by code: "
                  f"{', '.join(uncited)}")

    for p in problems:
        print(f"PROBLEM  {p}", file=sys.stderr)
    for dl in drift:
        print(f"DRIFT    {dl}", file=sys.stderr)

    if problems or drift:
        print(f"\n{len(problems)} problem(s), {len(drift)} drift(s)",
              file=sys.stderr)
        return 1
    if not args.quiet:
        print("  no drift")
    return 0


if __name__ == "__main__":
    sys.exit(main())
