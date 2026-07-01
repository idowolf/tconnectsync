#!/usr/bin/env python3
"""ProcessBasal tests driven by real captured LID_BASAL_DELIVERY (279) events.

Fixtures are copied verbatim from the live Tandem Source API pump-logs
(deviceAssignmentId redacted). Each 279 event becomes a Nightscout "Temp Basal":
rate = commandedRate milliunits/hr -> units/hr (round 2), duration = gap to the
next basal event (the last event's gap is measured to time_end), reason = the
commandedRateSource enum member name.

  - RUN_*     : a short consecutive Algorithm-sourced run (rates 1.28/1.0/0.99)
  - SRC_*     : one event per commandedRateSource value present in the data
                (0 Suspended, 1 Profile, 2 TempRate, 4 TempRateAndAlgorithm)
"""

import unittest
import arrow

from tconnectsync.sync.tandemsource.process_basal import ProcessBasal
from tconnectsync.eventparser.generic import Events

from ...api.fake import TConnectApi
from ...nightscout_fake import NightscoutApi

REDACTED = "00000000-0000-0000-0000-000000000000"
ENTERED_BY = 'Pump (tconnectsync)'

# Real consecutive 279 events (Algorithm source; note the non-round 1279/994).
RUN_EVENTS = [
    {"deviceAssignmentId": REDACTED, "eventCode": 279, "sequenceGroup": 0, "sequenceNumber": 441311, "pumpDateTime": "2026-05-14T00:01:00", "eventProperties": {"commandedRateSource": 3, "reservedA2": 3, "spareA3": 0, "commandedRate": 1279, "profileBasalRate": 1000, "algorithmRate": 1279, "tempRate": 65535}, "estimatedDateTime": "2026-05-14T00:01:00Z"},
    {"deviceAssignmentId": REDACTED, "eventCode": 279, "sequenceGroup": 0, "sequenceNumber": 441336, "pumpDateTime": "2026-05-14T00:06:00", "eventProperties": {"commandedRateSource": 3, "reservedA2": 3, "spareA3": 0, "commandedRate": 1000, "profileBasalRate": 1000, "algorithmRate": 1000, "tempRate": 65535}, "estimatedDateTime": "2026-05-14T00:06:00Z"},
    {"deviceAssignmentId": REDACTED, "eventCode": 279, "sequenceGroup": 0, "sequenceNumber": 441346, "pumpDateTime": "2026-05-14T00:11:00", "eventProperties": {"commandedRateSource": 3, "reservedA2": 3, "spareA3": 0, "commandedRate": 994, "profileBasalRate": 1000, "algorithmRate": 994, "tempRate": 65535}, "estimatedDateTime": "2026-05-14T00:11:00Z"},
]
# Consecutive events are 5 min apart; end the window 5 min after the last event.
RUN_TIME_START = arrow.get('2026-05-14T00:00:00-04:00')
RUN_TIME_END = arrow.get('2026-05-14T00:16:00-04:00')

RUN_ENTRIES = [
    {'eventType': 'Temp Basal', 'reason': 'Algorithm', 'duration': 5.0, 'absolute': 1.28, 'rate': 1.28, 'created_at': '2026-05-14 00:01:00-04:00', 'carbs': None, 'insulin': None, 'enteredBy': ENTERED_BY, 'pump_event_id': '441311'},
    {'eventType': 'Temp Basal', 'reason': 'Algorithm', 'duration': 5.0, 'absolute': 1.0, 'rate': 1.0, 'created_at': '2026-05-14 00:06:00-04:00', 'carbs': None, 'insulin': None, 'enteredBy': ENTERED_BY, 'pump_event_id': '441336'},
    {'eventType': 'Temp Basal', 'reason': 'Algorithm', 'duration': 5.0, 'absolute': 0.99, 'rate': 0.99, 'created_at': '2026-05-14 00:11:00-04:00', 'carbs': None, 'insulin': None, 'enteredBy': ENTERED_BY, 'pump_event_id': '441346'},
]

