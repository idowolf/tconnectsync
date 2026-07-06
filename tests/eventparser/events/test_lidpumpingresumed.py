#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidPumpingResumed(unittest.TestCase):
    """12: LID_PUMPING_RESUMED. Real captures all share preResumeState:100 and
    only differ in insulinAmount; two fixtures show that field varying."""
    maxDiff = None

    def setUp(self):
        # Real captured pump-log events (verbatim).
        self.fixtureA = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 12,
            "sequenceGroup": 0,
            "sequenceNumber": 394429,
            "pumpDateTime": "2026-04-30T10:16:31",
            "eventProperties": {"preResumeState": 100, "insulinAmount": 105},
            "estimatedDateTime": "2026-04-30T10:16:31Z",
        }
        self.fixtureB = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 12,
            "sequenceGroup": 0,
            "sequenceNumber": 478545,
            "pumpDateTime": "2026-05-24T11:41:19",
            "eventProperties": {"preResumeState": 100, "insulinAmount": 13},
            "estimatedDateTime": "2026-05-24T11:41:19Z",
        }

    def test_dispatches_to_correct_class(self):
        self.assertIsInstance(Event(self.fixtureA), eventtypes.LidPumpingResumed)
        self.assertNotIsInstance(Event(self.fixtureA), RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureA)
        self.assertEqual(ev.eventId, 12)
        self.assertEqual(ev.seqNum, 394429)

    def test_timestamp_preserves_wall_clock(self):
        ev = Event(self.fixtureA)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-04-30T10:16:31")

    def test_plain_fields(self):
        ev = Event(self.fixtureA)
        self.assertEqual(ev.preResumeState, 100)
        self.assertEqual(ev.insulinAmount, 105)

    def test_insulin_amount_varies_across_captures(self):
        self.assertEqual(Event(self.fixtureA).insulinAmount, 105)
        self.assertEqual(Event(self.fixtureB).insulinAmount, 13)
        # preResumeState is constant across real captures.
        self.assertEqual(Event(self.fixtureB).preResumeState, 100)

    def test_todict_is_json_serializable(self):
        ev = Event(self.fixtureB)
        d = ev.todict()
        json.dumps(d)  # must not raise
        self.assertEqual(d["id"], 12)
        self.assertEqual(d["name"], "LID_PUMPING_RESUMED")
        self.assertEqual(d["seqNum"], 478545)
        self.assertEqual(d["preResumeState"], 100)
        self.assertEqual(d["insulinAmount"], 13)


if __name__ == "__main__":
    unittest.main()
