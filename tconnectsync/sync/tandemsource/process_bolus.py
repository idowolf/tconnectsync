import logging
import arrow

from ...features import DEFAULT_FEATURES
from ... import features
from ...eventparser.generic import Events, decode_raw_events, EVENT_LEN
from ...eventparser.utils import bitmask_to_list
from ...eventparser import events as eventtypes
from ...domain.tandemsource.event_class import EventClass
from .helpers import insulin_float_round
from ...parser.nightscout import (
    BOLUS_EVENTTYPE,
    NightscoutEntry
)
from ...parser.tidepool import TidepoolEntry
from ...secret import UPLOAD_DESTINATION

logger = logging.getLogger(__name__)

class ProcessBolus:
    def __init__(self, tconnect, upload_api, tconnect_device_id, pretend, features=DEFAULT_FEATURES):
        self.tconnect = tconnect
        self.upload_api = upload_api  # Can be NightscoutApi or TidepoolApi
        self.tconnect_device_id = tconnect_device_id
        self.pretend = pretend
        self.features = features

    def enabled(self):
        return features.BOLUS in self.features

    def process(self, events, time_start, time_end):
        logger.debug("ProcessBolus: querying for last uploaded entry")
        
        # Query for last upload based on destination
        if UPLOAD_DESTINATION == 'tidepool':
            last_upload = self.upload_api.last_uploaded_entry('bolus', time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["time"])
            logger.info("Last Tidepool bolus upload: %s" % last_upload_time)
        else:
            last_upload = self.upload_api.last_uploaded_entry(BOLUS_EVENTTYPE, time_start=time_start, time_end=time_end)
            last_upload_time = None
            if last_upload:
                last_upload_time = arrow.get(last_upload["created_at"])
            logger.info("Last Nightscout bolus upload: %s" % last_upload_time)

        # TODO EXTENDED BOLUSES
        bolusCompletedEvents = []
        bolusEventsForId = {}
        for event in sorted(events, key=lambda x: x.eventTimestamp):
            if event.bolusid not in bolusEventsForId.keys():
                bolusEventsForId[event.bolusid] = {}

            bolusEventsForId[event.bolusid][type(event)] = event

            if type(event) == eventtypes.LidBolusCompleted:
                if last_upload_time and arrow.get(event.eventTimestamp) <= last_upload_time:
                    if self.pretend:
                        logger.info("Skipping bolusCompletedEvent not after last upload time: %s (time range: %s - %s)" % (event, time_start, time_end))
                    continue

                bolusCompletedEvents.append(event)

        bolusCompletedEvents.sort(key=lambda e: e.eventTimestamp)



        upload_entries = []
        for bolusCompleted in bolusCompletedEvents:
            m = bolusEventsForId[bolusCompleted.bolusid]

            entry = self.bolus_to_entry(
                bolusCompleted,
                bolusRequested1 = m.get(eventtypes.LidBolusRequestedMsg1),
                bolusRequested2 = m.get(eventtypes.LidBolusRequestedMsg2),
                bolusRequested3 = m.get(eventtypes.LidBolusRequestedMsg3),
            )
            
            # Tidepool returns a list of entries (bolus + food)
            if isinstance(entry, list):
                upload_entries.extend(entry)
            else:
                upload_entries.append(entry)

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


    def bolus_to_entry(self, bolusCompleted, bolusRequested1, bolusRequested2, bolusRequested3):
        """
        Convert bolus event to either Nightscout or Tidepool format based on UPLOAD_DESTINATION.
        """
        if UPLOAD_DESTINATION == 'tidepool':
            return self.bolus_to_tidepool(bolusCompleted, bolusRequested1, bolusRequested2, bolusRequested3)
        else:
            return self.bolus_to_nsentry(bolusCompleted, bolusRequested1, bolusRequested2, bolusRequested3)
    
    def bolus_to_tidepool(self, bolusCompleted, bolusRequested1, bolusRequested2, bolusRequested3):
        """
        Convert bolus event to Tidepool format.
        Returns a list of entries (bolus + food).
        """
        suffixes = []
        if bolusRequested2 and bolusRequested2.useroverride == eventtypes.LidBolusRequestedMsg2.UseroverrideEnum.Yes:
            suffixes.append('(Override)')

        if bolusRequested2 and bolusRequested2.declinedcorrection == eventtypes.LidBolusRequestedMsg2.DeclinedcorrectionEnum.Yes:
            suffixes.append('(Declined Correction)')

        suffix = (' ' + (' '.join(suffixes))) if suffixes else ''

        seq_nums = []
        for e in [bolusCompleted, bolusRequested1, bolusRequested2, bolusRequested3]:
            if e:
                seq_nums.append(str(e.seqNum))

        notes = ''
        if bolusRequested2 and str(bolusRequested2.optionsRaw) in eventtypes.LidBolusRequestedMsg2.OptionsMap:
            notes = eventtypes.LidBolusRequestedMsg2.OptionsMap['%d' % bolusRequested2.optionsRaw]

        # TidepoolEntry.bolus returns a list of entries
        return TidepoolEntry.bolus(
            bolus = insulin_float_round(bolusCompleted.insulindelivered),
            carbs = bolusRequested1.carbamount if bolusRequested1 and bolusRequested1.carbamount>0 else None,
            created_at = bolusCompleted.eventTimestamp.format(),
            notes = notes + suffix,
            bg = bolusRequested1.BG if bolusRequested1 and bolusRequested1.BG > 0 else None,
            pump_event_id = ",".join(seq_nums)
        )

    def bolus_to_nsentry(self, bolusCompleted, bolusRequested1, bolusRequested2, bolusRequested3):
        """
        Convert bolus event to Nightscout format (original implementation).
        """
        suffixes = []
        if bolusRequested2 and bolusRequested2.useroverride == eventtypes.LidBolusRequestedMsg2.UseroverrideEnum.Yes:
            suffixes.append('(Override)')

        if bolusRequested2 and bolusRequested2.declinedcorrection == eventtypes.LidBolusRequestedMsg2.DeclinedcorrectionEnum.Yes:
            suffixes.append('(Declined Correction)')

        suffix = (' ' + (' '.join(suffixes))) if suffixes else ''

        seq_nums = []
        for e in [bolusCompleted, bolusRequested1, bolusRequested2, bolusRequested3]:
            if e:
                seq_nums.append(str(e.seqNum))

        notes = ''
        if bolusRequested2 and str(bolusRequested2.optionsRaw) in eventtypes.LidBolusRequestedMsg2.OptionsMap:
            notes = eventtypes.LidBolusRequestedMsg2.OptionsMap['%d' % bolusRequested2.optionsRaw]


        return NightscoutEntry.bolus(
            bolus = insulin_float_round(bolusCompleted.insulindelivered),
            carbs = bolusRequested1.carbamount if bolusRequested1 and bolusRequested1.carbamount>0 else None,
            created_at = bolusCompleted.eventTimestamp.format(),
            notes = notes + suffix,
            bg = bolusRequested1.BG if bolusRequested1 and bolusRequested1.BG > 0 else None,
            pump_event_id = ",".join(seq_nums)
        )

