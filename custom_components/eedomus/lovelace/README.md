# Eedomus Configuration Panel - Lovelace Card

A modern Lovelace card for configuring Eedomus device mapping and dynamic properties, compatible with Home Assistant 2026.1+.

## Features

- **Entity Properties Configuration**: Configure which entity types should receive frequent updates
- **Device-Specific Overrides**: Override dynamic behavior for individual devices by periph_id
- **Device Status View**: View dynamic status and configuration for all devices
- **Configuration Switching**: Switch between default and custom configurations
- **Real-time Updates**: Changes are applied immediately and saved to configuration files
- **Opportunistic Refresh**: Dynamic devices are included in optimized refresh mechanisms

## Dynamic Devices Definition

**Dynamic devices** are devices whose state can change unpredictably due to user actions. These include:

- **Buttons and switches** - Can be toggled by users at any time
- **Covers/Shutters** - Can be opened/closed by users
- **Motion detectors** - State changes based on movement detection
- **Binary sensors** - State changes based on environmental conditions

**Non-dynamic devices** typically include:
- **Temperature sensors** - Change slowly and predictably
- **Humidity sensors** - Change gradually
- **Static information displays** - Rarely change

Dynamic devices are included in **opportunistic refresh mechanisms** to ensure their state is kept up-to-date without unnecessary polling.

## Installation

### Manual Installation

1. Copy the `lovelace` folder to your `custom_components/eedomus/` directory
2. Add the following to your `configuration.yaml`:

```yaml
lovelace:
  mode: yaml
  resources:
    - url: /local/eedomus/lovelace/config_panel.js
      type: module
```

3. Restart Home Assistant

### HACS Installation (Recommended)

1. Add this repository to HACS
2. Install the "Eedomus Configuration Panel" integration
3. The card will be automatically registered

## Usage

### Adding the Card to Your Dashboard

Add the following YAML to your Lovelace configuration:

```yaml
type: custom:eedomus-config-panel-card
```

Or use the UI editor:
1. Click "Add Card"
2. Search for "Eedomus Configuration Panel"
3. Select the card

### Using the Configuration Panel

#### Entity Properties Tab

- **Toggle switches** to enable/disable dynamic updates for each entity type
- Changes are saved automatically to your custom configuration
- Default values are loaded from `device_mapping.yaml`

#### Device Overrides Tab

- View all devices with manual overrides
- **Remove overrides** to revert to default behavior
- **Toggle switches** to change dynamic status for specific devices
- Use the search bar to find specific devices

#### All Devices Tab

- View all configured devices and their dynamic status
- See the reasoning behind each device's dynamic status
- Identify which devices have manual overrides
- Use the search bar to filter devices

### Configuration Files

The panel works with two configuration files:

1. **`device_mapping.yaml`** - Default configuration (read-only in UI)
2. **`custom_mapping.yaml`** - Custom configuration (editable via UI)

When you make changes in the UI, they are saved to `custom_mapping.yaml` and override the default values.

## Configuration Structure

### Entity Properties

```yaml
dynamic_entity_properties:
  light: true      # Lights receive frequent updates
  switch: true     # Switches receive frequent updates  
  binary_sensor: true  # Binary sensors receive frequent updates
  sensor: false    # Sensors do not receive frequent updates
  climate: false   # Climate devices do not receive frequent updates
  cover: true      # Covers receive frequent updates
  select: false    # Select entities do not receive frequent updates
  scene: false     # Scenes do not receive frequent updates
```

### Device-Specific Overrides

```yaml
specific_device_dynamic_overrides:
  "123456": false  # Device with periph_id 123456 will not receive frequent updates
  "789012": true   # Device with periph_id 789012 will receive frequent updates
```

## Priority System

The panel uses a priority system to determine if a device should be dynamic:

1. **Specific Device Override** (highest priority) - Manual override in UI
2. **Explicit `is_dynamic` property** - Set in YAML configuration
3. **Entity Type Property** - Based on `dynamic_entity_properties`
4. **Fallback** - Default behavior (light, switch, binary_sensor, cover are dynamic)

## Best Practices

### Configuration Recommendations

1. **Start with defaults**: Use the default configuration as a starting point
2. **Monitor behavior**: Observe which devices actually need frequent updates
3. **Fine-tune gradually**: Adjust configurations based on actual usage patterns
4. **Document changes**: Keep track of manual overrides in your configuration

### Common Configuration Scenarios

**Scenario 1: Motion detectors in high-traffic areas**
- Set as dynamic for real-time responsiveness
- Include in security automations

**Scenario 2: Temperature sensors in stable environments**
- Set as static to reduce API calls
- Refresh every 5-10 minutes is sufficient

**Scenario 3: Smart lights with physical switches**
- Set as dynamic to detect manual changes
- Ensure state synchronization between physical and digital controls

