# History Option Debug Guide

## Issue Summary

The history option is showing as `False` in logs even when it should be enabled. This document explains the root cause and provides solutions.

## Root Cause Analysis

### The Problem

The history option logic is working correctly, but there are two potential scenarios causing confusion:

1. **Scenario 1: History enabled in config, but options has False (default)**
   - User enables history in config_flow
   - User saves options without changing history (remains False by default)
   - System correctly falls back to config value (True)
   - But logs show `history=False` because that's the raw options value

2. **Scenario 2: History option not properly saved in storage**
   - The option might not be saved correctly during config_flow or options_flow
   - The storage file might have incorrect or missing values

### Current Logic Flow

```python
# From __init__.py and coordinator.py

# Step 1: Read from config
history_from_config = config_entry.data.get(CONF_ENABLE_HISTORY, False)

# Step 2: Check if explicitly set in options
if CONF_ENABLE_HISTORY in config_entry.options:
    history_from_options = config_entry.options[CONF_ENABLE_HISTORY]
    
    # Step 3: Only use options if explicitly enabled (not False)
    if history_from_options != False:
        history_enabled = history_from_options  # Use options
    else:
        history_enabled = history_from_config  # Fall back to config
else:
    history_enabled = history_from_config  # No options, use config
```

### The Misleading Log Message

The current log message shows:
```
"Performing partial refresh for X peripherals (history retrieval: False)"
```

This shows the **final decision** (`history_retrieval`), but the confusion arises because:
- If options has `False` and config has `True`, the final decision is `True`
- But users see `False` in logs and assume history is disabled

## Debugging Steps

### 1. Check Current Logs

Look for these debug messages (added in recent fixes):

```
DEBUG: History option decision: config=<value>, options=<value>, final=<value>
```

This shows:
- `config`: Value from config_entry.data
- `options`: Value from config_entry.options (or "not_set")
- `final`: The actual decision made by the system

### 2. Verify Storage File

On the Raspberry Pi, check the storage file:

```bash
# Navigate to Home Assistant config directory
cd /config/.storage

# Find eedomus storage file
ls -la | grep eedomus

# Check the content
cat core.config_entries | grep -A 20 -B 5 "eedomus"
```

Look for the `history` option in both `data` and `options` sections.

### 3. Manual Fix (if needed)

If the history option is missing or incorrect in storage:

```bash
# Edit the storage file
nano /config/.storage/core.config_entries

# Find your eedomus entry and add/modify:
"options": {
    "history": true,
    ...
}

# Or use the provided script (if available)
python3 /config/www/check_and_fix_history_option.py
```

## Solutions

### Solution 1: Enable History via UI (Recommended)

1. Go to Home Assistant Settings
2. Find "Eedomus" integration
3. Click "Configure"
4. Enable the "Enable History" checkbox
5. Save the configuration

### Solution 2: Manual Storage Edit

If the UI option is not working:

1. SSH into your Raspberry Pi
2. Edit the storage file:
   ```bash
   nano /config/.storage/core.config_entries
   ```
3. Find your eedomus integration entry
4. Add or modify the `history` option:
   ```json
   "options": {
       "history": true,
       ...
   }
   ```
5. Save and restart Home Assistant

### Solution 3: Use Deployment Script

A deployment script is available to automate this:

```bash
# On the Raspberry Pi
bash /config/www/activate_history_feature.sh
```

This script will:
1. Check current history option status
2. Enable history if needed
3. Restart Home Assistant if changes were made

## Verification

After applying any fix, verify that history is working:

1. Check logs for debug messages:
   ```
   DEBUG: History option decision: config=True, options=True, final=True
   ```

2. Look for virtual history sensors:
   - `sensor.eedomus_history_progress` (global progress)
   - `sensor.eedomus_history_stats` (download statistics)
   - Individual device progress sensors

3. Check that history retrieval is happening:
   ```
   INFO: Performing partial refresh for X peripherals (history retrieval: True)
   ```

## Common Pitfalls

### Pitfall 1: Options Reset

When you save options without changing the history checkbox, it defaults to `False`. The system correctly falls back to the config value, but this can be confusing.

**Solution:** Always explicitly enable/disable history in the options UI.

### Pitfall 2: Config vs Options Conflict

If config has `True` but options has `False`, the system uses `True` (config wins). But logs might show confusing messages.

**Solution:** Make sure both config and options are consistent.

### Pitfall 3: Missing Options Entirely

If the `history` key is not present in options at all, the system falls back to config.

**Solution:** Ensure the option is explicitly set in options.

## Technical Details

### Code Changes Made

1. **Added debug logging** in both `__init__.py` and `coordinator.py`:
   ```python
   _LOGGER.debug(
       "History option decision: config=%s, options=%s, final=%s",
       history_from_config,
       config_entry.options.get(CONF_ENABLE_HISTORY, "not_set"),
       history_enabled
   )
   ```

2. **Improved log messages** to show the decision-making process

3. **Enhanced error handling** for missing or invalid options

### Future Improvements

1. **Better UI feedback**: Show which source (config/options) is being used
2. **Migration script**: Automatically fix inconsistent config/options
3. **Health check**: Warn users when config and options conflict
4. **Default value handling**: Make the fallback logic more explicit

## Troubleshooting

### "History shows False but should be True"

1. Check debug logs for the decision process
2. Verify storage file has correct values
3. Ensure you explicitly enabled history in the UI
4. Restart Home Assistant after making changes

### "Virtual sensors not created"

1. Check that `history_enabled` is `True` in logs
2. Verify `_create_virtual_history_sensors()` is being called
3. Look for errors in the logs during initialization

### "History retrieval not happening"

1. Check that `history_retrieval` is `True` in partial refresh logs
2. Verify peripherals are being added to the history queue
3. Check for API errors during history fetching

## References

- **Source code**: `hass-eedomus/custom_components/eedomus/coordinator.py`
- **Options flow**: `hass-eedomus/custom_components/eedomus/options_flow.py`
- **Initialization**: `hass-eedomus/custom_components/eedomus/__init__.py`
- **Constants**: `hass-eedomus/custom_components/eedomus/const.py`

## Support

If you're still having issues after trying these solutions:

1. Check the debug logs and note the exact messages
2. Verify your storage file content
3. Create a GitHub issue with:
   - Home Assistant version
   - Eedomus integration version
   - Relevant log snippets
   - Storage file content (redact sensitive info)
   - Steps to reproduce

The debug logs added in this version should help identify exactly where the issue is occurring.