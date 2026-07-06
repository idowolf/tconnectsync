#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidTubingFilled(unittest.TestCase):
    """63: LID_TUBING_FILLED, parsed from real captured pump-log events.

    Every captured code-63 event carries primeSize=-1 (a sentinel, not a real
    fill volume) and completionStatus=3 (Completed); fixtures differ in
    seqNum/position/wall-clock.
    """
    maxDiff = None

    def setUp(self):
        # Real capture: primeSize sentinel (-1), completionStatus Completed (3).
        self.fixtureNegativePrimeSize = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 63,
            "sequenceGroup": 0,
            "sequenceNumber": 394428,
            "pumpDateTime": "2026-04-30T10:16:09",
            "eventProperties": {"primeSize": -1, "completionStatus": 3, "position": 631224},
            "estimatedDateTime": "2026-04-30T10:16:09Z",
        }
        # Second real capture with a different seqNum/position/timestamp.
        self.fixtureCompleted = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 63,
            "sequenceGroup": 0,
            "sequenceNumber": 401423,
            "pumpDateTime": "2026-05-02T12:27:17",
            "eventProperties": {"primeSize": -1, "completionStatus": 3, "position": 594056},
            "estimatedDateTime": "2026-05-02T12:27:17Z",
        }

    def test_dispatches_to_lidtubingfilled(self):
        ev = Event(self.fixtureNegativePrimeSize)
        self.assertIsInstance(ev, eventtypes.LidTubingFilled)
        self.assertNotIsInstance(ev, RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureNegativePrimeSize)
        self.assertEqual(ev.eventId, 63)
        self.assertEqual(ev.seqNum, 394428)
        self.assertEqual(ev.NAME, "LID_TUBING_FILLED")

    def test_timestamp_preserves_wall_clock(self):
        ev = Event(self.fixtureNegativePrimeSize)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-04-30T10:16:09")

    def test_negative_primesize_sentinel_round_trips(self):
        # -1 is a sentinel and must survive verbatim (not treated as missing).
        ev = Event(self.fixtureNegativePrimeSize)
        self.assertEqual(ev.primeSize, -1)

    def test_position_round_trips(self):
        ev = Event(self.fixtureNegativePrimeSize)
        self.assertEqual(ev.position, 631224)

    def test_completionstatus_resolves_to_completed(self):
        ev = Event(self.fixtureNegativePrimeSize)
        self.assertEqual(ev.completionStatusRaw, 3)
        self.assertEqual(ev.completionStatus,
                         eventtypes.LidTubingFilled.CompletionstatusEnum.Completed)

    def test_second_capture_distinct_values(self):
        ev = Event(self.fixtureCompleted)
        self.assertEqual(ev.seqNum, 401423)
        self.assertEqual(ev.position, 594056)
        self.assertEqual(ev.primeSize, -1)
        self.assertEqual(ev.completionStatus,
                         eventtypes.LidTubingFilled.CompletionstatusEnum.Completed)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-05-02T12:27:17")

    def test_todict_is_json_serializable(self):
        ev = Event(self.fixtureNegativePrimeSize)
        td = ev.todict()
        json.dumps(td)  # must not raise
        self.assertEqual(td["id"], 63)
        self.assertEqual(td["name"], "LID_TUBING_FILLED")
        self.assertEqual(td["seqNum"], 394428)
        self.assertEqual(td["primeSize"], -1)
        self.assertEqual(td["completionStatusRaw"], 3)
        self.assertEqual(td["position"], 631224)


if __name__ == "__main__":
    unittest.main()
