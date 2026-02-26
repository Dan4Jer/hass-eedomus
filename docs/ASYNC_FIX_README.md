# Async I/O Fix for Custom Mappings

## Problem
The integration was generating blocking call warnings:
```
Detected blocking call to open with args ('/config/custom_components/eedomus/config/custom_mapping.yaml', 'r') inside the event loop
```

This violated Home Assistant's async I/O requirements and could potentially cause performance issues.

## Solution

### Changes Made

1. **Added async version of `load_custom_yaml_mappings()`**
   - Created `load_custom_yaml_mappings_async(hass)` that uses `hass.async_add_executor_job`
   - Maintains backward compatibility with existing synchronous calls

2. **Moved custom mappings loading to async context**
   - Modified `EedomusClimate` class to load custom mappings in `async_added_to_hass()` instead of `__init__()`
   - This ensures file I/O happens outside the event loop

### Files Modified

- `custom_components/eedomus/device_mapping.py`: Added async function
- `custom_components/eedomus/climate.py`: Moved custom mappings loading to async context
- `custom_components/eedomus/manifest.json`: Version bumped to 0.13.25-unstable

### Technical Details

The fix uses Home Assistant's recommended pattern for async file I/O:

```python
async def load_custom_yaml_mappings_async(hass):
    """Load custom mappings from custom_mapping.yaml file asynchronously."""
    def _load_sync():
        return load_custom_yaml_mappings()
    
    return await hass.async_add_executor_job(_load_sync)
```

### Verification

After deployment:
- ✅ No more blocking call warnings in logs
- ✅ Custom temperature sensor mappings still work correctly
- ✅ All climate entities properly linked to their temperature sensors
- ✅ No regression in functionality

### Backward Compatibility

The synchronous version `load_custom_yaml_mappings()` is still available for any legacy code that might need it, though its use is discouraged in new code.

## Related Documentation

- [Home Assistant Async I/O Guidelines](https://developers.home-assistant.io/docs/asyncio_blocking_operations/#open)
- [async_add_executor_job Documentation](https://developers.home-assistant.io/docs/asyncio_working_with_async/#running-in-executor)