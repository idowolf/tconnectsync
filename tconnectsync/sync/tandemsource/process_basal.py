import datetime
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

from typing import Iterable, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from ...api import TConnectApi
    from ...eventparser.raw_event import BaseEvent

logger = logging.getLogger(__name__)

class ProcessBasal:
    def __init__(self, tconnect: "TConnectApi", upload_api, tconnect_device_id: str, pretend: bool, features: List[str] = DEFAULT_FEATURES) -> None:
        self.tconnect = tconnect
        self.upload_api = upload_api  # Can be NightscoutApi or TidepoolApi
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features

    def enabled(self) -> bool:
        return features.BASAL in self.features

    def process(self, events: Iterable, time_start: arrow.Arrow, time_end: arrow.Arrow) -> List[dict]:
        logger.debug("ProcessBasal: querying for last uploaded entry")
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
        # For Tidepool: skip the still-open segment; its true duration is only
        #   known once the next basal event arrives. Since it was never uploaded,
        #   it stays after the last-upload time and is picked up on the next sync.
        #   Uploading it with a guessed duration would fabricate delivery data and
        #   create overlapping basal records on subsequent syncs.
        # For Nightscout: Truncate at time_end (original behavior)
        if UPLOAD_DESTINATION == 'tidepool':
            skipped = with_duration.pop()
            logger.info("Skipping still-open basal segment starting %s; it will sync once its end is known" % skipped[0])
            if not with_duration:
                logger.info("No completed basal events found to process")
                return []
        else:
            with_duration[-1][1] = time_end - with_duration[-1][0]

        upload_entries = []
        for item in with_duration:
            entry = self.basal_to_entry(*item)
            if entry:
                upload_entries.append(entry)

        return upload_entries

    def write(self, upload_entries: List[dict]) -> int:
        count = 0
        if UPLOAD_DESTINATION == 'tidepool':
            # For Tidepool, upload all basal entries in a single batch to maintain sequence
            if upload_entries:
                if self.pretend:
                    for entry in upload_entries:
                        logger.info("Would upload to Tidepool: %s" % entry)
                    count = len(upload_entries)
                else:
                    # Sort entries by time to ensure proper sequence
                    upload_entries.sort(key=lambda x: x.get('time', ''))

                    logger.info("Uploading %d basal entries to Tidepool in batch..." % len(upload_entries))
                    self.upload_api.upload_entries(upload_entries)
                    count = len(upload_entries)
        else:
            for entry in upload_entries:
                if self.pretend:
                    logger.info("Would upload to Nightscout: %s" % entry)
                else:
                    logger.info("Uploading to Nightscout: %s" % entry)
                    self.upload_api.upload_entry(entry)
                count += 1

        return count


    def basal_to_entry(self, start: arrow.Arrow, duration: datetime.timedelta, event: "BaseEvent") -> Optional[dict]:
        entry_cls = TidepoolEntry if UPLOAD_DESTINATION == 'tidepool' else NightscoutEntry
        if type(event) == eventtypes.LidBasalRateChange:
            value = insulin_float_round(event.commandedBasalRate)
            if IGNORE_ZERO_UNIT_BASAL and value < 0.01:
                logger.info("Ignoring basal entry with %.2f unit basal because IGNORE_ZERO_UNIT_BASAL=true: %s" % (value, event))
                return None
            return entry_cls.basal(
                value = value,
                duration_mins = duration.total_seconds() / 60,
                created_at = start.format(),
                reason = ', '.join(bitmask_to_list(event.changeType)),
                pump_event_id = "%s" % event.seqNum
            )
        if type(event) == eventtypes.LidBasalDelivery:
            value = insulin_milliunits_to_real(event.commandedRate)
            if IGNORE_ZERO_UNIT_BASAL and value < 0.01:
                logger.info("Ignoring basal entry with %.2f unit basal because IGNORE_ZERO_UNIT_BASAL=true: %s" % (value, event))
                return None
            return entry_cls.basal(
                value = value,
                duration_mins = duration.total_seconds() / 60,
                created_at = start.format(),
                reason = ', '.join(bitmask_to_list(event.commandedRateSource)),
                pump_event_id = "%s" % event.seqNum
            )

    # Backwards-compatible alias for the Nightscout-only converter
    def basal_to_nsentry(self, start: arrow.Arrow, duration: datetime.timedelta, event: "BaseEvent") -> Optional[dict]:
        return self.basal_to_entry(start, duration, event)