# One real event per commandedRateSource value seen in the data.
SRC_SUSPENDED = {"deviceAssignmentId": REDACTED, "eventCode": 279, "sequenceGroup": 0, "sequenceNumber": 447977, "pumpDateTime": "2026-05-15T23:40:01", "eventProperties": {"commandedRateSource": 0, "reservedA2": 0, "spareA3": 0, "commandedRate": 0, "profileBasalRate": 1000, "algorithmRate": 65535, "tempRate": 65535}, "estimatedDateTime": "2026-05-15T23:40:01Z"}
SRC_PROFILE = {"deviceAssignmentId": REDACTED, "eventCode": 279, "sequenceGroup": 0, "sequenceNumber": 447435, "pumpDateTime": "2026-05-15T20:48:27", "eventProperties": {"commandedRateSource": 1, "reservedA2": 0, "spareA3": 0, "commandedRate": 1000, "profileBasalRate": 1000, "algorithmRate": 65535, "tempRate": 65535}, "estimatedDateTime": "2026-05-15T20:48:27Z"}
SRC_TEMPRATE = {"deviceAssignmentId": REDACTED, "eventCode": 279, "sequenceGroup": 0, "sequenceNumber": 449599, "pumpDateTime": "2026-05-16T11:16:07", "eventProperties": {"commandedRateSource": 2, "reservedA2": 0, "spareA3": 0, "commandedRate": 500, "profileBasalRate": 1000, "algorithmRate": 65535, "tempRate": 500}, "estimatedDateTime": "2026-05-16T11:16:07Z"}
SRC_TEMP_AND_ALGO = {"deviceAssignmentId": REDACTED, "eventCode": 279, "sequenceGroup": 0, "sequenceNumber": 449321, "pumpDateTime": "2026-05-16T09:19:46", "eventProperties": {"commandedRateSource": 4, "reservedA2": 3, "spareA3": 0, "commandedRate": 0, "profileBasalRate": 1200, "algorithmRate": 0, "tempRate": 600}, "estimatedDateTime": "2026-05-16T09:19:46Z"}


class BasalTestBase(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tconnect = TConnectApi()
        self.nightscout = NightscoutApi()
        self.process = ProcessBasal(self.tconnect, self.nightscout, 'abcdef', pretend=False)
        self.nightscout.last_uploaded_entry = lambda *a, **k: None

    def run_events(self, events, time_start, time_end):
        return self.process.process(list(Events(events)), time_start, time_end)


class TestConsecutiveRun(BasalTestBase):
    def test_exact_entries(self):
        # (1) Each Temp Basal: rate (milliunits/1000, 1279 -> 1.28), Algorithm
        # reason, 5-min gaps between events, last gap measured to time_end.
        p = self.run_events(RUN_EVENTS, RUN_TIME_START, RUN_TIME_END)
        self.assertEqual(len(p), 3)
        for got, want in zip(p, RUN_ENTRIES):
            self.assertDictEqual(got, want)

    def test_nonround_rate_scaling(self):
        # (2) 994 milliunits/hr -> 0.99 u/hr, and 1279 -> 1.28.
        p = self.run_events(RUN_EVENTS, RUN_TIME_START, RUN_TIME_END)
        self.assertEqual(p[0]['rate'], 1.28)
        self.assertEqual(p[0]['absolute'], 1.28)
        self.assertEqual(p[2]['rate'], 0.99)


class TestRateSourceReason(BasalTestBase):
    def _run_single(self, event, minutes=10):
        created_at = arrow.get(event['pumpDateTime']).replace(tzinfo='-04:00')
        return self.run_events([event], arrow.get('2020-01-01'), created_at.shift(minutes=minutes))

    def test_profile_reason(self):
        # (3) commandedRateSource 1 -> "Profile".
        p = self._run_single(SRC_PROFILE)
        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], {'eventType': 'Temp Basal', 'reason': 'Profile', 'duration': 10.0, 'absolute': 1.0, 'rate': 1.0, 'created_at': '2026-05-15 20:48:27-04:00', 'carbs': None, 'insulin': None, 'enteredBy': ENTERED_BY, 'pump_event_id': '447435'})

    def test_temprate_reason(self):
        # (3) commandedRateSource 2 -> "TempRate".
        p = self._run_single(SRC_TEMPRATE)
        self.assertDictEqual(p[0], {'eventType': 'Temp Basal', 'reason': 'TempRate', 'duration': 10.0, 'absolute': 0.5, 'rate': 0.5, 'created_at': '2026-05-16 11:16:07-04:00', 'carbs': None, 'insulin': None, 'enteredBy': ENTERED_BY, 'pump_event_id': '449599'})

    def test_temprate_and_algorithm_reason(self):
        # (3) commandedRateSource 4 -> "TempRateAndAlgorithm".
        p = self._run_single(SRC_TEMP_AND_ALGO)
        self.assertEqual(p[0]['reason'], 'TempRateAndAlgorithm')

    def test_suspended_zero_rate(self):
        # Zero commandedRate (suspend) -> rate 0.0, reason "Suspended".
        p = self._run_single(SRC_SUSPENDED)
        self.assertDictEqual(p[0], {'eventType': 'Temp Basal', 'reason': 'Suspended', 'duration': 10.0, 'absolute': 0.0, 'rate': 0.0, 'created_at': '2026-05-15 23:40:01-04:00', 'carbs': None, 'insulin': None, 'enteredBy': ENTERED_BY, 'pump_event_id': '447977'})


