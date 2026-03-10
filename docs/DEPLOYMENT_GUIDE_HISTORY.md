# Deployment Guide: History Feature

## Overview

This guide provides step-by-step instructions for deploying the history feature to your Raspberry Pi running Home Assistant.

## Prerequisites

- Raspberry Pi with Home Assistant installed
- Eedomus integration already configured
- SSH access to the Raspberry Pi
- Basic familiarity with Linux commands

## Deployment Steps

### Step 1: Prepare the Deployment

1. **Copy files to Raspberry Pi**:
   ```bash
   # From your development machine
   scp -r hass-eedomus/ user@raspberrypi:/config/
   ```

2. **Navigate to Home Assistant config directory**:
   ```bash
   cd /config
   ```

### Step 2: Enable Debug Logging (Optional)

To get detailed logs for troubleshooting:

```bash
# Edit the configuration.yaml
nano configuration.yaml

# Add or modify the logger configuration:
logger:
  default: info
  logs:
    custom_components.eedomus: debug
    custom_components.eedomus.coordinator: debug
    custom_components.eedomus.__init__: debug
```

### Step 3: Enable History Option

#### Option A: Via Home Assistant UI (Recommended)

1. Go to Home Assistant web interface
2. Navigate to **Settings** > **Devices & Services**
3. Find **Eedomus** integration and click **Configure**
4. Enable the **Enable History** checkbox
5. Click **Submit** to save

#### Option B: Manual Storage Edit

If the UI method doesn't work:

```bash
# Edit the storage file
nano /config/.storage/core.config_entries

# Find your eedomus integration entry and add/modify:
"options": {
    "history": true,
    "scan_interval": 300,
    ...
}
```

#### Option C: Use Activation Script

```bash
# Run the activation script
bash /config/www/activate_history_feature.sh
```

### Step 4: Restart Home Assistant

```bash
# Restart Home Assistant to apply changes
sudo systemctl restart home-assistant@homeassistant
```

Or via the Home Assistant UI:
- Go to **Settings** > **System** > **Restart**

### Step 5: Verify Deployment

1. **Check logs for debug messages**:
   ```bash
   journalctl -u home-assistant@homeassistant -f | grep -i "history"
   ```

2. **Look for expected log messages**:
   ```
   DEBUG: History option decision: config=True, options=True, final=True
   INFO: Performing partial refresh for X peripherals (history retrieval: True)
   INFO: ✅ Virtual history sensors created successfully
   ```

3. **Verify virtual sensors exist**:
   - Go to **Settings** > **Devices & Services**
   - Look for entities starting with `sensor.eedomus_history_`
   - Expected sensors:
     - `sensor.eedomus_history_progress` (global progress)
     - `sensor.eedomus_history_stats` (download statistics)
     - `sensor.eedomus_history_progress_<device_id>` (per-device progress)

### Step 6: Monitor History Retrieval

1. **Check the global progress sensor**:
   - The `sensor.eedomus_history_progress` should show progress percentage
   - The `sensor.eedomus_history_stats` shows data size downloaded

2. **Monitor logs for progress**:
   ```bash
   journalctl -u home-assistant@homeassistant -f | grep -i "history.*fetch"
   ```

3. **Expected progress messages**:
   ```
   INFO: Fetching history for <device_id> (from <timestamp>)
   INFO: History fully fetched for <device_id> (<device_name>) (received X entries)
   INFO: Importing X historical states for <device_name> (<device_id>)
   ```

## Troubleshooting

### Issue: History shows as disabled in logs

**Solution:**
1. Check debug logs for the decision process
2. Verify storage file has correct values
3. Ensure you explicitly enabled history in the UI
4. Restart Home Assistant

**Debug commands:**
```bash
# Check storage file
cat /config/.storage/core.config_entries | grep -A 30 "eedomus"

# Check logs
journalctl -u home-assistant@homeassistant -f | grep -i "history.*decision"
```

### Issue: Virtual sensors not created

**Solution:**
1. Check that `history_enabled` is `True` in logs
2. Verify `_create_virtual_history_sensors()` is being called
3. Look for errors in the logs during initialization

**Debug commands:**
```bash
journalctl -u home-assistant@homeassistant -f | grep -i "virtual.*sensor"
```

### Issue: History retrieval not happening

**Solution:**
1. Check that `history_retrieval` is `True` in partial refresh logs
2. Verify peripherals are being added to the history queue
3. Check for API errors during history fetching

**Debug commands:**
```bash
journalctl -u home-assistant@homeassistant -f | grep -i "peripheral.*history"
```

## Performance Considerations

### Scan Interval

The history feature processes peripherals during the regular scan interval. You can adjust this:

```bash
# Edit the storage file
nano /config/.storage/core.config_entries

# Add or modify:
"options": {
    "scan_interval": 300,  # 5 minutes (default)
    "history_peripherals_per_scan": 1,  # Process 1 peripheral per scan
    ...
}
```

### Peripheral Processing Rate

To avoid overwhelming the system:

```bash
# Limit to 1 peripheral per scan interval (recommended for most users)
"history_peripherals_per_scan": 1

# For faster systems, you can increase this:
"history_peripherals_per_scan": 5
```

### Retry Delay

If history fetching fails, it will retry after the configured delay:

```bash
"history_retry_delay": 24  # Retry after 24 hours (default)
```

## Rollback

If you need to disable the history feature:

1. **Via UI**:
   - Go to **Settings** > **Devices & Services**
   - Configure Eedomus integration
   - Disable the **Enable History** checkbox
   - Save

2. **Manual**:
   ```bash
   nano /config/.storage/core.config_entries
   
   # Set history to false:
   "options": {
       "history": false,
       ...
   }
   ```

3. **Restart Home Assistant**:
   ```bash
   sudo systemctl restart home-assistant@homeassistant
   ```

## Support

If you encounter issues:

1. **Check the debug guide**: `docs/HISTORY_OPTION_DEBUG.md`
2. **Review logs**: Look for `DEBUG` and `ERROR` messages related to history
3. **Verify storage**: Ensure the `history` option is correctly set
4. **Create issue**: Provide log snippets and storage file content (redact sensitive info)

## References

- **Main documentation**: `docs/HISTORY_FEATURE_STATUS.md`
- **Debug guide**: `docs/HISTORY_OPTION_DEBUG.md`
- **Technical details**: `docs/HISTORY_TRACKING_ALTERNATIVE.md`
- **Source code**: `custom_components/eedomus/coordinator.py`