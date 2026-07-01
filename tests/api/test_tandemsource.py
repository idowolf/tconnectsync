#!/usr/bin/env python3

import arrow
import datetime
import unittest
import urllib.parse
from unittest.mock import patch

from tconnectsync.api.tandemsource import TandemSourceApi
from tconnectsync.api.common import ApiException
from tconnectsync.eventparser import events as eventtypes


# Representative GET api/reports/bff/pumper/{pumperId} response, mirroring the
# structure of a real captured account response: one active pump with settings
# and one never-uploaded pump (null date/settings fields).
BFF_PUMPER = {
    "firstName": "Test",
    "lastName": "User",
    "name": "Test User",
    "dateOfBirth": "1990-01-01",
    "lowGlucoseThreshold": 70,
    "highGlucoseThreshold": 180,
    "country": "US",
    "pumps": [
        {
            "algorithm": "Control-IQ",
            "availableDataRange": {"start": "2021-05-06T12:31:19", "end": "2022-02-16T22:45:58"},
            "assignmentId": "1b493210-9336-4901-a329-a352775738c5",
            "lastUploadDate": "2022-09-20T05:50:12Z",
            "maxDateOfEvents": "2022-02-16T22:45:58",
            "modelNumber": "1000354",
            "modelName": "t:slim X2™ Insulin Pump",
            "partNumber": "1011979",
            "serialNumber": "90556643",
            "softwareVersion": "7.8.0.0",
            "lastUploadClientType": "mobile_tconnect",
            "settings": {
                "id": "b7f931c8-63cd-44c9-86aa-56826f9057e5",
                "deviceAssignmentId": "1b493210-9336-4901-a329-a352775738c5",
                "uploadedTimeStamp": "2022-09-10T21:07:43.497",
                "settingsHash": "29EDDA8E7A72C1AD060271268CC7AE81FAD54B9D",
                "uploadId": "5da6a0ca-86c3-440f-9462-fa53168dcb9d",
                "details": {"profiles": {"numberOfProfiles": 1}},
            },
        },
        {
            "algorithm": "Basal-IQ",
            "availableDataRange": {"start": None, "end": None},
            "assignmentId": "f6631fff-f403-4ce4-9362-83eff9e2850e",
            "glucoseUnit": None,
            "lastUploadDate": None,
            "maxDateOfEvents": None,
            "modelNumber": "1000096",
            "modelName": "t:slim X2™ Insulin Pump",
            "partNumber": "1003314",
            "serialNumber": "514387",
            "softwareVersion": "6.0.3.0",
            "lastUploadClientType": None,
            "settings": None,
        },
    ],
}


