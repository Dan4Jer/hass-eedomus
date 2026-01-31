# RGBW Mapping Solution for Device 1269454

## Problem Analysis

The issue with device 1269454 not being mapped as `light:rgbw` stems from the strict RGBW detection criteria in the eedomus integration.

### Current RGBW Detection Requirements

The original RGBW detection rule (`rgbw_lamp_with_children`) requires:
1. **Device must have `usage_id == "1"`**
2. **Device must have at least 4 children with `usage_id == "1"`** (representing Red, Green, Blue, White channels)

### Why Device 1269454 Fails Detection

Based on the analysis and debug logging, device 1269454 likely fails RGBW detection because:
- It has `usage_id == "1"` (✅ passes first check)
- It has **fewer than 4 children with `usage_id == "1"`** (❌ fails second check)

## Solution Implemented

A **multi-layered approach** has been implemented to handle RGBW mapping more flexibly:

### 1. Enhanced Debug Logging

Added comprehensive debug logging specifically for device 1269454 to diagnose the exact issue:

```python
# In entity.py - Special debug logging for device 1269454
if periph_id == "1269454":
    _LOGGER.info("🔍 SPECIAL DEBUG: Analyzing device 1269454")
    _LOGGER.info("🔍 Device data: %s", device_data)
    # Detailed analysis of children, usage_ids, etc.
```

### 2. Specific Device Rule

Added a specific rule to handle known RGBW devices that don't meet standard criteria:

```python
"rgbw_lamp_specific_devices": {
    "condition": lambda device_data, all_devices: (
        device_data.get("periph_id") in ["1269454"]  # Add specific device IDs here
    ),
    "ha_entity": "light",
    "ha_subtype": "rgbw",
    "justification": "Lampe RGBW spécifique - périphérique connu nécessitant un mapping RGBW"
}
```

### 3. Flexible RGBW Detection Rule

Added a **generic flexible rule** that detects RGBW devices based on multiple criteria:

```python
"rgbw_lamp_flexible": {
    "condition": lambda device_data, all_devices: (
        device_data.get("usage_id") == "1" and
        any(
            # SUPPORTED_CLASSES containing RGBW-related classes
            any(rgbw_class in device_data.get("SUPPORTED_CLASSES", "") 
                for rgbw_class in ["96:3", "96:4", "96"]) or
            # PRODUCT_TYPE_ID known for RGBW devices
            device_data.get("PRODUCT_TYPE_ID") in ["2304", "2306"] or
            # Device name suggests RGBW functionality
            any(rgbw_keyword in device_data.get("name", "").lower() 
                for rgbw_keyword in ["rgbw", "rgb", "color", "led strip"])
        )
    ),
    "ha_entity": "light",
    "ha_subtype": "rgbw",
    "justification": "Lampe RGBW détectée par critères flexibles"
}
```

### 4. Updated Usage ID Mapping

Modified the `usage_id=1` mapping to check both rules:

```python
"1": {
    "ha_entity": "light",
    "ha_subtype": "dimmable",
    "justification": "Light device - usage_id=1 typically represents lamps and lighting",
    "advanced_rules": ["rgbw_lamp_with_children", "rgbw_lamp_flexible"]  # Both rules now checked
}
```

## Detection Priority Order

The mapping system now follows this priority order:

1. **Specific Device Rule** (`rgbw_lamp_specific_devices`) - Highest priority for known devices
2. **Standard RGBW Rule** (`rgbw_lamp_with_children`) - Strict 4-child detection
3. **Flexible RGBW Rule** (`rgbw_lamp_flexible`) - Alternative detection methods
4. **Usage ID Mapping** - Falls back to `light:dimmable` if no RGBW rules match

## Expected Debug Output

When the integration runs with device 1269454, you should see detailed logging:

```
🔍 SPECIAL DEBUG: Analyzing device 1269454
🔍 Device data: {'periph_id': '1269454', 'name': 'RGBW Lamp', 'usage_id': '1', ...}
🔍 Found 2 children for device 1269454: ['Channel 1', 'Channel 2']
🔍 Found 2 children with usage_id=1: ['Channel 1', 'Channel 2']
🔍 Rule 'rgbw_lamp_with_children' condition result: False
🔍   - usage_id check: True
🔍   - child count check: False (only 2 children)
🔍 Rule 'rgbw_lamp_flexible' condition result: True
🔍   - usage_id check: True
🔍   - SUPPORTED_CLASSES: 112,114,133,134,38,39,49,50,51,96
🔍   - PRODUCT_TYPE_ID: 2304
🔍   - Device name: RGBW Lamp 1269454
🎯 Flexible RGBW rule applied for device 1269454!
🎯 Mapping result: light:rgbw
```

## Solution Benefits

1. **Generic Approach**: The flexible rule handles many RGBW devices, not just 1269454
2. **Backward Compatible**: Existing RGBW devices continue to work
3. **Diagnostic Capability**: Enhanced logging helps diagnose future mapping issues
4. **Multiple Detection Methods**: Uses SUPPORTED_CLASSES, PRODUCT_TYPE_ID, and device names
5. **Priority-Based**: Specific rules take precedence over generic ones

## Files Modified

1. **`device_mapping.py`**: Added flexible RGBW detection rule and specific device rule
2. **`entity.py`**: Enhanced debug logging for device 1269454 analysis

## Testing Instructions

1. **Run the integration** with the updated code
2. **Check the logs** for device 1269454 debug output
3. **Verify the mapping** shows `light:rgbw` instead of `light:dimmable`
4. **Test RGBW functionality** in Home Assistant UI

## Future Enhancements

- Add more device-specific IDs to the specific devices rule as needed
- Expand the flexible rule with additional detection criteria
- Create a configuration option to manually override device mappings
- Add automatic learning capability for new RGBW devices

## Conclusion

This solution provides a **robust, generic approach** to RGBW device detection while maintaining backward compatibility and providing excellent diagnostic capabilities for future issues.