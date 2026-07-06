#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes


class TestLidBasalDelivery(unittest.TestCase):
    """279 LID_BASAL_DELIVERY: commandedRateSource enum + milliunits/hr rates.

    Fixtures are real captured pump-log dicts (copied verbatim), each with a
    different commandedRateSource so every enum member is exercised. reservedA2
    and spareA3 are ignored by the parser and not asserted on.
    """
    maxDiff = None

    def setUp(self):
        # commandedRateSource:0 -> Suspended; commandedRate 0, algorithmRate/tempRate sentinel.
        self.fixtureSuspended = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 279,
            "sequenceGroup": 0,
            "sequenceNumber": 394356,
            "pumpDateTime": "2026-04-30T10:04:05",
            "eventProperties": {
                "commandedRateSource": 0, "reservedA2": 3, "spareA3": 0,
                "commandedRate": 0, "profileBasalRate": 1200,
                "algorithmRate": 65535, "tempRate": 65535,
            },
            "estimatedDateTime": "2026-04-30T10:04:05Z",
        }
        # commandedRateSource:1 -> Profile; commandedRate follows profileBasalRate.
        self.fixtureProfile = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 279,
            "sequenceGroup": 0,
            "sequenceNumber": 409132,
            "pumpDateTime": "2026-05-04T18:58:52",
            "eventProperties": {
                "commandedRateSource": 1, "reservedA2": 3, "spareA3": 0,
                "commandedRate": 1000, "profileBasalRate": 1000,
                "algorithmRate": 65535, "tempRate": 65535,
            },
            "estimatedDateTime": "2026-05-04T18:58:52Z",
        }
        # commandedRateSource:2 -> TempRate; real tempRate=500 (not the 65535 sentinel).
        self.fixtureTempRate = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 279,
            "sequenceGroup": 0,
            "sequenceNumber": 449599,
            "pumpDateTime": "2026-05-16T11:16:07",
            "eventProperties": {
                "commandedRateSource": 2, "reservedA2": 0, "spareA3": 0,
                "commandedRate": 500, "profileBasalRate": 1000,
                "algorithmRate": 65535, "tempRate": 500,
            },
            "estimatedDateTime": "2026-05-16T11:16:07Z",
        }
        # commandedRateSource:3 -> Algorithm; commandedRate follows algorithmRate, tempRate sentinel.
        self.fixtureAlgorithm = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 279,
            "sequenceGroup": 0,
            "sequenceNumber": 393151,
            "pumpDateTime": "2026-04-30T00:08:30",
            "eventProperties": {
                "commandedRateSource": 3, "reservedA2": 3, "spareA3": 0,
                "commandedRate": 1061, "profileBasalRate": 1000,
                "algorithmRate": 1061, "tempRate": 65535,
            },
            "estimatedDateTime": "2026-04-30T00:08:30Z",
        }
        # commandedRateSource:4 -> TempRateAndAlgorithm; both algorithmRate and real tempRate=600 present.
        self.fixtureTempRateAndAlgorithm = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 279,
            "sequenceGroup": 0,
            "sequenceNumber": 449571,
            "pumpDateTime": "2026-05-16T11:01:05",
            "eventProperties": {
                "commandedRateSource": 4, "reservedA2": 3, "spareA3": 0,
                "commandedRate": 500, "profileBasalRate": 1000,
                "algorithmRate": 500, "tempRate": 500,
            },
            "estimatedDateTime": "2026-05-16T11:01:05Z",
        }

    def test_dispatches_to_correct_class(self):
        for fixture in (self.fixtureSuspended, self.fixtureProfile,
                        self.fixtureTempRate, self.fixtureAlgorithm,
                        self.fixtureTempRateAndAlgorithm):
            ev = Event(fixture)
            self.assertIsInstance(ev, eventtypes.LidBasalDelivery)

    def test_envelope_fields(self):
        ev = Event(self.fixtureAlgorithm)
        self.assertEqual(ev.eventId, 279)
        self.assertEqual(ev.seqNum, 393151)
        self.assertEqual(ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
                         "2026-04-30T00:08:30")

    def test_rate_fields_round_trip(self):
        ev = Event(self.fixtureAlgorithm)
        self.assertEqual(ev.commandedRate, 1061)
        self.assertEqual(ev.profileBasalRate, 1000)
        self.assertEqual(ev.algorithmRate, 1061)
        self.assertEqual(ev.tempRate, 65535)

    def test_temp_rate_sentinel_vs_real(self):
        # Algorithm capture uses the 65535 sentinel; TempRate capture has a real value.
        self.assertEqual(Event(self.fixtureAlgorithm).tempRate, 65535)
        self.assertEqual(Event(self.fixtureTempRate).tempRate, 500)
        self.assertEqual(Event(self.fixtureTempRateAndAlgorithm).tempRate, 500)

    def test_commanded_rate_source_suspended(self):
        ev = Event(self.fixtureSuspended)
        self.assertEqual(ev.commandedRateSourceRaw, 0)
        self.assertEqual(ev.commandedRateSource,
                         eventtypes.LidBasalDelivery.CommandedratesourceEnum.Suspended)

    def test_commanded_rate_source_profile(self):
        ev = Event(self.fixtureProfile)
        self.assertEqual(ev.commandedRateSourceRaw, 1)
        self.assertEqual(ev.commandedRateSource,
                         eventtypes.LidBasalDelivery.CommandedratesourceEnum.Profile)

    def test_commanded_rate_source_temp_rate(self):
        ev = Event(self.fixtureTempRate)
        self.assertEqual(ev.commandedRateSourceRaw, 2)
        self.assertEqual(ev.commandedRateSource,
                         eventtypes.LidBasalDelivery.CommandedratesourceEnum.TempRate)

    def test_commanded_rate_source_algorithm(self):
        ev = Event(self.fixtureAlgorithm)
        self.assertEqual(ev.commandedRateSourceRaw, 3)
        self.assertEqual(ev.commandedRateSource,
                         eventtypes.LidBasalDelivery.CommandedratesourceEnum.Algorithm)

    def test_commanded_rate_source_temp_rate_and_algorithm(self):
        ev = Event(self.fixtureTempRateAndAlgorithm)
        self.assertEqual(ev.commandedRateSourceRaw, 4)
        self.assertEqual(ev.commandedRateSource,
                         eventtypes.LidBasalDelivery.CommandedratesourceEnum.TempRateAndAlgorithm)

    def test_todict_is_json_serializable(self):
        for fixture in (self.fixtureSuspended, self.fixtureProfile,
                        self.fixtureTempRate, self.fixtureAlgorithm,
                        self.fixtureTempRateAndAlgorithm):
            d = Event(fixture).todict()
            json.dumps(d)  # must not raise
            self.assertEqual(d["id"], 279)
            self.assertEqual(d["name"], "LID_BASAL_DELIVERY")


if __name__ == "__main__":
    unittest.main()