class TestPumpMetadataAdapter(unittest.TestCase):
    maxDiff = None

    def _api(self):
        # Bypass __init__ (which performs a network login) to test the adapter.
        return TandemSourceApi.__new__(TandemSourceApi)

    def test_bff_pump_to_metadata_active_pump(self):
        meta = TandemSourceApi._bff_pump_to_metadata(BFF_PUMPER["pumps"][0])
        self.assertEqual(meta["deviceId"], "1b493210-9336-4901-a329-a352775738c5")
        self.assertEqual(meta["serialNumber"], "90556643")
        self.assertEqual(meta["modelNumber"], "1000354")
        self.assertEqual(meta["softwareVersion"], "7.8.0.0")
        self.assertEqual(meta["algorithm"], "Control-IQ")
        # maxDateOfEvents -> maxDateWithEvents
        self.assertEqual(meta["maxDateWithEvents"], "2022-02-16T22:45:58")
        # availableDataRange.start -> minDateWithEvents
        self.assertEqual(meta["minDateWithEvents"], "2021-05-06T12:31:19")
        # settings.details -> settings
        self.assertEqual(meta["settings"], {"profiles": {"numberOfProfiles": 1}})

    def test_bff_pump_to_metadata_never_uploaded_pump(self):
        meta = TandemSourceApi._bff_pump_to_metadata(BFF_PUMPER["pumps"][1])
        self.assertEqual(meta["deviceId"], "f6631fff-f403-4ce4-9362-83eff9e2850e")
        self.assertEqual(meta["serialNumber"], "514387")
        # null date/settings fields map to None, not KeyError
        self.assertIsNone(meta["maxDateWithEvents"])
        self.assertIsNone(meta["minDateWithEvents"])
        self.assertIsNone(meta["settings"])

    def test_pump_metadata_maps_all_pumps(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get_pumper", return_value=BFF_PUMPER):
            metas = api.pump_metadata()
        self.assertEqual(len(metas), 2)
        self.assertEqual(
            [m["deviceId"] for m in metas],
            [
                "1b493210-9336-4901-a329-a352775738c5",
                "f6631fff-f403-4ce4-9362-83eff9e2850e",
            ],
        )

    def test_pump_metadata_empty_when_no_pumps(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get_pumper", return_value={}):
            self.assertEqual(api.pump_metadata(), [])

    def test_available_data_range_key_absent(self):
        pump = dict(BFF_PUMPER["pumps"][0])
        del pump["availableDataRange"]
        meta = TandemSourceApi._bff_pump_to_metadata(pump)
        self.assertIsNone(meta["minDateWithEvents"])

    def test_settings_key_absent(self):
        pump = dict(BFF_PUMPER["pumps"][0])
        del pump["settings"]
        meta = TandemSourceApi._bff_pump_to_metadata(pump)
        self.assertIsNone(meta["settings"])

    def test_missing_required_key_raises(self):
        pump = dict(BFF_PUMPER["pumps"][0])
        del pump["serialNumber"]
        with self.assertRaises(KeyError):
            TandemSourceApi._bff_pump_to_metadata(pump)

    def test_mobi_controliq_plus_passthrough(self):
        pump = {
            "algorithm": "Control-IQ+",
            "availableDataRange": {"start": "2024-01-01T00:00:00", "end": "2026-05-27T23:03:06"},
            "assignmentId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "maxDateOfEvents": "2026-05-27T23:03:06",
            "modelNumber": "1004000",
            "modelName": "Tandem Mobi™ System",
            "partNumber": "1005000",
            "serialNumber": "1518994",
            "softwareVersion": "1.0.0.0",
            "lastUploadClientType": "mobile_mobi",
            "settings": None,
        }
        meta = TandemSourceApi._bff_pump_to_metadata(pump)
        self.assertEqual(meta["algorithm"], "Control-IQ+")
        self.assertEqual(meta["modelName"], "Tandem Mobi™ System")
        self.assertEqual(meta["deviceId"], "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


class TestDefaultEventIds(unittest.TestCase):
    def test_default_event_ids(self):
        ids = TandemSourceApi.DEFAULT_EVENT_IDS
        self.assertEqual(len(ids), 55)
        self.assertEqual(len(set(ids)), 55, "DEFAULT_EVENT_IDS contains duplicates")
        # FSL3 ids added for the BFF pump-logs endpoint
        self.assertTrue({477, 480, 486}.issubset(set(ids)))


# Trimmed real-shape pump-logs response (1 event + 1 clockChange).
PUMP_LOGS = {
    "events": [
        {
            "deviceAssignmentId": "1b493210-9336-4901-a329-a352775738c5",
            "eventCode": 16,
            "sequenceGroup": 1,
            "sequenceNumber": 100123,
            "pumpDateTime": "2024-01-10T08:15:30",
            "eventProperties": {"iob": 1.25, "bg": 112},
            "estimatedDateTime": "2024-01-10T08:15:30Z",
        }
    ],
    "clockChanges": [
        {
            "deviceAssignmentId": "1b493210-9336-4901-a329-a352775738c5",
            "eventCode": 13,
            "sequenceGroup": 0,
            "sequenceNumber": 5,
            "pumpDateTime": "2024-01-01T00:00:00",
            "eventProperties": {"timePrior": 1, "timeAfter": 2, "rawRtcTime": 3},
            "estimatedDateTime": "2024-01-01T00:00:00Z",
        }
    ],
}


class TestGetPumpLogs(unittest.TestCase):
    maxDiff = None

    def _api(self):
        api = TandemSourceApi.__new__(TandemSourceApi)
        api.pumperId = "PUMPER123"
        return api

    def _endpoint(self, mock_get):
        mock_get.assert_called_once()
        # (endpoint, query_dict) positional args
        self.assertEqual(mock_get.call_args.args[1], {})
        return mock_get.call_args.args[0]

    def _qs(self, endpoint, keep_blank=False):
        parsed = urllib.parse.urlparse(endpoint)
        return parsed.path, urllib.parse.parse_qs(parsed.query, keep_blank_values=keep_blank)

    def test_endpoint_path_and_params(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS) as mock_get:
            api.get_pump_logs("dev-uuid", min_date="2024-01-01", max_date="2024-01-15")
        endpoint = self._endpoint(mock_get)
        path, qs = self._qs(endpoint)
        self.assertEqual(path, "api/reports/bff/pump-logs/dev-uuid")
        self.assertEqual(qs["pumperId"], ["PUMPER123"])
        self.assertEqual(qs["startDate"], ["2024-01-01T00:00:00Z"])
        self.assertEqual(qs["endDate"], ["2024-01-15T23:59:59Z"])

    def test_default_event_ids_comma_joined(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS) as mock_get:
            api.get_pump_logs("dev", min_date="2024-01-01", max_date="2024-01-02")
        _, qs = self._qs(self._endpoint(mock_get))
        self.assertEqual(qs["eventIds"][0].split(","),
                         [str(i) for i in TandemSourceApi.DEFAULT_EVENT_IDS])

    def test_custom_event_ids_comma_joined(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS) as mock_get:
            api.get_pump_logs("dev", "2024-01-01", "2024-01-02", event_ids_filter=[16, 5, 28])
        _, qs = self._qs(self._endpoint(mock_get))
        self.assertEqual(qs["eventIds"], ["16,5,28"])

    def test_none_event_ids_empty(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS) as mock_get:
            api.get_pump_logs("dev", "2024-01-01", "2024-01-02", event_ids_filter=None)
        _, qs = self._qs(self._endpoint(mock_get), keep_blank=True)
        self.assertEqual(qs["eventIds"], [""])

    def test_return_value_passthrough(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS):
            result = api.get_pump_logs("dev", "2024-01-01", "2024-01-15")
        self.assertIs(result, PUMP_LOGS)

    def test_none_dates_default_to_today(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get", return_value=PUMP_LOGS) as mock_get:
            api.get_pump_logs("dev")
        _, qs = self._qs(self._endpoint(mock_get))
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.assertEqual(qs["startDate"], ["%sT00:00:00Z" % today])
        self.assertEqual(qs["endDate"], ["%sT23:59:59Z" % today])


def _ev(group, num, event_code=16, pump_date_time="2024-01-10T08:15:30", **props):
    """Trimmed real-shape pump-log event; eventCode 16 parses to LidBgReadingTaken."""
    return {
        "deviceAssignmentId": "1b493210-9336-4901-a329-a352775738c5",
        "eventCode": event_code,
        "sequenceGroup": group,
        "sequenceNumber": num,
        "pumpDateTime": pump_date_time,
        "eventProperties": props or {"iob": 1.25, "bg": 112},
        "estimatedDateTime": pump_date_time + "Z",
    }


class TestPumpLogWindows(unittest.TestCase):
    """#10: the range is paged into inclusive windows no larger than 28 days."""
    maxDiff = None

    def test_single_day(self):
        self.assertEqual(TandemSourceApi._pump_log_windows("2024-01-01", "2024-01-01"),
                         [("2024-01-01", "2024-01-01")])

    def test_short_range_is_one_window(self):
        # A span shorter than the window must still yield a covering window.
        self.assertEqual(TandemSourceApi._pump_log_windows("2024-01-01", "2024-01-15"),
                         [("2024-01-01", "2024-01-15")])

    def test_exactly_28_days_is_one_window(self):
        self.assertEqual(TandemSourceApi._pump_log_windows("2024-01-01", "2024-01-28"),
                         [("2024-01-01", "2024-01-28")])

    def test_29_days_splits(self):
        self.assertEqual(TandemSourceApi._pump_log_windows("2024-01-01", "2024-01-29"),
                         [("2024-01-01", "2024-01-28"), ("2024-01-29", "2024-01-29")])

    def test_long_range_windows_are_contiguous_and_bounded(self):
        windows = TandemSourceApi._pump_log_windows("2024-01-01", "2024-03-01")
        self.assertEqual(windows, [
            ("2024-01-01", "2024-01-28"),
            ("2024-01-29", "2024-02-25"),
            ("2024-02-26", "2024-03-01"),
        ])
        # each window <= 28 days, and windows are contiguous (no gaps/overlaps)
        for start, end in windows:
            self.assertLessEqual((arrow.get(end) - arrow.get(start)).days, 27)
        for (_, prev_end), (next_start, _) in zip(windows, windows[1:]):
            self.assertEqual(arrow.get(next_start), arrow.get(prev_end).shift(days=1))

    def test_reversed_dates_are_swapped(self):
        self.assertEqual(TandemSourceApi._pump_log_windows("2024-03-01", "2024-01-01"),
                         TandemSourceApi._pump_log_windows("2024-01-01", "2024-03-01"))

    def test_none_dates_default_to_single_today_window(self):
        windows = TandemSourceApi._pump_log_windows(None, None)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0][0], windows[0][1])


class TestPumpEvents(unittest.TestCase):
    """#16: pump_events pages get_pump_logs by window, dedupes, skips
    clockChanges, and yields parsed event objects."""
    maxDiff = None

    def _api(self):
        api = TandemSourceApi.__new__(TandemSourceApi)
        api.pumperId = "PUMPER123"
        return api

    def test_single_window_one_call_with_default_event_ids(self):
        api = self._api()
        resp = {"events": [_ev(0, 1)], "clockChanges": []}
        with patch.object(TandemSourceApi, "get_pump_logs", return_value=resp) as m:
            out = list(api.pump_events("dev-uuid", "2024-01-01", "2024-01-10"))
        m.assert_called_once_with("dev-uuid", "2024-01-01", "2024-01-10",
                                  TandemSourceApi.DEFAULT_EVENT_IDS)
        self.assertEqual([type(e).__name__ for e in out], ["LidBgReadingTaken"])

    def test_fetch_all_event_types_passes_none_filter(self):
        api = self._api()
        resp = {"events": [], "clockChanges": []}
        with patch.object(TandemSourceApi, "get_pump_logs", return_value=resp) as m:
            list(api.pump_events("dev", "2024-01-01", "2024-01-10", fetch_all_event_types=True))
        self.assertIsNone(m.call_args.args[3])

    def test_multi_window_paging_boundaries(self):
        api = self._api()
        responses = [
            {"events": [_ev(0, 1)], "clockChanges": []},
            {"events": [_ev(0, 2)], "clockChanges": []},
            {"events": [_ev(0, 3)], "clockChanges": []},
        ]
        with patch.object(TandemSourceApi, "get_pump_logs", side_effect=responses) as m:
            out = list(api.pump_events("dev", "2024-01-01", "2024-03-01"))
        windows = [(c.args[1], c.args[2]) for c in m.call_args_list]
        self.assertEqual(windows, [
            ("2024-01-01", "2024-01-28"),
            ("2024-01-29", "2024-02-25"),
            ("2024-02-26", "2024-03-01"),
        ])
        self.assertEqual([e.seqNum for e in out], [1, 2, 3])

    def test_dedupes_across_windows_by_group_and_number(self):
        api = self._api()
        # Same (sequenceGroup, sequenceNumber) appears in two windows -> kept once.
        responses = [
            {"events": [_ev(0, 100), _ev(0, 101)], "clockChanges": []},
            {"events": [_ev(0, 100), _ev(0, 102)], "clockChanges": []},
        ]
        with patch.object(TandemSourceApi, "get_pump_logs", side_effect=responses):
            out = list(api.pump_events("dev", "2024-01-01", "2024-02-15"))
        self.assertEqual([e.seqNum for e in out], [100, 101, 102])

    def test_same_number_different_group_not_deduped(self):
        api = self._api()
        responses = [
            {"events": [_ev(0, 100)], "clockChanges": []},
            {"events": [_ev(1, 100)], "clockChanges": []},
        ]
        with patch.object(TandemSourceApi, "get_pump_logs", side_effect=responses):
            out = list(api.pump_events("dev", "2024-01-01", "2024-02-15"))
        self.assertEqual(len(out), 2)

    def test_clock_changes_are_skipped(self):
        api = self._api()
        resp = {
            "events": [_ev(0, 1)],
            "clockChanges": [_ev(0, 5, event_code=13), _ev(0, 6, event_code=14)],
        }
        with patch.object(TandemSourceApi, "get_pump_logs", return_value=resp):
            out = list(api.pump_events("dev", "2024-01-01", "2024-01-10"))
        self.assertEqual([e.eventId for e in out], [16])

    def test_missing_events_key_is_tolerated(self):
        api = self._api()
        with patch.object(TandemSourceApi, "get_pump_logs", return_value={}):
            out = list(api.pump_events("dev", "2024-01-01", "2024-01-10"))
        self.assertEqual(out, [])


class TestGetRetry(unittest.TestCase):
    """get() retries once on 500, re-logs-in and retries once on 401, and
    raises immediately on other statuses; after one retry it gives up."""
    maxDiff = None

    def _api(self):
        api = TandemSourceApi.__new__(TandemSourceApi)
        api._email = 'e'
        api._password = 'p'
        api.accessTokenExpiresAt = 0
        return api

    def test_401_triggers_relogin_then_retry_succeeds(self):
        api = self._api()
        with patch.object(TandemSourceApi, "_get",
                          side_effect=[ApiException(401, 'unauth'), {'ok': True}]) as m_get, \
             patch.object(TandemSourceApi, "login", return_value=None) as m_login:
            result = api.get('ep', {})
        self.assertEqual(result, {'ok': True})
        self.assertEqual(m_login.call_count, 1)
        self.assertEqual(m_get.call_count, 2)

    def test_500_retries_without_relogin(self):
        api = self._api()
        with patch.object(TandemSourceApi, "_get",
                          side_effect=[ApiException(500, 'err'), {'ok': True}]) as m_get, \
             patch.object(TandemSourceApi, "login", return_value=None) as m_login:
            result = api.get('ep', {})
        self.assertEqual(result, {'ok': True})
        self.assertEqual(m_login.call_count, 0)
        self.assertEqual(m_get.call_count, 2)

    def test_other_status_raises_immediately(self):
        api = self._api()
        with patch.object(TandemSourceApi, "_get",
                          side_effect=ApiException(403, 'forbidden')) as m_get, \
             patch.object(TandemSourceApi, "login", return_value=None) as m_login:
            with self.assertRaises(ApiException):
                api.get('ep', {})
        self.assertEqual(m_login.call_count, 0)
        self.assertEqual(m_get.call_count, 1)

    def test_persistent_401_raises_after_one_retry(self):
        api = self._api()
        with patch.object(TandemSourceApi, "_get",
                          side_effect=[ApiException(401, 'unauth'), ApiException(401, 'unauth')]) as m_get, \
             patch.object(TandemSourceApi, "login", return_value=None) as m_login:
            with self.assertRaises(ApiException):
                api.get('ep', {})
        self.assertEqual(m_login.call_count, 1)
        self.assertEqual(m_get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
