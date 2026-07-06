#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidAlertActivated(unittest.TestCase):
    """4: LID_ALERT_ACTIVATED. alertid is a dictionary/enum field resolved
    through alertidRaw; faultlocatordata/param1/param2 are plain numeric fields.
    All fixtures are real captured pump-log events copied verbatim."""

    maxDiff = None

    def setUp(self):
        # alertId:50 -> DefaultAlert50; integer param2, zero fault/param1.
        self.fixtureDefaultAlert50 = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 4,
            "sequenceGroup": 0,
            "sequenceNumber": 395022,
            "pumpDateTime": "2026-04-30T14:26:30",
            "eventProperties": {"alertId": 50, "faultLocatorData": 0, "param1": 0, "param2": 866},
            "estimatedDateTime": "2026-04-30T14:26:30Z",
        }
        # alertId:51 -> ControlIqLow.
        self.fixtureControlIqLow = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 4,
            "sequenceGroup": 0,
            "sequenceNumber": 396263,
            "pumpDateTime": "2026-04-30T23:07:17",
            "eventProperties": {"alertId": 51, "faultLocatorData": 0, "param1": 0, "param2": 877},
            "estimatedDateTime": "2026-04-30T23:07:17Z",
        }
        # alertId:0 -> LowInsulinAlert (zero must resolve, not read as missing);
        # non-zero faultLocatorData and a fractional float param2.
        self.fixtureLowInsulinFloat = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 4,
            "sequenceGroup": 0,
            "sequenceNumber": 398333,
            "pumpDateTime": "2026-05-01T15:57:06",
            "eventProperties": {"alertId": 0, "faultLocatorData": 8242, "param1": 102, "param2": 249.76517},
            "estimatedDateTime": "2026-05-01T15:57:06Z",
        }
        # alertId:14 -> IncompleteFillTubingAlert; all-zero params.
        self.fixtureIncompleteFillTubing = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 4,
            "sequenceGroup": 0,
            "sequenceNumber": 420528,
            "pumpDateTime": "2026-05-08T00:52:18",
            "eventProperties": {"alertId": 14, "faultLocatorData": 8378, "param1": 0, "param2": 0},
            "estimatedDateTime": "2026-05-08T00:52:18Z",
        }
        # alertId:2 -> LowPowerAlert.
        self.fixtureLowPower = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 4,
            "sequenceGroup": 0,
            "sequenceNumber": 436691,
            "pumpDateTime": "2026-05-12T17:52:10",
            "eventProperties": {"alertId": 2, "faultLocatorData": 8306, "param1": 20, "param2": 1},
            "estimatedDateTime": "2026-05-12T17:52:10Z",
        }

    def test_dispatches_to_correct_class(self):
        for f in (self.fixtureDefaultAlert50, self.fixtureControlIqLow,
                  self.fixtureLowInsulinFloat, self.fixtureIncompleteFillTubing,
                  self.fixtureLowPower):
            ev = Event(f)
            self.assertIsInstance(ev, eventtypes.LidAlertActivated)
            self.assertNotIsInstance(ev, RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureDefaultAlert50)
        self.assertEqual(ev.eventId, 4)
        self.assertEqual(ev.seqNum, 395022)

        ev = Event(self.fixtureControlIqLow)
        self.assertEqual(ev.eventId, 4)
        self.assertEqual(ev.seqNum, 396263)

    def test_timestamp_preserves_wall_clock(self):
        ev = Event(self.fixtureDefaultAlert50)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-04-30T14:26:30")
        ev = Event(self.fixtureLowPower)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-05-12T17:52:10")

    def test_plain_fields(self):
        ev = Event(self.fixtureLowInsulinFloat)
        self.assertEqual(ev.faultLocatorData, 8242)
        self.assertEqual(ev.param1, 102)
        self.assertAlmostEqual(ev.param2, 249.76517)

        ev = Event(self.fixtureIncompleteFillTubing)
        self.assertEqual(ev.faultLocatorData, 8378)
        self.assertEqual(ev.param1, 0)
        self.assertEqual(ev.param2, 0)

    def test_alertid_enum_resolves_from_raw_int(self):
        ev = Event(self.fixtureDefaultAlert50)
        self.assertEqual(ev.alertIdRaw, 50)
        self.assertEqual(ev.alertId,
                         eventtypes.LidAlertActivated.AlertidEnum.DefaultAlert50)

        ev = Event(self.fixtureControlIqLow)
        self.assertEqual(ev.alertIdRaw, 51)
        self.assertEqual(ev.alertId,
                         eventtypes.LidAlertActivated.AlertidEnum.ControlIqLow)

        ev = Event(self.fixtureIncompleteFillTubing)
        self.assertEqual(ev.alertIdRaw, 14)
        self.assertEqual(ev.alertId,
                         eventtypes.LidAlertActivated.AlertidEnum.IncompleteFillTubingAlert)

        ev = Event(self.fixtureLowPower)
        self.assertEqual(ev.alertIdRaw, 2)
        self.assertEqual(ev.alertId,
                         eventtypes.LidAlertActivated.AlertidEnum.LowPowerAlert)

    def test_alertid_zero_value_resolves(self):
        # alertId:0 -> LowInsulinAlert (0 must not be treated as missing).
        ev = Event(self.fixtureLowInsulinFloat)
        self.assertEqual(ev.alertIdRaw, 0)
        self.assertEqual(ev.alertId,
                         eventtypes.LidAlertActivated.AlertidEnum.LowInsulinAlert)

    def test_todict_is_json_serializable(self):
        for f in (self.fixtureDefaultAlert50, self.fixtureLowInsulinFloat,
                  self.fixtureLowPower):
            ev = Event(f)
            d = ev.todict()
            json.dumps(d)  # must not raise
            self.assertEqual(d["id"], 4)
            self.assertEqual(d["name"], "LID_ALERT_ACTIVATED")

    def test_todict_round_trips_fields(self):
        ev = Event(self.fixtureLowInsulinFloat)
        d = ev.todict()
        self.assertEqual(d["seqNum"], 398333)
        self.assertEqual(d["alertIdRaw"], 0)
        self.assertEqual(d["faultLocatorData"], 8242)
        self.assertEqual(d["param1"], 102)
        self.assertAlmostEqual(d["param2"], 249.76517)


if __name__ == "__main__":
    unittest.main()
