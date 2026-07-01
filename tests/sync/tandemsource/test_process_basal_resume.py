#!/usr/bin/env python3

import unittest

from tconnectsync.sync.tandemsource.process_basal_resume import ProcessBasalResume
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.generic import Events

from ...api.fake import TConnectApi
from ...nightscout_fake import NightscoutApi

# Real captured LID_PUMPING_RESUMED (eventCode 12) events
# (deviceAssignmentId redacted).
RESUME_1 = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 12,
    "sequenceGroup": 0,
    "sequenceNumber": 448183,
    "pumpDateTime": "2026-05-16T00:14:14",
    "eventProperties": {"preResumeState": 100, "insulinAmount": 180},
    "estimatedDateTime": "2026-05-16T00:14:14Z",
}

RESUME_2 = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 12,
    "sequenceGroup": 0,
    "sequenceNumber": 452993,
    "pumpDateTime": "2026-05-17T09:35:15",
    "eventProperties": {"preResumeState": 100, "insulinAmount": 85},
    "estimatedDateTime": "2026-05-17T09:35:15Z",
}


class TestProcessBasalResume(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tconnect = TConnectApi()
        self.nightscout = NightscoutApi()
        self.process = ProcessBasalResume(self.tconnect, self.nightscout, 'abcdef', pretend=False)
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: None

    def test_single_resume(self):
        events = list(Events([dict(RESUME_1)]))
        self.assertEqual(type(events[0]), eventtypes.LidPumpingResumed)

        p = self.process.process(events, None, None)

        self.assertEqual(len(p), 1)
        # reason/notes hardcoded; preResumeState/insulinAmount unused.
        self.assertDictEqual(p[0], {
            'eventType': 'Basal Resume',
            'reason': 'Basal resumed',
            'notes': 'Basal resumed',
            'created_at': '2026-05-16 00:14:14-04:00',
            'enteredBy': 'Pump (tconnectsync)',
            'pump_event_id': '448183'
        })

    def test_two_resumes_sorted(self):
        # Pass out of order; expect time-sorted output.
        p = self.process.process(list(Events([dict(RESUME_2), dict(RESUME_1)])), None, None)

        self.assertEqual(len(p), 2)
        self.assertDictEqual(p[0], {
            'eventType': 'Basal Resume',
            'reason': 'Basal resumed',
            'notes': 'Basal resumed',
            'created_at': '2026-05-16 00:14:14-04:00',
            'enteredBy': 'Pump (tconnectsync)',
            'pump_event_id': '448183'
        })
        self.assertDictEqual(p[1], {
            'eventType': 'Basal Resume',
            'reason': 'Basal resumed',
            'notes': 'Basal resumed',
            'created_at': '2026-05-17 09:35:15-04:00',
            'enteredBy': 'Pump (tconnectsync)',
            'pump_event_id': '452993'
        })

    def test_dedup_skips_at_or_before_last_upload(self):
        # Last upload at first event time -> only strictly-later emitted.
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: {
            'created_at': '2026-05-16 00:14:14-04:00'
        }

        p = self.process.process(list(Events([dict(RESUME_1), dict(RESUME_2)])), None, None)

        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], {
            'eventType': 'Basal Resume',
            'reason': 'Basal resumed',
            'notes': 'Basal resumed',
            'created_at': '2026-05-17 09:35:15-04:00',
            'enteredBy': 'Pump (tconnectsync)',
            'pump_event_id': '452993'
        })


if __name__ == '__main__':
    unittest.main()
