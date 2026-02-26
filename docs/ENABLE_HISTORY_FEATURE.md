# Enabling the History Feature

## Overview

The history feature in the eedomus integration allows you to retrieve historical data from your eedomus devices. This feature is currently **disabled by default** as it's still in development and may impact performance.

## How to Enable the History Feature

There are two ways to enable the history feature:

### Method 1: Using the Home Assistant UI (Recommended)

1. **Navigate to the eedomus integration settings:**
   - Go to **Settings** → **Devices & Services**
   - Find your eedomus integration and click on the gear icon (⚙️)
   - Click on **Configure** or **Options**

2. **Enable the history option:**
   - Look for the **Enable History** checkbox
   - Check the box to enable history retrieval
   - Click **Submit** to save your changes

3. **Restart Home Assistant:**
   - After enabling the option, restart Home Assistant for the changes to take effect
   - You can do this by going to **Settings** → **System** → **Restart**

### Method 2: Using the Storage File (Advanced)

If you prefer to enable the history feature programmatically, you can modify the storage file directly:

1. **Locate the storage file:**
   - On your Raspberry Pi, navigate to `/config/.storage/`
   - Find the file that contains your eedomus configuration (usually named something like `core.config_entries`)

2. **Edit the storage file:**
   - Open the file with a text editor
   - Find the section that contains your eedomus integration options
   - Add or modify the `history` option to `true`:
     ```json
     "options": {
         "history": true,
         "api_eedomus": true,
         "api_proxy": false,
         "scan_interval": 300
     }
     ```

3. **Save the file and restart Home Assistant:**
   - Save the changes to the file
   - Restart Home Assistant for the changes to take effect

### Method 3: Using the Activation Script

We've provided a script to help you enable the history feature:

1. **Copy the script to your Raspberry Pi:**
   ```bash
   scp hass-eedomus/scripts/activate_history_feature.sh pi@your-raspberry-pi:/home/pi/
   ```

2. **Make the script executable:**
   ```bash
   chmod +x /home/pi/activate_history_feature.sh
   ```

3. **Run the script:**
   ```bash
   sudo /home/pi/activate_history_feature.sh
   ```

4. **Restart Home Assistant:**
   ```bash
   sudo systemctl restart home-assistant@pi.service
   ```

## Verifying the History Feature is Enabled

After enabling the history feature, you can verify it's working by:

1. **Checking the logs:**
   - Look for messages like `history=True` in the Home Assistant logs
   - You should see messages about history retrieval progress

2. **Checking the virtual sensors:**
   - The integration creates virtual sensors to track history retrieval progress:
     - `sensor.eedomus_history_progress` - Global progress
     - `sensor.eedomus_history_progress_{device_id}` - Per-device progress
     - `sensor.eedomus_history_stats` - Statistics

3. **Monitoring the logs for history retrieval:**
   - You should see messages like:
     ```
     Fetching history for {device_id} (from {timestamp})
     History fully fetched for {device_id} ({device_name}) (received {count} entries)
     ```

## Troubleshooting

### Issue: History option shows as False in logs

**Cause:** The history option is disabled by default.

**Solution:** Enable the history option using one of the methods above.

### Issue: No history data being retrieved

**Cause:** The history feature might not be enabled, or there might be an issue with the API.

**Solution:**
1. Verify the history option is enabled
2. Check the Home Assistant logs for errors
3. Ensure your eedomus API credentials are correct
4. Check that the eedomus API is accessible

### Issue: Performance impact

**Cause:** Retrieving history data can be resource-intensive.

**Solution:**
- Consider disabling history retrieval during peak usage times
- Monitor your system resources
- You can disable the history feature at any time by unchecking the option in the UI

## Disabling the History Feature

If you experience performance issues or no longer need the history feature, you can disable it:

1. **Using the UI:**
   - Go to **Settings** → **Devices & Services**
   - Find your eedomus integration and click on the gear icon (⚙️)
   - Click on **Configure** or **Options**
   - Uncheck the **Enable History** checkbox
   - Click **Submit** to save your changes
   - Restart Home Assistant

2. **Using the storage file:**
   - Edit the storage file as described above
   - Set `"history": false`
   - Save the file and restart Home Assistant

## Notes

- The history feature is still in development and may change in future versions
- History retrieval can take a significant amount of time depending on how much data you have
- The feature creates virtual sensors that use the Home Assistant state system for storage
- No additional database or Recorder component is required

## Support

If you encounter issues with the history feature, please:

1. Check the Home Assistant logs for errors
2. Verify that the history option is enabled
3. Ensure your eedomus API credentials are correct
4. Check that the eedomus API is accessible

For additional support, please refer to the [eedomus integration documentation](https://github.com/Dan4Jer/hass-eedomus).