class TestLastEventDurationCap(BasalTestBase):
    def test_duration_is_gap_to_time_end(self):
        # (4) Single event: duration == (time_end - event) in minutes.
        event = SRC_PROFILE
        created_at = arrow.get(event['pumpDateTime']).replace(tzinfo='-04:00')
        time_end = created_at.shift(minutes=37)
        p = self.run_events([event], arrow.get('2020-01-01'), time_end)
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]['duration'], 37.0)

    def test_duration_exceeds_one_day(self):
        # (4) time_end >24h after the event -> duration via .total_seconds()
        # exceeds 1440 minutes (25h == 1500).
        event = SRC_PROFILE
        created_at = arrow.get(event['pumpDateTime']).replace(tzinfo='-04:00')
        time_end = created_at.shift(hours=25)
        p = self.run_events([event], arrow.get('2020-01-01'), time_end)
        self.assertEqual(p[0]['duration'], 1500.0)
        self.assertGreater(p[0]['duration'], 1440)


class TestBasalDedup(BasalTestBase):
    def test_skips_events_at_or_before_last_upload(self):
        # (5) last upload at the first event's time -> only the later two emit,
        # and their durations re-derive against the surviving events / time_end.
        self.nightscout.last_uploaded_entry = lambda *a, **k: {'created_at': RUN_ENTRIES[0]['created_at']}
        p = self.run_events(RUN_EVENTS, RUN_TIME_START, RUN_TIME_END)
        self.assertEqual([e['pump_event_id'] for e in p], ['441336', '441346'])
        self.assertDictEqual(p[0], RUN_ENTRIES[1])
        self.assertDictEqual(p[1], RUN_ENTRIES[2])

    def test_all_skipped_when_last_upload_after_all(self):
        self.nightscout.last_uploaded_entry = lambda *a, **k: {'created_at': '2026-05-14 01:00:00-04:00'}
        self.assertEqual(self.run_events(RUN_EVENTS, RUN_TIME_START, RUN_TIME_END), [])


class TestBasalWrite(BasalTestBase):
    def test_write_uploads_treatments(self):
        p = self.run_events(RUN_EVENTS, RUN_TIME_START, RUN_TIME_END)
        count = self.process.write(p)
        self.assertEqual(count, 3)
        self.assertEqual(self.nightscout.uploaded_entries['treatments'], RUN_ENTRIES)


if __name__ == '__main__':
    unittest.main()
