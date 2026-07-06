#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidDateChanged(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        # Real captured code-14 (LID_DATE_CHANGED) events, copied verbatim from
        # the clockChanges arrays of pump-log responses.

        # datePrior == dateAfter: a resync that did not move the day.
        self.fixtureEqual = {
            "deviceAssignmentId": "73aeb403-1d22-4d12-a3fd-229e5b6641ee",
            "eventCode": 14,
            "sequenceGroup": 0,
            "sequenceNumber": 364364,
            "pumpDateTime": "2025-11-02T16:27:58",
            "eventProperties": {"datePrior": 6515, "dateAfter": 6515, "rawRtcTime": 1625159578},
            "estimatedDateTime": "2025-11-02T16:27:58Z",
        }

        # datePrior != dateAfter by one day: a small clock adjustment.
        self.fixtureOffByOne = {
            "deviceAssignmentId": "73aeb403-1d22-4d12-a3fd-229e5b6641ee",
            "eventCode": 14,
            "sequenceGroup": 0,
            "sequenceNumber": 418774,
            "pumpDateTime": "2025-11-18T22:55:04",
            "eventProperties": {"datePrior": 6530, "dateAfter": 6531, "rawRtcTime": 2958809165},
            "estimatedDateTime": "2025-11-18T22:55:04Z",
        }

        # Large jump (initial date set): datePrior far from dateAfter.
        self.fixtureLargeJump = {
            "deviceAssignmentId": "73aeb403-1d22-4d12-a3fd-229e5b6641ee",
            "eventCode": 14,
            "sequenceGroup": 0,
            "sequenceNumber": 95,
            "pumpDateTime": "2025-07-20T04:38:28",
            "eventProperties": {"datePrior": 4394, "dateAfter": 6410, "rawRtcTime": 1089120495},
            "estimatedDateTime": "2025-07-20T04:38:28Z",
        }

    def test_dispatches_to_liddatechanged(self):
        for fx in (self.fixtureEqual, self.fixtureOffByOne, self.fixtureLargeJump):
            ev = Event(fx)
            self.assertIsInstance(ev, eventtypes.LidDateChanged)
            self.assertNotIsInstance(ev, RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureOffByOne)
        self.assertEqual(ev.eventId, 14)
        self.assertEqual(ev.seqNum, 418774)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'), "2025-11-18T22:55:04")

    def test_equal_dates_round_trip(self):
        ev = Event(self.fixtureEqual)
        self.assertEqual(ev.datePrior, 6515)
        self.assertEqual(ev.dateAfter, 6515)
        self.assertEqual(ev.rawRtcTime, 1625159578)

    def test_off_by_one_dates_round_trip(self):
        ev = Event(self.fixtureOffByOne)
        self.assertEqual(ev.datePrior, 6530)
        self.assertEqual(ev.dateAfter, 6531)
        self.assertEqual(ev.rawRtcTime, 2958809165)

    def test_large_jump_dates_round_trip(self):
        ev = Event(self.fixtureLargeJump)
        self.assertEqual(ev.datePrior, 4394)
        self.assertEqual(ev.dateAfter, 6410)
        self.assertEqual(ev.rawRtcTime, 1089120495)

    def test_todict_is_json_serializable(self):
        for fx in (self.fixtureEqual, self.fixtureOffByOne, self.fixtureLargeJump):
            ev = Event(fx)
            d = ev.todict()
            json.dumps(d)  # must not raise
            self.assertEqual(d["id"], 14)
            self.assertEqual(d["name"], "LID_DATE_CHANGED")
            self.assertEqual(d["seqNum"], fx["sequenceNumber"])
            self.assertEqual(d["datePrior"], fx["eventProperties"]["datePrior"])
            self.assertEqual(d["dateAfter"], fx["eventProperties"]["dateAfter"])
            self.assertEqual(d["rawRtcTime"], fx["eventProperties"]["rawRtcTime"])


if __name__ == "__main__":
    unittest.main()
