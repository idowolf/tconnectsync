import logging
import arrow

from ...features import DEFAULT_FEATURES
from ... import features
from ... import secret
from ...eventparser.raw_event import TANDEM_EPOCH
from ...eventparser import events as eventtypes
from ...parser.nightscout import NightscoutEntry
from ...parser.tidepool import TidepoolEntry
from ...secret import UPLOAD_DESTINATION

from typing import Iterable, List, Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from ...api import TConnectApi
    from ...nightscout import NightscoutApi
    from ...eventparser.raw_event import BaseEvent

# The four CGM-reading event types share the glucoseValueStatus /
# currentGlucoseDisplayValue fields determine_glucose_value() reads.
CgmReadingEvent = Union[
    eventtypes.LidCgmDataG7,
    eventtypes.LidCgmDataGxb,
    eventtypes.LidCgmDataFsl2,
    eventtypes.LidCgmDataFsl3,
]

logger = logging.getLogger(__name__)

# Mirrors the Tandem Source frontend (CgmBuilder.determineGlucoseValue): out-of-range
# and special readings are reported as sentinel values rather than the raw display value.
GLUCOSE_LIMIT_LOW = 40
GLUCOSE_LIMIT_HIGH = 400
GLUCOSE_VALUE_LOW = 39
GLUCOSE_VALUE_HIGH = 401

def _resolve_glucose_value(display_value, status, *, precise, high, low):
    if status == high:
        return GLUCOSE_VALUE_HIGH
    if status == low:
        return GLUCOSE_VALUE_LOW
    if status == precise:
        if display_value < GLUCOSE_LIMIT_LOW:
            return GLUCOSE_VALUE_LOW
        if display_value > GLUCOSE_LIMIT_HIGH:
            return GLUCOSE_VALUE_HIGH
    return display_value

# Each sensor is handled separately: the glucoseValueStatus enums are NOT assumed
# to be consistent across sensor types (e.g. G6 names its members differently), so
# every branch resolves against that sensor's own enum members.
def determine_glucose_value(event: CgmReadingEvent) -> int:
    display_value = event.currentGlucoseDisplayValue
    status = event.glucoseValueStatus

    if isinstance(event, eventtypes.LidCgmDataG7):
        e = eventtypes.LidCgmDataG7.GlucosevaluestatusEnum
        return _resolve_glucose_value(display_value, status,
                                      precise=e.PreciseValue, high=e.SpecialHigh, low=e.SpecialLow)
    if isinstance(event, eventtypes.LidCgmDataGxb):
        e = eventtypes.LidCgmDataGxb.GlucosevaluestatusEnum
        return _resolve_glucose_value(display_value, status,
                                      precise=e.CurrentglucosedisplayvalueContainsTheGlucoseReading,
                                      high=e.TheGlucoseReadingIsHigh, low=e.TheGlucoseReadingIsLow)
    if isinstance(event, eventtypes.LidCgmDataFsl3):
        e = eventtypes.LidCgmDataFsl3.GlucosevaluestatusEnum
        return _resolve_glucose_value(display_value, status,
                                      precise=e.PreciseValue, high=e.SpecialHigh, low=e.SpecialLow)
    if isinstance(event, eventtypes.LidCgmDataFsl2):
        e = eventtypes.LidCgmDataFsl2.GlucosevaluestatusEnum
        return _resolve_glucose_value(display_value, status,
                                      precise=e.PreciseValue, high=e.SpecialHigh, low=e.SpecialLow)

    return display_value

class ProcessCGMReading:
    def __init__(self, tconnect: "TConnectApi", upload_api, tconnect_device_id: str, pretend: bool, features: List[str] = DEFAULT_FEATURES, timezone: Optional[str] = None) -> None:
        self.tconnect = tconnect
        self.upload_api = upload_api  # Can be NightscoutApi or TidepoolApi
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features
        self.timezone = timezone or secret.TIMEZONE_NAME

    def enabled(self) -> bool:
        return features.CGM in self.features

    def process(self, events: Iterable, time_start: arrow.Arrow, time_end: arrow.Arrow) -> List[dict]:
        logger.debug("ProcessCGMReading: querying for last uploaded entry")
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

            readings.append(event)

        upload_entries = []
        for event in readings:
            upload_entries.append(self.to_entry(event))

        return upload_entries

    def write(self, upload_entries: List[dict]) -> int:
        count = 0
        if UPLOAD_DESTINATION == 'tidepool':
            # Upload CGM readings in a single batch; a backfill can contain
            # hundreds of readings and per-entry requests are slow.
            if upload_entries:
                if self.pretend:
                    for entry in upload_entries:
                        logger.info("Would upload to Tidepool: %s" % entry)
                else:
                    logger.info("Uploading %d CGM readings to Tidepool in batch..." % len(upload_entries))
                    self.upload_api.upload_entries(upload_entries)
                count = len(upload_entries)
        else:
            for entry in upload_entries:
                if self.pretend:
                    logger.info("Would upload to Nightscout: %s" % entry)
                else:
                    logger.info("Uploading to Nightscout: %s" % entry)
                    self.upload_api.upload_entry(entry, entity='entries')
                count += 1

        return count

    def timestamp_for(self, event: "BaseEvent") -> arrow.Arrow:
        # For backfills the time the event was added to the pump's event store
        # might not be the time it actually occurred, so we use the egvTimestamp
        return arrow.get(TANDEM_EPOCH + event.egvTimeStamp, tzinfo='UTC').replace(tzinfo=self.timezone)

    def to_entry(self, event: "BaseEvent") -> Optional[dict]:
        if UPLOAD_DESTINATION == 'tidepool':
            return self.to_tidepool(event)
        return self.to_nsentry(event)

    def to_tidepool(self, event: "BaseEvent") -> Optional[dict]:
        # Out-of-range readings arrive as the same LOW/HIGH sentinel values
        # (39/401 mg/dL) the Tandem Source frontend uses.
        return TidepoolEntry.cgm(
            sgv = determine_glucose_value(event),
            created_at = self.timestamp_for(event).format(),
            pump_event_id = "%s" % event.seqNum,
        )

    def to_nsentry(self, event: "BaseEvent") -> Optional[dict]:
        return NightscoutEntry.entry(
            sgv = determine_glucose_value(event),
            created_at = self.timestamp_for(event).format(),
            pump_event_id = "%s" % event.seqNum,
        )
