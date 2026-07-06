#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent

# Real LID_ALERT_CLEARED (eventCode 26) events copied verbatim from a captured
# pump-log response. Each has a different alertId (dictionary enum) value.


class TestLidAlertCleared(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        # alertId 0 -> LowInsulinAlert (0 must not be treated as missing)
        self.fixtureLowInsulin = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 26,
            "sequenceGroup": 0,
            "sequenceNumber": 398601,
            "pumpDateTime": "2026-05-01T16:49:45",
            "eventProperties": {"alertId": 0, "faultLocatorData": 0},
            "estimatedDateTime": "2026-05-01T16:49:45Z",
        }
        # alertId 2 -> LowPowerAlert
        self.fixtureLowPower = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 26,
            "sequenceGroup": 0,
            "sequenceNumber": 439055,
            "pumpDateTime": "2026-05-13T10:06:58",
            "eventProperties": {"alertId": 2, "faultLocatorData": 0},
            "estimatedDateTime": "2026-05-13T10:06:58Z",
        }
        # alertId 14 -> IncompleteFillTubingAlert
        self.fixtureIncompleteFillTubing = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 26,
            "sequenceGroup": 0,
            "sequenceNumber": 420534,
            "pumpDateTime": "2026-05-08T00:52:50",
            "eventProperties": {"alertId": 14, "faultLocatorData": 0},
            "estimatedDateTime": "2026-05-08T00:52:50Z",
        }
        # alertId 51 -> ControlIqLow
        self.fixtureControlIqLow = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 26,
            "sequenceGroup": 0,
            "sequenceNumber": 396276,
            "pumpDateTime": "2026-04-30T23:12:18",
            "eventProperties": {"alertId": 51, "faultLocatorData": 0},
            "estimatedDateTime": "2026-04-30T23:12:18Z",
        }

    def test_dispatches_to_lidalertcleared(self):
        for fx in (self.fixtureLowInsulin, self.fixtureLowPower,
                   self.fixtureIncompleteFillTubing, self.fixtureControlIqLow):
            ev = Event(fx)
            self.assertIsInstance(ev, eventtypes.LidAlertCleared)
            self.assertNotIsInstance(ev, RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureControlIqLow)
        self.assertEqual(ev.eventId, 26)
        self.assertEqual(ev.seqNum, 396276)

    def test_timestamp_preserves_wall_clock(self):
        ev = Event(self.fixtureControlIqLow)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-04-30T23:12:18")

    def test_plain_field_round_trips(self):
        ev = Event(self.fixtureControlIqLow)
        self.assertEqual(ev.faultLocatorData, 0)

    def test_alertid_raw_round_trips(self):
        self.assertEqual(Event(self.fixtureLowInsulin).alertIdRaw, 0)
        self.assertEqual(Event(self.fixtureLowPower).alertIdRaw, 2)
        self.assertEqual(Event(self.fixtureIncompleteFillTubing).alertIdRaw, 14)
        self.assertEqual(Event(self.fixtureControlIqLow).alertIdRaw, 51)

    def test_alertid_resolves_to_enum(self):
        E = eventtypes.LidAlertCleared.AlertidEnum
        self.assertEqual(Event(self.fixtureLowInsulin).alertId, E.LowInsulinAlert)
        self.assertEqual(Event(self.fixtureLowPower).alertId, E.LowPowerAlert)
        self.assertEqual(Event(self.fixtureIncompleteFillTubing).alertId,
                         E.IncompleteFillTubingAlert)
        self.assertEqual(Event(self.fixtureControlIqLow).alertId, E.ControlIqLow)

    def test_alertid_zero_resolves(self):
        # alertId 0 must resolve, not be dropped as a falsy/missing value.
        ev = Event(self.fixtureLowInsulin)
        self.assertEqual(ev.alertIdRaw, 0)
        self.assertEqual(ev.alertId,
                         eventtypes.LidAlertCleared.AlertidEnum.LowInsulinAlert)

    def test_todict_is_json_serializable(self):
        ev = Event(self.fixtureControlIqLow)
        d = ev.todict()
        json.dumps(d)  # must not raise
        self.assertEqual(d["id"], 26)
        self.assertEqual(d["name"], "LID_ALERT_CLEARED")
        self.assertEqual(d["seqNum"], 396276)
        self.assertEqual(d["alertIdRaw"], 51)
        self.assertEqual(d["faultLocatorData"], 0)


if __name__ == "__main__":
    unittest.main()
