#!/usr/bin/env python3

import unittest
import arrow

from tconnectsync.sync.tandemsource.process_user_mode import ProcessUserMode
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.generic import Event, Events

from ...api.fake import TConnectApi
from ...nightscout_fake import NightscoutApi

class TestProcessUserModeSleep(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tconnect = TConnectApi()
        self.nightscout = NightscoutApi()
        self.tconnect_device_id = 'abcdef'
        self.process = ProcessUserMode(self.tconnect, self.nightscout, self.tconnect_device_id, pretend=False)

    def test_single_start_sleep_active(self):
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: None

        events = [
            # 2024-12-04 23:00:23-05:00 - sleep start
            Event(b'\x00\xe5\x1f\xd7\\\x87\x00\x10\t\xaa\x00\x01\x00\x01\x00\x00\x01\x00\x00\xf0\x01\x01\x00\x00\x00\x00')
        ]

        self.assertEqual(type(events[0]), eventtypes.LidAaUserModeChange)
        self.assertEqual(events[0].previousUserMode, eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Normal)
        self.assertEqual(events[0].currentUserMode, eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Sleeping)
        self.assertEqual(events[0].requestedAction, eventtypes.LidAaUserModeChange.RequestedactionEnum.StartSleep)

        time_end = arrow.get('2024-12-04T23:00:30-05:00')
        p = self.process.process(events, time_start=None, time_end=time_end)

        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], {
            "eventType": 'Sleep',
            "reason": 'Sleep (Scheduled) - Not Ended',
            "notes": 'Sleep (Scheduled) - Not Ended',
            "duration": 0.11666666666666667,
            "created_at": '2024-12-04 23:00:23-05:00',
            "enteredBy": "Pump (tconnectsync)",
            "pump_event_id": '1051050'
        })
        self.assertEqual(self.nightscout.deleted_entries, [])

    def test_single_stop_sleep_no_last_uploaded(self):
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: None

        events = [
            # 2024-12-04 09:01:23-05:00 - sleep end
            Event(b'\x00\xe5\x1f\xd6\x97\xe3\x00\x0f\xfe\xb0\x00\x02\x01\x00\x00\x00\x00\x00\x00\xf0\x01\x01\x00\x00\x00\x00')
        ]

        self.assertEqual(type(events[0]), eventtypes.LidAaUserModeChange)
        self.assertEqual(events[0].previousUserMode, eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Sleeping)
        self.assertEqual(events[0].currentUserMode, eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Normal)
        self.assertEqual(events[0].requestedAction, eventtypes.LidAaUserModeChange.RequestedactionEnum.StopSleep)

        time_end = arrow.get('2024-12-04T23:00:30-05:00')
        p = self.process.process(events, time_start=None, time_end=time_end)

        self.assertEqual(len(p), 0)
        self.assertEqual(self.nightscout.deleted_entries, [])


    def test_start_and_stop_sleep(self):
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: None

        events = [
            # 2024-12-04 23:00:23-05:00 - sleep start
            Event(b'\x00\xe5\x1f\xd7\\\x87\x00\x10\t\xaa\x00\x01\x00\x01\x00\x00\x01\x00\x00\xf0\x01\x01\x00\x00\x00\x00'),
            # 2024-12-05 09:01:23-05:00 - sleep end
            Event(b'\x00\xe5\x1f\xd7\xe9c\x00\x10\x10\xf8\x00\x02\x01\x00\x00\x00\x00\x00\x00\xf0\x01\x01\x00\x00\x00\x00')
        ]

        self.assertEqual(type(events[0]), eventtypes.LidAaUserModeChange)
        self.assertEqual(events[0].previousUserMode, eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Normal)
        self.assertEqual(events[0].currentUserMode, eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Sleeping)
        self.assertEqual(events[0].requestedAction, eventtypes.LidAaUserModeChange.RequestedactionEnum.StartSleep)


        self.assertEqual(type(events[1]), eventtypes.LidAaUserModeChange)
        self.assertEqual(events[1].previousUserMode, eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Sleeping)
        self.assertEqual(events[1].currentUserMode, eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Normal)
        self.assertEqual(events[1].requestedAction, eventtypes.LidAaUserModeChange.RequestedactionEnum.StopSleep)

        time_end = arrow.get('2024-12-05T10:00:00-05:00')
        p = self.process.process(events, time_start=None, time_end=time_end)

        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], {
            "eventType": 'Sleep',
            "reason": 'Sleep (Scheduled)',
            "notes": 'Sleep (Scheduled)',
            "duration": 601.0,
            "created_at": '2024-12-04 23:00:23-05:00',
            "enteredBy": "Pump (tconnectsync)",
            "pump_event_id": '1051050,1052920'
        })
        self.assertEqual(self.nightscout.deleted_entries, [])

    def test_stop_with_partial_last_uploaded(self):
        self.nightscout.last_uploaded_entry = lambda eventType, **kwargs: {
            'Sleep': {
                "eventType": 'Sleep',
                "reason": 'Sleep (Scheduled) - Not Ended',
                "notes": 'Sleep (Scheduled) - Not Ended',
                "duration": 0.11666666666666667,
                "created_at": '2024-12-04 23:00:23-05:00',
                "enteredBy": "Pump (tconnectsync)",
                "pump_event_id": '1051050',
                "_id": "id_to_delete"
            }
        }.get(eventType)

        events = [
            # 2024-12-05 09:01:23-05:00 - sleep end
            Event(b'\x00\xe5\x1f\xd7\xe9c\x00\x10\x10\xf8\x00\x02\x01\x00\x00\x00\x00\x00\x00\xf0\x01\x01\x00\x00\x00\x00')
        ]

        self.assertEqual(type(events[0]), eventtypes.LidAaUserModeChange)
        self.assertEqual(events[0].previousUserMode, eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Sleeping)
        self.assertEqual(events[0].currentUserMode, eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Normal)
        self.assertEqual(events[0].requestedAction, eventtypes.LidAaUserModeChange.RequestedactionEnum.StopSleep)

        time_end = arrow.get('2024-12-05T10:00:00-05:00')
        p = self.process.process(events, time_start=None, time_end=time_end)

        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], {
            "eventType": 'Sleep',
            "reason": 'Sleep (Scheduled)',
            "notes": 'Sleep (Scheduled)',
            "duration": 601.0,
            "created_at": '2024-12-04 23:00:23-05:00',
            "enteredBy": "Pump (tconnectsync)",
            "pump_event_id": '1051050,1052920'
        })
        self.assertEqual(self.nightscout.deleted_entries, ['treatments/id_to_delete'])


