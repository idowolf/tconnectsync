import logging
import arrow

from ...secret import IGNORE_ZERO_UNIT_BASAL, UPLOAD_DESTINATION
from ...features import DEFAULT_FEATURES
from ... import features
from ...eventparser.generic import Events, decode_raw_events, EVENT_LEN
from ...eventparser.utils import bitmask_to_list
from ...eventparser import events as eventtypes
from .helpers import insulin_float_round, insulin_milliunits_to_real
from ...domain.tandemsource.event_class import EventClass
from ...parser.nightscout import (
    BASAL_EVENTTYPE,
    NightscoutEntry
)
from ...parser.tidepool import TidepoolEntry

logger = logging.getLogger(__name__)

class ProcessBasal:
    def __init__(self, tconnect, upload_api, tconnect_device_id, pretend, features=DEFAULT_FEATURES):
        self.tconnect = tconnect
        self.upload_api = upload_api  # Can be NightscoutApi or TidepoolApi
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features

    def enabled(self):
        return features.BASAL in self.features

    def process(self, events, time_start, time_end):
        logger.debug("ProcessBasal: querying for last uploaded entry")
        
        # Query for last upload based on destination
        if UPLOAD_DESTINATION == 'tidepool':
            last_upload = self.upload_api.last_uploaded_entry('basal', time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["time"])
            logger.info("Last Tidepool basal upload: %s" % last_upload_time)
        else:
            last_upload = self.upload_api.last_uploaded_entry(BASAL_EVENTTYPE, time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["created_at"])
            logger.info("Last Nightscout basal upload: %s" % last_upload_time)

        with_duration = []
        for event in sorted(events, key=lambda x: x.eventTimestamp):
            if last_upload_time and arrow.get(event.eventTimestamp) <= last_upload_time:
                if self.pretend:
                    logger.info("Skipping basal event not after last upload time: %s (time range: %s - %s)" % (event, time_start, time_end))
                continue

            with_duration.append([event.eventTimestamp, None, event])

        if not with_duration:
            logger.info("No basal events found to process")
            return []

        for i in range(len(with_duration)-1):
            with_duration[i][1] = with_duration[i+1][0] - with_duration[i][0]

        # For the last basal, we need to determine its duration
        # For Tidepool: Use a generous duration to avoid gaps between sync periods
        # For Nightscout: Truncate at time_end (original behavior)
        if UPLOAD_DESTINATION == 'tidepool':
            # Extend last basal to end of day or 24 hours, whichever is longer
            # This prevents gaps when syncing consecutive date ranges
            last_basal_start = with_duration[-1][0]
            end_of_day = last_basal_start.ceil('day')  # Round up to end of day
            duration_to_end_of_day = end_of_day - last_basal_start
            duration_to_time_end = time_end - last_basal_start
            
            # Use the longer duration to ensure continuity
            with_duration[-1][1] = max(duration_to_end_of_day, duration_to_time_end)
            logger.debug("Last basal duration set to %s (extends to end of day to avoid gaps)" % with_duration[-1][1])
        else:
            with_duration[-1][1] = time_end - with_duration[-1][0]

        upload_entries = []
        for item in with_duration:
            entry = self.basal_to_entry(*item)
            if entry:
                upload_entries.append(entry)

        return upload_entries

    def write(self, upload_entries):
        count = 0
        destination = "Tidepool" if UPLOAD_DESTINATION == 'tidepool' else "Nightscout"
        
        if UPLOAD_DESTINATION == 'tidepool':
            # For Tidepool, upload all basal entries in a single batch to maintain sequence
            if upload_entries:
                if self.pretend:
                    for entry in upload_entries:
                        logger.info("Would upload to %s: %s" % (destination, entry))
                    count = len(upload_entries)
                else:
                    # Sort entries by time to ensure proper sequence
                    upload_entries.sort(key=lambda x: x.get('time', ''))
                    
                    logger.info("Uploading %d basal entries to Tidepool in batch..." % len(upload_entries))
                    self.upload_api.upload_entries(upload_entries)
                    count = len(upload_entries)
                    logger.info("✓ Uploaded %d basal entries successfully" % count)
        else:
            # For Nightscout, upload one at a time (original behavior)
            for entry in upload_entries:
                if self.pretend:
                    logger.info("Would upload to %s: %s" % (destination, entry))
                else:
                    logger.info("Uploading to %s: %s" % (destination, entry))
                    self.upload_api.upload_entry(entry)
                count += 1

        return count

    def basal_to_entry(self, start, duration, event):
        """
        Convert basal event to either Nightscout or Tidepool format based on UPLOAD_DESTINATION.
        """
        if UPLOAD_DESTINATION == 'tidepool':
            return self.basal_to_tidepool(start, duration, event)
        else:
            return self.basal_to_nsentry(start, duration, event)
    
    def basal_to_tidepool(self, start, duration, event):
        """
        Convert basal event to Tidepool format.
        """
        if type(event) == eventtypes.LidBasalRateChange:
            value = insulin_float_round(event.commandedbasalrate)
            if IGNORE_ZERO_UNIT_BASAL and value < 0.01:
                logger.info("Ignoring basal entry with %.2f unit basal because IGNORE_ZERO_UNIT_BASAL=true: %s" % (value, event))
                return None
            return TidepoolEntry.basal(
                value = value,
                duration_mins = duration.seconds / 60,
                created_at = start.format(),
                reason = ', '.join(bitmask_to_list(event.changetype)),
                pump_event_id = "%s" % event.seqNum
            )
        if type(event) == eventtypes.LidBasalDelivery:
            value = insulin_milliunits_to_real(event.commandedRate)
            if IGNORE_ZERO_UNIT_BASAL and value < 0.01:
                logger.info("Ignoring basal entry with %.2f unit basal because IGNORE_ZERO_UNIT_BASAL=true: %s" % (value, event))
                return None
            return TidepoolEntry.basal(
                value = value,
                duration_mins = duration.seconds / 60,
                created_at = start.format(),
                reason = ', '.join(bitmask_to_list(event.commandedRateSource)),
                pump_event_id = "%s" % event.seqNum
            )

    def basal_to_nsentry(self, start, duration, event):
        """
        Convert basal event to Nightscout format (original implementation).
        """
        if type(event) == eventtypes.LidBasalRateChange:
            value = insulin_float_round(event.commandedbasalrate)
            if IGNORE_ZERO_UNIT_BASAL and value < 0.01:
                logger.info("Ignoring basal entry with %.2f unit basal because IGNORE_ZERO_UNIT_BASAL=true: %s" % (value, event))
                return None
            return NightscoutEntry.basal(
                value = value,
                duration_mins = duration.seconds / 60,
                created_at = start.format(),
                reason = ', '.join(bitmask_to_list(event.changetype)),
                pump_event_id = "%s" % event.seqNum
            )
        if type(event) == eventtypes.LidBasalDelivery:
            value = insulin_milliunits_to_real(event.commandedRate)
            if IGNORE_ZERO_UNIT_BASAL and value < 0.01:
                logger.info("Ignoring basal entry with %.2f unit basal because IGNORE_ZERO_UNIT_BASAL=true: %s" % (value, event))
                return None
            return NightscoutEntry.basal(
                value = value,
                duration_mins = duration.seconds / 60,
                created_at = start.format(),
                reason = ', '.join(bitmask_to_list(event.commandedRateSource)),
                pump_event_id = "%s" % event.seqNum
            )
