import logging
import arrow

from ...features import DEFAULT_FEATURES
from ... import features
from ...eventparser.generic import Events, decode_raw_events, EVENT_LEN
from ...eventparser.utils import bitmask_to_list
from ...eventparser import events as eventtypes
from ...domain.tandemsource.event_class import EventClass
from ...parser.nightscout import (
    SITECHANGE_EVENTTYPE,
    NightscoutEntry
)
from ...parser.tidepool import TidepoolEntry
from ...secret import UPLOAD_DESTINATION

logger = logging.getLogger(__name__)

class ProcessCartridge:
    def __init__(self, tconnect, upload_api, tconnect_device_id, pretend, features=DEFAULT_FEATURES):
        self.tconnect = tconnect
        self.upload_api = upload_api
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features

    def enabled(self):
        return features.PUMP_EVENTS in self.features

    def process(self, events, time_start, time_end):
        logger.debug("ProcessCartridge: querying for last uploaded entry")
        
        if UPLOAD_DESTINATION == 'tidepool':
            last_upload = self.upload_api.last_uploaded_entry('deviceEvent', time_start=time_start, time_end=time_end, subtype='reservoirChange')
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["time"])
            logger.info("Last Tidepool sitechange upload: %s" % last_upload_time)
        else:
            last_upload = self.upload_api.last_uploaded_entry(SITECHANGE_EVENTTYPE, time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["created_at"])
            logger.info("Last Nightscout sitechange upload: %s" % last_upload_time)

        cartFilledEvents = []
        cannulaFilledEvents = []
        tubingFilledEvents = []
        for event in sorted(events, key=lambda x: x.eventTimestamp):
            if last_upload_time and arrow.get(event.eventTimestamp) <= last_upload_time:
                if self.pretend:
                    logger.info("Skipping %s not after last upload time: %s (time range: %s - %s)" % (type(event), event, time_start, time_end))
                continue

            if type(event) == eventtypes.LidCartridgeFilled:
                cartFilledEvents.append(event)
            elif type(event) == eventtypes.LidCannulaFilled:
                cannulaFilledEvents.append(event)
            elif type(event) == eventtypes.LidTubingFilled:
                tubingFilledEvents.append(event)

        cartFilledEvents.sort(key=lambda e: e.eventTimestamp)
        cannulaFilledEvents.sort(key=lambda e: e.eventTimestamp)
        tubingFilledEvents.sort(key=lambda e: e.eventTimestamp)

        upload_entries = []
        for cartFilled in cartFilledEvents:
            upload_entries.append(self.cart_to_entry(cartFilled))

        for cannulaFilled in cannulaFilledEvents:
            upload_entries.append(self.cannula_to_entry(cannulaFilled))

        for tubingFilled in tubingFilledEvents:
            upload_entries.append(self.tubing_to_entry(tubingFilled))


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

    def cart_to_entry(self, cartFilled):
        reason = "Cartridge Filled" + (" (%du filled)" % round(cartFilled.v2Volume) if cartFilled.v2Volume else "")
        if UPLOAD_DESTINATION == 'tidepool':
            return TidepoolEntry.sitechange(
                created_at = cartFilled.eventTimestamp.format(),
                reason = reason,
                pump_event_id = "%s" % cartFilled.seqNum
            )
        else:
            return NightscoutEntry.sitechange(
                created_at = cartFilled.eventTimestamp.format(),
                reason = reason,
                pump_event_id = "%s" % cartFilled.seqNum
            )

    def cannula_to_entry(self, cannulaFilled):
        reason = "Cannula Filled" + (" (%du primed)" % round(cannulaFilled.primesize, 2) if cannulaFilled.primesize else "")
        if UPLOAD_DESTINATION == 'tidepool':
            return TidepoolEntry.sitechange(
                created_at = cannulaFilled.eventTimestamp.format(),
                reason = reason,
                pump_event_id = "%s" % cannulaFilled.seqNum
            )
        else:
            return NightscoutEntry.sitechange(
                created_at = cannulaFilled.eventTimestamp.format(),
                reason = reason,
                pump_event_id = "%s" % cannulaFilled.seqNum
            )

    def tubing_to_entry(self, tubingFilled):
        reason = "Tubing Filled" + (" (%du primed)" % round(tubingFilled.primesize) if tubingFilled.primesize else "")
        if UPLOAD_DESTINATION == 'tidepool':
            return TidepoolEntry.sitechange(
                created_at = tubingFilled.eventTimestamp.format(),
                reason = reason,
                pump_event_id = "%s" % tubingFilled.seqNum
            )
        else:
            return NightscoutEntry.sitechange(
                created_at = tubingFilled.eventTimestamp.format(),
                reason = reason,
                pump_event_id = "%s" % tubingFilled.seqNum
            )