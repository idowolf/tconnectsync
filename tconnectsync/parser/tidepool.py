import arrow
from ..secret import TIMEZONE_NAME

ENTERED_BY = "Pump (tconnectsync)"
DEVICE_ID = "TConnectSync-TandemPump"

"""
Conversion methods for parsing Tandem data into Tidepool data model format.
Reference: https://tidepool.stoplight.io/docs/tidepool-api/

Notes on conventions, learned against the live ingest service (jellyfish):
- "time" is submitted already normalized to UTC ("...Z"), matching how the
  server stores it. This keeps server-side ids stable (they hash the time
  string) so duplicate submissions dedupe and "previous" references match.
- Free-text metadata goes in "payload", NOT "annotations": Tidepool's web app
  renders unknown annotation codes as a "we can't be 100% certain of this
  data" warning on every datum.
- payload.tconnectsync_event distinguishes datums that share a Tidepool
  type/subType (e.g. pump alarms vs CGM alerts, both deviceEvent/alarm) so
  deduplication queries can filter to the right slice.
"""
class TidepoolEntry:

    @staticmethod
    def _base_entry(time_str, entry_type, pump_event_id=""):
        """
        Create base fields common to all Tidepool entries.

        Args:
            time_str: ISO 8601 timestamp string (with timezone offset)
            entry_type: Tidepool data type
            pump_event_id: Optional event ID from pump
        """
        dt = arrow.get(time_str)

        entry = {
            "type": entry_type,
            # UTC, formatted exactly like the Tidepool backend stores it
            "time": dt.to('UTC').format("YYYY-MM-DDTHH:mm:ss") + "Z",
            "deviceTime": dt.format("YYYY-MM-DDTHH:mm:ss"),
            "deviceId": DEVICE_ID,
            "timezone": TIMEZONE_NAME,
            "timezoneOffset": int(dt.utcoffset().total_seconds() // 60),  # minutes from UTC
            "payload": {},
        }

        if pump_event_id:
            entry["payload"]["pump_event_id"] = str(pump_event_id)

        return entry

    @staticmethod
    def basal(value, duration_mins, created_at, reason="", pump_event_id=""):
        """
        Create a Tidepool basal insulin entry.

        Args:
            value: Basal rate in Units/hour
            duration_mins: Duration in minutes
            created_at: ISO 8601 timestamp
            reason: Description of why basal changed
            pump_event_id: Event ID from pump
        """
        entry = TidepoolEntry._base_entry(created_at, "basal", pump_event_id)

        # Determine delivery type based on reason
        delivery_type = "scheduled"  # Default
        if reason:
            reason_lower = reason.lower()
            if "temp" in reason_lower or "temporary" in reason_lower:
                delivery_type = "temp"
            elif "suspend" in reason_lower:
                delivery_type = "suspend"
            elif "automated" in reason_lower or "algorithm" in reason_lower:
                delivery_type = "automated"

        entry.update({
            "deliveryType": delivery_type,
            "rate": float(value),
            "duration": int(duration_mins * 60 * 1000),  # milliseconds
        })
        if reason:
            entry["payload"]["reason"] = reason

        return entry

    @staticmethod
    def link_previous(entry, previous):
        """
        Attach a "previous" reference to an entry, linking it to the datum that
        precedes it in its series. The Tidepool ingest service uses this to
        verify continuity; without it every basal (and suspend/resume tuple)
        is annotated as possibly missing a segment ("basal/mismatched-series",
        "status/unknown-previous"), which the web app surfaces as warnings.

        Args:
            entry: The entry to annotate (modified in place and returned)
            previous: The preceding datum: either the previously built entry
                or a datum fetched back from the Tidepool API
        """
        if not previous:
            return entry

        # Strip nesting and server-side fields; keep the identity and content
        # fields the server hashes/validates.
        skip = ('previous', 'annotations', 'id', 'uploadId', 'guid',
                'createdTime', 'modifiedTime', 'revision', 'origin')
        entry["previous"] = {k: v for k, v in previous.items() if k not in skip}
        return entry

    @staticmethod
    def bolus(bolus, carbs, created_at, notes="", bg="", bg_type="", pump_event_id=""):
        """
        Create Tidepool bolus and food entries.

        Args:
            bolus: Insulin amount in Units
            carbs: Carbohydrate amount in grams
            created_at: ISO 8601 timestamp
            notes: Additional notes
            bg: Blood glucose value
            bg_type: Type of BG reading ("Sensor" or "Finger")
            pump_event_id: Event ID from pump

        Returns:
            List of entries (bolus entry, and optionally food entry)
        """
        entries = []

        # Create bolus entry
        bolus_entry = TidepoolEntry._base_entry(created_at, "bolus", pump_event_id)
        # Note: expectedNormal is deliberately omitted; it is only meant for
        # interrupted boluses and makes Tidepool display the bolus as cut short.
        bolus_entry.update({
            "subType": "normal",
            "normal": float(bolus),
        })

        if notes:
            bolus_entry["payload"]["notes"] = notes

        entries.append(bolus_entry)

        # Create food entry if carbs are present
        if carbs and carbs > 0:
            food_entry = TidepoolEntry._base_entry(created_at, "food", pump_event_id)
            food_entry.update({
                "nutrition": {
                    "carbohydrate": {
                        "net": int(carbs),
                        "units": "grams"
                    }
                }
            })
            entries.append(food_entry)

        # Create SMBG entry if BG is present
        if bg and bg > 0:
            smbg_entry = TidepoolEntry._base_entry(created_at, "smbg", pump_event_id)
            smbg_entry.update({
                "value": float(bg) / 18.01559,  # Convert mg/dL to mmol/L
                "units": "mmol/L"
            })

            # Add subType based on bg_type
            if bg_type == "Finger":
                smbg_entry["subType"] = "manual"

            entries.append(smbg_entry)

        return entries

    @staticmethod
    def cgm(sgv, created_at, pump_event_id=""):
        """
        Create a Tidepool CGM (continuous glucose monitor) entry.

        Args:
            sgv: Sensor glucose value in mg/dL
            created_at: ISO 8601 timestamp
            pump_event_id: Event ID from pump
        """
        entry = TidepoolEntry._base_entry(created_at, "cbg", pump_event_id)
        entry.update({
            "value": float(sgv) / 18.01559,  # Convert mg/dL to mmol/L
            "units": "mmol/L"
        })

        return entry

    @staticmethod
    def sitechange(created_at, reason="", pump_event_id=""):
        """
        Create a Tidepool device event for site/infusion set change.

        Args:
            created_at: ISO 8601 timestamp
            reason: Description
            pump_event_id: Event ID from pump
        """
        entry = TidepoolEntry._base_entry(created_at, "deviceEvent", pump_event_id)
        entry.update({
            "subType": "reservoirChange",
        })
        if reason:
            entry["payload"]["reason"] = reason

        return entry

    @staticmethod
    def basalsuspension(created_at, reason="", pump_event_id=""):
        """
        Create a Tidepool device event for basal suspension.

        Args:
            created_at: ISO 8601 timestamp
            reason: Reason for suspension
            pump_event_id: Event ID from pump
        """
        entry = TidepoolEntry._base_entry(created_at, "deviceEvent", pump_event_id)
        entry.update({
            "subType": "status",
            "status": "suspended",
            "reason": {
                "suspended": "manual" if "user" in reason.lower() else "automatic"
            },
        })
        if reason:
            entry["payload"]["reason"] = reason

        return entry

    @staticmethod
    def basalresume(created_at, pump_event_id=""):
        """
        Create a Tidepool device event for basal resume.

        Note: the ingest service treats a resume carrying previous=<suspend
        datum> as the completion of that suspension (it sets the suspend's
        duration) rather than storing a separate record. Callers should link
        the matching suspend via link_previous().

        Args:
            created_at: ISO 8601 timestamp
            pump_event_id: Event ID from pump
        """
        entry = TidepoolEntry._base_entry(created_at, "deviceEvent", pump_event_id)
        entry.update({
            "subType": "status",
            "status": "resumed",
            "reason": {
                "resumed": "manual"
            }
        })

        return entry

    @staticmethod
    def alarm(created_at, reason="", pump_event_id=""):
        """
        Create a Tidepool device event for pump alarm.

        Args:
            created_at: ISO 8601 timestamp
            reason: Alarm description
            pump_event_id: Event ID from pump
        """
        entry = TidepoolEntry._base_entry(created_at, "deviceEvent", pump_event_id)
        entry.update({
            "subType": "alarm",
            "alarmType": "other",
        })
        entry["payload"]["tconnectsync_event"] = "alarm"
        if reason:
            entry["payload"]["reason"] = reason

        return entry

    @staticmethod
    def cgm_alert(created_at, reason="", pump_event_id=""):
        """
        Create a Tidepool device event for CGM alert.

        Args:
            created_at: ISO 8601 timestamp
            reason: Alert description
            pump_event_id: Event ID from pump
        """
        # Tidepool has no "alert" deviceEvent subType (valid subTypes are alarm,
        # calibration, prime, pumpSettingsOverride, reservoirChange, status,
        # timeChange), so CGM alerts are represented as an alarm with the
        # alert description preserved in the payload.
        entry = TidepoolEntry._base_entry(created_at, "deviceEvent", pump_event_id)
        entry.update({
            "subType": "alarm",
            "alarmType": "other",
        })
        entry["payload"]["tconnectsync_event"] = "cgm-alert"
        if reason:
            entry["payload"]["reason"] = reason

        return entry

    @staticmethod
    def activity(created_at, duration, reason="", event_type="physicalActivity", pump_event_id=""):
        """
        Create a Tidepool physical activity entry.

        Args:
            created_at: ISO 8601 timestamp
            duration: Duration in minutes
            reason: Activity description
            event_type: Type of activity (used for classification)
            pump_event_id: Event ID from pump
        """
        entry = TidepoolEntry._base_entry(created_at, "physicalActivity", pump_event_id)
        entry.update({
            "duration": {
                "value": int(duration),
                "units": "minutes"
            },
            "name": reason or event_type,
        })
        entry["payload"]["tconnectsync_event"] = event_type
        if reason:
            entry["payload"]["reason"] = reason

        return entry

    @staticmethod
    def upload_record(upload_id, user_id, device_serial=None, version="tconnectsync"):
        """
        Create a Tidepool upload session record. Uploading one with the same
        uploadId as the data entries lets the Tidepool web app attribute the
        data to "Tandem" instead of showing "Unspecified Data Source".

        Args:
            upload_id: The uploadId shared with the session's data entries
            user_id: The Tidepool user id the data belongs to
            device_serial: The pump serial number, if known
            version: Client version string
        """
        now = arrow.utcnow()

        return {
            "type": "upload",
            "uploadId": upload_id,
            "byUser": user_id,
            "deviceManufacturers": ["Tandem"],
            "deviceModel": "t:slim X2",
            "deviceSerialNumber": str(device_serial) if device_serial else "unknown",
            "deviceTags": ["insulin-pump", "cgm"],
            "timeProcessing": "utc-bootstrapping",
            "timezone": TIMEZONE_NAME,
            "version": version,
            "client": {"name": "tconnectsync", "version": version},
            "computerTime": now.to(TIMEZONE_NAME).format("YYYY-MM-DDTHH:mm:ss"),
            "time": now.format("YYYY-MM-DDTHH:mm:ss") + "Z",
            "deviceTime": now.to(TIMEZONE_NAME).format("YYYY-MM-DDTHH:mm:ss"),
            "deviceId": DEVICE_ID,
        }
