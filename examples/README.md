# Examples

- [`automations.yaml`](automations.yaml) — alerting on early departures and
  other verdicts, with filtering by route and stop.
- [`dashboard.yaml`](dashboard.yaml) — history graphs of the deviation
  metrics, counter tiles, and a plain-English "how late was the last bus"
  card. Paste a card via **Edit dashboard → + Add card → Manual**, or the
  whole view via **⋮ → Raw configuration editor**.

# Installing the example automations

Two ways. The first needs no file editing and is the one to use if you are not
sure.

## Option 1 — paste one automation in the UI (recommended)

1. **Settings → Automations & scenes → + Create automation → Create new automation**
2. Top-right **⋮ → Edit in YAML**
3. Delete the placeholder content, then paste **one** automation from
   [`automations.yaml`](automations.yaml) — **without** its leading `- `, and
   with the remaining lines shifted left by two spaces so `id:` starts at
   column 1:

   ```yaml
   id: tripshot_departed_early
   alias: Transit - bus departed early
   mode: queued
   max: 10
   triggers:
     - trigger: event
       event_type: tripshot_tracker_event
       event_data:
         verdict: depart_early
   actions:
     - action: persistent_notification.create
       data:
         title: "{{ trigger.event.data.route }} left early"
         message: >-
           Bus {{ trigger.event.data.bus }} left {{ trigger.event.data.stop }}
           {{ (trigger.event.data.deviation_seconds / -60) | round(1) }} minutes
           early.
   ```

4. **Save**, and give it a name if prompted.

Repeat per automation. Home Assistant writes them into your `automations.yaml`
for you, so you never touch the file directly.

## Option 2 — edit `automations.yaml`

`automations.yaml` lives next to `configuration.yaml` in your Home Assistant
config directory (in the **File editor** or **Studio Code Server** add-on it is
at the top level; over SSH or Samba it is `/config/`).

A default install already has this line in `configuration.yaml`:

```yaml
automation: !include automations.yaml
```

If that line is missing, add it — otherwise the file is never read.

Then append the contents of [`automations.yaml`](automations.yaml) to your own
`automations.yaml`, keeping the `- id:` list items at the left margin, and
**Developer tools → YAML → Reload automations** (a full restart also works).

### The two files take different shapes

`automations.yaml` is a **plain list**. There is no `automation:` key inside it
— that key lives in `configuration.yaml`, on the `!include` line.

```yaml
# automations.yaml — correct
- id: tripshot_departed_early
  alias: Transit - bus departed early
  ...

- id: tripshot_no_buses_running
  ...
```

```yaml
# automations.yaml — WRONG, this is configuration.yaml's shape
automation:
  - id: tripshot_departed_early
    ...
```

If you would rather keep everything in `configuration.yaml` instead, use the
second shape there and drop the `!include` line.

## Checking it works

- **Developer tools → Events**, listen to `tripshot_tracker_event`, and watch a
  real arrival or departure fire one. This confirms the integration is
  producing events before you debug an automation on top of it.
- **Settings → Automations**, open one, **⋮ → Run** to test the action. Note
  that a manual run has no `trigger` variable, so templates referring to
  `trigger.event.data` will render empty — that is expected, not a fault.
- **Settings → Automations → ⋮ → Traces** shows why a run did or did not
  proceed past its conditions.

## Choosing where the alerts go

The examples all use `notify.persistent_notification`, which needs no setup and
posts to the Home Assistant sidebar. Every marked line looks like:

```yaml
    - action: notify.persistent_notification   # <- change target here
      data:
        title: "..."
        message: "..."
```

### 1. Find the name of your target

**Developer tools → Actions**, type `notify.` in the picker. Whatever is listed
is what you can call. Typical entries:

| Action | Goes to | Needs |
|---|---|---|
| `notify.persistent_notification` | sidebar | nothing |
| `notify.mobile_app_<device>` | one phone | the Companion app, signed in |
| `notify.<name>` | whatever you configured | e.g. Telegram, email, ntfy |

If no `notify.mobile_app_…` appears, the Companion app is not installed or not
signed in on that device. Install it and sign in, and it registers itself.

Avoid `notify.notify` — it resolves to whichever notify action Home Assistant
happens to find first, so it can silently deliver somewhere unintended.

### 2. Swap it in

Change only the action name. `title` and `message` are the same fields for all
of them, so nothing else moves:

```yaml
    - action: notify.mobile_app_pixel_9
      data:
        title: "..."
        message: "..."
```

Test it first in **Developer tools → Actions**: pick the action, type a message,
**Perform action**, and confirm it arrives before wiring it into an automation.

### 3. One place to change it (recommended)

Editing five automations every time you change phone is tedious. Define a
notify group once in `configuration.yaml`:

```yaml
notify:
  - platform: group
    name: transit_alerts
    services:
      - action: mobile_app_pixel_9        # name only, no "notify." prefix
      - action: persistent_notification
```

