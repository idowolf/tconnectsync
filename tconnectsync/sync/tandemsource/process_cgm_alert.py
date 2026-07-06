import logging
import arrow

from ...features import DEFAULT_FEATURES
from ... import features
from ...eventparser.generic import Events, decode_raw_events, EVENT_LEN
from ...eventparser.utils import bitmask_to_list
from ...eventparser import events as eventtypes
from ...domain.tandemsource.event_class import EventClass
from ...parser.nightscout import (
    CGM_ALERT_EVENTTYPE,
    NightscoutEntry
)
from ...parser.tidepool import TidepoolEntry
from ...secret import UPLOAD_DESTINATION

logger = logging.getLogger(__name__)

class ProcessCGMAlert:
    def __init__(self, tconnect, upload_api, tconnect_device_id, pretend, features=DEFAULT_FEATURES):
        self.tconnect = tconnect
        self.upload_api = upload_api
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features

    def enabled(self):
        return features.CGM_ALERTS in self.features

    def process(self, events, time_start, time_end):
        logger.debug("ProcessCGMAlert: querying for last uploaded entry")
        
        if UPLOAD_DESTINATION == 'tidepool':
            last_upload = self.upload_api.last_uploaded_entry('deviceEvent', time_start=time_start, time_end=time_end, subtype='alarm', annotation_code='tconnectsync/cgm-alert')
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["time"])
            logger.info("Last Tidepool cgmalert upload: %s" % last_upload_time)
        else:
            last_upload = self.upload_api.last_uploaded_entry(CGM_ALERT_EVENTTYPE, time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["created_at"])
            logger.info("Last Nightscout cgmalert upload: %s" % last_upload_time)

        alertEvents = []
        for event in sorted(events, key=lambda x: x.eventTimestamp):
            if last_upload_time and arrow.get(event.eventTimestamp) <= last_upload_time:
                if self.pretend:
                    logger.info("Skipping %s not after last upload time: %s (time range: %s - %s)" % (type(event), event, time_start, time_end))
                continue

            alertEvents.append(event)

        alertEvents.sort(key=lambda e: e.eventTimestamp)

        upload_entries = []
        for event in alertEvents:
            e = self.alert_to_entry(event)
            if e:
                upload_entries.append(e)

        return upload_entries

    def write(self, upload_entries):
        count = 0
        destination = "Tidepool" if UPLOAD_DESTINATION == 'tidepool' else "Nightscout"
        
        for entry in upload_entries:
            if self.pretend:
                logger.info("Would upload to %s: %s" % (destination, entry))
            else:
                logger.info("Uploading to %s: %s" % (destination, entry))
                self.upload_api.upload_entry(entry)
            count += 1

        return count

    def alert_to_entry(self, alert):
        if UPLOAD_DESTINATION == 'tidepool':
            return self.alert_to_tidepool(alert)
        else:
            return self.alert_to_nsentry(alert)
    
    def alert_to_tidepool(self, alert):
        if not alert.dalertid:
            logger.info("ProcessCGMAlert: Skipping alert with unknown dalertid %d: %s" % (alert.dalertidRaw, alert))
            return None

        if type(alert) == eventtypes.LidCgmAlertActivated:
            return TidepoolEntry.cgm_alert(
                created_at = alert.eventTimestamp.format(),
                reason = ("CGM Alert (%s)" % alert.dalertid.name) if alert.dalertid else "CGM Alert (Unknown)",
                pump_event_id = "%s" % alert.seqNum
            )
        elif type(alert) == eventtypes.LidCgmAlertActivatedDex:
            if alert.dalertid == eventtypes.LidCgmAlertActivatedDex.DalertidEnum.CgmOutOfRange:
                logger.info("ProcessCGMAlert: Skipping alert with CgmOutOfRange dalertid %d: %s" % (alert.dalertidRaw, alert))
                return None
            return TidepoolEntry.cgm_alert(
                created_at = alert.eventTimestamp.format(),
                reason = ("Dexcom CGM Alert (%s)" % alert.dalertid.name) if alert.dalertid else "Dexcom CGM Alert (Unknown)",
                pump_event_id = "%s" % alert.seqNum
            )
        elif type(alert) == eventtypes.LidCgmAlertActivatedFsl2:
            return TidepoolEntry.cgm_alert(
                created_at = alert.eventTimestamp.format(),
                reason = ("Libre CGM Alert (%s)" % alert.dalertid.name) if alert.dalertid else "Libre CGM Alert (Unknown)",
                pump_event_id = "%s" % alert.seqNum
            )

    def alert_to_nsentry(self, alert):
        if not alert.dalertid:
            logger.info("ProcessCGMAlert: Skipping alert with unknown dalertid %d: %s" % (alert.dalertidRaw, alert))
            return None

        if type(alert) == eventtypes.LidCgmAlertActivated:
            return NightscoutEntry.cgm_alert(
                created_at = alert.eventTimestamp.format(),
                reason = ("CGM Alert (%s)" % alert.dalertid.name) if alert.dalertid else "CGM Alert (Unknown)",
                pump_event_id = "%s" % alert.seqNum
            )
        elif type(alert) == eventtypes.LidCgmAlertActivatedDex:
            if alert.dalertid == eventtypes.LidCgmAlertActivatedDex.DalertidEnum.CgmOutOfRange:
                logger.info("ProcessCGMAlert: Skipping alert with CgmOutOfRange dalertid %d: %s" % (alert.dalertidRaw, alert))
                return None
            return NightscoutEntry.cgm_alert(
                created_at = alert.eventTimestamp.format(),
                reason = ("Dexcom CGM Alert (%s)" % alert.dalertid.name) if alert.dalertid else "Dexcom CGM Alert (Unknown)",
                pump_event_id = "%s" % alert.seqNum
            )
        elif type(alert) == eventtypes.LidCgmAlertActivatedFsl2:
            return NightscoutEntry.cgm_alert(
                created_at = alert.eventTimestamp.format(),
                reason = ("Libre CGM Alert (%s)" % alert.dalertid.name) if alert.dalertid else "Libre CGM Alert (Unknown)",
                pump_event_id = "%s" % alert.seqNum
            )