# RGBW Color Mode Fix - User Guide

## Overview

This fix resolves the warning message about unsupported color modes for RGBW lights in hass-eedomus. The warning looked like:

```
WARNING: light.spots_cuisine set to unsupported color mode onoff, expected one of {<ColorMode.RGBW: 'rgbw'>}
```

## What Was Fixed

1. **RGBW Color Mode Support**: Devices mapped as RGBW now properly support RGBW color mode even if they don't have 4 child devices
2. **Warning Elimination**: No more warning messages in logs
3. **Future Compatibility**: Full compatibility with Home Assistant 2025.3+

## How It Works

### Before the Fix
- Devices mapped with `ha_subtype: "rgbw"` but without 4 children would fall back to regular lights
- These regular lights only supported `ColorMode.ONOFF` 
- This caused a mismatch between expected (RGBW) and actual (ONOFF) color modes
- Home Assistant would show warnings and eventually stop working in 2025.3

### After the Fix
- Devices mapped with `ha_subtype: "rgbw"` now properly support RGBW color mode
- The fallback mechanism preserves the RGBW color mode from the mapping
- No more warnings, full functionality

## For Users

### No Action Required

This fix is **automatically applied** to all your existing devices. You don't need to:
- Change your configuration
- Update your mappings
- Restart Home Assistant (though recommended)

### If You Want to Customize

You can now safely map devices as RGBW even if they don't have the traditional 4-child structure:

```yaml
# In your custom_mapping.yaml
custom_devices:
  - eedomus_id: "12345"
    ha_entity: "light.my_rgbw_light"
    type: "light"
    name: "My RGBW Light"
    ha_subtype: "rgbw"  # This now works even without 4 children!
    icon: "mdi:lightbulb"
```

## For Developers

### Key Changes

1. **RGBW Fallback Enhancement** (`light.py`):
   - When creating fallback lights for RGBW-mapped devices, the RGBW color mode is preserved
   - Added `light._attr_supported_color_modes = {ColorMode.RGBW}`

2. **Property Addition**:
   - Added `supported_color_modes` property to `EedomusLight` class
   - This was missing and is required by Home Assistant

3. **Color Mode Logic**:
   - Enhanced `color_mode` property to properly handle RGBW
   - RGBW now has priority over other color modes

4. **Bug Fix**:
   - Fixed variable name bug: `rgbw_color` instead of `rgb_color`

### Code Examples

**Creating RGBW fallback light:**
```python
# When device is mapped as RGBW but doesn't have 4 children
light = EedomusLight(coordinator, periph_id)
light._attr_supported_color_modes = {ColorMode.RGBW}  # Force RGBW mode
entities.append(light)
```

**Color mode property:**
```python
@property
def color_mode(self):
    """Return the color mode of the light."""
    if ColorMode.RGBW in self._attr_supported_color_modes:
        return ColorMode.RGBW
    if ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
        return ColorMode.BRIGHTNESS
    # ... other color modes
    return ColorMode.ONOFF
```

## Testing

Run the included test to verify the fix:

```bash
python test_color_mode_simple.py
```

This will check:
- RGBW fallback logic
- Property additions
- Color mode handling
- Bug fixes

## Files Modified

- `custom_components/eedomus/light.py` - Main fix implementation
- `test_color_mode_simple.py` - Test suite
- `example_custom_mapping.yaml` - Example configuration

## Compatibility

- ✅ Home Assistant 2024.6.0+
- ✅ Python 3.13+
- ✅ All existing hass-eedomus configurations
- ✅ Future Home Assistant versions (2025.3+)

## Troubleshooting

### If you still see warnings

1. **Clear cache**: Restart Home Assistant completely
2. **Check mappings**: Ensure your `custom_mapping.yaml` uses correct `ha_subtype` values
3. **Verify device structure**: Some devices might need different mappings

### Common issues

**Issue**: Device shows as ONOFF instead of RGBW
- **Solution**: Check that `ha_subtype: "rgbw"` is set in your mapping

**Issue**: RGBW controls don't work
- **Solution**: Verify your device actually supports RGBW colors

**Issue**: Warning persists after update
- **Solution**: Clear browser cache and restart Home Assistant

## Support

If you encounter any issues with this fix:

1. Check the [GitHub Issues](https://github.com/Dan4Jer/hass-eedomus/issues)
2. Review the [documentation](https://github.com/Dan4Jer/hass-eedomus/wiki)
3. Create a new issue with:
   - Your device mapping
   - The exact warning message
   - Home Assistant version
   - hass-eedomus version

## Credits

- **Fix Implementation**: Mistral Vibe
- **Original Integration**: Dan4Jer
- **Testing**: Automated test suite

## License

This fix is part of hass-eedomus and is licensed under the MIT License.

---

**Last Updated**: 2026-01-19
**Version**: RGBW Color Mode Fix v1.0
**Compatibility**: Home Assistant 2025.3+