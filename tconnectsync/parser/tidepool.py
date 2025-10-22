import arrow
from ..secret import TIMEZONE_NAME

ENTERED_BY = "Pump (tconnectsync)"
DEVICE_ID = "TConnectSync-TandemPump"

"""
Conversion methods for parsing Tandem data into Tidepool data model format.
Reference: https://tidepool.stoplight.io/docs/tidepool-api/
"""
class TidepoolEntry:
    
    @staticmethod
    def _base_entry(time_str, entry_type, pump_event_id=""):
        """
        Create base fields common to all Tidepool entries.
        
        Args:
            time_str: ISO 8601 timestamp string
            entry_type: Tidepool data type
            pump_event_id: Optional event ID from pump
        """
        dt = arrow.get(time_str)
        
        return {
            "type": entry_type,
            "time": dt.isoformat(),
            "deviceTime": dt.format("YYYY-MM-DDTHH:mm:ss"),
            "deviceId": DEVICE_ID,
            "timezone": TIMEZONE_NAME,
            "timezoneOffset": dt.utcoffset().total_seconds() / 60,  # minutes from UTC
        }
    
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
            "annotations": [{
                "code": "tconnectsync/basal/reason",
                "value": reason
            }] if reason else []
        })
        
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
        bolus_entry.update({
            "subType": "normal",
            "normal": float(bolus),
            "expectedNormal": float(bolus),
        })
        
        if notes:
            bolus_entry["annotations"] = [{
                "code": "tconnectsync/bolus/notes",
                "value": notes
            }]
        
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
            "subType": "reservoirChange",  # or "cannulaChange"
            "annotations": [{
                "code": "tconnectsync/sitechange",
                "value": reason
            }] if reason else []
        })
        
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
            "annotations": [{
                "code": "tconnectsync/basal-suspension",
                "value": reason
            }] if reason else []
        })
        
        return entry
    
    @staticmethod
    def basalresume(created_at, pump_event_id=""):
        """
        Create a Tidepool device event for basal resume.
        
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
            "annotations": [{
                "code": "tconnectsync/alarm",
                "value": reason
            }] if reason else []
        })
        
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
        entry = TidepoolEntry._base_entry(created_at, "deviceEvent", pump_event_id)
        entry.update({
            "subType": "alert",
            "annotations": [{
                "code": "tconnectsync/cgm-alert",
                "value": reason
            }] if reason else []
        })
        
        return entry
    
    @staticmethod
    def cgm_sensor_event(created_at, event_subtype, reason="", pump_event_id=""):
        """
        Create a Tidepool device event for CGM sensor start/stop/calibration.
        
        Args:
            created_at: ISO 8601 timestamp
            event_subtype: "sensorStart", "sensorStop", or "calibration"
            reason: Additional details
            pump_event_id: Event ID from pump
        """
        entry = TidepoolEntry._base_entry(created_at, "deviceEvent", pump_event_id)
        entry.update({
            "subType": event_subtype,
            "annotations": [{
                "code": f"tconnectsync/cgm-{event_subtype}",
                "value": reason
            }] if reason else []
        })
        
        return entry
    
    @staticmethod
    def cgm_start(created_at, reason="", pump_event_id=""):
        """Convenience method for CGM session start"""
        return TidepoolEntry.cgm_sensor_event(created_at, "sensorStart", reason, pump_event_id)
    
    @staticmethod
    def cgm_join(created_at, reason="", pump_event_id=""):
        """Convenience method for CGM session join"""
        return TidepoolEntry.cgm_sensor_event(created_at, "sensorStart", reason, pump_event_id)
    
    @staticmethod
    def cgm_stop(created_at, reason="", pump_event_id=""):
        """Convenience method for CGM session stop"""
        return TidepoolEntry.cgm_sensor_event(created_at, "sensorStop", reason, pump_event_id)
    
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
            "annotations": [{
                "code": "tconnectsync/activity",
                "value": f"{event_type}: {reason}" if reason else event_type
            }]
        })
        
        return entry
    
    @staticmethod
    def devicestatus(created_at, batteryVoltage, batteryPercent, pump_event_id=""):
        """
        Create a Tidepool device status entry.
        
        Args:
            created_at: ISO 8601 timestamp
            batteryVoltage: Battery voltage
            batteryPercent: Battery percentage
            pump_event_id: Event ID from pump
        """
        entry = TidepoolEntry._base_entry(created_at, "deviceStatus", pump_event_id)
        entry.update({
            "battery": {
                "value": float(batteryVoltage),
                "units": "volts"
            }
        })
        
        if batteryPercent:
            entry["batteryPercent"] = int(batteryPercent)
        
        return entry
    
    @staticmethod
    def upload_metadata():
        """
        Create a Tidepool upload metadata entry.
        This should be included at the start of each upload session.
        """
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        
        return {
            "type": "upload",
            "deviceManufacturers": ["Tandem"],
            "deviceModel": "t:slim X2",
            "deviceSerialNumber": "TConnectSync",
            "deviceTags": ["insulin-pump", "cgm"],
            "timeProcessing": "across-the-board-timezone",
            "timezone": TIMEZONE_NAME,
            "version": "1.0.0-tconnectsync",
            "computerTime": now.strftime("%Y-%m-%dT%H:%M:%S"),
            "time": now.isoformat(),
            "deviceId": DEVICE_ID,
            "deviceTime": now.strftime("%Y-%m-%dT%H:%M:%S"),
        }
