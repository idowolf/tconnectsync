#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidAlarmCleared(unittest.TestCase):
    """28: LID_ALARM_CLEARED. Real captured pump-log events; alarmId is a
    dictionary transform resolving to an AlarmidEnum member."""
    maxDiff = None

    def setUp(self):
        # Real capture: alarmId 18 -> RESUME_PUMP_ALARM.
        self.fixtureResumePumpAlarm = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 28,
            "sequenceGroup": 0,
            "sequenceNumber": 398734,
            "pumpDateTime": "2026-05-01T17:11:22",
            "eventProperties": {"alarmId": 18},
            "estimatedDateTime": "2026-05-01T17:11:22Z",
        }
        # Real capture: alarmId 23 -> RESUME_PUMP_ALARM2.
        self.fixtureResumePumpAlarm2 = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 28,
            "sequenceGroup": 0,
            "sequenceNumber": 398733,
            "pumpDateTime": "2026-05-01T17:11:22",
            "eventProperties": {"alarmId": 23},
            "estimatedDateTime": "2026-05-01T17:11:22Z",
        }

    def test_dispatches_to_correct_class(self):
        self.assertIsInstance(Event(self.fixtureResumePumpAlarm), eventtypes.LidAlarmCleared)
        self.assertIsInstance(Event(self.fixtureResumePumpAlarm2), eventtypes.LidAlarmCleared)
        self.assertNotIsInstance(Event(self.fixtureResumePumpAlarm), RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureResumePumpAlarm)
        self.assertEqual(ev.eventId, 28)
        self.assertEqual(ev.seqNum, 398734)

        ev2 = Event(self.fixtureResumePumpAlarm2)
        self.assertEqual(ev2.eventId, 28)
        self.assertEqual(ev2.seqNum, 398733)

    def test_timestamp_preserves_wall_clock(self):
        ev = Event(self.fixtureResumePumpAlarm)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'), "2026-05-01T17:11:22")

    def test_alarmid_resolves_resume_pump_alarm(self):
        # alarmId:18 -> RESUME_PUMP_ALARM
        ev = Event(self.fixtureResumePumpAlarm)
        self.assertEqual(ev.alarmIdRaw, 18)
        self.assertEqual(ev.alarmId, eventtypes.LidAlarmCleared.AlarmidEnum.ResumePumpAlarm)

    def test_alarmid_resolves_resume_pump_alarm2(self):
        # alarmId:23 -> RESUME_PUMP_ALARM2
        ev = Event(self.fixtureResumePumpAlarm2)
        self.assertEqual(ev.alarmIdRaw, 23)
        self.assertEqual(ev.alarmId, eventtypes.LidAlarmCleared.AlarmidEnum.ResumePumpAlarm2)

    def test_todict_is_json_serializable(self):
        for f in (self.fixtureResumePumpAlarm, self.fixtureResumePumpAlarm2):
            ev = Event(f)
            d = ev.todict()
            json.dumps(d)  # must not raise
            self.assertEqual(d["id"], 28)
            self.assertEqual(d["name"], "LID_ALARM_CLEARED")

        self.assertEqual(Event(self.fixtureResumePumpAlarm).todict(), {
            "id": 28,
            "name": "LID_ALARM_CLEARED",
            "seqNum": 398734,
            "eventTimestamp": "2026-05-01T17:11:22-04:00",
            "alarmIdRaw": 18,
        })


if __name__ == "__main__":
    unittest.main()
