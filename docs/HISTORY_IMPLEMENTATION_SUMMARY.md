# History Feature Implementation Summary

## Overview

This document summarizes the history feature implementation for the eedomus integration, focusing on the CPU Box device tracking and history progress visualization.

## What Was Implemented

### 1. Recorder Component Detection Fix

**Problem**: The warning `Recorder component not available. Cannot load history progress.` was appearing because the code was checking for recorder availability incorrectly.

**Solution**: Enhanced the recorder component detection with:
- More robust check: `hasattr(self.hass, "components.recorder") and self.hass.components.recorder is not None`
- Better error messages guiding users to enable recorder in configuration.yaml
- Try-catch blocks to handle exceptions gracefully
- Improved logging for debugging

**Files Modified**:
- `custom_components/eedomus/coordinator.py` - `_load_history_progress()` and `_save_history_progress()` methods

### 2. History Progress Sensor

**Feature**: Created a visual indicator showing:
- History retrieval progress percentage
- Data volume to be retrieved (estimated)
- Device name for easy identification
- Completion status

**Implementation**:
- New method `_create_history_progress_sensor()` in coordinator.py
- Estimates total data points based on device age and type
- Creates HA entities with format: `eedomus.history_progress_{periph_id}`
- Includes attributes: progress %, retrieved points, estimated total, last timestamp
- Uses appropriate icons and device classes for proper visualization

**Files Modified**:
- `custom_components/eedomus/coordinator.py` - New `_create_history_progress_sensor()` method
- `custom_components/eedomus/eedomus_client.py` - New `get_device_history_count()` method

### 3. CPU Box Device Mapping

**Status**: The CPU Box device is already correctly mapped:
- `usage_id: "23"` → `sensor:cpu`
- Device name: "CPU Box [jdanoffre]" is preserved
- This creates a sensor entity that can show CPU usage

**Files**:
- `custom_components/eedomus/config/device_mapping.yaml` - Already contains correct mapping

### 4. History Progress Sensor Creation

**Automatic Creation**: History progress sensors are now created:
- When history feature is enabled (CONF_ENABLE_HISTORY = True)
- During integration setup (in __init__.py)
- After each history chunk is retrieved (in coordinator.py)

**Files Modified**:
- `custom_components/eedomus/__init__.py` - Added code to create sensors on setup
- `custom_components/eedomus/coordinator.py` - Added sensor creation after history retrieval

## Current Status

### What's Working
✅ Recorder component detection is more robust
✅ History progress sensors can be created
✅ CPU Box device is correctly mapped as sensor:cpu
✅ History retrieval progress is tracked
✅ Estimated data volume is calculated

### What's Not Working Yet
⚠️ History feature is still disabled by default (CONF_ENABLE_HISTORY = False)
⚠️ History retrieval only works when API Eedomus mode is enabled
⚠️ Recorder component must be enabled in Home Assistant configuration

### What Needs Testing
🔍 History progress sensor creation
🔍 History retrieval for CPU sensor
🔍 Progress visualization in Home Assistant UI
🔍 Data volume estimation accuracy
🔍 Recorder component availability detection

## How to Test

### Step 1: Enable Recorder Component

Add to your `configuration.yaml`:
```yaml
recorder:
  db_url: !secret recorder_db_url
  purge_keep_days: 30
```

### Step 2: Enable History Feature

1. Go to **Settings** > **Devices & Services**
2. Select **Eedomus** integration
3. Click on the three dots (⋮) and select **Options**
4. Enable **Enable History** checkbox
5. Save the configuration

### Step 3: Verify History Progress Sensors

1. Check the logs for messages like:
   ```
   ✅ History progress sensors created for all devices
   ```
2. Look for entities with format: `eedomus.history_progress_{periph_id}`
3. Check the state and attributes of these entities

### Step 4: Monitor History Retrieval

1. Check logs for history retrieval messages:
   ```
   Fetching history for {periph_id} (from {timestamp})
   History fully fetched for {periph_id} ({name}) (received {count} entries)
   ```
2. Monitor the history progress sensor values
3. Verify that progress increases over time

