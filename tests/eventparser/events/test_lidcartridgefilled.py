#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidCartridgeFilled(unittest.TestCase):
    """33: LID_CARTRIDGE_FILLED. All fixtures are real captured pump-log
    events (verbatim). insulinVolume varies; v2Volume is always 0."""
    maxDiff = None

    def setUp(self):
        # Smallest observed insulinVolume.
        self.fixtureMin = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 33,
            "sequenceGroup": 0,
            "sequenceNumber": 418402,
            "pumpDateTime": "2026-05-07T10:35:59",
            "eventProperties": {"insulinVolume": 60, "v2Volume": 0},
            "estimatedDateTime": "2026-05-07T10:35:59Z",
        }
        # A mid-range fill.
        self.fixtureMid = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 33,
            "sequenceGroup": 0,
            "sequenceNumber": 394427,
            "pumpDateTime": "2026-04-30T10:16:09",
            "eventProperties": {"insulinVolume": 105, "v2Volume": 0},
            "estimatedDateTime": "2026-04-30T10:16:09Z",
        }
        # Largest observed insulinVolume.
        self.fixtureMax = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 33,
            "sequenceGroup": 0,
            "sequenceNumber": 463083,
            "pumpDateTime": "2026-05-20T02:15:04",
            "eventProperties": {"insulinVolume": 190, "v2Volume": 0},
            "estimatedDateTime": "2026-05-20T02:15:04Z",
        }

    def test_dispatches_to_lidcartridgefilled(self):
        ev = Event(self.fixtureMid)
        self.assertIsInstance(ev, eventtypes.LidCartridgeFilled)
        self.assertIsNot(type(ev), RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureMid)
        self.assertEqual(ev.eventId, 33)
        self.assertEqual(ev.seqNum, 394427)
        self.assertEqual(
            ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
            "2026-04-30T10:16:09")

    def test_insulinvolume_round_trips(self):
        self.assertEqual(Event(self.fixtureMin).insulinVolume, 60)
        self.assertEqual(Event(self.fixtureMid).insulinVolume, 105)
        self.assertEqual(Event(self.fixtureMax).insulinVolume, 190)

    def test_v2volume_round_trips(self):
        for fixture in (self.fixtureMin, self.fixtureMid, self.fixtureMax):
            self.assertEqual(Event(fixture).v2Volume, 0)

    def test_todict_is_json_serializable(self):
        for fixture in (self.fixtureMin, self.fixtureMid, self.fixtureMax):
            d = Event(fixture).todict()
            json.dumps(d)  # must not raise
            self.assertEqual(d["id"], 33)
            self.assertEqual(d["name"], "LID_CARTRIDGE_FILLED")

    def test_todict_reflects_real_values(self):
        d = Event(self.fixtureMax).todict()
        self.assertEqual(d["seqNum"], 463083)
        self.assertEqual(d["insulinVolume"], 190)
        self.assertEqual(d["v2Volume"], 0)


if __name__ == "__main__":
    unittest.main()
