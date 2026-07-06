#!/usr/bin/env python3
"""ProcessBolus tests driven by real captured pump-log payloads.

Each self.fixture* is a complete event group (every message sharing one bolusId,
all event codes) copied verbatim from the live Tandem Source API
(deviceAssignmentId redacted):
  - self.fixtureRegular  (bolusId 1868): a standard, completed bolus
  - self.fixtureExtended (bolusId 2046): an extended (combo) bolus, 25% now / 75%
        over 180 min, whose extended portion was aborted early
  - self.fixtureCanceled (bolusId 1644): a standard bolus canceled mid-delivery
"""

import unittest
import arrow

from tconnectsync.sync.tandemsource.process_bolus import ProcessBolus
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.generic import Events

from ...api.fake import TConnectApi
from ...nightscout_fake import NightscoutApi

TIME_START = arrow.get('2020-01-01')
TIME_END = arrow.get('2030-01-01')
ENTERED_BY = 'Pump (tconnectsync)'

# Expected Nightscout treatments produced from the real fixtures below.
REGULAR_ENTRY = {
    'eventType': 'Combo Bolus',
    'created_at': '2025-11-27 12:47:18-05:00',
    'carbs': 15,
    'insulin': 3.14,
    'notes': 'BLE Standard Bolus',
    'enteredBy': ENTERED_BY,
    'pump_event_id': '450262,450238,450239,450240',
    'glucose': '131',
}

# The extended bolus produces TWO treatments: the initial ("now") portion at its
# completion time, and the extended portion added separately at the later time it
# finished delivering.
EXTENDED_INITIAL_ENTRY = {
    'eventType': 'Combo Bolus',
    'created_at': '2025-12-12 20:57:51-05:00',
    'carbs': 50,
    'insulin': 2.08,
    'notes': 'BLE Extended Bolus',
    'enteredBy': ENTERED_BY,
    'pump_event_id': '502769,502747,502748,502749',
    'glucose': '111',
}
EXTENDED_PORTION_ENTRY = {
    'eventType': 'Combo Bolus',
    'created_at': '2025-12-12 23:14:27-05:00',
    'carbs': 0,
    'insulin': 4.69,
    'notes': 'Extended Bolus',
    'enteredBy': ENTERED_BY,
    'pump_event_id': '503184',
}

CANCELED_ENTRY = {
    'eventType': 'Combo Bolus',
    'created_at': '2026-05-18 10:15:39-04:00',
    'carbs': 0,
    'insulin': 0.05,
    'notes': 'BLE Standard Bolus (Override)',
    'enteredBy': ENTERED_BY,
    'pump_event_id': '456849,456827,456828,456829',
    'glucose': '151',
}


