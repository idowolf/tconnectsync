#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidBolusCompleted(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        # Real captured LID_BOLUS_COMPLETED (eventCode 20) events, verbatim.
        # completionStatus 3 -> Completed, insulinDelivered == insulinRequested.
        self.fixtureCompleted = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 20,
            "sequenceGroup": 0,
            "sequenceNumber": 394675,
            "pumpDateTime": "2026-04-30T12:01:53",
            "eventProperties": {
                "completionStatus": 3, "bolusId": 1423, "iob": 10.088287,
                "insulinDelivered": 8.33, "insulinRequested": 8.33,
            },
            "estimatedDateTime": "2026-04-30T12:01:53Z",
        }
        # completionStatus 0 -> UserAborted, an interrupted bolus where
        # insulinDelivered (0.04657) is far below insulinRequested (0.5).
        self.fixtureInterrupted = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 20,
            "sequenceGroup": 0,
            "sequenceNumber": 456849,
            "pumpDateTime": "2026-05-18T10:15:39",
            "eventProperties": {
                "completionStatus": 0, "bolusId": 1644, "iob": 1.2275107,
                "insulinDelivered": 0.04657, "insulinRequested": 0.5,
            },
            "estimatedDateTime": "2026-05-18T10:15:39Z",
        }

    def test_dispatches_to_lidboluscompleted(self):
        self.assertIsInstance(Event(self.fixtureCompleted), eventtypes.LidBolusCompleted)
        self.assertIsInstance(Event(self.fixtureInterrupted), eventtypes.LidBolusCompleted)
        self.assertNotIsInstance(Event(self.fixtureCompleted), RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureCompleted)
        self.assertEqual(ev.eventId, 20)
        self.assertEqual(ev.seqNum, 394675)
        # eventTimestamp keeps pumpDateTime's wall-clock.
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'), "2026-04-30T12:01:53")

    def test_completed_fields_round_trip(self):
        ev = Event(self.fixtureCompleted)
        self.assertEqual(ev.bolusId, 1423)
        self.assertAlmostEqual(ev.insulinDelivered, 8.33)
        self.assertAlmostEqual(ev.insulinRequested, 8.33)
        self.assertAlmostEqual(ev.iob, 10.088287)

    def test_interrupted_fields_round_trip(self):
        ev = Event(self.fixtureInterrupted)
        self.assertEqual(ev.bolusId, 1644)
        self.assertAlmostEqual(ev.insulinDelivered, 0.04657)
        self.assertAlmostEqual(ev.insulinRequested, 0.5)
        self.assertAlmostEqual(ev.iob, 1.2275107)
        # Interrupted: less insulin delivered than requested.
        self.assertLess(ev.insulinDelivered, ev.insulinRequested)

    def test_completionstatus_resolves_to_enum(self):
        completed = Event(self.fixtureCompleted)
        self.assertEqual(completed.completionStatusRaw, 3)
        self.assertEqual(completed.completionStatus,
                         eventtypes.LidBolusCompleted.CompletionstatusEnum.Completed)

        interrupted = Event(self.fixtureInterrupted)
        self.assertEqual(interrupted.completionStatusRaw, 0)
        self.assertEqual(interrupted.completionStatus,
                         eventtypes.LidBolusCompleted.CompletionstatusEnum.UserAborted)

    def test_todict_is_json_serializable(self):
        for fixture in (self.fixtureCompleted, self.fixtureInterrupted):
            ev = Event(fixture)
            d = ev.todict()
            json.dumps(d)  # must not raise
            self.assertEqual(d["id"], 20)
            self.assertEqual(d["name"], "LID_BOLUS_COMPLETED")


if __name__ == "__main__":
    unittest.main()
