import logging
import arrow

from ...features import DEFAULT_FEATURES
from ... import features
from ...eventparser.generic import Events, decode_raw_events, EVENT_LEN
from ...eventparser.utils import bitmask_to_list
from ...eventparser import events as eventtypes
from ...domain.tandemsource.event_class import EventClass
from ...parser.nightscout import (
    BASALSUSPENSION_EVENTTYPE,
    NightscoutEntry
)
from ...parser.tidepool import TidepoolEntry
from ...secret import UPLOAD_DESTINATION

logger = logging.getLogger(__name__)

class ProcessBasalSuspension:
    def __init__(self, tconnect, upload_api, tconnect_device_id, pretend, features=DEFAULT_FEATURES):
        self.tconnect = tconnect
        self.upload_api = upload_api
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features

    def enabled(self):
        return features.PUMP_EVENTS in self.features or features.BASAL in self.features

    def process(self, events, time_start, time_end):
        logger.debug("ProcessBasalSuspension: querying for last uploaded suspension")
        
        if UPLOAD_DESTINATION == 'tidepool':
            last_upload = self.upload_api.last_uploaded_entry('deviceEvent', time_start=time_start, time_end=time_end, subtype='status', status='suspended')
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["time"])
            logger.info("Last Tidepool basalsuspension upload: %s" % last_upload_time)
        else:
            last_upload = self.upload_api.last_uploaded_entry(BASALSUSPENSION_EVENTTYPE, time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["created_at"])
            logger.info("Last Nightscout basalsuspension upload: %s" % last_upload_time)

        upload_entries = []
        for event in sorted(events, key=lambda x: x.eventTimestamp):
            if last_upload_time and arrow.get(event.eventTimestamp) <= last_upload_time:
                if self.pretend:
                    logger.info("Skipping basalsuspension event not after last upload time: %s (time range: %s - %s)" % (event, time_start, time_end))
                continue

            upload_entries.append(self.suspension_to_entry(event))


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

    def suspension_to_entry(self, event):
        if UPLOAD_DESTINATION == 'tidepool':
            return self.suspension_to_tidepool(event)
        else:
            return self.suspension_to_nsentry(event)
    
    def suspension_to_tidepool(self, event):
        if type(event) == eventtypes.LidPumpingSuspended:
            return TidepoolEntry.basalsuspension(
                created_at = event.eventTimestamp.format(),
                reason = ', '.join(bitmask_to_list(event.suspendreason)),
                pump_event_id = "%s" % event.seqNum
            )

    def suspension_to_nsentry(self, event):
        if type(event) == eventtypes.LidPumpingSuspended:
            return NightscoutEntry.basalsuspension(
                created_at = event.eventTimestamp.format(),
                reason = ', '.join(bitmask_to_list(event.suspendreason)),
                pump_event_id = "%s" % event.seqNum
            )
