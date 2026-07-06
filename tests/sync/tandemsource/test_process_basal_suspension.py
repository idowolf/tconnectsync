#!/usr/bin/env python3

import unittest

from tconnectsync.sync.tandemsource.process_basal_suspension import ProcessBasalSuspension
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.generic import Events

from ...api.fake import TConnectApi
from ...nightscout_fake import NightscoutApi

# Real captured LID_PUMPING_SUSPENDED (eventCode 11) events
# (deviceAssignmentId redacted). Captures only contain suspendReason 0 (UserAborted).
SUSPEND_1 = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 11,
    "sequenceGroup": 0,
    "sequenceNumber": 447946,
    "pumpDateTime": "2026-05-15T23:39:19",
    "eventProperties": {"preSuspendState": 106, "insulinAmount": 55, "suspendReason": 0, "rpaTimeout": 15},
    "estimatedDateTime": "2026-05-15T23:39:19Z",
}

SUSPEND_2 = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 11,
    "sequenceGroup": 0,
    "sequenceNumber": 452900,
    "pumpDateTime": "2026-05-17T09:19:36",
    "eventProperties": {"preSuspendState": 106, "insulinAmount": 95, "suspendReason": 0, "rpaTimeout": 15},
    "estimatedDateTime": "2026-05-17T09:19:36Z",
}


class TestProcessBasalSuspension(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tconnect = TConnectApi()
        self.nightscout = NightscoutApi()
        self.process = ProcessBasalSuspension(self.tconnect, self.nightscout, 'abcdef', pretend=False)
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: None

    def test_single_suspension(self):
        events = list(Events([dict(SUSPEND_1)]))
        self.assertEqual(type(events[0]), eventtypes.LidPumpingSuspended)
        self.assertEqual(events[0].suspendReason, eventtypes.LidPumpingSuspended.SuspendreasonEnum.UserAborted)

        p = self.process.process(events, None, None)

        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], {
            'eventType': 'Basal Suspension',
            'reason': 'UserAborted',
            'notes': 'UserAborted',
            'created_at': '2026-05-15 23:39:19-04:00',
            'enteredBy': 'Pump (tconnectsync)',
            'pump_event_id': '447946',
        })
        # Suspensions carry no duration.
        self.assertNotIn('duration', p[0])

    def test_two_suspensions_sorted(self):
        # Pass out of order; expect time-sorted output.
        p = self.process.process(list(Events([dict(SUSPEND_2), dict(SUSPEND_1)])), None, None)

        self.assertEqual(len(p), 2)
        self.assertEqual(p[0]['pump_event_id'], '447946')
        self.assertEqual(p[0]['created_at'], '2026-05-15 23:39:19-04:00')
        self.assertEqual(p[1]['pump_event_id'], '452900')
        self.assertEqual(p[1]['created_at'], '2026-05-17 09:19:36-04:00')

    def test_dedup_inclusive_boundary(self):
        # last upload at first event's time -> only strictly-later events emitted.
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: {
            'created_at': '2026-05-15 23:39:19-04:00'
        }

        p = self.process.process(list(Events([dict(SUSPEND_1), dict(SUSPEND_2)])), None, None)

        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]['pump_event_id'], '452900')


if __name__ == '__main__':
    unittest.main()