class BolusTestBase(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tconnect = TConnectApi()
        self.nightscout = NightscoutApi()
        self.process = ProcessBolus(self.tconnect, self.nightscout, 'abcdef', pretend=False)
        self.nightscout.last_uploaded_entry = lambda *a, **k: None

        # Real captured event groups (verbatim, deviceAssignmentId redacted).
        self.fixtureRegular = [
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 64, "sequenceGroup": 0, "sequenceNumber": 450238, "pumpDateTime": "2025-11-27T12:45:32", "eventProperties": {"bolusId": 1868, "bolusType": 3, "correctionBolusIncluded": 1, "carbAmount": 15, "bg": 131, "iob": 0.06, "carbRatio": 0}, "estimatedDateTime": "2025-11-27T12:45:32Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 65, "sequenceGroup": 0, "sequenceNumber": 450239, "pumpDateTime": "2025-11-27T12:45:32", "eventProperties": {"bolusId": 1868, "options": 4, "standardPercent": 100, "duration": 0, "spareB6": 0, "isf": 0, "targetBg": 0, "userOverride": 0, "declinedCorrection": 0, "selectedIob": 1}, "estimatedDateTime": "2025-11-27T12:45:32Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 66, "sequenceGroup": 0, "sequenceNumber": 450240, "pumpDateTime": "2025-11-27T12:45:32", "eventProperties": {"bolusId": 1868, "spareA2": 0, "foodBolusSize": 2.5, "correctionBolusSize": 0.64, "totalBolusSize": 3.14}, "estimatedDateTime": "2025-11-27T12:45:32Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 55, "sequenceGroup": 0, "sequenceNumber": 450247, "pumpDateTime": "2025-11-27T12:45:47", "eventProperties": {"bolusId": 1868, "selectedIob": 1, "spareA3": 0, "iob": 0.059388563, "bolusSize": 3.1399999}, "estimatedDateTime": "2025-11-27T12:45:47Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 450248, "pumpDateTime": "2025-11-27T12:45:47", "eventProperties": {"bolusId": 1868, "bolusDeliveryStatus": 1, "bolusType": [0, 3, 4], "bolusSource": 8, "remoteId": 76, "requestedNow": 3140, "requestedLater": 0, "correction": 640, "extendedDurationRequested": 0, "deliveredTotal": 0}, "estimatedDateTime": "2025-11-27T12:45:47Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 450260, "pumpDateTime": "2025-11-27T12:47:18", "eventProperties": {"bolusId": 1868, "bolusDeliveryStatus": 0, "bolusType": [0, 3, 4], "bolusSource": 8, "remoteId": 76, "requestedNow": 3140, "requestedLater": 0, "correction": 640, "extendedDurationRequested": 0, "deliveredTotal": 3140}, "estimatedDateTime": "2025-11-27T12:47:18Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 20, "sequenceGroup": 0, "sequenceNumber": 450262, "pumpDateTime": "2025-11-27T12:47:18", "eventProperties": {"completionStatus": 3, "bolusId": 1868, "iob": 3.1993885, "insulinDelivered": 3.1399999, "insulinRequested": 3.1399999}, "estimatedDateTime": "2025-11-27T12:47:18Z"},
            ]

        self.fixtureExtended = [
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 64, "sequenceGroup": 0, "sequenceNumber": 502747, "pumpDateTime": "2025-12-12T20:56:36", "eventProperties": {"bolusId": 2046, "bolusType": 3, "correctionBolusIncluded": 0, "carbAmount": 50, "bg": 111, "iob": 8.57, "carbRatio": 0}, "estimatedDateTime": "2025-12-12T20:56:36Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 65, "sequenceGroup": 0, "sequenceNumber": 502748, "pumpDateTime": "2025-12-12T20:56:36", "eventProperties": {"bolusId": 2046, "options": 5, "standardPercent": 25, "duration": 180, "spareB6": 0, "isf": 0, "targetBg": 0, "userOverride": 0, "declinedCorrection": 0, "selectedIob": 1}, "estimatedDateTime": "2025-12-12T20:56:36Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 66, "sequenceGroup": 0, "sequenceNumber": 502749, "pumpDateTime": "2025-12-12T20:56:36", "eventProperties": {"bolusId": 2046, "spareA2": 0, "foodBolusSize": 8.33, "correctionBolusSize": 0, "totalBolusSize": 8.330001}, "estimatedDateTime": "2025-12-12T20:56:36Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 55, "sequenceGroup": 0, "sequenceNumber": 502761, "pumpDateTime": "2025-12-12T20:56:51", "eventProperties": {"bolusId": 2046, "selectedIob": 1, "spareA3": 0, "iob": 8.567241, "bolusSize": 2.083}, "estimatedDateTime": "2025-12-12T20:56:51Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502762, "pumpDateTime": "2025-12-12T20:56:51", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 0}, "estimatedDateTime": "2025-12-12T20:56:51Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 20, "sequenceGroup": 0, "sequenceNumber": 502769, "pumpDateTime": "2025-12-12T20:57:51", "eventProperties": {"completionStatus": 3, "bolusId": 2046, "iob": 10.65024, "insulinDelivered": 2.0829997, "insulinRequested": 2.083}, "estimatedDateTime": "2025-12-12T20:57:51Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 59, "sequenceGroup": 0, "sequenceNumber": 502771, "pumpDateTime": "2025-12-12T20:57:51", "eventProperties": {"bolusId": 2046, "selectedIob": 1, "spareA3": 0, "iob": 10.65024, "bolexSize": 6.247}, "estimatedDateTime": "2025-12-12T20:57:51Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502772, "pumpDateTime": "2025-12-12T20:57:51", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 2083}, "estimatedDateTime": "2025-12-12T20:57:51Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502773, "pumpDateTime": "2025-12-12T20:57:51", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 2083}, "estimatedDateTime": "2025-12-12T20:57:51Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502778, "pumpDateTime": "2025-12-12T21:00:13", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 2257}, "estimatedDateTime": "2025-12-12T21:00:13Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502793, "pumpDateTime": "2025-12-12T21:05:13", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 2430}, "estimatedDateTime": "2025-12-12T21:05:13Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502804, "pumpDateTime": "2025-12-12T21:10:13", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 2604}, "estimatedDateTime": "2025-12-12T21:10:13Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502816, "pumpDateTime": "2025-12-12T21:15:15", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 2777}, "estimatedDateTime": "2025-12-12T21:15:15Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502829, "pumpDateTime": "2025-12-12T21:20:16", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 2951}, "estimatedDateTime": "2025-12-12T21:20:16Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502841, "pumpDateTime": "2025-12-12T21:25:16", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 3124}, "estimatedDateTime": "2025-12-12T21:25:16Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502853, "pumpDateTime": "2025-12-12T21:30:17", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 3298}, "estimatedDateTime": "2025-12-12T21:30:17Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502868, "pumpDateTime": "2025-12-12T21:35:17", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 3471}, "estimatedDateTime": "2025-12-12T21:35:17Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502879, "pumpDateTime": "2025-12-12T21:40:17", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 3645}, "estimatedDateTime": "2025-12-12T21:40:17Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502891, "pumpDateTime": "2025-12-12T21:45:18", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 3818}, "estimatedDateTime": "2025-12-12T21:45:18Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502904, "pumpDateTime": "2025-12-12T21:50:18", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 3992}, "estimatedDateTime": "2025-12-12T21:50:18Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502917, "pumpDateTime": "2025-12-12T21:55:18", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 4165}, "estimatedDateTime": "2025-12-12T21:55:18Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502928, "pumpDateTime": "2025-12-12T22:00:19", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 4339}, "estimatedDateTime": "2025-12-12T22:00:19Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502956, "pumpDateTime": "2025-12-12T22:05:19", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 4512}, "estimatedDateTime": "2025-12-12T22:05:19Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502967, "pumpDateTime": "2025-12-12T22:10:19", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 4686}, "estimatedDateTime": "2025-12-12T22:10:19Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502979, "pumpDateTime": "2025-12-12T22:15:20", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 4859}, "estimatedDateTime": "2025-12-12T22:15:20Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 502991, "pumpDateTime": "2025-12-12T22:20:20", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 5033}, "estimatedDateTime": "2025-12-12T22:20:20Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503003, "pumpDateTime": "2025-12-12T22:25:20", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 5206}, "estimatedDateTime": "2025-12-12T22:25:20Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503016, "pumpDateTime": "2025-12-12T22:30:20", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 5380}, "estimatedDateTime": "2025-12-12T22:30:20Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503029, "pumpDateTime": "2025-12-12T22:35:21", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 5554}, "estimatedDateTime": "2025-12-12T22:35:21Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503040, "pumpDateTime": "2025-12-12T22:40:21", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 5727}, "estimatedDateTime": "2025-12-12T22:40:21Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503067, "pumpDateTime": "2025-12-12T22:45:21", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 5901}, "estimatedDateTime": "2025-12-12T22:45:21Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503079, "pumpDateTime": "2025-12-12T22:50:22", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 6074}, "estimatedDateTime": "2025-12-12T22:50:22Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503102, "pumpDateTime": "2025-12-12T22:54:56", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 6074}, "estimatedDateTime": "2025-12-12T22:54:56Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503136, "pumpDateTime": "2025-12-12T22:57:14", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 6248}, "estimatedDateTime": "2025-12-12T22:57:14Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503148, "pumpDateTime": "2025-12-12T23:02:13", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 6421}, "estimatedDateTime": "2025-12-12T23:02:13Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503163, "pumpDateTime": "2025-12-12T23:07:14", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 6595}, "estimatedDateTime": "2025-12-12T23:07:14Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503177, "pumpDateTime": "2025-12-12T23:12:13", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 1, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 6768}, "estimatedDateTime": "2025-12-12T23:12:13Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 21, "sequenceGroup": 0, "sequenceNumber": 503184, "pumpDateTime": "2025-12-12T23:14:27", "eventProperties": {"completionStatus": 0, "bolusId": 2046, "iob": 9.066635, "insulinDelivered": 4.6852484, "insulinRequested": 6.247}, "estimatedDateTime": "2025-12-12T23:14:27Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 503185, "pumpDateTime": "2025-12-12T23:14:27", "eventProperties": {"bolusId": 2046, "bolusDeliveryStatus": 0, "bolusType": [0, 1, 4], "bolusSource": 8, "remoteId": 254, "requestedNow": 2083, "requestedLater": 6247, "correction": 0, "extendedDurationRequested": 180, "deliveredTotal": 6768}, "estimatedDateTime": "2025-12-12T23:14:27Z"},
            ]

        self.fixtureCanceled = [
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 64, "sequenceGroup": 0, "sequenceNumber": 456827, "pumpDateTime": "2026-05-18T10:15:21", "eventProperties": {"bolusId": 1644, "bolusType": 3, "correctionBolusIncluded": 0, "carbAmount": 0, "bg": 151, "iob": 1.181, "carbRatio": 0}, "estimatedDateTime": "2026-05-18T10:15:21Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 65, "sequenceGroup": 0, "sequenceNumber": 456828, "pumpDateTime": "2026-05-18T10:15:21", "eventProperties": {"bolusId": 1644, "options": 4, "standardPercent": 100, "duration": 0, "spareB6": 0, "isf": 0, "targetBg": 0, "userOverride": 1, "declinedCorrection": 0, "selectedIob": 1}, "estimatedDateTime": "2026-05-18T10:15:21Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 66, "sequenceGroup": 0, "sequenceNumber": 456829, "pumpDateTime": "2026-05-18T10:15:21", "eventProperties": {"bolusId": 1644, "spareA2": 0, "foodBolusSize": 0, "correctionBolusSize": 0, "totalBolusSize": 0.5}, "estimatedDateTime": "2026-05-18T10:15:21Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 55, "sequenceGroup": 0, "sequenceNumber": 456836, "pumpDateTime": "2026-05-18T10:15:36", "eventProperties": {"bolusId": 1644, "selectedIob": 1, "spareA3": 0, "iob": 1.1809407, "bolusSize": 0.5}, "estimatedDateTime": "2026-05-18T10:15:36Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 456837, "pumpDateTime": "2026-05-18T10:15:36", "eventProperties": {"bolusId": 1644, "bolusDeliveryStatus": 1, "bolusType": [0, 2], "bolusSource": 8, "remoteId": 108, "requestedNow": 500, "requestedLater": 0, "correction": 0, "extendedDurationRequested": 0, "deliveredTotal": 0}, "estimatedDateTime": "2026-05-18T10:15:36Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 280, "sequenceGroup": 0, "sequenceNumber": 456847, "pumpDateTime": "2026-05-18T10:15:39", "eventProperties": {"bolusId": 1644, "bolusDeliveryStatus": 0, "bolusType": [0, 2], "bolusSource": 8, "remoteId": 108, "requestedNow": 500, "requestedLater": 0, "correction": 0, "extendedDurationRequested": 0, "deliveredTotal": 47}, "estimatedDateTime": "2026-05-18T10:15:39Z"},
                {"deviceAssignmentId": "redacted-device-assignment-id", "eventCode": 20, "sequenceGroup": 0, "sequenceNumber": 456849, "pumpDateTime": "2026-05-18T10:15:39", "eventProperties": {"completionStatus": 0, "bolusId": 1644, "iob": 1.2275107, "insulinDelivered": 0.04657, "insulinRequested": 0.5}, "estimatedDateTime": "2026-05-18T10:15:39Z"},
            ]

    def run_group(self, events):
        return self.process.process(list(Events(events)), TIME_START, TIME_END)


