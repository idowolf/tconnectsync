#!/usr/bin/env python3

import unittest
from unittest.mock import patch

from tconnectsync.sync.tandemsource.update_profiles import UpdateProfiles
from tconnectsync.domain.tandemsource.pump_settings import PumpSettings

from ...api.fake import TConnectApi
from ...nightscout_fake import NightscoutApi

DEVICE_ID = '1114157'

# Trimmed real BFF settings.details shape (from the captured bff/pumper
# response). Values condensed; PumpSettings.from_dict is patched in these
# tests, so we only assert it is reached with this blob — parsing the new
# shape is covered when PumpSettings is migrated.
SETTINGS_DETAILS = {
    'basalLimitSettings': {'basalLimitDefault': 5000, 'basalLimit': 5000},
    'globalMaxBolusSettings': {'maxBolus': 25000, 'maxBolusDefault': 25000},
    'profiles': {'numberOfProfiles': 1, 'activeSegment': 0, 'activeIdp': 0, 'profile': []},
}


def _meta(device_id=DEVICE_ID, settings=None):
    # settings, when provided, is the raw settings.details blob; wrap it in the
    # BFF settings envelope ({'details': ...}) that update_profiles unwraps.
    return {
        'assignmentId': device_id,
        'serialNumber': '1518994',
        'modelNumber': '1004000',
        'modelName': 'Tandem Mobi™ System',
        'softwareVersion': '1.0.0.0',
        'algorithm': 'Control-IQ',
        'maxDateOfEvents': '2026-05-27T23:03:06',
        'availableDataRange': {'start': '2020-01-02T00:00:00', 'end': '2026-05-27T23:03:06'},
        'settings': {'details': settings} if settings is not None else None,
    }


class _ReachedFromDict(Exception):
    pass


class FakeTandemSourceApi:
    def __init__(self, metadata):
        self._metadata = metadata

    def get_pumper(self):
        return {'pumps': self._metadata}

    def needs_relogin(self):
        # Required so TConnectApi.tandemsource returns this fake, not a real API.
        return False


# A fuller real-shape settings.details for end-to-end compare_profiles tests.
FULL_SETTINGS_DETAILS = {
    'profiles': {
        'numberOfProfiles': 1, 'activeSegment': 0, 'activeIdp': 0,
        'profile': [
            {
                'idp': 0, 'timeDependentSegmentNumber': 2, 'name': 'A',
                'carbEntry': 'UnitsAsCarbs', 'maxBolus': 25000, 'insulinDuration': 300,
                'timeDependentSegments': [
                    {'startTime': 0, 'basalRate': 800, 'carbRatio': 6000, 'targetBg': 110, 'isf': 30, 'status': []},
                    {'startTime': 480, 'basalRate': 1200, 'carbRatio': 6000, 'targetBg': 110, 'isf': 30, 'status': []},
                ],
            },
        ],
    },
    'cgmSettings': {'highGlucoseAlertMgPerDl': 200, 'lowGlucoseAlertMgPerDl': 80},
}


class TestCompareProfilesWithNewSettings(unittest.TestCase):
    maxDiff = None

    def _updater(self):
        tconnect = TConnectApi()
        tconnect._tandemsource = FakeTandemSourceApi([])
        return UpdateProfiles(tconnect, NightscoutApi(), DEVICE_ID, pretend=True)

    def test_builds_ns_profile_from_new_settings(self):
        pump_settings = PumpSettings.from_dict(FULL_SETTINGS_DETAILS)
        changed, new_profile = self._updater().compare_profiles(pump_settings, {})

        self.assertTrue(changed)
        self.assertEqual(new_profile['defaultProfile'], 'A')
        self.assertIn('A', new_profile['store'])
        store = new_profile['store']['A']
        # milliunit->unit scaling and per-segment schedule preserved
        self.assertEqual([b['value'] for b in store['basal']], [0.8, 1.2])
        self.assertEqual([b['time'] for b in store['basal']], ['00:00', '08:00'])
        self.assertEqual(store['carbratio'][0]['value'], 6.0)
        self.assertEqual(store['sens'][0]['value'], 30)
        # target_low/high sourced from the flat cgmSettings
        self.assertEqual(store['target_low'][0]['value'], 80)
        self.assertEqual(store['target_high'][0]['value'], 200)
        self.assertEqual(store['dia'], '5.0')

    def test_no_change_when_ns_already_matches(self):
        pump_settings = PumpSettings.from_dict(FULL_SETTINGS_DETAILS)
        updater = self._updater()
        _, built = updater.compare_profiles(pump_settings, {})
        # Feed the freshly built profile back in as the current NS profile.
        changed, _ = updater.compare_profiles(pump_settings, built)
        self.assertFalse(changed)


class TestUpdateProfilesSettingsSourcing(unittest.TestCase):
    maxDiff = None

    def _updater(self, metadata, device_id=DEVICE_ID):
        tconnect = TConnectApi()
        tconnect._tandemsource = FakeTandemSourceApi(metadata)
        nightscout = NightscoutApi()
        return UpdateProfiles(tconnect, nightscout, device_id, pretend=True)

    def test_matching_device_with_settings_reaches_from_dict(self):
        updater = self._updater([_meta(settings=SETTINGS_DETAILS)])
        # Sentinel proves we pass the guard and hand settings.details to from_dict.
        with patch.object(PumpSettings, 'from_dict', side_effect=_ReachedFromDict) as fd:
            with self.assertRaises(_ReachedFromDict):
                updater.update(pretend=True)
        fd.assert_called_once_with(SETTINGS_DETAILS)

    def test_matching_device_with_null_settings_returns_false(self):
        updater = self._updater([_meta(settings=None)])
        with patch.object(PumpSettings, 'from_dict') as fd:
            result = updater.update(pretend=True)
        self.assertFalse(result)
        fd.assert_not_called()

    def test_no_device_match_returns_false(self):
        updater = self._updater([_meta(device_id='some-other-device', settings=SETTINGS_DETAILS)])
        with patch.object(PumpSettings, 'from_dict') as fd:
            result = updater.update(pretend=True)
        self.assertFalse(result)
        fd.assert_not_called()

    def test_empty_metadata_returns_false(self):
        updater = self._updater([])
        with patch.object(PumpSettings, 'from_dict') as fd:
            result = updater.update(pretend=True)
        self.assertFalse(result)
        fd.assert_not_called()


if __name__ == "__main__":
    unittest.main()
