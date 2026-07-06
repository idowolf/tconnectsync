import logging
import arrow

from typing import Iterable, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from ...api import TConnectApi
    from ...eventparser.raw_event import BaseEvent

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
    def __init__(self, tconnect: "TConnectApi", upload_api, tconnect_device_id: str, pretend: bool, features: List[str] = DEFAULT_FEATURES) -> None:
        self.tconnect = tconnect
        self.upload_api = upload_api  # Can be NightscoutApi or TidepoolApi
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features

    def enabled(self) -> bool:
        return features.PUMP_EVENTS in self.features

    def process(self, events: Iterable, time_start: arrow.Arrow, time_end: arrow.Arrow) -> List[dict]:
        logger.debug("ProcessBasalResume: querying for last uploaded resume-suspension")
        if UPLOAD_DESTINATION == 'tidepool':
            return self.process_tidepool(events, time_start, time_end)
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

            entry = self.resume_to_entry(event)
            if entry:
                upload_entries.append(entry)


        return upload_entries

    def write(self, upload_entries: List[dict]) -> int:
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


    def process_tidepool(self, events: Iterable, time_start: arrow.Arrow, time_end: arrow.Arrow) -> List[dict]:
        # Tidepool does not store resume events as separate records: a resume
        # carrying previous=<the suspend datum> completes that suspension by
        # setting its duration. So instead of dedup by last-uploaded resume,
        # match each resume event to the nearest preceding stored suspension
        # that hasn't been completed yet (no duration).
        suspends = self.upload_api.uploaded_entries('deviceEvent', time_start=time_start, time_end=time_end, subtype='status', status='suspended')
        open_suspends = [s for s in suspends if 'duration' not in s]
        logger.info("ProcessBasalResume: %d stored suspensions in window, %d incomplete" % (len(suspends), len(open_suspends)))

        upload_entries = []
        for event in sorted(events, key=lambda x: x.eventTimestamp):
            entry = self.resume_to_tidepool(event)
            if not entry:
                continue

            # Nearest incomplete suspension at or before the resume time
            resume_time = arrow.get(entry['time'])
            match = None
            for suspend in open_suspends:
                if arrow.get(suspend['time']) <= resume_time:
                    match = suspend
                else:
                    break

            if not match:
                logger.info("ProcessBasalResume: Skipping resume with no incomplete suspension to complete: %s" % event)
                continue

            open_suspends.remove(match)
            TidepoolEntry.link_previous(entry, match)
            upload_entries.append(entry)

        return upload_entries

    def resume_to_entry(self, event: "BaseEvent") -> Optional[dict]:
        if UPLOAD_DESTINATION == 'tidepool':
            return self.resume_to_tidepool(event)
        return self.resume_to_nsentry(event)

    def resume_to_tidepool(self, event: "BaseEvent") -> Optional[dict]:
        if type(event) == eventtypes.LidPumpingResumed:
            return TidepoolEntry.basalresume(
                created_at = event.eventTimestamp.format(),
                pump_event_id = "%s" % event.seqNum
            )

    def resume_to_nsentry(self, event: "BaseEvent") -> Optional[dict]:
        if type(event) == eventtypes.LidPumpingResumed:
            return NightscoutEntry.basalresume(
                created_at = event.eventTimestamp.format(),
                pump_event_id = "%s" % event.seqNum
            )
