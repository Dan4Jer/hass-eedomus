# Security Warning Fix

## Current Status

The security warning appears because the `api_proxy_disable_security` setting is currently set to `True` in your Home Assistant configuration.

## What the Warning Means

```
⚠️ SECURITY WARNING: API Proxy IP validation has been disabled for debugging purposes.
This exposes your webhook endpoints to potential abuse from any IP address.
Only use this setting temporarily for debugging in secure environments.
```

This warning indicates that the API Proxy is accepting requests from any IP address, which could be a security risk if your Home Assistant instance is accessible from the internet.

## How to Fix It

### Option 1: Use the Options Flow (Recommended)

1. Go to Home Assistant settings
2. Find the eedomus integration
3. Click on "Configure" or "Options"
4. The UI mode is now re-enabled (previously disabled)
5. Look for the `api_proxy_disable_security` setting
6. Set it to `False` (disabled)
7. Save the configuration

### Option 2: Manual Database Edit (Advanced)

If you need to fix it immediately without waiting for the UI:

1. Access your Home Assistant database (usually SQLite)
2. Find the `config_entries` table
3. Locate the eedomus integration entry
4. Update the `data` or `options` JSON field to set `api_proxy_disable_security` to `false`

### Option 3: Wait for Next Update

The default value in the code is already set to `False` (security enabled). For new installations, this will be the default. Existing installations will need to manually change the setting.

## Technical Details

- **Default value**: `False` (security enabled)
- **Current value**: `True` (security disabled) - this is what's causing the warning
- **File**: `custom_components/eedomus/const.py` line 58
- **Used in**: `__init__.py` line 168-169

## Why Was It Disabled?

This setting was likely disabled during development/debugging to allow testing from different IP addresses. Now that the system is stable, it should be re-enabled for security.

## After Fixing

Once you set `api_proxy_disable_security` to `False`:
- The warning will disappear
- The API Proxy will only accept requests from your eedomus server's IP address
- Your system will be more secure against potential abuse
