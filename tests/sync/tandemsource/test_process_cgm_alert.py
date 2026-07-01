#!/usr/bin/env python3

import unittest

from tconnectsync.sync.tandemsource.process_cgm_alert import ProcessCGMAlert
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.generic import Events

from ...api.fake import TConnectApi
from ...nightscout_fake import NightscoutApi

# Real captured LID_CGM_ALERT_ACTIVATED_DEX (eventCode 369) events
# (deviceAssignmentId redacted). dalertId maps to LidCgmAlertActivatedDex.DalertidEnum.

# dalertId 2 -> CgmHigh
CGM_ALERT_HIGH = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 369,
    "sequenceGroup": 0,
    "sequenceNumber": 443773,
    "pumpDateTime": "2026-05-14T19:26:34",
    "eventProperties": {"dalertId": 2, "sensorType": 3, "spareA2": 0, "faultLocatorData": 8468, "param1": 210, "param2": 200},
    "estimatedDateTime": "2026-05-14T19:26:34Z",
}

# dalertId 3 -> CgmLow
CGM_ALERT_LOW = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 369,
    "sequenceGroup": 0,
    "sequenceNumber": 443243,
    "pumpDateTime": "2026-05-14T15:41:34",
    "eventProperties": {"dalertId": 3, "sensorType": 3, "spareA2": 0, "faultLocatorData": 8467, "param1": 80, "param2": 80},
    "estimatedDateTime": "2026-05-14T15:41:34Z",
}

# dalertId 14 -> CgmOutOfRange (explicitly skipped)
CGM_ALERT_OUT_OF_RANGE = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 369,
    "sequenceGroup": 0,
    "sequenceNumber": 447441,
    "pumpDateTime": "2026-05-15T20:52:28",
    "eventProperties": {"dalertId": 14, "sensorType": 3, "spareA2": 0, "faultLocatorData": 8462, "param1": 25, "param2": 917},
    "estimatedDateTime": "2026-05-15T20:52:28Z",
}

# dalertId 31 -> unmapped (resolves to None, skipped)
CGM_ALERT_UNMAPPED = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 369,
    "sequenceGroup": 0,
    "sequenceNumber": 448285,
    "pumpDateTime": "2026-05-16T01:04:28",
    "eventProperties": {"dalertId": 31, "sensorType": 3, "spareA2": 0, "faultLocatorData": 10355, "param1": 43170, "param2": 452},
    "estimatedDateTime": "2026-05-16T01:04:28Z",
}

# eventCode 370 (Cleared) - not in CGM_ALERT class
CGM_ALERT_CLEARED = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 370,
    "sequenceGroup": 0,
    "sequenceNumber": 443314,
    "pumpDateTime": "2026-05-14T15:56:33",
    "eventProperties": {"dalertId": 3, "sensorType": 3},
    "estimatedDateTime": "2026-05-14T15:56:33Z",
}

# eventCode 371 (Ack) - not in CGM_ALERT class
CGM_ALERT_ACK = {
    "deviceAssignmentId": "00000000-0000-0000-0000-000000000000",
    "eventCode": 371,
    "sequenceGroup": 0,
    "sequenceNumber": 446797,
    "pumpDateTime": "2026-05-15T16:43:28",
    "eventProperties": {"dalertId": 12, "sensorType": 3, "spareA2": 0, "ackSource": 0},
    "estimatedDateTime": "2026-05-15T16:43:28Z",
}


class TestProcessCGMAlert(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tconnect = TConnectApi()
        self.nightscout = NightscoutApi()
        self.process = ProcessCGMAlert(self.tconnect, self.nightscout, 'abcdef', pretend=False)
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: None

    def test_event_types(self):
        # Sanity: verify parsed types and enum members match the real data.
        high = list(Events([dict(CGM_ALERT_HIGH)]))[0]
        low = list(Events([dict(CGM_ALERT_LOW)]))[0]
        oor = list(Events([dict(CGM_ALERT_OUT_OF_RANGE)]))[0]
        unmapped = list(Events([dict(CGM_ALERT_UNMAPPED)]))[0]
        self.assertEqual(type(high), eventtypes.LidCgmAlertActivatedDex)
        self.assertEqual(high.dalertId, eventtypes.LidCgmAlertActivatedDex.DalertidEnum.CgmHigh)
        self.assertEqual(low.dalertId, eventtypes.LidCgmAlertActivatedDex.DalertidEnum.CgmLow)
        self.assertEqual(oor.dalertId, eventtypes.LidCgmAlertActivatedDex.DalertidEnum.CgmOutOfRange)
        self.assertIsNone(unmapped.dalertId)

    def test_mapped_alerts(self):
        # Two real 369 events -> exact NS dicts, sorted by timestamp (low first).
        p = self.process.process(list(Events([dict(CGM_ALERT_HIGH), dict(CGM_ALERT_LOW)])), None, None)

        self.assertEqual(len(p), 2)
        self.assertDictEqual(p[0], {
            'eventType': 'CGM Alert',
            'reason': 'Dexcom CGM Alert (CgmLow)',
            'notes': 'Dexcom CGM Alert (CgmLow)',
            'created_at': '2026-05-14 15:41:34-04:00',
            'enteredBy': 'Pump (tconnectsync)',
            'pump_event_id': '443243'
        })
        self.assertDictEqual(p[1], {
            'eventType': 'CGM Alert',
            'reason': 'Dexcom CGM Alert (CgmHigh)',
            'notes': 'Dexcom CGM Alert (CgmHigh)',
            'created_at': '2026-05-14 19:26:34-04:00',
            'enteredBy': 'Pump (tconnectsync)',
            'pump_event_id': '443773'
        })

    def test_out_of_range_skipped(self):
        # CgmOutOfRange (14) is explicitly skipped.
        p = self.process.process(list(Events([dict(CGM_ALERT_OUT_OF_RANGE)])), None, None)
        self.assertEqual(p, [])

    def test_unmapped_dalertid_skipped(self):
        # Unmapped dalertId (31) resolves to None and is skipped without crashing.
        p = self.process.process(list(Events([dict(CGM_ALERT_UNMAPPED)])), None, None)
        self.assertEqual(p, [])

    def test_cleared_and_ack_not_synced(self):
        # 370 (Cleared) / 371 (Ack) are not in EventClass.CGM_ALERT -> no output.
        p = self.process.process(list(Events([dict(CGM_ALERT_CLEARED), dict(CGM_ALERT_ACK)])), None, None)
        self.assertEqual(p, [])

    def test_dedup_only_later_emitted(self):
        # last upload at the low alert's created_at -> only strictly-later (high) emitted.
        self.nightscout.last_uploaded_entry = lambda *args, **kwargs: {"created_at": "2026-05-14 15:41:34-04:00"}
        p = self.process.process(list(Events([dict(CGM_ALERT_HIGH), dict(CGM_ALERT_LOW)])), None, None)

        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], {
            'eventType': 'CGM Alert',
            'reason': 'Dexcom CGM Alert (CgmHigh)',
            'notes': 'Dexcom CGM Alert (CgmHigh)',
            'created_at': '2026-05-14 19:26:34-04:00',
            'enteredBy': 'Pump (tconnectsync)',
            'pump_event_id': '443773'
        })


if __name__ == '__main__':
    unittest.main()
