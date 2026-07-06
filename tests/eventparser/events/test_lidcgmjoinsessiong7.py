#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidCgmJoinSessionG7(unittest.TestCase):
    """394 LID_CGM_JOIN_SESSION_G7: cgmTimestamp/sessionSignature are plain ints."""
    maxDiff = None

    def setUp(self):
        # Real captured pump-log events (values copied verbatim).
        self.fixtureLowCgmTs = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 394,
            "sequenceGroup": 0,
            "sequenceNumber": 413856,
            "pumpDateTime": "2026-05-06T01:53:28",
            "eventProperties": {"cgmTimestamp": 3042, "sessionSignature": 72},
            "estimatedDateTime": "2026-05-06T01:53:28Z",
        }
        self.fixtureHighCgmTs = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 394,
            "sequenceGroup": 0,
            "sequenceNumber": 449825,
            "pumpDateTime": "2026-05-16T12:38:39",
            "eventProperties": {"cgmTimestamp": 51767, "sessionSignature": 117},
            "estimatedDateTime": "2026-05-16T12:38:39Z",
        }
        self.fixtureSharedSignature = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 394,
            "sequenceGroup": 0,
            "sequenceNumber": 481763,
            "pumpDateTime": "2026-05-25T09:39:19",
            "eventProperties": {"cgmTimestamp": 248, "sessionSignature": 117},
            "estimatedDateTime": "2026-05-25T09:39:19Z",
        }

    def test_dispatches_to_correct_class(self):
        ev = Event(self.fixtureLowCgmTs)
        self.assertIsInstance(ev, eventtypes.LidCgmJoinSessionG7)
        self.assertNotIsInstance(ev, RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureLowCgmTs)
        self.assertEqual(ev.eventId, 394)
        self.assertEqual(ev.seqNum, 413856)

    def test_timestamp_preserves_wall_clock(self):
        ev = Event(self.fixtureLowCgmTs)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-05-06T01:53:28")

    def test_plain_fields_round_trip(self):
        ev = Event(self.fixtureLowCgmTs)
        self.assertEqual(ev.cgmTimestamp, 3042)
        self.assertEqual(ev.sessionSignature, 72)

    def test_high_cgm_timestamp_fixture(self):
        ev = Event(self.fixtureHighCgmTs)
        self.assertEqual(ev.eventId, 394)
        self.assertEqual(ev.seqNum, 449825)
        self.assertEqual(ev.cgmTimestamp, 51767)
        self.assertEqual(ev.sessionSignature, 117)

    def test_shared_signature_fixture(self):
        # Same sessionSignature as the high-cgm fixture but a distinct cgmTimestamp.
        ev = Event(self.fixtureSharedSignature)
        self.assertEqual(ev.seqNum, 481763)
        self.assertEqual(ev.cgmTimestamp, 248)
        self.assertEqual(ev.sessionSignature, 117)

    def test_todict_is_json_serializable(self):
        ev = Event(self.fixtureLowCgmTs)
        d = ev.todict()
        json.dumps(d)  # must not raise
        self.assertEqual(d["id"], 394)
        self.assertEqual(d["name"], "LID_CGM_JOIN_SESSION_G7")
        self.assertEqual(d["seqNum"], 413856)
        self.assertEqual(d["cgmTimestamp"], 3042)
        self.assertEqual(d["sessionSignature"], 72)


if __name__ == "__main__":
    unittest.main()
