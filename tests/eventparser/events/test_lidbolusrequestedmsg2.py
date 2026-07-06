#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidBolusRequestedMsg2(unittest.TestCase):
    """65: LID_BOLUS_REQUESTED_MSG2 — real captured pump-log events."""
    maxDiff = None

    def setUp(self):
        # BLE standard bolus, user did NOT override the bolus size.
        self.fixtureBleStandard = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 65,
            "sequenceGroup": 0,
            "sequenceNumber": 394642,
            "pumpDateTime": "2026-04-30T11:57:38",
            "eventProperties": {
                "bolusId": 1423, "options": 4, "standardPercent": 100,
                "duration": 0, "spareB6": 0, "isf": 0, "targetBg": 0,
                "userOverride": 0, "declinedCorrection": 0, "selectedIob": 1,
            },
            "estimatedDateTime": "2026-04-30T11:57:38Z",
        }

        # BLE standard bolus, user DID override the bolus size.
        self.fixtureUserOverride = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 65,
            "sequenceGroup": 0,
            "sequenceNumber": 394840,
            "pumpDateTime": "2026-04-30T13:13:28",
            "eventProperties": {
                "bolusId": 1424, "options": 4, "standardPercent": 100,
                "duration": 0, "spareB6": 0, "isf": 0, "targetBg": 0,
                "userOverride": 1, "declinedCorrection": 0, "selectedIob": 1,
            },
            "estimatedDateTime": "2026-04-30T13:13:28Z",
        }

        # Quick bolus (options=2).
        self.fixtureQuick = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 65,
            "sequenceGroup": 0,
            "sequenceNumber": 395147,
            "pumpDateTime": "2026-04-30T15:12:59",
            "eventProperties": {
                "bolusId": 1425, "options": 2, "standardPercent": 100,
                "duration": 0, "spareB6": 0, "isf": 0, "targetBg": 0,
                "userOverride": 0, "declinedCorrection": 0, "selectedIob": 1,
            },
            "estimatedDateTime": "2026-04-30T15:12:59Z",
        }

    def test_dispatches_to_correct_class(self):
        ev = Event(self.fixtureBleStandard)
        self.assertIsInstance(ev, eventtypes.LidBolusRequestedMsg2)
        self.assertNotIsInstance(ev, RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureBleStandard)
        self.assertEqual(ev.eventId, 65)
        self.assertEqual(ev.seqNum, 394642)
        self.assertEqual(
            ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'), "2026-04-30T11:57:38")

    def test_plain_fields_round_trip(self):
        ev = Event(self.fixtureBleStandard)
        self.assertEqual(ev.bolusId, 1423)
        self.assertEqual(ev.standardPercent, 100)
        self.assertEqual(ev.duration, 0)
        self.assertEqual(ev.isf, 0)
        self.assertEqual(ev.targetBg, 0)

    def test_options_enum_ble_standard(self):
        ev = Event(self.fixtureBleStandard)
        self.assertEqual(ev.optionsRaw, 4)
        self.assertEqual(ev.options,
                         eventtypes.LidBolusRequestedMsg2.OptionsEnum.BleStandardBolus)

    def test_options_enum_quick(self):
        ev = Event(self.fixtureQuick)
        self.assertEqual(ev.optionsRaw, 2)
        self.assertEqual(ev.options,
                         eventtypes.LidBolusRequestedMsg2.OptionsEnum.QuickBolus)

    def test_selectediob_enum(self):
        ev = Event(self.fixtureBleStandard)
        self.assertEqual(ev.selectedIobRaw, 1)
        self.assertEqual(ev.selectedIob,
                         eventtypes.LidBolusRequestedMsg2.SelectediobEnum.SwanIobMeal)

    def test_useroverride_enum_no(self):
        ev = Event(self.fixtureBleStandard)
        self.assertEqual(ev.userOverrideRaw, 0)
        self.assertEqual(ev.userOverride,
                         eventtypes.LidBolusRequestedMsg2.UseroverrideEnum.No)

    def test_useroverride_enum_yes(self):
        ev = Event(self.fixtureUserOverride)
        self.assertEqual(ev.userOverrideRaw, 1)
        self.assertEqual(ev.userOverride,
                         eventtypes.LidBolusRequestedMsg2.UseroverrideEnum.Yes)

    def test_declinedcorrection_enum(self):
        ev = Event(self.fixtureBleStandard)
        self.assertEqual(ev.declinedCorrectionRaw, 0)
        self.assertEqual(ev.declinedCorrection,
                         eventtypes.LidBolusRequestedMsg2.DeclinedcorrectionEnum.No)

    def test_todict_is_json_serializable(self):
        for fixture in (self.fixtureBleStandard, self.fixtureUserOverride,
                        self.fixtureQuick):
            ev = Event(fixture)
            json.dumps(ev.todict())  # must not raise


if __name__ == "__main__":
    unittest.main()
