# TConnectSync - Tidepool Integration Guide

This is an adapted version of [tconnectsync](https://github.com/jwoglom/tconnectsync) that supports uploading Tandem pump data to **Tidepool** in addition to Nightscout.

## What's New

- ✅ Support for uploading to Tidepool API
- ✅ Automatic data format conversion (Tandem → Tidepool data model)
- ✅ Support for both Tidepool integration and production environments
- ✅ Backward compatible with Nightscout
- ✅ Switch between destinations via configuration

## Quick Start

### 1. Prerequisites

- Python 3.7 or higher
- A Tandem t:slim X2 pump with t:connect/Tandem Source account
- A Tidepool account (create at https://int-app.tidepool.org/signup for testing)

### 2. Installation

```bash
cd tconnectsync
pip3 install -e .
```

Or using pipenv:

```bash
pipenv install
```

### 3. Configuration

Copy the example environment file:

```bash
cp .env.tidepool.example .env
```

Edit `.env` and set:

```bash
# Tandem credentials
TCONNECT_EMAIL='your_tandem_email@example.com'
TCONNECT_PASSWORD='your_tandem_password'

# Upload to Tidepool
UPLOAD_DESTINATION='tidepool'

# Tidepool credentials
TIDEPOOL_USERNAME='your_tidepool_email@example.com'
TIDEPOOL_PASSWORD='your_tidepool_password'
TIDEPOOL_ENV='int'  # Use 'int' for testing, 'prd' for production

# Timezone
TIMEZONE_NAME='America/Los_Angeles'
```

**IMPORTANT:** 
- Use `TIDEPOOL_ENV='int'` for development/testing
- Only use `TIDEPOOL_ENV='prd'` when you're ready for production data
- You need separate Tidepool accounts for integration vs. production

### 4. Test the Connection

```bash
tconnectsync --check-login
```

Or with pipenv:

```bash
pipenv run tconnectsync --check-login
```

### 5. Sync Data

#### One-time sync (last 1 day):

```bash
tconnectsync
```

#### One-time sync (custom date range):

```bash
tconnectsync --start-date 2025-01-01 --end-date 2025-01-10
```

#### Continuous auto-update:

```bash
tconnectsync --auto-update
```

## Data Types Supported

The following data types are uploaded to Tidepool:

| Tandem Data | Tidepool Type | Description |
|-------------|---------------|-------------|
| **Bolus** | `bolus` + `food` | Insulin boluses and carbohydrate entries |
| **Basal** | `basal` | Basal insulin delivery (scheduled, temp, automated) |
| **CGM** | `cbg` | Continuous glucose readings |
| **Pump Events** | `deviceEvent` | Alarms, suspensions, site changes, etc. |
| **Activity** | `physicalActivity` | Exercise and sleep modes |
| **Device Status** | `deviceStatus` | Battery status and pump information |

## Switching Between Nightscout and Tidepool

You can easily switch between upload destinations by changing one environment variable:

### Upload to Tidepool:
```bash
UPLOAD_DESTINATION='tidepool'
```

### Upload to Nightscout:
```bash
UPLOAD_DESTINATION='nightscout'
```

The appropriate API and data format will be used automatically.

## Features Configuration

Control what data gets synced using the `--features` flag:

```bash
# Sync only basal and bolus data
tconnectsync --features BASAL BOLUS

# Sync everything (default)
tconnectsync --features BASAL BOLUS PUMP_EVENTS PROFILES

# Include CGM data (creates 30+ minute lag, not recommended with Dexcom Share)
tconnectsync --features BASAL BOLUS CGM
```

Available features:
- `BASAL` - Basal insulin delivery
- `BOLUS` - Bolus insulin and carbs
- `PUMP_EVENTS` - Alarms, suspensions, site changes, modes
- `PROFILES` - Insulin profile settings
- `CGM` - CGM readings (use only if no other CGM source)

## How It Works

### Data Flow

```
Tandem Source → TConnectSync → Tidepool
     (API)          (Adapter)      (API)
```

1. **Fetch**: Connects to Tandem Source API to get pump events
2. **Transform**: Converts Tandem's data format to Tidepool's data model
3. **Upload**: Sends data to Tidepool via their REST API

### Tidepool Data Model Mapping

| Component | Function |
|-----------|----------|
| `tconnectsync/tidepool.py` | Tidepool API client (authentication, upload) |
| `tconnectsync/parser/tidepool.py` | Data format converters (Tandem → Tidepool) |
| `tconnectsync/secret.py` | Configuration management |

## Technical Details

### Tidepool API Endpoints Used

- `POST /auth/login` - Authentication
- `POST /data/{userId}` - Upload diabetes data
- `GET /data/{userId}` - Query existing data (for deduplication)

### Data Format Example

Tandem bolus event is converted to Tidepool format:

```python
# Tandem format (internal)
{
    "insulin": 5.5,
    "carbs": 45,
    "timestamp": "2025-01-15T12:30:00"
}

# Tidepool format (uploaded)
[
    {
        "type": "bolus",
        "subType": "normal",
        "normal": 5.5,
        "time": "2025-01-15T12:30:00.000Z",
        "deviceTime": "2025-01-15T12:30:00",
        "timezone": "America/Los_Angeles",
        "timezoneOffset": -480,
        "deviceId": "TConnectSync-TandemPump",
        "uploadId": "abc123..."
    },
    {
        "type": "food",
        "nutrition": {
            "carbohydrate": {
                "net": 45,
                "units": "grams"
            }
        },
        "time": "2025-01-15T12:30:00.000Z",
        ...
    }
]
```

## Troubleshooting

### Authentication Failed

**Problem:** "Tidepool authentication failed: 401"

**Solution:**
- Verify your `TIDEPOOL_USERNAME` and `TIDEPOOL_PASSWORD`
- Make sure you're using the correct environment (`int` vs `prd`)
- Check if your account exists on that environment

### No Data Uploaded

**Problem:** Script runs but no data appears in Tidepool

**Solutions:**
1. Check that `UPLOAD_DESTINATION='tidepool'` is set
2. Verify your timezone (`TIMEZONE_NAME`) matches your pump
3. Try `--verbose` flag for detailed logging:
   ```bash
   tconnectsync --verbose
   ```
4. Check Tidepool web interface: https://int-app.tidepool.org (for integration)

### Data Format Errors

**Problem:** "Failed to upload data: 400"

**Solutions:**
- The data format may not match Tidepool's requirements
- Check the error message for specific field issues
- Report issues at: https://github.com/jwoglom/tconnectsync/issues

### Environment Mismatch

**Problem:** Account exists on production but using integration environment

**Solution:**
- Create a separate account for integration testing at https://int-app.tidepool.org/signup
- OR switch to production with `TIDEPOOL_ENV='prd'` (not recommended for testing)

## Running Continuously

### With Supervisord

Create `/etc/supervisor/conf.d/tconnectsync.conf`:

```ini
[program:tconnectsync]
command=/path/to/tconnectsync/run.sh
directory=/path/to/tconnectsync/
stderr_logfile=/path/to/tconnectsync/stderr.log
stdout_logfile=/path/to/tconnectsync/stdout.log
user=your_username
numprocs=1
autostart=true
autorestart=true
```

Create `run.sh`:

```bash
#!/bin/bash
tconnectsync --auto-update
```

Start the service:

```bash
sudo supervisorctl start tconnectsync
```

### With Cron

Edit crontab to run every 15 minutes:

```bash
crontab -e
```

Add:

```
*/15 * * * * /path/to/tconnectsync/run.sh
```

## Security Notes

- **Never commit your `.env` file** to version control
- Use integration environment (`int`) for development
- Your Tidepool credentials are stored locally only
- Sessions tokens expire and are refreshed automatically

## Support & Contributions

- Original tconnectsync: https://github.com/jwoglom/tconnectsync
- Tidepool API docs: https://tidepool.stoplight.io/docs/tidepool-api
- Report issues: https://github.com/jwoglom/tconnectsync/issues

## License

This project maintains the same license as the original tconnectsync project.

## Credits

- **Original tconnectsync:** [jwoglom](https://github.com/jwoglom/tconnectsync)
- **Tidepool Integration:** Adapted for Tidepool data model and API

---

**Questions?** Check the main [README.md](README.md) for general tconnectsync documentation.
