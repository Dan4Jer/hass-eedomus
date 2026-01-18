# Eedomus Device Mapping Table Documentation

This document provides a comprehensive mapping between eedomus devices and Home Assistant entities, generated from the eedomus API.

## Table Overview

The table below shows how eedomus devices are mapped to Home Assistant entities based on their characteristics, usage IDs, and supported classes.

### Table Structure

| Column | Description |
|--------|-------------|
| **parent_id** | The parent device ID (empty if standalone) |
| **perph_id** | The unique peripheral device ID |
| **usage_id:usage_name** | The usage ID and its descriptive name |
| **SUPPORTED_CLASSES** | Z-Wave classes supported by the device (simplified to base class numbers only) |
| **ha_type:ha_subtype** | Home Assistant entity type and subtype |
| **justification** | Reason for the specific mapping |

**Note**: SUPPORTED_CLASSES are simplified to show only the base Z-Wave class numbers (e.g., "38,49" instead of "38:1,49:2"). This makes the table more readable while preserving the essential class information.

## Generated Device Mapping Table

```
# Eedomus Device Mapping Table

This table shows the mapping between eedomus devices and Home Assistant entities.

## Table Structure

| parent_id | perph_id | usage_id:usage_name | SUPPORTED_CLASSES | ha_type:ha_subtype | justification |
|-----------|----------|---------------------|-------------------|-------------------|---------------|
|  | 1077374 | 7:Température | 49:2,38:1 | sensor:temperature | usage_id=7 |
|  | 1077644 | 1:Lumière RGBW | 38:1,96:3 | light:dimmable | usage_id=1 |
|  | 1078123 | 48:Volet | 38:1,48:1 | cover:shutter | usage_id=48 |
|  | 1090995 | 37:Détecteur de mouvement | 37:1,48:1 | binary_sensor:motion | usage_id=37 |
|  | 1090996 | 7:Température | 49:2 | sensor:temperature | usage_id=7 |
|  | 1145719 | 1:Lumière | 38:1,96:3 | light:dimmable | usage_id=1 |
|  | 1252440 | 19:Consigne chauffage | 67:1 | sensor:unknown | default |
|  | 2486570 | 27:Détecteur de fumée | 48:1 | binary_sensor:smoke | usage_id=27 |
|  | 3415417 | 36:Détecteur d'inondation | 48:1 | binary_sensor:moisture | usage_id=36 |
|  | 3445481 | 48:Volet Parent | 94:1 | cover:shutter | usage_id=48 |
```

## Mapping Logic

The mapping from eedomus devices to Home Assistant entities follows this priority order:

1. **Usage ID Mapping**: Devices are first mapped based on their `usage_id`
2. **Name Patterns**: If usage_id is unknown, the device name is analyzed for patterns
3. **Fallback**: Default to `sensor:unknown` if no specific mapping is found

### Common Usage ID Mappings

| usage_id | HA Entity | HA Subtype | Description |
|----------|-----------|------------|-------------|
| 1 | light | dimmable | Light devices |
| 7 | sensor | temperature | Temperature sensors |
| 23 | sensor | cpu_usage | CPU usage monitors |
| 26 | sensor | energy | Energy consumption sensors |
| 27 | binary_sensor | smoke | Smoke detectors |
| 36 | binary_sensor | moisture | Flood/water sensors |
| 37 | binary_sensor | motion | Motion detectors |
| 38 | climate | fil_pilote | Fil pilote heating systems |
| 48 | cover | shutter | Shutters/blinds |

## Device Examples

### Temperature Sensors (usage_id=7)
- **Device**: Fibaro FGK-101
- **HA Entity**: `sensor.temperature`
- **Example**: "Température Salon" (1077374), "Température Extérieure" (1090996)

### Motion Detectors (usage_id=37)
- **Device**: Fibaro FGMS-001
- **HA Entity**: `binary_sensor.motion`
- **Example**: "Mouvement Entrée" (1090995)

### Shutters/Blinds (usage_id=48)
- **Device**: Fibaro FGR-223
- **HA Entity**: `cover.shutter`
- **Example**: "Volet Salon" (1078123), "Volet Chambre Parent" (3445481)

### Light Devices (usage_id=1)
- **Device**: Fibaro FGRGBW-441
- **HA Entity**: `light.dimmable`
- **Example**: "Spots Cuisine" (1145719), "Lumière RGBW Salon" (1077644)

### Smoke Detectors (usage_id=27)
- **Device**: Fibaro FGSD-002
- **HA Entity**: `binary_sensor.smoke`
- **Example**: "Fumée Couloir" (2486570)

## API Integration

This table is generated using the following eedomus API endpoints:

1. **Peripherals List**: `http://IP_DE_TA_BOX/api/get?action=periph.list&api_user=API_USER&api_secret=API_KEY&show_config=1`
2. **Peripherals Values**: `http://IP_DE_TA_BOX/api/get?action=periph.value_list&api_user=API_USER&api_secret=API_KEY&periph_id=all`
3. **Peripherals Characteristics**: `http://IP_DE_TA_BOX/api/get?action=periph.caract&api_user=API_USER&api_secret=API_KEY&periph_id=all`

## Usage in Development

This table serves as an intermediate representation for:

1. **Mapping Validation**: Verify that devices are correctly mapped to HA entities
2. **Debugging**: Identify mapping issues and edge cases
3. **Documentation**: Provide clear examples of device mappings
4. **Testing**: Create test cases based on real device data

## Future Enhancements

The mapping system can be enhanced by:

1. **Adding more usage_id mappings** based on real device data
2. **Improving pattern recognition** for device names
3. **Integrating PRODUCT_TYPE_ID** for more precise mapping
4. **Adding device-specific exceptions** for known edge cases

## Related Files

- `generate_device_table_mock.py` - Script that generates this table
- `device_data.json` - Raw JSON data used to generate the table
- `devices_class_mapping.py` - Main mapping logic implementation
- `entity.py` - Entity base class with mapping function

## How to Regenerate

To regenerate this table with your own eedomus data:

1. Update the API credentials in `generate_device_table_mock.py`
2. Run: `python generate_device_table_mock.py`
3. The updated table will be saved to `device_mapping_table.md`

## Notes

- This table uses mock data for demonstration purposes
- Real implementations should use actual API calls to get current device data
- The mapping logic continues to evolve based on community feedback and new device discoveries