class TestProcessUserModeExercise(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tconnect = TConnectApi()
        self.nightscout = NightscoutApi()
        self.tconnect_device_id = 'abcdef'
        self.process = ProcessUserMode(self.tconnect, self.nightscout, self.tconnect_device_id, pretend=False)

    def test_single_start_exercise_active(self):
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: None

        events = [
            # 2024-12-04 23:00:23-05:00 - exercise start
            Event(b'\x00\xe5\x1f\xd7\\\x87\x00\x10\t\xaa\x00\x03\x00\x02\x00\x00\x01\x00\x00\xf0\x00\x01\x00\x00\x00\x00'),
        ]

        self.assertEqual(type(events[0]), eventtypes.LidAaUserModeChange)
        self.assertEqual(events[0].previousUserMode, eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Normal)
        self.assertEqual(events[0].currentUserMode, eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Exercising)
        self.assertEqual(events[0].requestedAction, eventtypes.LidAaUserModeChange.RequestedactionEnum.StartExercise)

        time_end = arrow.get('2024-12-04T23:00:30-05:00')
        p = self.process.process(events, time_start=None, time_end=time_end)

        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], {
            "eventType": 'Exercise',
            "reason": 'Exercise - Not Ended',
            "notes": 'Exercise - Not Ended',
            "duration": 0.11666666666666667,
            "created_at": '2024-12-04 23:00:23-05:00',
            "enteredBy": "Pump (tconnectsync)",
            "pump_event_id": '1051050'
        })
        self.assertEqual(self.nightscout.deleted_entries, [])

    def test_single_stop_exercise_no_last_uploaded(self):
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: None

        events = [
            # 2024-12-04 09:01:23-05:00 - exercise end
            Event(b'\x00\xe5\x1f\xd6\x97\xe3\x00\x0f\xfe\xb0\x00\x04\x02\x00\x00\x00\x00\x00\x00\xf0\x01\x03\x00\x00\x00\x00')
        ]

        self.assertEqual(type(events[0]), eventtypes.LidAaUserModeChange)
        self.assertEqual(events[0].previousUserMode, eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Exercising)
        self.assertEqual(events[0].currentUserMode, eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Normal)
        self.assertEqual(events[0].requestedAction, eventtypes.LidAaUserModeChange.RequestedactionEnum.StopExercise)

        time_end = arrow.get('2024-12-04T23:00:30-05:00')
        p = self.process.process(events, time_start=None, time_end=time_end)

        self.assertEqual(len(p), 0)
        self.assertEqual(self.nightscout.deleted_entries, [])


    def test_start_and_stop_exercise(self):
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: None

        events = [
            # 2024-12-04 23:00:23-05:00 - exercise start
            Event(b'\x00\xe5\x1f\xd7\\\x87\x00\x10\t\xaa\x00\x03\x00\x02\x00\x00\x01\x00\x00\xf0\x00\x01\x00\x00\x00\x00'),
            # 2024-12-05 09:01:23-05:00 - exercise end
            Event(b'\x00\xe5\x1f\xd7\xe9c\x00\x10\x10\xf8\x00\x04\x02\x00\x00\x00\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x00')
        ]

        self.assertEqual(type(events[0]), eventtypes.LidAaUserModeChange)
        self.assertEqual(events[0].previousUserMode, eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Normal)
        self.assertEqual(events[0].currentUserMode, eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Exercising)
        self.assertEqual(events[0].requestedAction, eventtypes.LidAaUserModeChange.RequestedactionEnum.StartExercise)


        self.assertEqual(type(events[1]), eventtypes.LidAaUserModeChange)
        self.assertEqual(events[1].previousUserMode, eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Exercising)
        self.assertEqual(events[1].currentUserMode, eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Normal)
        self.assertEqual(events[1].requestedAction, eventtypes.LidAaUserModeChange.RequestedactionEnum.StopExercise)

        time_end = arrow.get('2024-12-05T10:00:00-05:00')
        p = self.process.process(events, time_start=None, time_end=time_end)

        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], {
            "eventType": 'Exercise',
            "reason": 'Exercise',
            "notes": 'Exercise',
            "duration": 601.0,
            "created_at": '2024-12-04 23:00:23-05:00',
            "enteredBy": "Pump (tconnectsync)",
            "pump_event_id": '1051050,1052920'
        })
        self.assertEqual(self.nightscout.deleted_entries, [])

    def test_stop_with_partial_last_uploaded(self):
        self.nightscout.last_uploaded_entry = lambda eventType, **kwargs: {
            'Exercise': {
                "eventType": 'Exercise',
                "reason": 'Exercise - Not Ended',
                "notes": 'Exercise - Not Ended',
                "duration": 0.11666666666666667,
                "created_at": '2024-12-04 23:00:23-05:00',
                "enteredBy": "Pump (tconnectsync)",
                "pump_event_id": '1051050',
                "_id": 'id_to_delete'
            }
        }.get(eventType)

        events = [
            # 2024-12-05 09:01:23-05:00 - exercise end
            Event(b'\x00\xe5\x1f\xd7\xe9c\x00\x10\x10\xf8\x00\x04\x02\x00\x00\x00\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x00')
        ]

        self.assertEqual(type(events[0]), eventtypes.LidAaUserModeChange)
        self.assertEqual(events[0].previousUserMode, eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Exercising)
        self.assertEqual(events[0].currentUserMode, eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Normal)
        self.assertEqual(events[0].requestedAction, eventtypes.LidAaUserModeChange.RequestedactionEnum.StopExercise)

        time_end = arrow.get('2024-12-05T10:00:00-05:00')
        p = self.process.process(events, time_start=None, time_end=time_end)

        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], {
            "eventType": 'Exercise',
            "reason": 'Exercise',
            "notes": 'Exercise',
            "duration": 601.0,
            "created_at": '2024-12-04 23:00:23-05:00',
            "enteredBy": "Pump (tconnectsync)",
            "pump_event_id": '1051050,1052920'
        })
        self.assertEqual(self.nightscout.deleted_entries, ['treatments/id_to_delete'])



