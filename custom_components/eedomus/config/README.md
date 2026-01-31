# Device Mapping Configuration

This directory contains the YAML configuration files for mapping eedomus devices to Home Assistant entities.

## Files

### `device_mapping.yaml`
Default device mappings provided by the integration. This file contains:
- Advanced rules for complex device detection (RGBW lamps, etc.)
- Usage ID mappings for standard device types
- Name pattern mappings for regex-based matching
- Default fallback mapping

### `custom_mapping.yaml`
User-customizable mappings that override the default mappings. Users can add their own:
- Custom rules for specific devices
- Custom usage ID mappings
- Custom name patterns

## How It Works

1. The integration loads `device_mapping.yaml` first (default mappings)
2. Then loads `custom_mapping.yaml` (user customizations)
3. Merges them with custom mappings taking precedence
4. Uses the merged configuration for device entity mapping

## Priority Order

1. **Custom rules** (from `custom_mapping.yaml`)
2. **Advanced rules** (RGBW detection, parent-child relationships)
3. **Usage ID mappings** (from YAML files)
4. **Name pattern matching** (regex patterns)
5. **Default mapping** (fallback)

## Customization

To customize device mappings:

1. Edit `custom_mapping.yaml`
2. Add your custom rules following the same structure as `device_mapping.yaml`
3. Restart Home Assistant or use the reload service

## Example

```yaml
# custom_mapping.yaml
version: 1.0

custom_rules:
  - name: "My Custom RGBW Device"
    priority: 1
    conditions:
      - usage_id: "1"
      - name: ".*my rgbw.*"
    mapping:
      ha_entity: "light"
      ha_subtype: "rgbw"
      justification: "Custom RGBW device mapping"

custom_usage_id_mappings:
  "42":
    ha_entity: "sensor"
    ha_subtype: "custom"
    justification: "Custom sensor type"
```

## Notes

- Do not modify `device_mapping.yaml` directly as it may be overwritten during updates
- All customizations should go in `custom_mapping.yaml`
- The integration will automatically merge both files at startup
- Changes take effect immediately after restart or reload
