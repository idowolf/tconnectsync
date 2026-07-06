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
    ALARM_EVENTTYPE,
    NightscoutEntry
)
from ...parser.tidepool import TidepoolEntry
from ...secret import UPLOAD_DESTINATION

logger = logging.getLogger(__name__)

class ProcessAlarm:
    def __init__(self, tconnect: "TConnectApi", upload_api, tconnect_device_id: str, pretend: bool, features: List[str] = DEFAULT_FEATURES) -> None:
        self.tconnect = tconnect
        self.upload_api = upload_api  # Can be NightscoutApi or TidepoolApi
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features

    def enabled(self) -> bool:
        return features.PUMP_EVENTS in self.features

    def process(self, events: Iterable, time_start: arrow.Arrow, time_end: arrow.Arrow) -> List[dict]:
        logger.debug("ProcessAlarm: querying for last uploaded alarm")
        if UPLOAD_DESTINATION == 'tidepool':
            last_upload = self.upload_api.last_uploaded_entry('deviceEvent', time_start=time_start, time_end=time_end, subtype='alarm', annotation_code='tconnectsync/alarm')
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["time"])
            logger.info("Last Tidepool alarm upload: %s" % last_upload_time)
        else:
            last_upload = self.upload_api.last_uploaded_entry(ALARM_EVENTTYPE, time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["created_at"])
            logger.info("Last Nightscout alarm upload: %s" % last_upload_time)

        upload_entries = []
        for event in sorted(events, key=lambda x: x.eventTimestamp):
            if last_upload_time and arrow.get(event.eventTimestamp) <= last_upload_time:
                if self.pretend:
                    logger.info("Skipping Alarm event not after last upload time: %s (time range: %s - %s)" % (event, time_start, time_end))
                continue

            if self.skip_event(event):
                continue

            entry = self.alarm_to_entry(event)
            if entry:
                upload_entries.append(entry)


        return upload_entries

    def skip_event(self, event: "BaseEvent") -> bool:
        return event.alarmId in (
            eventtypes.LidAlarmActivated.AlarmidEnum.ResumePumpAlarm,
            eventtypes.LidAlarmActivated.AlarmidEnum.ResumePumpAlarm2
        )

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


    def alarm_to_entry(self, event: "BaseEvent") -> Optional[dict]:
        if UPLOAD_DESTINATION == 'tidepool':
            return self.alarm_to_tidepool(event)
        return self.alarm_to_nsentry(event)

    def alarm_to_tidepool(self, event: "BaseEvent") -> Optional[dict]:
        if type(event) == eventtypes.LidAlarmActivated:
            return TidepoolEntry.alarm(
                created_at = event.eventTimestamp.format(),
                reason = "%s" % event.alarmId.name,
                pump_event_id = "%s" % event.seqNum
            )
        elif type(event) == eventtypes.LidMalfunctionActivated:
            return TidepoolEntry.alarm(
                created_at = event.eventTimestamp.format(),
                reason = "Malfunction",
                pump_event_id = "%s" % event.seqNum
            )

    def alarm_to_nsentry(self, event: "BaseEvent") -> Optional[dict]:
        if type(event) == eventtypes.LidAlarmActivated:
            return NightscoutEntry.alarm(
                created_at = event.eventTimestamp.format(),
                reason = "%s" % event.alarmId.name,
                pump_event_id = "%s" % event.seqNum
            )
        elif type(event) == eventtypes.LidMalfunctionActivated:
            return NightscoutEntry.alarm(
                created_at = event.eventTimestamp.format(),
                reason = "Malfunction",
                pump_event_id = "%s" % event.seqNum
            )
