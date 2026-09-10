"""The settings form must accept exactly the documented values.

A range bound is easy to get subtly wrong, and the failure is invisible until
someone tries to enter the value the docs told them to.
"""

from __future__ import annotations

import pytest

pytest.importorskip("homeassistant")

import homeassistant  # noqa: E402,F401  (installs the voluptuous shim first)

from custom_components.tripshot_tracker.config_flow import (  # noqa: E402
    settings_schema,
)
from custom_components.tripshot_tracker.const import (  # noqa: E402
    CONF_ARRIVAL_EARLY_BUFFER_SEC,
    CONF_CONFIRM_POLLS,
    CONF_MEASUREMENT_GRACE_SEC,
    CONF_POLL_INTERVAL_SEC,
    CONF_TIMEZONE,
    TUNABLES,
)

TZ = "America/New_York"


def submit(**overrides):
    data = dict(TUNABLES)
    data[CONF_TIMEZONE] = TZ
    data.update(overrides)
    return settings_schema(ha_timezone=TZ)(data)


def accepted(**overrides) -> bool:
    try:
        submit(**overrides)
        return True
    except Exception:
        return False


class TestConfirmPolls:
    """1 is the "off" value, not 0 — the field counts polls, and zero polls
    agreeing is not a coherent setting."""

    def test_one_is_accepted_and_is_the_off_switch(self):
        assert accepted(**{CONF_CONFIRM_POLLS: 1})

    def test_zero_is_rejected(self):
        assert not accepted(**{CONF_CONFIRM_POLLS: 0})

    @pytest.mark.parametrize("value", [1, 2, 3, 4, 5])
    def test_the_documented_range_is_accepted(self, value):
        assert accepted(**{CONF_CONFIRM_POLLS: value})

    @pytest.mark.parametrize("value", [-1, 0, 6, 100])
    def test_outside_the_range_is_rejected(self, value):
        assert not accepted(**{CONF_CONFIRM_POLLS: value})

    def test_the_default_is_two(self):
        assert TUNABLES[CONF_CONFIRM_POLLS] == 2


class TestTimezone:
    """Empty means "follow Home Assistant", so it has to be enterable."""

    def test_empty_is_accepted(self):
        assert accepted(**{CONF_TIMEZONE: ""})

    def test_a_zone_name_is_accepted(self):
        assert accepted(**{CONF_TIMEZONE: "Europe/London"})

    def test_the_declared_default_validates(self):
        """The default must itself pass the schema it is the default for."""
        assert accepted(**{CONF_TIMEZONE: TUNABLES[CONF_TIMEZONE]})


class TestGrace:
    def test_minus_one_means_follow_the_poll_interval(self):
        assert accepted(**{CONF_MEASUREMENT_GRACE_SEC: -1})

    def test_an_explicit_value_is_accepted(self):
        assert accepted(**{CONF_MEASUREMENT_GRACE_SEC: 11})

    def test_zero_is_accepted(self):
        """Distinct from -1: it means no grace at all."""
        assert accepted(**{CONF_MEASUREMENT_GRACE_SEC: 0})


class TestEveryDefaultValidates:
    """Every declared default must pass the form that declares it."""

    def test_all_tunable_defaults_are_acceptable(self):
        assert accepted()

    @pytest.mark.parametrize("key", sorted(TUNABLES))
    def test_each_default_individually(self, key):
        assert accepted(**{key: TUNABLES[key]}), f"{key}={TUNABLES[key]!r}"


class TestOtherBounds:
    def test_poll_interval_floor(self):
        assert accepted(**{CONF_POLL_INTERVAL_SEC: 10})
        assert not accepted(**{CONF_POLL_INTERVAL_SEC: 9})

    def test_buffers_may_be_zero(self):
        assert accepted(**{CONF_ARRIVAL_EARLY_BUFFER_SEC: 0})
