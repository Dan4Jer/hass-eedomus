# Eedomus Integration - Options Configuration

## Overview

The Eedomus integration provides a flexible configuration system that allows you to customize device mappings and behavior through both UI and YAML editing modes.

## Configuration Modes

### YAML Editor Mode

The YAML editor provides direct access to the `custom_mapping.yaml` configuration file with:

- **Syntax highlighting** for better readability
- **Validation** before saving to catch errors early
- **Preview** functionality to see how your changes will be applied
- **Template generation** for new configurations

### UI Mode (Deprecated)

The UI mode has been removed in favor of the more powerful YAML editor. All configuration is now done through the YAML interface.

## YAML Configuration Structure

The `custom_mapping.yaml` file supports the following sections:

### Metadata

```yaml
metadata:
  version: "1.0"
  last_modified: "2026-01-01"
  changes:
    - "Added support for new device types"
```

### Custom Devices

```yaml
custom_devices:
  - eedomus_id: "12345"
    ha_entity: "light.my_light"
    type: "light"
    ha_subtype: "rgbw"
    icon: "mdi:lightbulb"
    room: "Living Room"
    parent_periph_id: "67890"
    attributes:
      color_mode: "rgbw"
      brightness: true
```

### Custom Rules

```yaml
custom_rules:
  - name: "Override temperature sensor"
    condition:
      usage_id: "temperature_1"
      state: "on"
    actions:
      - type: "override"
        ha_entity: "sensor.temperature"
        attributes:
          device_class: "temperature"
```

### Usage ID Mappings

```yaml
custom_usage_id_mappings:
  "temperature_1":
    ha_entity: "sensor"
    ha_subtype: "temperature"
    device_class: "temperature"
    justification: "Custom mapping for temperature sensor"
```

### Temperature Setpoint Mappings

```yaml
temperature_setpoint_mappings:
  "thermostat_1":
    ha_entity: "climate.thermostat"
    unit_of_measurement: "°C"
    justification: "Custom thermostat mapping"
```

### Name Patterns

```yaml
custom_name_patterns:
  - pattern: "^Living Room (.*)"
    replacement: "$1"
    target: "name"
```

## Using the YAML Editor

### Accessing the Editor

1. Go to **Settings** > **Devices & Services**
2. Select the **Eedomus** integration
3. Click **Configure**
4. The YAML editor will open with your current configuration

### Editing Configuration

1. Make your changes in the YAML editor
2. Click **Preview** to validate your changes
3. If validation succeeds, click **Save** to apply
4. If validation fails, correct the errors and try again

### Preview Mode

The preview mode shows:
- Your YAML content with syntax highlighting
- Validation status (✅ Valid or ❌ Error)
- Any validation errors with details

### Saving Configuration

When you save:
1. The YAML is parsed and validated
2. If valid, it's saved to `custom_mapping.yaml`
3. The integration reloads with your new configuration
4. Any errors are shown in the UI

## Validation Rules

The YAML configuration is validated against the following rules:

### Required Fields

- `custom_devices` entries require: `eedomus_id`, `ha_entity`, `type`
- `custom_rules` entries require: `name`, `condition`, `actions`
- Conditions require: `usage_id`, `state`
- Actions require: `type`

### Valid Types

- Device types: `light`, `switch`, `sensor`, `cover`, `binary_sensor`, `climate`, `select`, `text_sensor`
- Action types: `override`, `ignore`, `transform`
- State values: `on`, `off`, `unavailable`

### Target Values

- Name patterns target: `name`, `entity_id`

## Error Handling

Common errors and solutions:

### Invalid YAML Syntax

```
Error: "expected str for dictionary value @ data['metadata']['version']"
```

**Solution:** Ensure all string values are quoted:
```yaml
version: "1.0"  # Correct
version: 1.0     # Incorrect
```

### Missing Required Fields

```
Error: "required key not provided @ data['custom_devices'][0]['eedomus_id']"
```

**Solution:** Add all required fields to your device entry.

### Invalid Device Type

```
Error: "invalid value: 'invalid_type'"
```

**Solution:** Use one of the supported device types.

## Best Practices

1. **Always preview** before saving to catch errors early
2. **Use quotes** for all string values to avoid YAML parsing issues
3. **Keep a backup** of your configuration before making major changes
4. **Test changes** with a small subset of devices first
5. **Use comments** to document your custom mappings

## Example Configuration

```yaml
# Eedomus Custom Mapping Configuration
# Edit this file to override default device mappings

metadata:
  version: "1.0"
  last_modified: "2026-01-01"
  changes:
    - "Initial configuration"
    - "Added living room light"

custom_rules:
  - name: "Override living room temperature"
    condition:
      usage_id: "temp_living"
      state: "on"
    actions:
      - type: "override"
        ha_entity: "sensor.living_room_temperature"
        attributes:
          device_class: "temperature"
          unit_of_measurement: "°C"

custom_usage_id_mappings:
  "temp_living":
    ha_entity: "sensor"
    ha_subtype: "temperature"
    device_class: "temperature"
    justification: "Custom mapping for living room temperature"

temperature_setpoint_mappings:
  "thermostat_main":
    ha_entity: "climate.main_thermostat"
    unit_of_measurement: "°C"
    justification: "Main thermostat mapping"

custom_name_patterns:
  - pattern: "^Room (.*)"
    replacement: "$1"
    target: "name"

custom_devices:
  - eedomus_id: "12345"
    ha_entity: "light.living_room_main"
    type: "light"
    ha_subtype: "rgbw"
    icon: "mdi:lightbulb"
    room: "Living Room"
    parent_periph_id: "67890"
    attributes:
      color_mode: "rgbw"
      brightness: true

  - eedomus_id: "12346"
    ha_entity: "switch.living_room_fan"
    type: "switch"
    icon: "mdi:fan"
    room: "Living Room"
```

## Troubleshooting

### Configuration Not Loading

1. Check the Home Assistant logs for errors
2. Verify your YAML syntax is correct
3. Ensure all required fields are present
4. Try the preview function to validate

### Changes Not Applied

1. Make sure you clicked **Save** after editing
2. Check that the configuration was saved to `custom_mapping.yaml`
3. Restart Home Assistant if changes don't appear
4. Check the integration logs for errors

### Validation Errors

1. Read the error message carefully
2. Check the specific line mentioned in the error
3. Compare with the example configuration
4. Use the preview function to test fixes

## Support

For issues with the YAML editor or configuration:

1. Check the Home Assistant logs
2. Review this documentation
3. Compare with the example configuration
4. Contact support with your configuration and error messages
