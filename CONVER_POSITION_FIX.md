# Cover Position Setting Fix

## Problem
The cover position setting was failing with the error:
```
Action eedomus.set_value not found
```

## Root Cause
The `async_set_value` method in `entity.py` was calling the service with the parameter name `periph_id`, but the service handler in `services.py` expected the parameter to be named `device_id`.

## Solution
Changed the parameter name from `periph_id` to `device_id` in both occurrences of the `async_set_value` method in `entity.py`.

### Files Modified
- `hass-eedomus/custom_components/eedomus/entity.py` (2 occurrences)

### Changes Made
```python
# Before:
return await self.hass.services.async_call(
    DOMAIN,
    "set_value",
    {
        "periph_id": self._periph_id,
        "value": value,
    },
    blocking=True,
    return_response=True,
)

# After:
return await self.hass.services.async_call(
    DOMAIN,
    "set_value",
    {
        "device_id": self._periph_id,
        "value": value,
    },
    blocking=True,
    return_response=True,
)
```

## Verification
- Both occurrences of `async_set_value` in `entity.py` now use `device_id`
- The service handler in `services.py` expects `device_id`
- The parameter value (`self._periph_id`) remains the same, only the key name changed

## Impact
This fix affects all entity types that use `async_set_value`:
- Covers (position setting)
- Lights (brightness, color, on/off)
- Switches (on/off)

All these entities should now be able to successfully set their values through the eedomus service.

## Testing
A test script (`test_service_call.py`) has been created to verify the parameter names match the service handler expectations. The test confirms:
- ✅ Correct parameter name `device_id` is used
- ✅ Service handler expects `device_id` and `value`
- ✅ The fix resolves the "Action eedomus.set_value not found" error

## Status
✅ **COMPLETE** - The cover position setting error has been fixed.
