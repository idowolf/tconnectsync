#!/usr/bin/env python3

import unittest
import arrow

from tconnectsync.sync.tandemsource.choose_device import (
    ChooseDevice,
    InvalidSerialNumber,
    NoDevicesFound,
)

from ...api.fake import TConnectApi
from ...secrets import build_secrets

LOGGER = "tconnectsync.sync.tandemsource.choose_device"


class FakeTandemSourceApi:
    """Fake TandemSource API returning a configurable get_pumper() pumps list of
    raw BffPump dicts."""
    def __init__(self, pumps=None):
        self._pumps = pumps if pumps is not None else []

    def get_pumper(self):
        return {'pumps': self._pumps}

    def needs_relogin(self):
        return False


def pump(serial, assignmentId=None, maxDate=None):
    return {
        'serialNumber': serial,
        'assignmentId': assignmentId if assignmentId is not None else ('dev-' + serial),
        'maxDateOfEvents': maxDate,
    }


class TestChooseDevice(unittest.TestCase):
    maxDiff = None

    def _choose(self, pumps, **secret_kwargs):
        tconnect = TConnectApi()
        tconnect._tandemsource = FakeTandemSourceApi(pumps=pumps)
        secret = build_secrets(**secret_kwargs)
        return ChooseDevice(secret, tconnect)

    # --- auto-select branch (sentinel 11111111 or falsy) ---

    def test_empty_list_raises_no_devices_found(self):
        cd = self._choose([], PUMP_SERIAL_NUMBER=11111111)
        with self.assertRaises(NoDevicesFound):
            cd.choose()

    def test_auto_selects_most_recent_regardless_of_order(self):
        older = pump('111', maxDate=arrow.utcnow().shift(days=-10).isoformat())
        newer = pump('222', maxDate=arrow.utcnow().shift(days=-1).isoformat())
        cd = self._choose([newer, older], PUMP_SERIAL_NUMBER=11111111)
        self.assertIs(cd.choose(), newer)

    def test_auto_select_skips_never_uploaded_pumps(self):
        never = pump('111', maxDate=None)  # first in the list
        dated = pump('222', maxDate=arrow.utcnow().shift(days=-2).isoformat())
        cd = self._choose([never, dated], PUMP_SERIAL_NUMBER=11111111)
        self.assertIs(cd.choose(), dated)

    def test_auto_select_falls_back_to_first_when_all_never_uploaded(self):
        first = pump('111', maxDate=None)
        second = pump('222', maxDate=None)
        cd = self._choose([first, second], PUMP_SERIAL_NUMBER=11111111)
        self.assertIs(cd.choose(), first)

    def test_sentinel_int_triggers_auto_select(self):
        p = pump('90556643', maxDate=arrow.utcnow().shift(days=-1).isoformat())
        cd = self._choose([p], PUMP_SERIAL_NUMBER=11111111)
        # Must not raise InvalidSerialNumber even though no serial == 11111111
        self.assertIs(cd.choose(), p)

    def test_falsy_serial_triggers_auto_select(self):
        p = pump('90556643', maxDate=arrow.utcnow().shift(days=-1).isoformat())
        cd = self._choose([p], PUMP_SERIAL_NUMBER=None)
        self.assertIs(cd.choose(), p)

    # --- explicit-serial branch ---

    def test_explicit_serial_overrides_recency(self):
        chosen = pump('90556643', maxDate=arrow.utcnow().shift(days=-10).isoformat())
        newer = pump('99999999', maxDate=arrow.utcnow().shift(days=-1).isoformat())
        cd = self._choose([newer, chosen], PUMP_SERIAL_NUMBER=90556643)
        self.assertIs(cd.choose(), chosen)

    def test_unknown_serial_raises_invalid_serial_number(self):
        p = pump('90556643', maxDate=arrow.utcnow().shift(days=-1).isoformat())
        cd = self._choose([p], PUMP_SERIAL_NUMBER=12345678)
        with self.assertRaisesRegex(InvalidSerialNumber, "is not present on your account"):
            cd.choose()

    # --- stale-pump warning ---

    def test_stale_selected_pump_warns(self):
        p = pump('90556643', maxDate=arrow.utcnow().shift(days=-5).isoformat())
        cd = self._choose([p], PUMP_SERIAL_NUMBER=90556643)
        with self.assertLogs(LOGGER, level="WARNING") as cm:
            cd.choose()
        self.assertTrue(any("no events in the last" in m for m in cm.output))

    def test_fresh_selected_pump_does_not_warn(self):
        p = pump('90556643', maxDate=arrow.utcnow().shift(days=-1).isoformat())
        cd = self._choose([p], PUMP_SERIAL_NUMBER=90556643)
        # assertNoLogs is 3.10+; CI runs 3.8, so assert INFO logs contain no warning text.
        with self.assertLogs(LOGGER, level="INFO") as cm:
            cd.choose()
        self.assertFalse(any("no events in the last" in m for m in cm.output))

    def test_unparseable_date_on_selected_pump_is_swallowed(self):
        p = pump('90556643', maxDate="not-a-date")
        cd = self._choose([p], PUMP_SERIAL_NUMBER=90556643)
        with self.assertLogs(LOGGER, level="INFO") as cm:
            device = cd.choose()
        self.assertIs(device, p)
        self.assertFalse(any("no events in the last" in m for m in cm.output))


if __name__ == "__main__":
    unittest.main()
