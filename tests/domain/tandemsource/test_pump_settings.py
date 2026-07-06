#!/usr/bin/env python3

import unittest

from tconnectsync.domain.tandemsource.pump_settings import PumpSettings

# Trimmed real bff/pumper settings.details (values from a captured account,
# schedule condensed to two segments). Extra top-level blocks the parser
# ignores (basalLimitSettings/controlIqSettings/...) are omitted.
SETTINGS_DETAILS = {
    "profiles": {
        "numberOfProfiles": 2,
        "activeSegment": 0,
        "activeIdp": 0,
        "profile": [
            {
                "idp": 0,
                "timeDependentSegmentNumber": 2,
                "name": "A",
                "carbEntry": "UnitsAsCarbs",
                "maxBolus": 25000,
                "insulinDuration": 300,
                "timeDependentSegments": [
                    {"startTime": 0, "basalRate": 800, "carbRatio": 6000, "targetBg": 110, "isf": 30,
                     "status": ["BasalRateAvailability"]},
                    {"startTime": 480, "basalRate": 1200, "carbRatio": 6000, "targetBg": 110, "isf": 30,
                     "status": ["BasalRateAvailability"]},
                ],
            },
            {
                "idp": 2,
                "timeDependentSegmentNumber": 1,
                "name": "No delivery",
                "carbEntry": "UnitsAsCarbs",
                "maxBolus": 25000,
                "insulinDuration": 300,
                # An all-zero segment must be dropped as a skip.
                "timeDependentSegments": [
                    {"startTime": 0, "basalRate": 0, "carbRatio": 0, "targetBg": 0, "isf": 0, "status": []},
                    {"startTime": 720, "basalRate": 500, "carbRatio": 12000, "targetBg": 120, "isf": 45, "status": []},
                ],
            },
        ],
    },
    "cgmSettings": {
        "highGlucoseAlertMgPerDl": 200,
        "highGlucoseAlertEnabled": True,
        "lowGlucoseAlertMgPerDl": 80,
        "lowGlucoseAlertEnabled": True,
        "riseRateAlertLevel": 3,
    },
    # Blocks the parser does not consume; must be ignored, not error.
    "basalLimitSettings": {"basalLimitDefault": 5000, "basalLimit": 2500},
    "controlIqSettings": {"weight": 140, "closedLoop": False},
}


class TestPumpSettingsFromDict(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.settings = PumpSettings.from_dict(SETTINGS_DETAILS)

    def test_profiles_container(self):
        self.assertEqual(self.settings.profiles.activeIdp, 0)
        self.assertEqual(len(self.settings.profiles.profile), 2)
        self.assertEqual([p.name for p in self.settings.profiles.profile], ["A", "No delivery"])

    def test_profile_fields(self):
        profile = self.settings.profiles.profile[0]
        self.assertEqual(profile.idp, 0)
        self.assertEqual(profile.insulinDuration, 300)
        self.assertEqual(profile.maxBolus, 25000)
        self.assertEqual(profile.carbEntry, "UnitsAsCarbs")

    def test_segments_parse_with_new_key(self):
        # The BFF names the container timeDependentSegments (was tDependentSegs).
        profile = self.settings.profiles.profile[0]
        self.assertEqual(len(profile.timeDependentSegments), 2)
        seg = profile.timeDependentSegments[0]
        self.assertEqual((seg.startTime, seg.basalRate, seg.carbRatio, seg.targetBg, seg.isf),
                         (0, 800, 6000, 110, 30))

    def test_tdependentsegs_alias(self):
        profile = self.settings.profiles.profile[0]
        self.assertIs(profile.tDependentSegs, profile.timeDependentSegments)

    def test_skip_segments_are_dropped(self):
        # "No delivery" has one all-zero (skip) segment and one real segment.
        profile = self.settings.profiles.profile[1]
        self.assertEqual(len(profile.timeDependentSegments), 1)
        self.assertEqual(profile.timeDependentSegments[0].startTime, 720)

    def test_cgm_settings_are_flat(self):
        self.assertEqual(self.settings.cgmSettings.lowGlucoseAlertMgPerDl, 80)
        self.assertEqual(self.settings.cgmSettings.highGlucoseAlertMgPerDl, 200)


if __name__ == "__main__":
    unittest.main()
