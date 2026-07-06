#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidTimeChanged(unittest.TestCase):
    """13: LID_TIME_CHANGED. Real captures from the clockChanges array.
    timePrior/timeAfter are ms-of-day; compare them to see whether the clock
    moved forward or backward."""
    maxDiff = None

    def setUp(self):
        # Real capture: clock moved forward (timeAfter > timePrior).
        self.fixtureForward = {
            "deviceAssignmentId": "73aeb403-1d22-4d12-a3fd-229e5b6641ee",
            "eventCode": 13,
            "sequenceGroup": 0,
            "sequenceNumber": 182932,
            "pumpDateTime": "2025-09-11T10:28:11",
            "eventProperties": {
                "timePrior": 12513657, "timeAfter": 37691000,
                "rawRtcTime": 1380540797,
            },
            "estimatedDateTime": "2025-09-11T10:28:11Z",
        }
        # Real capture: clock moved backward (timeAfter < timePrior).
        self.fixtureBackward = {
            "deviceAssignmentId": "73aeb403-1d22-4d12-a3fd-229e5b6641ee",
            "eventCode": 13,
            "sequenceGroup": 0,
            "sequenceNumber": 364365,
            "pumpDateTime": "2025-11-02T15:27:37",
            "eventProperties": {
                "timePrior": 59278139, "timeAfter": 55657000,
                "rawRtcTime": 1625159580,
            },
            "estimatedDateTime": "2025-11-02T15:27:37Z",
        }

    def test_dispatches_to_lidtimechanged(self):
        self.assertIsInstance(Event(self.fixtureForward), eventtypes.LidTimeChanged)
        self.assertIsInstance(Event(self.fixtureBackward), eventtypes.LidTimeChanged)
        self.assertNotIsInstance(Event(self.fixtureForward), RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureForward)
        self.assertEqual(ev.eventId, 13)
        self.assertEqual(ev.seqNum, 182932)

        ev = Event(self.fixtureBackward)
        self.assertEqual(ev.eventId, 13)
        self.assertEqual(ev.seqNum, 364365)

    def test_timestamp_preserves_wall_clock(self):
        # eventTimestamp keeps pumpDateTime's wall-clock (tz forced to the
        # configured TIMEZONE_NAME), so the naive portion round-trips exactly.
        ev = Event(self.fixtureForward)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'), "2025-09-11T10:28:11")

        ev = Event(self.fixtureBackward)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'), "2025-11-02T15:27:37")

    def test_time_fields_round_trip(self):
        ev = Event(self.fixtureForward)
        self.assertEqual(ev.timePrior, 12513657)
        self.assertEqual(ev.timeAfter, 37691000)
        self.assertEqual(ev.rawRtcTime, 1380540797)

        ev = Event(self.fixtureBackward)
        self.assertEqual(ev.timePrior, 59278139)
        self.assertEqual(ev.timeAfter, 55657000)
        self.assertEqual(ev.rawRtcTime, 1625159580)

    def test_forward_and_backward_direction(self):
        # timeAfter > timePrior means the clock jumped forward, and vice versa.
        fwd = Event(self.fixtureForward)
        self.assertGreater(fwd.timeAfter, fwd.timePrior)

        bwd = Event(self.fixtureBackward)
        self.assertLess(bwd.timeAfter, bwd.timePrior)

    def test_todict_is_json_serializable(self):
        for fixture in (self.fixtureForward, self.fixtureBackward):
            ev = Event(fixture)
            d = ev.todict()
            json.dumps(d)  # must not raise
            self.assertEqual(d["id"], 13)
            self.assertEqual(d["name"], "LID_TIME_CHANGED")
            self.assertEqual(d["timePrior"], fixture["eventProperties"]["timePrior"])
            self.assertEqual(d["timeAfter"], fixture["eventProperties"]["timeAfter"])
            self.assertEqual(d["rawRtcTime"], fixture["eventProperties"]["rawRtcTime"])


if __name__ == "__main__":
    unittest.main()
