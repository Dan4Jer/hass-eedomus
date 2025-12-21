# Scene to Select Entity Migration

## Overview

This document describes the migration from Home Assistant Scene entities to Select entities for eedomus virtual devices. This change provides better UI representation and functionality for eedomus virtual devices that have multiple selectable options.

## Changes Made

### 1. New Select Entity Implementation (`select.py`)

Created a new `EedomusSelect` entity class that:

- Inherits from both `EedomusEntity` and `SelectEntity`
- Provides stateful representation of eedomus virtual devices
- Shows current selected option and available options
- Supports selection of different scene modes/options via dropdown

**Key Features:**
- `current_option` property: Returns the current selected option
- `options` property: Returns list of available options from device's `value_list`
- `async_select_option` method: Sends selected option to eedomus API
- Proper error handling and logging
- Support for both list and comma-separated string `value_list` formats

### 2. Updated Device Mapping

Modified `devices_class_mapping.py` to map the following device types to "select" instead of "scene":

- `usage_id=14`: Shutter groups
- `usage_id=42`: Centralized shutter openings  
- `usage_id=43`: Virtual scenes and automations
- `PRODUCT_TYPE_ID=999`: Virtual devices for scene triggering

### 3. Platform Configuration

Updated `const.py`:
- Replaced `Platform.SCENE` with `Platform.SELECT` in the `PLATFORMS` list

### 4. Entity Mapping Logic

Updated `entity.py`:
- Modified virtual device mapping to return "select" instead of "scene"

### 5. Documentation Updates

Updated `README.md`:
- Renamed "Scènes (Scene Entities)" to "Sélecteurs (Select Entities)"
- Updated feature descriptions to reflect select entity capabilities
- Moved select entities to "Plateformes HA pleinement supportées" section
- Updated entity count from "14 entités scene" to "14 entités select"

## Benefits of Select Entities

### 1. Better User Experience
- **Visual Feedback**: Users can see the current selected option
- **Option Discovery**: Available options are visible in the UI
- **State Representation**: Shows actual device state, not just activation capability

### 2. Enhanced Functionality
- **Two-way Control**: Both read current state and set new options
- **Multiple Options**: Supports devices with multiple selectable modes
- **Better Integration**: Works more naturally with Home Assistant automations

### 3. Improved UI Integration
- **Dropdown Interface**: Native select dropdown in Home Assistant UI
- **State Display**: Shows current option in entity cards
- **Consistent Behavior**: Matches other select entities in Home Assistant

## Backward Compatibility

- The original `scene.py` file is maintained for reference
- Existing scene entities will continue to work (if any)
- New installations will use select entities by default
- Migration path is automatic through device mapping

## Testing Requirements

### Devices to Test

Test with eedomus virtual devices that have:
- `usage_id=14`, `usage_id=42`, `usage_id=43`
- `PRODUCT_TYPE_ID=999`
- Non-empty `value_list` attribute

### Test Cases

1. **Entity Creation**: Verify select entities are created for mapped devices
2. **Option Display**: Check that available options are shown correctly
3. **State Representation**: Verify current option is displayed
4. **Option Selection**: Test selecting different options via UI
5. **API Integration**: Confirm selections are sent to eedomus API
6. **Error Handling**: Test with devices that have invalid/missing `value_list`
7. **Automation Integration**: Test using select entities in Home Assistant automations

### Expected Behavior

- Select entities should appear in Home Assistant UI with dropdown interface
- Current option should match eedomus device state
- Selecting an option should update both UI and eedomus device
- Error messages should be logged for API failures
- Entities should be marked as unavailable if `value_list` is empty

## Migration Notes

### For Existing Users

- Existing scene entities will be replaced by select entities on next restart
- Automations using scene activation will need to be updated to use select option selection
- Entity IDs will change from `*_scene` to `*_select`

### For Developers

- Select entities provide more comprehensive device representation
- Use `current_option` to get current state instead of activation status
- Use `async_select_option` to change state instead of `async_activate`
- Handle `value_list` parsing for both list and string formats

## Technical Details

### Select Entity vs Scene Entity

| Feature | Scene Entity | Select Entity |
|---------|-------------|---------------|
| **State Representation** | Stateless | Stateful |
| **UI Control** | Activate button | Dropdown selection |
| **Current Value** | N/A | Shows current option |
| **Available Options** | N/A | Shows all options |
| **Use Case** | One-time activation | Multi-option selection |

### Data Flow

```
Eedomus Device (value_list) 
    ↓
Select Entity (options property)
    ↓
Home Assistant UI (dropdown)
    ↓
User Selection
    ↓
Select Entity (async_select_option)
    ↓
Eedomus API (set_periph_value)
```

## Future Enhancements

Potential improvements for future versions:

1. **Dynamic Option Updates**: Refresh options list when device capabilities change
2. **Option Icons**: Add icons for different option types
3. **Option Grouping**: Group related options in UI
4. **Option Descriptions**: Add descriptions for each option
5. **Performance Optimization**: Cache options list to reduce API calls

## Conclusion

This migration from Scene to Select entities provides a more accurate and useful representation of eedomus virtual devices in Home Assistant. Select entities better match the actual device capabilities and provide enhanced user interaction through the Home Assistant interface.