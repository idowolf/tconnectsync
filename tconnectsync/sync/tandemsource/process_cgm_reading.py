import logging
import arrow

from ...features import DEFAULT_FEATURES
from ... import features
from ...eventparser.generic import Events, decode_raw_events, EVENT_LEN
from ...eventparser.utils import bitmask_to_list
from ...eventparser.raw_event import TANDEM_EPOCH
from ...eventparser import events as eventtypes
from ...domain.tandemsource.event_class import EventClass
from ...parser.nightscout import (
    CGM_START_EVENTTYPE,
    NightscoutEntry
)
from ...parser.tidepool import TidepoolEntry
from ...secret import UPLOAD_DESTINATION, TIMEZONE_NAME

logger = logging.getLogger(__name__)

class ProcessCGMReading:
    def __init__(self, tconnect, upload_api, tconnect_device_id, pretend, features=DEFAULT_FEATURES):
        self.tconnect = tconnect
        self.upload_api = upload_api  # Can be NightscoutApi or TidepoolApi
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features

    def enabled(self):
        return features.CGM in self.features

    def process(self, events, time_start, time_end):
        logger.debug("ProcessCGMReading: querying for last uploaded entry")
        
        # Query for last upload based on destination
        if UPLOAD_DESTINATION == 'tidepool':
            # Only look at cbg (CGM) entries: smbg entries come from bolus BG
            # readings and would wrongly mask not-yet-uploaded CGM history.
            last_upload = self.upload_api.last_uploaded_entry('cbg', time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["time"])
            logger.info("ProcessCGMReading: Last Tidepool cbg upload: %s" % last_upload_time)
        else:
            last_upload = self.upload_api.last_uploaded_bg_entry(time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload and "dateString" in last_upload:
                last_upload_time = arrow.get(last_upload["dateString"])
            elif last_upload and "date" in last_upload:
                last_upload_time = arrow.get(last_upload["date"])
            logger.info("ProcessCGMReading: Last Nightscout bg upload: %s" % last_upload_time)

        readings = []
        for event in sorted(events, key=lambda x: self.timestamp_for(x)):
            if last_upload_time and self.timestamp_for(event) <= last_upload_time:
                if self.pretend:
                    logger.info("ProcessCGMReading: Skipping %s not after last upload time: %s (time range: %s - %s)" % (type(event), event, time_start, time_end))
                continue

            # Out-of-range (high/low) readings report a display value of 0,
            # which must not be uploaded as an actual glucose value
            if not event.currentglucosedisplayvalue or event.currentglucosedisplayvalue <= 0:
                logger.info("ProcessCGMReading: Skipping out-of-range/empty CGM reading: %s" % event)
                continue

            readings.append(event)

        upload_entries = []
        for event in readings:
            upload_entries.append(self.to_entry(event))

        return upload_entries

    def write(self, upload_entries):
        count = 0
        destination = "Tidepool" if UPLOAD_DESTINATION == 'tidepool' else "Nightscout"

        if UPLOAD_DESTINATION == 'tidepool':
            # Upload CGM readings in a single batch; a backfill can contain
            # hundreds of readings and per-entry requests are slow.
            if upload_entries:
                if self.pretend:
                    for entry in upload_entries:
                        logger.info("Would upload to %s: %s" % (destination, entry))
                else:
                    logger.info("Uploading %d CGM readings to Tidepool in batch..." % len(upload_entries))
                    self.upload_api.upload_entries(upload_entries)
                count = len(upload_entries)
        else:
            for entry in upload_entries:
                if self.pretend:
                    logger.info("Would upload to %s: %s" % (destination, entry))
                else:
                    logger.info("Uploading to %s: %s" % (destination, entry))
                    self.upload_api.upload_entry(entry, entity='entries')
                count += 1

        return count

    def timestamp_for(self, event):
        # For backfills the time the event was added to the pump's event store
        # might not be the time it actually occurred, so we use the egvTimestamp.
        # Like all pump event timestamps, egvTimestamp is in the pump's local
        # wall-clock time, not UTC (see RawEvent.timestamp).
        return arrow.get(TANDEM_EPOCH + event.egvTimestamp, tzinfo='UTC').replace(tzinfo=TIMEZONE_NAME)

    def to_entry(self, event):
        """
        Convert CGM reading to either Nightscout or Tidepool format based on UPLOAD_DESTINATION.
        """
        if UPLOAD_DESTINATION == 'tidepool':
            return self.to_tidepool(event)
        else:
            return self.to_nsentry(event)
    
    def to_tidepool(self, event):
        """
        Convert CGM reading to Tidepool format.
        """
        return TidepoolEntry.cgm(
            sgv = event.currentglucosedisplayvalue,
            created_at = self.timestamp_for(event).format(),
            pump_event_id = "%s" % event.seqNum,
        )

    def to_nsentry(self, event):
        """
        Convert CGM reading to Nightscout format (original implementation).
        """
        return NightscoutEntry.entry(
            sgv = event.currentglucosedisplayvalue,
            created_at = self.timestamp_for(event).format(),
            pump_event_id = "%s" % event.seqNum,
        )