class TestRegularBolus(BolusTestBase):
    def test_single_completed_bolus(self):
        p = self.run_group(self.fixtureRegular)
        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], REGULAR_ENTRY)

    def test_non_bolus_class_events_ignored(self):
        # The real group carries LidBolusActivated (55) and LidBolusDelivery (280)
        # too; they must not produce extra treatments.
        self.assertIn(280, {e['eventCode'] for e in self.fixtureRegular})
        self.assertIn(55, {e['eventCode'] for e in self.fixtureRegular})
        self.assertEqual(len(self.run_group(self.fixtureRegular)), 1)


class TestExtendedBolus(BolusTestBase):
    def test_produces_two_entries(self):
        p = self.run_group(self.fixtureExtended)
        self.assertEqual(len(p), 2)
        self.assertDictEqual(p[0], EXTENDED_INITIAL_ENTRY)
        self.assertDictEqual(p[1], EXTENDED_PORTION_ENTRY)

    def test_initial_portion_matches_now_amount(self):
        # Initial entry carries the "now" insulin (2.083 -> 2.08) plus carbs/bg,
        # exactly like a standard bolus.
        p = self.run_group(self.fixtureExtended)
        self.assertEqual(p[0]['insulin'], 2.08)
        self.assertEqual(p[0]['carbs'], 50)
        self.assertEqual(p[0]['glucose'], '111')

    def test_extended_portion_insulin_only(self):
        # Extended entry carries only the extended delivered insulin (4.685 ->
        # 4.69, the aborted-early amount, not the 6.247 requested), no carbs/bg.
        p = self.run_group(self.fixtureExtended)
        ext = p[1]
        self.assertEqual(ext['insulin'], 4.69)
        self.assertEqual(ext['carbs'], 0)
        self.assertNotIn('glucose', ext)
        self.assertEqual(ext['notes'], 'Extended Bolus')

    def test_total_delivered_across_both_entries(self):
        # Neither portion is dropped: 2.08 + 4.69 == 6.77u actually delivered.
        p = self.run_group(self.fixtureExtended)
        self.assertAlmostEqual(p[0]['insulin'] + p[1]['insulin'], 6.77, places=2)

    def test_in_progress_emits_only_initial(self):
        # A sync running before the extended portion finishes (no LidBolexCompleted
        # yet) posts just the initial bolus; nothing is lost.
        raw = [e for e in self.fixtureExtended if e['eventCode'] != 21]
        p = self.run_group(raw)
        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], EXTENDED_INITIAL_ENTRY)

    def test_extended_portion_added_on_later_sync(self):
        # Next sync (last upload == the initial's time) skips the already-uploaded
        # initial and posts only the extended portion.
        self.nightscout.last_uploaded_entry = lambda *a, **k: {'created_at': EXTENDED_INITIAL_ENTRY['created_at']}
        p = self.run_group(self.fixtureExtended)
        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], EXTENDED_PORTION_ENTRY)