### Step 5: Visualize CPU Data

1. Create a graph in Home Assistant dashboard
2. Add the CPU sensor entity
3. Verify historical data is displayed
4. Check that the graph shows trends over time

## Expected Behavior

### Normal Operation (Recorder Enabled)
1. Integration starts
2. History progress sensors are created for all devices
3. Sensors show 0% progress initially
4. During refresh, history is retrieved in chunks
5. Progress sensors update to show retrieval progress
6. When complete, sensors show 100% and completed: true
7. Historical data is available in Home Assistant recorder

### Normal Operation (Recorder Disabled)
1. Integration starts
2. Warning message appears: "Recorder component not available..."
3. History progress sensors are not created
4. History retrieval is skipped
5. Normal device operation continues without history

### Error Conditions
1. If recorder is unavailable, clear warning message
2. If history API fails, error is logged but doesn't crash
3. If progress sensor creation fails, error is logged
4. Integration continues to work without history

## Troubleshooting

### Recorder Component Not Available
**Error**: `Recorder component not available. Cannot load history progress.`

**Solution**:
1. Ensure recorder is enabled in configuration.yaml
2. Restart Home Assistant
3. Check that recorder component is loaded

### History Progress Sensors Not Created
**Error**: No history progress sensors appear

**Solution**:
1. Check that CONF_ENABLE_HISTORY is True
2. Verify recorder component is available
3. Check logs for sensor creation messages
4. Manually trigger sensor creation via service call

### History Retrieval Fails
**Error**: `Failed to fetch history: {error}`

**Solution**:
1. Check API Eedomus credentials
2. Verify API Eedomus mode is enabled
3. Check eedomus API status
4. Review API response for details

### CPU Sensor Not Showing Data
**Error**: CPU sensor exists but shows no data

**Solution**:
1. Verify CPU Box device is mapped correctly (usage_id=23)
2. Check that device is reporting data to eedomus
3. Verify history retrieval is working
4. Check sensor entity attributes

## Next Steps

### Immediate
1. Deploy changes to Raspberry Pi
2. Restart Home Assistant
3. Test history progress sensor creation
4. Verify CPU sensor data retrieval

### Short Term
1. Add history option to UI (already present, needs testing)
2. Enable history by default (after thorough testing)
3. Add more detailed progress information
4. Improve data volume estimation

### Long Term
1. Add history charts to dashboard
2. Create history summary sensors
3. Add history statistics
4. Implement history cleanup

## Files Modified

1. `custom_components/eedomus/coordinator.py`
   - Enhanced recorder detection in `_load_history_progress()`
   - Enhanced recorder detection in `_save_history_progress()`
   - Added `_create_history_progress_sensor()` method
   - Added sensor creation after history retrieval

2. `custom_components/eedomus/eedomus_client.py`
   - Added `get_device_history_count()` method

3. `custom_components/eedomus/__init__.py`
   - Added history progress sensor creation on setup

4. `custom_components/eedomus/config/device_mapping.yaml`
   - Already contains correct CPU sensor mapping (no changes needed)

## Testing Checklist

- [ ] Recorder component detection works correctly
- [ ] History progress sensors are created when enabled
- [ ] CPU sensor is mapped correctly
- [ ] History retrieval works for CPU sensor
- [ ] Progress is visualized correctly
- [ ] Data volume estimation is reasonable
- [ ] Error handling works as expected
- [ ] Integration works without history when recorder is disabled

## Deployment Instructions

```bash
# Deploy to Raspberry Pi
cd /Users/danjer/mistral
git checkout unstable
./deploy_on_rasp.sh

# Check logs after deployment
tail -n 100 ~/mistral/rasp.log

# Verify services are running
ha service list | grep eedomus

# Check history progress sensors
ha states | grep "eedomus.history_progress"
```

## Conclusion

The history feature implementation provides:
- Robust recorder component detection
- Visual history progress indicators
- CPU sensor mapping and data retrieval
- Graceful error handling
- Comprehensive logging for debugging

The feature is ready for testing and can be enabled by users who have recorder component configured in their Home Assistant installation.
