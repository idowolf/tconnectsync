#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidCgmAlertActivatedDex(unittest.TestCase):
    """369 LID_CGM_ALERT_ACTIVATED_DEX: dalertId resolves via a dictionary
    transform enum, sensorType is an enum. All fixtures are real captures."""
    maxDiff = None

    def setUp(self):
        # dalertId:2 -> CgmHigh
        self.fixtureHigh = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 369, "sequenceGroup": 0, "sequenceNumber": 394822,
            "pumpDateTime": "2026-04-30T13:13:00",
            "eventProperties": {
                "dalertId": 2, "sensorType": 3, "spareA2": 0,
                "faultLocatorData": 8468, "param1": 214, "param2": 200,
            },
            "estimatedDateTime": "2026-04-30T13:13:00Z",
        }
        # dalertId:3 -> CgmLow
        self.fixtureLow = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 369, "sequenceGroup": 0, "sequenceNumber": 398698,
            "pumpDateTime": "2026-05-01T16:58:01",
            "eventProperties": {
                "dalertId": 3, "sensorType": 3, "spareA2": 0,
                "faultLocatorData": 8467, "param1": 73, "param2": 80,
            },
            "estimatedDateTime": "2026-05-01T16:58:01Z",
        }
        # dalertId:1 -> CgmFixedLow
        self.fixtureFixedLow = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 369, "sequenceGroup": 0, "sequenceNumber": 403231,
            "pumpDateTime": "2026-05-03T01:28:03",
            "eventProperties": {
                "dalertId": 1, "sensorType": 3, "spareA2": 0,
                "faultLocatorData": 8467, "param1": 53, "param2": 55,
            },
            "estimatedDateTime": "2026-05-03T01:28:03Z",
        }
        # dalertId:14 -> CgmOutOfRange
        self.fixtureOutOfRange = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 369, "sequenceGroup": 0, "sequenceNumber": 409133,
            "pumpDateTime": "2026-05-04T18:59:00",
            "eventProperties": {
                "dalertId": 14, "sensorType": 3, "spareA2": 0,
                "faultLocatorData": 8462, "param1": 25, "param2": 917,
            },
            "estimatedDateTime": "2026-05-04T18:59:00Z",
        }
        # dalertId:11 -> CgmSensorFail
        self.fixtureSensorFail = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 369, "sequenceGroup": 0, "sequenceNumber": 481654,
            "pumpDateTime": "2026-05-25T08:35:32",
            "eventProperties": {
                "dalertId": 11, "sensorType": 3, "spareA2": 0,
                "faultLocatorData": 8481, "param1": 35, "param2": 765,
            },
            "estimatedDateTime": "2026-05-25T08:35:32Z",
        }

    def test_dispatches_to_correct_class(self):
        for f in (self.fixtureHigh, self.fixtureLow, self.fixtureFixedLow,
                  self.fixtureOutOfRange, self.fixtureSensorFail):
            ev = Event(f)
            self.assertIsInstance(ev, eventtypes.LidCgmAlertActivatedDex)
            self.assertNotIsInstance(ev, RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureHigh)
        self.assertEqual(ev.eventId, 369)
        self.assertEqual(ev.seqNum, 394822)

    def test_timestamp_preserves_wall_clock(self):
        ev = Event(self.fixtureSensorFail)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-05-25T08:35:32")

    def test_plain_fields_round_trip(self):
        ev = Event(self.fixtureOutOfRange)
        self.assertEqual(ev.faultLocatorData, 8462)
        self.assertEqual(ev.param1, 25)
        self.assertEqual(ev.param2, 917)

    def test_dalertid_dictionary_enum_resolves(self):
        cases = [
            (self.fixtureHigh, 2, eventtypes.LidCgmAlertActivatedDex.DalertidEnum.CgmHigh),
            (self.fixtureLow, 3, eventtypes.LidCgmAlertActivatedDex.DalertidEnum.CgmLow),
            (self.fixtureFixedLow, 1, eventtypes.LidCgmAlertActivatedDex.DalertidEnum.CgmFixedLow),
            (self.fixtureOutOfRange, 14, eventtypes.LidCgmAlertActivatedDex.DalertidEnum.CgmOutOfRange),
            (self.fixtureSensorFail, 11, eventtypes.LidCgmAlertActivatedDex.DalertidEnum.CgmSensorFail),
        ]
        for f, raw, member in cases:
            ev = Event(f)
            self.assertEqual(ev.dalertIdRaw, raw)
            self.assertEqual(ev.dalertId, member)

    def test_sensortype_enum_resolves(self):
        # every capture is sensorType:3 -> Dexcom G7
        for f in (self.fixtureHigh, self.fixtureLow, self.fixtureFixedLow,
                  self.fixtureOutOfRange, self.fixtureSensorFail):
            ev = Event(f)
            self.assertEqual(ev.sensorTypeRaw, 3)
            self.assertEqual(ev.sensorType,
                             eventtypes.LidCgmAlertActivatedDex.SensortypeEnum.CgmTypeDexcomG7)

    def test_todict_is_json_serializable(self):
        for f in (self.fixtureHigh, self.fixtureLow, self.fixtureFixedLow,
                  self.fixtureOutOfRange, self.fixtureSensorFail):
            ev = Event(f)
            json.dumps(ev.todict())  # must not raise


if __name__ == "__main__":
    unittest.main()
