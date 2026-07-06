import datetime
import requests
import hashlib
import time
import urllib.parse
import arrow
import logging

from urllib.parse import urljoin

from .api.common import ApiException

def format_datetime(date):
    return arrow.get(date).isoformat()

logger = logging.getLogger(__name__)

class TidepoolApi:
    def __init__(self, base_url, username, password, user_id=None):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session_token = None
        self.user_id = user_id
        self.upload_id = None
        
        # Authenticate on initialization
        self.authenticate()
    
    def authenticate(self):
        """
        Authenticate with Tidepool using basic authentication.
        Returns the session token.
        """
        logger.info(f"Authenticating to Tidepool as {self.username}...")
        
        url = f"{self.base_url}/auth/login"
        response = requests.post(
            url,
            auth=(self.username, self.password)
        )
        
        if response.status_code != 200:
            raise ApiException(response.status_code, f"Tidepool authentication failed: {response.status_code} - {response.text}")
        
        # Extract session token from headers
        self.session_token = response.headers.get('X-Tidepool-Session-Token')
        if not self.session_token:
            raise Exception("No session token received from Tidepool authentication")
        
        # Extract user ID from response body
        user_data = response.json()
        self.user_id = user_data.get('userid')
        
        logger.info(f"✓ Tidepool authentication successful! User ID: {self.user_id}")
        return self.session_token
    
    def _get_headers(self):
        """Get headers with authentication token"""
        if not self.session_token:
            self.authenticate()
        
        return {
            'X-Tidepool-Session-Token': self.session_token,
            'Content-Type': 'application/json'
        }
    
    def generate_upload_id(self):
        """Generate a unique upload ID"""
        hash_string = f"{self.user_id}-TConnectSync-{int(time.time())}"
        upload_id = hashlib.md5(hash_string.encode()).hexdigest()
        return upload_id
    
    def upload_entries(self, tidepool_entries, retry_on_401=True):
        """
        Upload multiple entries to Tidepool in a single batch.
        
        Args:
            tidepool_entries: List of Tidepool-formatted data entries
            retry_on_401: Whether to retry after re-authenticating on 401 error
        """
        if not tidepool_entries:
            logger.info("No entries to upload")
            return
        
        # Generate upload ID if not exists
        if not self.upload_id:
            self.upload_id = self.generate_upload_id()
        
        url = f"{self.base_url}/data/{self.user_id}"
        
        # Add uploadId to all entries
        for entry in tidepool_entries:
            if 'uploadId' not in entry:
                entry['uploadId'] = self.upload_id
        
        response = requests.post(
            url,
            headers=self._get_headers(),
            json=tidepool_entries
        )
        
        # Handle 401 (token expired) by re-authenticating and retrying once
        if response.status_code == 401 and retry_on_401:
            logger.warning("Tidepool session token expired, re-authenticating...")
            self.authenticate()
            # Retry with new token (but don't retry again to avoid infinite loop)
            return self.upload_entries(tidepool_entries, retry_on_401=False)
        
        if response.status_code not in [200, 201]:
            raise ApiException(response.status_code, f"Tidepool upload failed: {response.status_code} - {response.text}")
        
        logger.info(f"✓ Uploaded {len(tidepool_entries)} entries to Tidepool")
        return response.json()
    
    def upload_entry(self, tidepool_entry):
        """
        Upload a single entry to Tidepool.
        
        Args:
            tidepool_entry: Single Tidepool-formatted data entry
        """
        return self.upload_entries([tidepool_entry])
    
    def last_uploaded_entry(self, entry_type, time_start=None, time_end=None, subtype=None, status=None, annotation_code=None):
        """
        Get the most recent uploaded entry of a specific type.

        Args:
            entry_type: The Tidepool data type (e.g., 'bolus', 'basal')
            time_start: Start time filter
            time_end: End time filter
            subtype: Only consider entries with this subType (e.g. 'alarm').
                Several processors share the 'deviceEvent' type; without this
                filter one processor's uploads would mask another's events.
            status: Only consider entries with this status (e.g. 'suspended')
            annotation_code: Only consider entries carrying an annotation with
                this code (e.g. 'tconnectsync/cgm-alert')

        Returns:
            The most recent matching entry dict or None
        """
        try:
            url = f"{self.base_url}/data/{self.user_id}"

            params = {
                'type': entry_type
            }

            if time_start:
                params['startDate'] = format_datetime(time_start)
            if time_end:
                params['endDate'] = format_datetime(time_end)

            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params
            )

            if response.status_code != 200:
                logger.warning(f"Tidepool last_uploaded_entry {entry_type} response: {response.status_code}")
                return None

            entries = response.json()

            def matches(entry):
                if subtype and entry.get('subType') != subtype:
                    return False
                if status and entry.get('status') != status:
                    return False
                if annotation_code and not any(
                        a.get('code') == annotation_code for a in (entry.get('annotations') or [])):
                    return False
                return True

            entries = [e for e in entries if matches(e)]
            if entries:
                # Sort by time and return the most recent
                entries.sort(key=lambda x: x.get('time', ''), reverse=True)
                return entries[0]

            return None
        except Exception as e:
            logger.warning(f"Error getting last uploaded entry: {e}")
            return None
    
    def last_uploaded_bg_entry(self, time_start=None, time_end=None):
        """
        Get the most recent uploaded blood glucose entry (CGM/CBG).
        
        Args:
            time_start: Start time filter
            time_end: End time filter
            
        Returns:
            The most recent BG entry dict or None
        """
        # Try CBG (continuous) first, then SMBG (self-monitored)
        cbg = self.last_uploaded_entry('cbg', time_start, time_end)
        if cbg:
            return cbg
        
        return self.last_uploaded_entry('smbg', time_start, time_end)
    
    def last_uploaded_activity(self, activityType, time_start=None, time_end=None):
        """
        Get the most recent uploaded activity entry.
        For Tidepool, we'll use physicalActivity type.
        
        Args:
            activityType: Activity type identifier
            time_start: Start time filter
            time_end: End time filter
            
        Returns:
            The most recent activity entry dict or None
        """
        return self.last_uploaded_entry('physicalActivity', time_start, time_end)
    
    def last_uploaded_devicestatus(self, time_start=None, time_end=None):
        """
        Get the most recent uploaded device status entry.
        For Tidepool, we'll use deviceStatus type.
        
        Args:
            time_start: Start time filter
            time_end: End time filter
            
        Returns:
            The most recent device status entry dict or None
        """
        return self.last_uploaded_entry('deviceStatus', time_start, time_end)
