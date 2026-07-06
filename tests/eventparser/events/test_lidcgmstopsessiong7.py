#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidCgmStopSessionG7(unittest.TestCase):
    """447: LID_CGM_STOP_SESSION_G7. sessionStopReason is a plain int (no enum
    in the generated class), so it round-trips as its captured value. Fixtures
    are real captured events copied verbatim, one per distinct stop reason."""
    maxDiff = None

    def setUp(self):
        # sessionStopReason=5 with a real stop time and stopSessionCode=1.
        self.fixtureReason5 = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 447,
            "sequenceGroup": 0,
            "sequenceNumber": 413840,
            "pumpDateTime": "2026-05-06T01:53:10",
            "eventProperties": {
                "currentTransmitterTime": 890598, "sessionStartTime": 73,
                "sessionStopTime": 890591, "sessionDuration": 10,
                "sessionStopReason": 5, "stopSessionCode": 1,
            },
            "estimatedDateTime": "2026-05-06T01:53:10Z",
        }
        # sessionStopReason=16 with zero stop time / code.
        self.fixtureReason16 = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 447,
            "sequenceGroup": 0,
            "sequenceNumber": 449816,
            "pumpDateTime": "2026-05-16T12:38:30",
            "eventProperties": {
                "currentTransmitterTime": 905595, "sessionStartTime": 72,
                "sessionStopTime": 0, "sessionDuration": 10,
                "sessionStopReason": 16, "stopSessionCode": 0,
            },
            "estimatedDateTime": "2026-05-16T12:38:30Z",
        }
        # sessionStopReason=15 with a UINT32-max sessionStartTime sentinel.
        self.fixtureReason15 = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 447,
            "sequenceGroup": 0,
            "sequenceNumber": 481653,
            "pumpDateTime": "2026-05-25T08:35:32",
            "eventProperties": {
                "currentTransmitterTime": 814740, "sessionStartTime": 4294967295,
                "sessionStopTime": 0, "sessionDuration": 10,
                "sessionStopReason": 15, "stopSessionCode": 0,
            },
            "estimatedDateTime": "2026-05-25T08:35:32Z",
        }

    def test_dispatches_to_lidcgmstopsessiong7(self):
        ev = Event(self.fixtureReason5)
        self.assertIsInstance(ev, eventtypes.LidCgmStopSessionG7)
        self.assertIsNot(type(ev), RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureReason5)
        self.assertEqual(ev.eventId, 447)
        self.assertEqual(ev.seqNum, 413840)
        # eventTimestamp keeps pumpDateTime's wall-clock.
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-05-06T01:53:10")

    def test_session_time_fields_round_trip(self):
        ev = Event(self.fixtureReason5)
        self.assertEqual(ev.currentTransmitterTime, 890598)
        self.assertEqual(ev.sessionStartTime, 73)
        self.assertEqual(ev.sessionStopTime, 890591)
        self.assertEqual(ev.sessionDuration, 10)
        self.assertEqual(ev.stopSessionCode, 1)

    def test_session_start_time_sentinel_round_trips(self):
        # UINT32-max sentinel must survive as-is.
        ev = Event(self.fixtureReason15)
        self.assertEqual(ev.sessionStartTime, 4294967295)
        self.assertEqual(ev.sessionStopTime, 0)
        self.assertEqual(ev.stopSessionCode, 0)

    def test_session_stop_reason_is_raw_int(self):
        # No enum is generated for sessionStopReason; it stays the captured int.
        self.assertFalse(hasattr(eventtypes.LidCgmStopSessionG7,
                                 "SessionstopreasonEnum"))
        self.assertEqual(Event(self.fixtureReason5).sessionStopReason, 5)
        self.assertEqual(Event(self.fixtureReason16).sessionStopReason, 16)
        self.assertEqual(Event(self.fixtureReason15).sessionStopReason, 15)

    def test_todict_is_json_serializable(self):
        for fixture in (self.fixtureReason5, self.fixtureReason16,
                        self.fixtureReason15):
            d = Event(fixture).todict()
            json.dumps(d)  # must not raise
            self.assertEqual(d["id"], 447)
            self.assertEqual(d["name"], "LID_CGM_STOP_SESSION_G7")
            self.assertEqual(
                d["sessionStopReason"],
                fixture["eventProperties"]["sessionStopReason"])


if __name__ == "__main__":
    unittest.main()
