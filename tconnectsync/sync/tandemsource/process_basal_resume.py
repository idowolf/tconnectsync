import logging
import arrow

from ...features import DEFAULT_FEATURES
from ... import features
from ...eventparser.generic import Events, decode_raw_events, EVENT_LEN
from ...eventparser.utils import bitmask_to_list
from ...eventparser import events as eventtypes
from ...domain.tandemsource.event_class import EventClass
from ...parser.nightscout import (
    BASALRESUME_EVENTTYPE,
    NightscoutEntry
)
from ...parser.tidepool import TidepoolEntry
from ...secret import UPLOAD_DESTINATION

logger = logging.getLogger(__name__)

class ProcessBasalResume:
    def __init__(self, tconnect, upload_api, tconnect_device_id, pretend, features=DEFAULT_FEATURES):
        self.tconnect = tconnect
        self.upload_api = upload_api
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features

    def enabled(self):
        return features.PUMP_EVENTS in self.features

    def process(self, events, time_start, time_end):
        logger.debug("ProcessBasalResume: querying for last uploaded resume-suspension")
        
        if UPLOAD_DESTINATION == 'tidepool':
            last_upload = self.upload_api.last_uploaded_entry('deviceEvent', time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["time"])
            logger.info("Last Tidepool BasalResume upload: %s" % last_upload_time)
        else:
            last_upload = self.upload_api.last_uploaded_entry(BASALRESUME_EVENTTYPE, time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["created_at"])
            logger.info("Last Nightscout BasalResume upload: %s" % last_upload_time)

        upload_entries = []
        for event in sorted(events, key=lambda x: x.eventTimestamp):
            if last_upload_time and arrow.get(event.eventTimestamp) <= last_upload_time:
                if self.pretend:
                    logger.info("Skipping BasalResume event not after last upload time: %s (time range: %s - %s)" % (event, time_start, time_end))
                continue

            upload_entries.append(self.resume_to_entry(event))


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

    def resume_to_entry(self, event):
        if UPLOAD_DESTINATION == 'tidepool':
            return self.resume_to_tidepool(event)
        else:
            return self.resume_to_nsentry(event)
    
    def resume_to_tidepool(self, event):
        if type(event) == eventtypes.LidPumpingResumed:
            return TidepoolEntry.basalresume(
                created_at = event.eventTimestamp.format(),
                pump_event_id = "%s" % event.seqNum
            )

    def resume_to_nsentry(self, event):
        if type(event) == eventtypes.LidPumpingResumed:
            return NightscoutEntry.basalresume(
                created_at = event.eventTimestamp.format(),
                pump_event_id = "%s" % event.seqNum
            )