Restart, then use `notify.transit_alerts` everywhere. After that, changing who
gets alerted — adding a second phone, muting the sidebar copy — means editing
the group, and every automation follows.

Two details from the Home Assistant docs: entries under `services:` use
`action:` with only the **name portion** (`mobile_app_pixel_9`, not
`notify.mobile_app_pixel_9`), and this YAML form is a *notify action group*,
which is a different thing from the Notify group helper offered in the UI.

### Newer entity-style notifications

Recent Home Assistant versions also expose notify *entities*, called with a
target rather than a per-device action name:

```yaml
    - action: notify.send_message
      target:
        entity_id: notify.pixel_9
      data:
        message: "..."
```

Both styles work. The examples use the action style because it takes `title` as
well as `message`, and because it is what most existing setups already have.

## Entity names include the route

Each stop is a device, and the device is named `<route> <stop>` — so a stop
served by two lines gives two distinct devices rather than one name used twice.

That makes entity IDs longer:

| | |
|---|---|
| Device | `Red Line Rush Rhees Library Back Side` |
| Entity ID | `sensor.red_line_rush_rhees_library_back_side_depart_early` |
| Full name | `Red Line Rush Rhees Library Back Side Depart early` |
| Shown on the device page | `Depart early` |

Both lines here call at Rush Rhees Library Back Side and Eastman Living Center,
so without the route in the name the two sets of entities would collide and
Home Assistant would disambiguate them with a `_2` suffix — assigned by
whichever config entry was set up first, and liable to move if an entry is ever
removed and re-added.

```
sensor.red_line_eastman_living_center_depart_early
sensor.red_line_rush_rhees_library_back_side_depart_early
sensor.orange_line_eastman_living_center_depart_early
sensor.orange_line_rush_rhees_library_back_side_depart_early
sensor.orange_line_towers_depart_early
```

Entity IDs are assigned once, when an entity is first created, and Home
Assistant never revises them. **Entities that already exist keep the IDs they
were given**, including any `_2` suffix; only newly created ones use the route-
qualified form. To bring existing ones across, either remove and re-add the
config entry (counters reset), or rename them under
**Settings → Devices & services → Entities**.

If the full names are too long for a dashboard, rename the device under
**Settings → Devices & services → Devices** — Home Assistant offers to rename
its entity IDs at the same time, and nothing in this integration depends on
either the device name or the entity ID.

## Choosing which route and stop to alert on

Filtering happens in the trigger's `event_data`. **Every key you list must
match exactly; every key you leave out matches anything.** So the filter is
built by adding keys, not by writing conditions.

### Everything, one route, one stop

```yaml
# every tracked route, every stop
triggers:
  - trigger: event
    event_type: tripshot_tracker_event
    event_data:
      verdict: depart_early
```

```yaml
# one route, any of its stops
    event_data:
      route: Red Line
      verdict: depart_early
```

```yaml
# one stop on one route
    event_data:
      route: Red Line
      stop: Rush Rhees Library Back Side
      verdict: depart_early
```

```yaml
# one stop, whichever route is calling there
    event_data:
      stop: Rush Rhees Library Back Side
      verdict: depart_early
```

That last one matters when several lines share a stop: without `route`, you get
alerts from every route that serves it.

### Several routes, or several stops

`event_data` matches one value per key. For a set, trigger broadly and narrow
with a condition:

```yaml
triggers:
  - trigger: event
    event_type: tripshot_tracker_event
    event_data:
      verdict: depart_early
conditions:
  - condition: template
    value_template: >-
      {{ trigger.event.data.route in ['Red Line', 'Orange Line'] }}
```

The same shape works for stops, or for both at once:

```yaml
    value_template: >-
      {{ trigger.event.data.route == 'Red Line'
         and trigger.event.data.stop in ['Eastman Living Center',
                                         'Rush Rhees Library Back Side'] }}
```

### Filtering by anything else in the event

Any field can be filtered the same way — `verdict`, `kind`, `punctuality`,
`bus`:

```yaml
    event_data:
      route: Red Line
      kind: arrival          # arrivals only, ignore departures
      punctuality: late      # any lateness, early or on-time ignored
```

```yaml
    event_data:
      bus: "2603"            # follow one vehicle
```

Note `verdict` is the specific one (`depart_early`), while `kind` +
`punctuality` are its two halves — use whichever reads better.

### Names or ids

`route` and `stop` are display names: readable, but they change if the operator
renames something. `route_id` and `stop_id` are UUIDs: stable, unreadable.

```yaml
    event_data:
      route_id: 22443444-e127-4e40-8927-a3192e750369
      verdict: depart_early
```

Names are fine for a personal setup. Reach for the ids if an alert mysteriously
stops firing — a rename upstream is the usual reason.

### Finding the exact values

Names must match character for character. Rather than guessing, watch a real
one: **Developer tools → Events**, listen to `tripshot_tracker_event`, and read
the values off an event as it fires. The stop names also appear on each stop's
device page.
