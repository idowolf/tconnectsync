#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes

# Real captured LID_CGM_ALERT_ACK_DEX (371) events, copied verbatim.
# dalertId/sensorType/ackSource are dictionary/enum fields. "spareA2" is
# ignored by the parser (kept here but never asserted on).


class TestLidCgmAlertAckDex(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        # dalertId:2 (CGM High), sensorType:3 (G7), ackSource:0 (by User)
        self.fixtureCgmHigh = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 371,
            "sequenceGroup": 0,
            "sequenceNumber": 416807,
            "pumpDateTime": "2026-05-06T23:04:58",
            "eventProperties": {"dalertId": 2, "sensorType": 3, "spareA2": 0, "ackSource": 0},
            "estimatedDateTime": "2026-05-06T23:04:58Z",
        }
        # dalertId:12 (CGM Sensor Expiring Soon), sensorType:3 (G7), ackSource:0 (by User)
        self.fixtureSensorExpiringSoon = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 371,
            "sequenceGroup": 0,
            "sequenceNumber": 446797,
            "pumpDateTime": "2026-05-15T16:43:28",
            "eventProperties": {"dalertId": 12, "sensorType": 3, "spareA2": 0, "ackSource": 0},
            "estimatedDateTime": "2026-05-15T16:43:28Z",
        }
        # dalertId:32 (not in enum -> None), sensorType:3 (G7), ackSource:1 (by Software)
        self.fixtureAckBySoftware = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 371,
            "sequenceGroup": 0,
            "sequenceNumber": 449784,
            "pumpDateTime": "2026-05-16T12:34:28",
            "eventProperties": {"dalertId": 32, "sensorType": 3, "spareA2": 0, "ackSource": 1},
            "estimatedDateTime": "2026-05-16T12:34:28Z",
        }

    def test_dispatches_to_lidcgmalertackdex(self):
        for fx in (self.fixtureCgmHigh, self.fixtureSensorExpiringSoon, self.fixtureAckBySoftware):
            self.assertIsInstance(Event(fx), eventtypes.LidCgmAlertAckDex)

    def test_envelope_fields(self):
        ev = Event(self.fixtureCgmHigh)
        self.assertEqual(ev.eventId, 371)
        self.assertEqual(ev.seqNum, 416807)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'), "2026-05-06T23:04:58")

    def test_dalertid_resolves_cgm_high(self):
        ev = Event(self.fixtureCgmHigh)
        self.assertEqual(ev.dalertIdRaw, 2)
        self.assertEqual(ev.dalertId, eventtypes.LidCgmAlertAckDex.DalertidEnum.CgmHigh)

    def test_dalertid_resolves_sensor_expiring_soon(self):
        ev = Event(self.fixtureSensorExpiringSoon)
        self.assertEqual(ev.dalertIdRaw, 12)
        self.assertEqual(ev.dalertId, eventtypes.LidCgmAlertAckDex.DalertidEnum.CgmSensorExpiringSoon)

    def test_sensortype_resolves_g7(self):
        for fx in (self.fixtureCgmHigh, self.fixtureSensorExpiringSoon, self.fixtureAckBySoftware):
            ev = Event(fx)
            self.assertEqual(ev.sensorTypeRaw, 3)
            self.assertEqual(ev.sensorType, eventtypes.LidCgmAlertAckDex.SensortypeEnum.CgmTypeDexcomG7)

    def test_acksource_resolves_by_user(self):
        ev = Event(self.fixtureCgmHigh)
        self.assertEqual(ev.ackSourceRaw, 0)
        self.assertEqual(ev.ackSource, eventtypes.LidCgmAlertAckDex.AcksourceEnum.AlertAcknowledgedByUser)

    def test_acksource_resolves_by_software(self):
        ev = Event(self.fixtureAckBySoftware)
        self.assertEqual(ev.ackSourceRaw, 1)
        self.assertEqual(ev.ackSource, eventtypes.LidCgmAlertAckDex.AcksourceEnum.AlertAcknowledgedBySoftware)

    def test_todict_is_json_serializable(self):
        for fx in (self.fixtureCgmHigh, self.fixtureSensorExpiringSoon, self.fixtureAckBySoftware):
            ev = Event(fx)
            d = ev.todict()
            json.dumps(d)  # must not raise
            self.assertEqual(d["id"], 371)
            self.assertEqual(d["name"], "LID_CGM_ALERT_ACK_DEX")


if __name__ == "__main__":
    unittest.main()
