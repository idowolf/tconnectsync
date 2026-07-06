#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidPumpingSuspended(unittest.TestCase):
    """11: LID_PUMPING_SUSPENDED. All real captures share suspendReason:0
    (UserAborted); only insulinAmount varies, so two captures suffice."""
    maxDiff = None

    def setUp(self):
        # Real captured pump-log events (verbatim), eventCode 11.
        self.fixtureA = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 11,
            "sequenceGroup": 0,
            "sequenceNumber": 394335,
            "pumpDateTime": "2026-04-30T10:01:49",
            "eventProperties": {
                "preSuspendState": 106, "insulinAmount": 120,
                "suspendReason": 0, "rpaTimeout": 15,
            },
            "estimatedDateTime": "2026-04-30T10:01:49Z",
        }
        self.fixtureB = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 11,
            "sequenceGroup": 0,
            "sequenceNumber": 401271,
            "pumpDateTime": "2026-05-02T11:49:43",
            "eventProperties": {
                "preSuspendState": 106, "insulinAmount": 150,
                "suspendReason": 0, "rpaTimeout": 15,
            },
            "estimatedDateTime": "2026-05-02T11:49:43Z",
        }

    def test_dispatches_to_correct_class(self):
        self.assertIsInstance(Event(self.fixtureA), eventtypes.LidPumpingSuspended)
        self.assertNotIsInstance(Event(self.fixtureA), RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureA)
        self.assertEqual(ev.eventId, 11)
        self.assertEqual(ev.seqNum, 394335)

    def test_timestamp_preserves_wall_clock(self):
        ev = Event(self.fixtureA)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-04-30T10:01:49")

    def test_plain_fields_round_trip(self):
        ev = Event(self.fixtureA)
        self.assertEqual(ev.preSuspendState, 106)
        self.assertEqual(ev.insulinAmount, 120)
        self.assertEqual(ev.rpaTimeout, 15)

    def test_suspendreason_resolves_to_enum(self):
        # suspendReason:0 -> UserAborted
        ev = Event(self.fixtureA)
        self.assertEqual(ev.suspendReasonRaw, 0)
        self.assertEqual(ev.suspendReason,
                         eventtypes.LidPumpingSuspended.SuspendreasonEnum.UserAborted)

    def test_second_capture_distinct_insulin_amount(self):
        ev = Event(self.fixtureB)
        self.assertEqual(ev.seqNum, 401271)
        self.assertEqual(ev.insulinAmount, 150)
        self.assertEqual(ev.suspendReason,
                         eventtypes.LidPumpingSuspended.SuspendreasonEnum.UserAborted)

    def test_todict_is_json_serializable(self):
        ev = Event(self.fixtureA)
        d = ev.todict()
        json.dumps(d)  # must not raise
        self.assertEqual(d["id"], 11)
        self.assertEqual(d["name"], "LID_PUMPING_SUSPENDED")
        self.assertEqual(d["insulinAmount"], 120)
        self.assertEqual(d["suspendReasonRaw"], 0)


if __name__ == "__main__":
    unittest.main()
