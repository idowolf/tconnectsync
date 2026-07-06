#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidAaUserModeChange(unittest.TestCase):
    """229 LID_AA_USER_MODE_CHANGE, from real captured pump-log events."""
    maxDiff = None

    def setUp(self):
        # Normal <- Sleeping, requestedAction StopSleep, activeSleepSchedule [0].
        self.fixtureStopSleep = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 229,
            "sequenceGroup": 0,
            "sequenceNumber": 456851,
            "pumpDateTime": "2026-05-18T10:15:53",
            "eventProperties": {
                "currentUserMode": 0, "previousUserMode": 1, "requestedAction": 2,
                "spareA3": 0, "sleepStartedByGui": 1, "activeSleepSchedule": [0],
                "spareB6": 0, "exerciseStoppedByTimer": 0, "exerciseChoice": 0,
                "exerciseTime": 0, "eatingSoonStoppedByTimer": 0,
            },
            "estimatedDateTime": "2026-05-18T10:15:53Z",
        }
        # Sleeping <- Normal, requestedAction StartSleep, activeSleepSchedule [0].
        self.fixtureStartSleep = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 229,
            "sequenceGroup": 0,
            "sequenceNumber": 456855,
            "pumpDateTime": "2026-05-18T10:16:00",
            "eventProperties": {
                "currentUserMode": 1, "previousUserMode": 0, "requestedAction": 1,
                "spareA3": 0, "sleepStartedByGui": 1, "activeSleepSchedule": [0],
                "spareB6": 0, "exerciseStoppedByTimer": 0, "exerciseChoice": 0,
                "exerciseTime": 0, "eatingSoonStoppedByTimer": 0,
            },
            "estimatedDateTime": "2026-05-18T10:16:00Z",
        }
        # Exercising <- Normal, requestedAction StartExercise, empty activeSleepSchedule.
        self.fixtureStartExercise = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 229,
            "sequenceGroup": 0,
            "sequenceNumber": 456961,
            "pumpDateTime": "2026-05-18T10:20:04",
            "eventProperties": {
                "currentUserMode": 2, "previousUserMode": 0, "requestedAction": 3,
                "spareA3": 0, "sleepStartedByGui": 0, "activeSleepSchedule": [],
                "spareB6": 0, "exerciseStoppedByTimer": 0, "exerciseChoice": 0,
                "exerciseTime": 0, "eatingSoonStoppedByTimer": 0,
            },
            "estimatedDateTime": "2026-05-18T10:20:04Z",
        }
        # Sleeping <- Exercising, requestedAction StopExercise, activeSleepSchedule [0].
        self.fixtureStopExercise = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 229,
            "sequenceGroup": 0,
            "sequenceNumber": 456965,
            "pumpDateTime": "2026-05-18T10:20:15",
            "eventProperties": {
                "currentUserMode": 1, "previousUserMode": 2, "requestedAction": 4,
                "spareA3": 0, "sleepStartedByGui": 0, "activeSleepSchedule": [0],
                "spareB6": 0, "exerciseStoppedByTimer": 0, "exerciseChoice": 0,
                "exerciseTime": 0, "eatingSoonStoppedByTimer": 0,
            },
            "estimatedDateTime": "2026-05-18T10:20:15Z",
        }

    def test_dispatches_to_correct_class(self):
        for fx in (self.fixtureStopSleep, self.fixtureStartSleep,
                   self.fixtureStartExercise, self.fixtureStopExercise):
            ev = Event(fx)
            self.assertIsInstance(ev, eventtypes.LidAaUserModeChange)
            self.assertNotIsInstance(ev, RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureStopSleep)
        self.assertEqual(ev.eventId, 229)
        self.assertEqual(ev.seqNum, 456851)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-05-18T10:15:53")

    def test_envelope_fields_other_fixture(self):
        ev = Event(self.fixtureStartExercise)
        self.assertEqual(ev.eventId, 229)
        self.assertEqual(ev.seqNum, 456961)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-05-18T10:20:04")

    def test_stop_sleep_enums(self):
        ev = Event(self.fixtureStopSleep)
        self.assertEqual(ev.currentUserModeRaw, 0)
        self.assertEqual(ev.currentUserMode,
                         eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Normal)
        self.assertEqual(ev.previousUserModeRaw, 1)
        self.assertEqual(ev.previousUserMode,
                         eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Sleeping)
        self.assertEqual(ev.requestedActionRaw, 2)
        self.assertEqual(ev.requestedAction,
                         eventtypes.LidAaUserModeChange.RequestedactionEnum.StopSleep)

    def test_start_sleep_enums(self):
        ev = Event(self.fixtureStartSleep)
        self.assertEqual(ev.currentUserMode,
                         eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Sleeping)
        self.assertEqual(ev.previousUserMode,
                         eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Normal)
        self.assertEqual(ev.requestedAction,
                         eventtypes.LidAaUserModeChange.RequestedactionEnum.StartSleep)

    def test_start_exercise_enums(self):
        ev = Event(self.fixtureStartExercise)
        self.assertEqual(ev.currentUserMode,
                         eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Exercising)
        self.assertEqual(ev.previousUserMode,
                         eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Normal)
        self.assertEqual(ev.requestedAction,
                         eventtypes.LidAaUserModeChange.RequestedactionEnum.StartExercise)

    def test_stop_exercise_enums(self):
        ev = Event(self.fixtureStopExercise)
        self.assertEqual(ev.currentUserMode,
                         eventtypes.LidAaUserModeChange.CurrentusermodeEnum.Sleeping)
        self.assertEqual(ev.previousUserMode,
                         eventtypes.LidAaUserModeChange.PrevioususermodeEnum.Exercising)
        self.assertEqual(ev.requestedAction,
                         eventtypes.LidAaUserModeChange.RequestedactionEnum.StopExercise)

    def test_active_sleep_schedule_single_bit(self):
        # activeSleepSchedule:[0] -> 1<<0 == 1 -> SleepSchedule1IsActive
        ev = Event(self.fixtureStopSleep)
        self.assertEqual(ev.activeSleepScheduleRaw, 1)
        self.assertEqual(ev.activeSleepSchedule,
                         eventtypes.LidAaUserModeChange.ActivesleepscheduleBitmask.SleepSchedule1IsActive)

    def test_active_sleep_schedule_empty(self):
        # An empty array folds to 0 (empty IntFlag), not None.
        ev = Event(self.fixtureStartExercise)
        self.assertEqual(ev.activeSleepScheduleRaw, 0)
        self.assertEqual(ev.activeSleepSchedule,
                         eventtypes.LidAaUserModeChange.ActivesleepscheduleBitmask(0))
        self.assertEqual(int(ev.activeSleepSchedule), 0)

    def test_todict_json_serializable(self):
        for fx in (self.fixtureStopSleep, self.fixtureStartSleep,
                   self.fixtureStartExercise, self.fixtureStopExercise):
            ev = Event(fx)
            d = ev.todict()
            json.dumps(d)  # must not raise
            self.assertEqual(d["id"], 229)
            self.assertEqual(d["name"], "LID_AA_USER_MODE_CHANGE")


if __name__ == "__main__":
    unittest.main()
