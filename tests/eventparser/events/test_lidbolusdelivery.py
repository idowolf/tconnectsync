#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidBolusDelivery(unittest.TestCase):
    """280: LID_BOLUS_DELIVERY. All fixtures are real captured pump-log events."""
    maxDiff = None

    def setUp(self):
        # Manual pump-button bolus, started: bolusType [0] (Now),
        # bolusSource 0 (PumpButton), bolusDeliveryStatus 1 (BolusStarted).
        self.fixturePumpButtonStarted = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 280,
            "sequenceGroup": 0,
            "sequenceNumber": 395159,
            "pumpDateTime": "2026-04-30T15:13:14",
            "eventProperties": {
                "bolusId": 1425, "bolusDeliveryStatus": 1, "bolusType": [0],
                "bolusSource": 0, "remoteId": 145, "requestedNow": 2000,
                "requestedLater": 0, "correction": 0,
                "extendedDurationRequested": 0, "deliveredTotal": 0,
            },
            "estimatedDateTime": "2026-04-30T15:13:14Z",
        }

        # Carb+correction BLE bolus, started: bolusType [0,3,4]
        # (Now|Correction|Carb), bolusSource 8 (Ble), status 1 (BolusStarted).
        self.fixtureCarbCorrectionStarted = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 280,
            "sequenceGroup": 0,
            "sequenceNumber": 395971,
            "pumpDateTime": "2026-04-30T21:38:00",
            "eventProperties": {
                "bolusId": 1426, "bolusDeliveryStatus": 1, "bolusType": [0, 3, 4],
                "bolusSource": 8, "remoteId": 146, "requestedNow": 10960,
                "requestedLater": 0, "correction": 130,
                "extendedDurationRequested": 0, "deliveredTotal": 0,
            },
            "estimatedDateTime": "2026-04-30T21:38:00Z",
        }

        # Completion of the same bolus: status 0 (BolusCompleted),
        # deliveredTotal now populated (10960).
        self.fixtureCarbCorrectionCompleted = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 280,
            "sequenceGroup": 0,
            "sequenceNumber": 395991,
            "pumpDateTime": "2026-04-30T21:40:03",
            "eventProperties": {
                "bolusId": 1426, "bolusDeliveryStatus": 0, "bolusType": [0, 3, 4],
                "bolusSource": 8, "remoteId": 146, "requestedNow": 10960,
                "requestedLater": 0, "correction": 130,
                "extendedDurationRequested": 0, "deliveredTotal": 10960,
            },
            "estimatedDateTime": "2026-04-30T21:40:03Z",
        }

    def test_dispatches_to_correct_class(self):
        self.assertIsInstance(Event(self.fixturePumpButtonStarted),
                              eventtypes.LidBolusDelivery)
        self.assertNotIsInstance(Event(self.fixturePumpButtonStarted), RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureCarbCorrectionStarted)
        self.assertEqual(ev.eventId, 280)
        self.assertEqual(ev.seqNum, 395971)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-04-30T21:38:00")

    def test_plain_fields_round_trip(self):
        ev = Event(self.fixtureCarbCorrectionStarted)
        self.assertEqual(ev.bolusId, 1426)
        self.assertEqual(ev.requestedNow, 10960)
        self.assertEqual(ev.deliveredTotal, 0)
        self.assertEqual(ev.correction, 130)
        self.assertEqual(ev.remoteId, 146)
        self.assertEqual(ev.requestedLater, 0)
        self.assertEqual(ev.extendedDurationRequested, 0)

    def test_completion_carries_delivered_total(self):
        ev = Event(self.fixtureCarbCorrectionCompleted)
        self.assertEqual(ev.bolusId, 1426)
        self.assertEqual(ev.deliveredTotal, 10960)

    def test_bolustype_single_bit_folds_and_resolves(self):
        # bolusType [0] -> 1<<0 == 1 -> Now
        ev = Event(self.fixturePumpButtonStarted)
        self.assertEqual(ev.bolusTypeRaw, 1)
        self.assertEqual(ev.bolusType, eventtypes.LidBolusDelivery.BolustypeBitmask.Now)

    def test_bolustype_multi_bit_folds_and_resolves(self):
        # bolusType [0,3,4] -> 1<<0 | 1<<3 | 1<<4 == 25 -> Now|Correction|Carb
        ev = Event(self.fixtureCarbCorrectionStarted)
        self.assertEqual(ev.bolusTypeRaw, sum(1 << i for i in [0, 3, 4]))
        self.assertEqual(ev.bolusTypeRaw, 25)
        bt = eventtypes.LidBolusDelivery.BolustypeBitmask
        self.assertEqual(ev.bolusType, bt.Now | bt.Correction | bt.Carb)

    def test_bolussource_resolves(self):
        self.assertEqual(
            Event(self.fixturePumpButtonStarted).bolusSource,
            eventtypes.LidBolusDelivery.BolussourceEnum.PumpButton)
        self.assertEqual(
            Event(self.fixtureCarbCorrectionStarted).bolusSource,
            eventtypes.LidBolusDelivery.BolussourceEnum.Ble)

    def test_bolusdeliverystatus_resolves(self):
        self.assertEqual(
            Event(self.fixtureCarbCorrectionStarted).bolusDeliveryStatus,
            eventtypes.LidBolusDelivery.BolusdeliverystatusEnum.BolusStarted)
        self.assertEqual(
            Event(self.fixtureCarbCorrectionCompleted).bolusDeliveryStatus,
            eventtypes.LidBolusDelivery.BolusdeliverystatusEnum.BolusCompleted)

    def test_todict_is_json_serializable(self):
        for fixture in (self.fixturePumpButtonStarted,
                        self.fixtureCarbCorrectionStarted,
                        self.fixtureCarbCorrectionCompleted):
            ev = Event(fixture)
            json.dumps(ev.todict())  # must not raise


if __name__ == "__main__":
    unittest.main()