**Scenario 4: Weather stations with slow-changing data**
- Set individual sensors as static
- Only refresh when meaningful changes occur

## Troubleshooting

### Card not appearing

- Ensure the JavaScript file is accessible at `/local/eedomus/lovelace/config_panel.js`
- Check browser console for errors
- Verify the card is registered in Lovelace resources

### Changes not saved

- Check file permissions for `custom_mapping.yaml`
- Verify the Eedomus integration has write access to the config directory
- Check Home Assistant logs for errors

### Debugging refresh mechanisms

To debug the opportunistic refresh behavior:

1. **Enable debug logging**:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.eedomus: debug
       custom_components.eedomus.coordinator: debug
   ```

2. **Monitor refresh cycles**:
   - Look for "Partial refresh" and "Full refresh" messages in logs
   - Check which devices are included in each refresh cycle
   - Verify refresh frequencies match your configuration

3. **Check device status**:
   - Use the "All Devices" tab to see current dynamic status
   - Verify the "reason" for each device's dynamic status
   - Look for devices that should be dynamic but aren't

4. **Test specific devices**:
   - Manually toggle a device override
   - Observe the refresh behavior in logs
   - Verify the device appears in partial refresh cycles

## Advanced Configuration

### Custom Refresh Intervals

You can customize refresh intervals in your configuration:

```yaml
# In your configuration.yaml
eedomus:
  scan_interval: 30  # Default refresh interval in seconds
  dynamic_refresh_interval: 15  # More frequent for dynamic devices
```

### Device-Specific Refresh Rates

For advanced use cases, you can implement device-specific refresh rates by creating custom rules in your configuration.

### Refresh Mechanisms

### Opportunistic Refresh Strategy

Dynamic devices benefit from an **opportunistic refresh mechanism** that optimizes API calls:

1. **Partial Refreshes**: Only dynamic devices are included in frequent partial refresh cycles
2. **Batched Requests**: Multiple dynamic devices are refreshed in single API calls
3. **State Change Detection**: Only devices that have actually changed trigger updates
4. **Adaptive Frequency**: Refresh frequency adapts based on device activity

### Performance Optimization

- **Dynamic devices**: Included in frequent refresh cycles (every 30-60 seconds)
- **Static devices**: Refreshed less frequently (every 5-10 minutes)
- **Manual overrides**: Allow fine-tuning for specific use cases

### API Impact

The opportunistic refresh mechanism minimizes API load by:
- Grouping similar device types in single requests
- Skipping unchanged devices
- Using efficient delta updates when possible
- Implementing exponential backoff for error conditions

## Performance considerations

- Dynamic devices are included in optimized refresh cycles
- Use static configuration for devices that change slowly (temperature sensors, humidity)
- Use dynamic configuration for devices that need real-time updates (lights, switches, motion detectors)
- Monitor API usage in Home Assistant logs to fine-tune your configuration

## Development

### Building

The card uses modern JavaScript (ES6+) and requires no build step.

### Testing

1. Enable debug logging in Home Assistant
2. Monitor the browser console for errors
3. Check Home Assistant logs for backend issues

## Frequently Asked Questions

### What exactly is a "dynamic device"?

A dynamic device is one whose state can change unpredictably due to user actions or environmental factors. Examples include:
- Light switches (can be toggled manually)
- Motion detectors (state changes based on movement)
- Door/window sensors (state changes when opened/closed)
- Smart plugs with physical buttons

### How does opportunistic refresh work?

Opportunistic refresh is an optimization strategy that:
1. Only includes dynamic devices in frequent refresh cycles
2. Groups multiple devices in single API requests
3. Skips devices that haven't changed since last refresh
4. Adapts refresh frequency based on device activity patterns

### Should I make all my devices dynamic?

No. Only devices that can change state unpredictably should be dynamic. Devices like temperature sensors, humidity sensors, or static displays should remain static to reduce unnecessary API calls and improve system performance.

### How do I know if my configuration is optimal?

Monitor these indicators:
- **API call frequency**: Should be reasonable for your number of dynamic devices
- **State update latency**: Dynamic devices should update quickly (within seconds)
- **System load**: CPU and memory usage should remain stable
- **User experience**: Interface should feel responsive without delays

### Can I have different refresh rates for different devices?

Yes, you can:
1. Use entity type properties for broad categories
2. Add specific device overrides for individual devices
3. Create custom rules in your configuration for advanced scenarios

### What happens if I remove a device override?

The device will revert to its default behavior based on:
1. Its entity type property (from `dynamic_entity_properties`)
2. The fallback logic if no entity type property is defined

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/Dan4Jer/hass-eedomus/issues).

## License

This project is licensed under the MIT License.