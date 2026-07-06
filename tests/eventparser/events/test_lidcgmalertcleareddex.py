#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidCgmAlertClearedDex(unittest.TestCase):
    """370 LID_CGM_ALERT_CLEARED_DEX: dalertId (dict->enum) and sensorType (enum).

    All fixtures are real captured pump-log events copied verbatim; they share
    sensorType 3 (Dexcom G7) and differ only in dalertId.
    """
    maxDiff = None

    def setUp(self):
        # dalertId 3 -> CgmLow
        self.fixtureCgmLow = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 370, "sequenceGroup": 0, "sequenceNumber": 398753,
            "pumpDateTime": "2026-05-01T17:18:01",
            "eventProperties": {"dalertId": 3, "sensorType": 3},
            "estimatedDateTime": "2026-05-01T17:18:01Z",
        }
        # dalertId 1 -> CgmFixedLow
        self.fixtureCgmFixedLow = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 370, "sequenceGroup": 0, "sequenceNumber": 403279,
            "pumpDateTime": "2026-05-03T01:48:03",
            "eventProperties": {"dalertId": 1, "sensorType": 3},
            "estimatedDateTime": "2026-05-03T01:48:03Z",
        }
        # dalertId 14 -> CgmOutOfRange
        self.fixtureCgmOutOfRange = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 370, "sequenceGroup": 0, "sequenceNumber": 409147,
            "pumpDateTime": "2026-05-04T19:07:08",
            "eventProperties": {"dalertId": 14, "sensorType": 3},
            "estimatedDateTime": "2026-05-04T19:07:08Z",
        }

    def test_dispatches_to_correct_class(self):
        ev = Event(self.fixtureCgmLow)
        self.assertIsInstance(ev, eventtypes.LidCgmAlertClearedDex)
        self.assertNotIsInstance(ev, RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureCgmLow)
        self.assertEqual(ev.eventId, 370)
        self.assertEqual(ev.seqNum, 398753)

    def test_timestamp_preserves_wall_clock(self):
        ev = Event(self.fixtureCgmLow)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-05-01T17:18:01")

    def test_dalertid_resolves_to_enum(self):
        self.assertEqual(Event(self.fixtureCgmLow).dalertIdRaw, 3)
        self.assertEqual(Event(self.fixtureCgmLow).dalertId,
                         eventtypes.LidCgmAlertClearedDex.DalertidEnum.CgmLow)

        self.assertEqual(Event(self.fixtureCgmFixedLow).dalertIdRaw, 1)
        self.assertEqual(Event(self.fixtureCgmFixedLow).dalertId,
                         eventtypes.LidCgmAlertClearedDex.DalertidEnum.CgmFixedLow)

        self.assertEqual(Event(self.fixtureCgmOutOfRange).dalertIdRaw, 14)
        self.assertEqual(Event(self.fixtureCgmOutOfRange).dalertId,
                         eventtypes.LidCgmAlertClearedDex.DalertidEnum.CgmOutOfRange)

    def test_sensortype_resolves_to_enum(self):
        ev = Event(self.fixtureCgmLow)
        self.assertEqual(ev.sensorTypeRaw, 3)
        self.assertEqual(ev.sensorType,
                         eventtypes.LidCgmAlertClearedDex.SensortypeEnum.CgmTypeDexcomG7)

    def test_todict_is_json_serializable(self):
        ev = Event(self.fixtureCgmOutOfRange)
        d = ev.todict()
        json.dumps(d)  # must not raise
        self.assertEqual(d["id"], 370)
        self.assertEqual(d["name"], "LID_CGM_ALERT_CLEARED_DEX")
        self.assertEqual(d["seqNum"], 409147)
        self.assertEqual(d["dalertIdRaw"], 14)
        self.assertEqual(d["sensorTypeRaw"], 3)


if __name__ == "__main__":
    unittest.main()
