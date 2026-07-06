#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidBolusRequestedMsg3(unittest.TestCase):
    """66: LID_BOLUS_REQUESTED_MSG3. Fixtures are real captured pump-log
    events copied verbatim (spareA2 is present but ignored by the parser)."""
    maxDiff = None

    def setUp(self):
        # food-only bolus; total carries float rounding (8.330001).
        self.fixtureFoodOnly = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 66,
            "sequenceGroup": 0,
            "sequenceNumber": 394643,
            "pumpDateTime": "2026-04-30T11:57:38",
            "eventProperties": {
                "bolusId": 1423, "spareA2": 0, "foodBolusSize": 8.33,
                "correctionBolusSize": 0, "totalBolusSize": 8.330001,
            },
            "estimatedDateTime": "2026-04-30T11:57:38Z",
        }

        # food + correction; both components non-zero.
        self.fixtureFoodAndCorrection = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 66,
            "sequenceGroup": 0,
            "sequenceNumber": 395961,
            "pumpDateTime": "2026-04-30T21:37:45",
            "eventProperties": {
                "bolusId": 1426, "spareA2": 0, "foodBolusSize": 10.83,
                "correctionBolusSize": 0.13, "totalBolusSize": 10.96,
            },
            "estimatedDateTime": "2026-04-30T21:37:45Z",
        }

        # correction-only food component; total exceeds correction.
        self.fixtureCorrectionOnly = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 66,
            "sequenceGroup": 0,
            "sequenceNumber": 398360,
            "pumpDateTime": "2026-05-01T16:02:12",
            "eventProperties": {
                "bolusId": 1430, "spareA2": 0, "foodBolusSize": 0,
                "correctionBolusSize": 1.47, "totalBolusSize": 3,
            },
            "estimatedDateTime": "2026-05-01T16:02:12Z",
        }

        # both breakdown components zero but a non-zero total.
        self.fixtureTotalOnly = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 66,
            "sequenceGroup": 0,
            "sequenceNumber": 394841,
            "pumpDateTime": "2026-04-30T13:13:28",
            "eventProperties": {
                "bolusId": 1424, "spareA2": 0, "foodBolusSize": 0,
                "correctionBolusSize": 0, "totalBolusSize": 4,
            },
            "estimatedDateTime": "2026-04-30T13:13:28Z",
        }

    def test_dispatches_to_correct_class(self):
        ev = Event(self.fixtureFoodOnly)
        self.assertIsInstance(ev, eventtypes.LidBolusRequestedMsg3)
        self.assertNotIsInstance(ev, RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureFoodOnly)
        self.assertEqual(ev.eventId, 66)
        self.assertEqual(ev.seqNum, 394643)

    def test_timestamp_preserves_wall_clock(self):
        ev = Event(self.fixtureFoodOnly)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-04-30T11:57:38")

    def test_food_only(self):
        ev = Event(self.fixtureFoodOnly)
        self.assertEqual(ev.bolusId, 1423)
        self.assertAlmostEqual(ev.foodBolusSize, 8.33)
        self.assertAlmostEqual(ev.correctionBolusSize, 0)
        self.assertAlmostEqual(ev.totalBolusSize, 8.330001)

    def test_food_and_correction(self):
        ev = Event(self.fixtureFoodAndCorrection)
        self.assertEqual(ev.bolusId, 1426)
        self.assertAlmostEqual(ev.foodBolusSize, 10.83)
        self.assertAlmostEqual(ev.correctionBolusSize, 0.13)
        self.assertAlmostEqual(ev.totalBolusSize, 10.96)

    def test_correction_only(self):
        ev = Event(self.fixtureCorrectionOnly)
        self.assertEqual(ev.bolusId, 1430)
        self.assertAlmostEqual(ev.foodBolusSize, 0)
        self.assertAlmostEqual(ev.correctionBolusSize, 1.47)
        self.assertAlmostEqual(ev.totalBolusSize, 3)

    def test_total_only(self):
        ev = Event(self.fixtureTotalOnly)
        self.assertEqual(ev.bolusId, 1424)
        self.assertAlmostEqual(ev.foodBolusSize, 0)
        self.assertAlmostEqual(ev.correctionBolusSize, 0)
        self.assertAlmostEqual(ev.totalBolusSize, 4)

    def test_todict_json_serializable(self):
        for fixture in (self.fixtureFoodOnly, self.fixtureFoodAndCorrection,
                        self.fixtureCorrectionOnly, self.fixtureTotalOnly):
            ev = Event(fixture)
            d = ev.todict()
            json.dumps(d)  # must not raise
            self.assertEqual(d["id"], 66)
            self.assertEqual(d["name"], "LID_BOLUS_REQUESTED_MSG3")


if __name__ == "__main__":
    unittest.main()