class TestCanceledBolus(BolusTestBase):
    def test_records_actual_delivered_not_requested(self):
        # User aborted a 0.5u bolus after only 0.04657u delivered; the treatment
        # reflects what was actually delivered (0.05), not the 0.5 requested.
        p = self.run_group(self.fixtureCanceled)
        self.assertEqual(len(p), 1)
        self.assertDictEqual(p[0], CANCELED_ENTRY)

    def test_override_note(self):
        p = self.run_group(self.fixtureCanceled)
        self.assertIn('(Override)', p[0]['notes'])


class TestBolusDedup(BolusTestBase):
    def test_skips_completions_at_or_before_last_upload(self):
        # last upload after both extended completions -> nothing new.
        self.nightscout.last_uploaded_entry = lambda *a, **k: {'created_at': '2025-12-13 00:00:00-05:00'}
        self.assertEqual(self.run_group(self.fixtureExtended), [])

    def test_boundary_is_inclusive(self):
        # A completion exactly at last_upload_time is treated as already uploaded.
        self.nightscout.last_uploaded_entry = lambda *a, **k: {'created_at': REGULAR_ENTRY['created_at']}
        self.assertEqual(self.run_group(self.fixtureRegular), [])


class TestMultipleBoluses(BolusTestBase):
    def test_batch_time_sorted(self):
        raw = self.fixtureRegular + self.fixtureExtended + self.fixtureCanceled
        p = self.run_group(raw)
        self.assertEqual(p, [REGULAR_ENTRY, EXTENDED_INITIAL_ENTRY, EXTENDED_PORTION_ENTRY, CANCELED_ENTRY])


class TestBolusWrite(BolusTestBase):
    def test_write_uploads_treatments(self):
        p = self.run_group(self.fixtureRegular)
        count = self.process.write(p)
        self.assertEqual(count, 1)
        self.assertEqual(self.nightscout.uploaded_entries['treatments'], [REGULAR_ENTRY])


if __name__ == '__main__':
    unittest.main()