# Real captured LID_AA_USER_MODE_CHANGE (eventCode 229) events
# (deviceAssignmentId redacted).
SLEEP_START = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 229,
    "sequenceGroup": 0,
    "sequenceNumber": 456855,
    "pumpDateTime": "2026-05-18T10:16:00",
    "estimatedDateTime": "2026-05-18T10:16:00Z",
    "eventProperties": {
        "currentUserMode": 1, "previousUserMode": 0, "requestedAction": 1,
        "spareA3": 0, "sleepStartedByGui": 1, "activeSleepSchedule": [0],
        "spareB6": 0, "exerciseStoppedByTimer": 0, "exerciseChoice": 0,
        "exerciseTime": 0, "eatingSoonStoppedByTimer": 0,
    },
}

SLEEP_STOP = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 229,
    "sequenceGroup": 0,
    "sequenceNumber": 456952,
    "pumpDateTime": "2026-05-18T10:19:55",
    "estimatedDateTime": "2026-05-18T10:19:55Z",
    "eventProperties": {
        "currentUserMode": 0, "previousUserMode": 1, "requestedAction": 2,
        "spareA3": 0, "sleepStartedByGui": 1, "activeSleepSchedule": [0],
        "spareB6": 0, "exerciseStoppedByTimer": 0, "exerciseChoice": 0,
        "exerciseTime": 0, "eatingSoonStoppedByTimer": 0,
    },
}

