#!/usr/bin/env python3

import json
import unittest

from tconnectsync.eventparser.generic import Event
from tconnectsync.eventparser import events as eventtypes
from tconnectsync.eventparser.raw_event import RawEvent


class TestLidNewDay(unittest.TestCase):
    """90: LID_NEW_DAY. Real captured pump-log events.

    featuresBitmask / featureBitmaskIndex arrive as JSON arrays but the schema
    declares them plain (no bitmask transform), so the parser stores the raw
    value verbatim (the list as-is, e.g. []).
    """
    maxDiff = None

    def setUp(self):
        # commandedBasalRate == 0
        self.fixtureZeroBasal = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 90,
            "sequenceGroup": 0,
            "sequenceNumber": 393109,
            "pumpDateTime": "2026-04-30T00:00:00",
            "eventProperties": {
                "commandedBasalRate": 0,
                "featuresBitmask": [],
                "featureBitmaskIndex": [],
            },
            "estimatedDateTime": "2026-04-30T00:00:00Z",
        }
        # fractional commandedBasalRate
        self.fixtureFractionalBasal = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 90,
            "sequenceGroup": 0,
            "sequenceNumber": 396368,
            "pumpDateTime": "2026-05-01T00:00:00",
            "eventProperties": {
                "commandedBasalRate": 0.763,
                "featuresBitmask": [],
                "featureBitmaskIndex": [],
            },
            "estimatedDateTime": "2026-05-01T00:00:00Z",
        }
        # integer-valued commandedBasalRate == 1
        self.fixtureUnitBasal = {
            "deviceAssignmentId": "4ff6bebc-d4d6-4423-b123-eecfcf5a4238",
            "eventCode": 90,
            "sequenceGroup": 0,
            "sequenceNumber": 409989,
            "pumpDateTime": "2026-05-05T00:00:00",
            "eventProperties": {
                "commandedBasalRate": 1,
                "featuresBitmask": [],
                "featureBitmaskIndex": [],
            },
            "estimatedDateTime": "2026-05-05T00:00:00Z",
        }

    def test_dispatches_to_lidnewday(self):
        ev = Event(self.fixtureZeroBasal)
        self.assertIsInstance(ev, eventtypes.LidNewDay)
        self.assertIsNot(type(ev), RawEvent)

    def test_envelope_fields(self):
        ev = Event(self.fixtureZeroBasal)
        self.assertEqual(ev.eventId, 90)
        self.assertEqual(ev.seqNum, 393109)

    def test_timestamp_preserves_wall_clock(self):
        ev = Event(self.fixtureZeroBasal)
        self.assertEqual(
            ev.eventTimestamp.format('YYYY-MM-DDTHH:mm:ss'),
            "2026-04-30T00:00:00",
        )

    def test_commanded_basal_rate_zero(self):
        ev = Event(self.fixtureZeroBasal)
        self.assertEqual(ev.commandedBasalRate, 0)

    def test_commanded_basal_rate_fractional(self):
        ev = Event(self.fixtureFractionalBasal)
        self.assertEqual(ev.commandedBasalRate, 0.763)

    def test_commanded_basal_rate_unit(self):
        ev = Event(self.fixtureUnitBasal)
        self.assertEqual(ev.commandedBasalRate, 1)

    def test_features_bitmask_holds_list_verbatim(self):
        # No transform on the schema: the captured list is stored as-is.
        ev = Event(self.fixtureZeroBasal)
        self.assertEqual(ev.featuresBitmask, [])
        self.assertIsInstance(ev.featuresBitmask, list)

    def test_feature_bitmask_index_holds_list_verbatim(self):
        ev = Event(self.fixtureZeroBasal)
        self.assertEqual(ev.featureBitmaskIndex, [])
        self.assertIsInstance(ev.featureBitmaskIndex, list)

    def test_todict_is_json_serializable(self):
        ev = Event(self.fixtureFractionalBasal)
        d = ev.todict()
        json.dumps(d)  # must not raise
        self.assertEqual(d["id"], 90)
        self.assertEqual(d["name"], "LID_NEW_DAY")
        self.assertEqual(d["seqNum"], 396368)
        self.assertEqual(d["commandedBasalRate"], 0.763)
        self.assertEqual(d["featuresBitmask"], [])
        self.assertEqual(d["featureBitmaskIndex"], [])


if __name__ == "__main__":
    unittest.main()
