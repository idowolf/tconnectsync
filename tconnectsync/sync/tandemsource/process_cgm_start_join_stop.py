import logging
import arrow

from ...features import DEFAULT_FEATURES
from ... import features
from ...eventparser.generic import Events, decode_raw_events, EVENT_LEN
from ...eventparser.utils import bitmask_to_list
from ...eventparser import events as eventtypes
from ...domain.tandemsource.event_class import EventClass
from ...parser.nightscout import (
    CGM_START_EVENTTYPE,
    CGM_JOIN_EVENTTYPE,
    CGM_STOP_EVENTTYPE,
    NightscoutEntry
)
from ...parser.tidepool import TidepoolEntry
from ...secret import UPLOAD_DESTINATION

logger = logging.getLogger(__name__)

class ProcessCGMStartJoinStop:
    def __init__(self, tconnect, upload_api, tconnect_device_id, pretend, features=DEFAULT_FEATURES):
        self.tconnect = tconnect
        self.upload_api = upload_api
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features

    def enabled(self):
        return features.PUMP_EVENTS in self.features or features.CGM_ALERTS in self.features

    def process(self, events, time_start, time_end):
        if UPLOAD_DESTINATION == 'tidepool':
            # Tidepool doesn't support explicit CGM sensor start/stop/join events
            # The presence of CGM data (cbg entries) implies an active sensor
            logger.info("ProcessCGMStartJoinStop: Skipping CGM session events for Tidepool (not supported)")
            return []
        
        # For Nightscout, query multiple event types
        last_upload = None
        last_upload_time = None
        for eventtype in [CGM_START_EVENTTYPE, CGM_JOIN_EVENTTYPE, CGM_STOP_EVENTTYPE]:
            logger.debug("ProcessCGMStartJoinStop: querying for last uploaded entry for %s" % eventtype)
            _last_upload = self.upload_api.last_uploaded_entry(eventtype, time_start=time_start, time_end=time_end)
            _last_upload_time = None
            if _last_upload:
                _last_upload_time = arrow.get(_last_upload["created_at"])

                if not last_upload_time:
                    last_upload = _last_upload
                    last_upload_time = _last_upload_time
                elif _last_upload_time > last_upload_time:
                    last_upload = _last_upload
                    last_upload_time = _last_upload_time
            logger.info("ProcessCGMStartJoinStop: Last Nightscout %s upload: %s" % (eventtype, _last_upload_time))
        logger.info("ProcessCGMStartJoinStop: Overall last Nightscout upload: %s %s" % (last_upload_time, last_upload))

        allEvents = []
        for event in sorted(events, key=lambda x: x.eventTimestamp):
            if last_upload_time and arrow.get(event.eventTimestamp) <= last_upload_time:
                if self.pretend:
                    logger.info("ProcessCGMStartJoinStop: Skipping %s not after last upload time: %s (time range: %s - %s)" % (type(event), event, time_start, time_end))
                continue

            allEvents.append(event)

        allEvents.sort(key=lambda e: e.eventTimestamp)

        upload_entries = []
        for event in allEvents:
            upload_entries.append(self.to_entry(event))

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

    def to_entry(self, event):
        if UPLOAD_DESTINATION == 'tidepool':
            return self.to_tidepool(event)
        else:
            return self.to_nsentry(event)
    
    def to_tidepool(self, event):
        if type(event) in EventClass._CGM_START:
            return TidepoolEntry.cgm_start(
                created_at = event.eventTimestamp.format(),
                reason = "CGM Session Started",
                pump_event_id = "%s" % event.seqNum
            )
        elif type(event) in EventClass._CGM_JOIN:
            return TidepoolEntry.cgm_join(
                created_at = event.eventTimestamp.format(),
                reason = "CGM Session Joined",
                pump_event_id = "%s" % event.seqNum
            )
        elif type(event) in EventClass._CGM_STOP:
            return TidepoolEntry.cgm_stop(
                created_at = event.eventTimestamp.format(),
                reason = "CGM Session Stopped",
                pump_event_id = "%s" % event.seqNum
            )

    def to_nsentry(self, event):
        if type(event) in EventClass._CGM_START:
            return NightscoutEntry.cgm_start(
                created_at = event.eventTimestamp.format(),
                reason = "CGM Session Started",
                pump_event_id = "%s" % event.seqNum
            )
        elif type(event) in EventClass._CGM_JOIN:
            return NightscoutEntry.cgm_join(
                created_at = event.eventTimestamp.format(),
                reason = "CGM Session Joined",
                pump_event_id = "%s" % event.seqNum
            )
        elif type(event) in EventClass._CGM_STOP:
            return NightscoutEntry.cgm_stop(
                created_at = event.eventTimestamp.format(),
                reason = "CGM Session Stopped",
                pump_event_id = "%s" % event.seqNum
            )