EXERCISE_START = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 229,
    "sequenceGroup": 0,
    "sequenceNumber": 456961,
    "pumpDateTime": "2026-05-18T10:20:04",
    "estimatedDateTime": "2026-05-18T10:20:04Z",
    "eventProperties": {
        "currentUserMode": 2, "previousUserMode": 0, "requestedAction": 3,
        "spareA3": 0, "sleepStartedByGui": 0, "activeSleepSchedule": [],
        "spareB6": 0, "exerciseStoppedByTimer": 0, "exerciseChoice": 0,
        "exerciseTime": 0, "eatingSoonStoppedByTimer": 0,
    },
}

EXERCISE_STOP = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 229,
    "sequenceGroup": 0,
    "sequenceNumber": 456965,
    "pumpDateTime": "2026-05-18T10:20:15",
    "estimatedDateTime": "2026-05-18T10:20:15Z",
    "eventProperties": {
        "currentUserMode": 1, "previousUserMode": 2, "requestedAction": 4,
        "spareA3": 0, "sleepStartedByGui": 0, "activeSleepSchedule": [0],
        "spareB6": 0, "exerciseStoppedByTimer": 0, "exerciseChoice": 0,
        "exerciseTime": 0, "eatingSoonStoppedByTimer": 0,
    },
}


class TestProcessUserModeJson(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tconnect = TConnectApi()
        self.nightscout = NightscoutApi()
        self.process = ProcessUserMode(self.tconnect, self.nightscout, 'abcdef', pretend=False)
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: None

    def test_sleep_and_exercise_pairs(self):
        events = list(Events([dict(SLEEP_START), dict(SLEEP_STOP), dict(EXERCISE_START), dict(EXERCISE_STOP)]))
        p = self.process.process(events, time_start=None, time_end=None)

        self.assertEqual(len(p), 2)

        self.assertEqual(p[0]['eventType'], 'Sleep')
        self.assertEqual(p[0]['reason'], 'Sleep (Manual)')
        self.assertEqual(p[0]['pump_event_id'], '456855,456952')
        self.assertEqual(p[0]['created_at'], '2026-05-18 10:16:00-04:00')
        self.assertAlmostEqual(p[0]['duration'], 3.9166666666666665)

        self.assertEqual(p[1]['eventType'], 'Exercise')
        self.assertEqual(p[1]['pump_event_id'], '456961,456965')
        self.assertEqual(p[1]['created_at'], '2026-05-18 10:20:04-04:00')
        self.assertAlmostEqual(p[1]['duration'], 0.18333333333333332)


if __name__ == '__main__':
    unittest.main()