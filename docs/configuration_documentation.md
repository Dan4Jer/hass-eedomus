# Configuration Guide for Eedomus Integration

## Configuration Options

### Basic Configuration

#### api_host
**Description**: Local IP address of your Eedomus box (e.g., `xxx.XXX.xxx.XXX`)
**Purpose**: Allows Home Assistant to communicate directly with your Eedomus box
**Required**: Yes
**Example**: `192.168.1.100`

#### api_user
**Description**: API username from your Eedomus account
**Purpose**: Authenticates requests to the Eedomus API
**Required**: Only if API Eedomus mode is enabled
**Location**: Eedomus web interface > "My Account" > "API Credentials"

#### api_secret
**Description**: API password from your Eedomus account
**Purpose**: Authenticates requests to the Eedomus API
**Required**: Only if API Eedomus mode is enabled
**Location**: Eedomus web interface > "My Account" > "API Credentials"
**Security**: This field is masked and secure

### Connection Modes

#### enable_api_eedomus (default: True)
**Description**: Enable direct API polling from Eedomus box
**Purpose**: Pull device states and send commands
**Recommended**: Yes (for full functionality)
**Without this**: Integration has limited functionality

#### enable_api_proxy (default: False)
**Description**: Enable webhook-based communication
**Purpose**: Allow Eedomus to push updates to Home Assistant
**Use cases**:
- Trigger Home Assistant automations from Eedomus scenarios
- Control HA entities directly from Eedomus
- Real-time updates without polling

### Data Retrieval

#### scan_interval (default: 300 seconds)
**Description**: Time between API polls (in seconds)
**Purpose**: Control how often Home Assistant checks device states
**Recommendations**:
- **300s (5min)**: Good balance for most users
- **60s (1min)**: For real-time monitoring (higher load)
- **900s (15min)**: For low-power mode (less responsive)

#### enable_history (default: False)
**Description**: Enable historical data retrieval
**Status**: Fully implemented ✅
**Features**:
- Track progress of history retrieval
- View download statistics
- Access historical sensor data
**Requirements**:
- API Eedomus mode must be enabled
- Recorder component recommended (but not required)

### Advanced Options

#### enable_set_value_retry (default: True)
**Description**: Automatically retry failed value sets
**Purpose**: Handle cases where values are initially refused
**Use cases**:
- Fix invalid values automatically
- Improve reliability for unstable devices

#### max_retries (default: 3)
**Description**: Maximum retry attempts for failed commands
**Purpose**: Control retry behavior
**Use cases**:
- Increase for unstable networks
- Decrease for faster failure detection

### Webhook & Security

#### enable_webhook (default: True)
**Description**: Enable webhook endpoints
**Purpose**: Allow Eedomus to trigger Home Assistant actions
**Features**:
- Refresh device states
- Internal actions (future)
- Custom integrations

#### api_proxy_disable_security (default: False)
**⚠️ Security Warning**: Disable IP validation for API Proxy
**Purpose**: Allow non-standard IP access (debugging only)
**Security Risk**: Exposes webhook endpoints to potential abuse
**Recommendation**: Keep disabled in production environments

### PHP Fallback

#### php_fallback_enabled (default: False)
**Description**: Use PHP script to bypass API limitations
**Purpose**: Set values not in default options
**Requirements**: PHP script must be configured
**Use cases**:
- Advanced device control
- Custom value ranges
- Workaround API restrictions

#### php_fallback_script_name (default: "fallback.php")
**Description**: Name of the PHP fallback script
**Purpose**: Specify custom script location
**Example**: "custom_fallback.php"

#### php_fallback_timeout (default: 5 seconds)
**Description**: Timeout for PHP fallback requests
**Purpose**: Control response time
**Recommendations**:
- Increase for slow servers (10-30s)
- Decrease for faster response (2-5s)

### Uninstall Options

#### remove_entities_on_uninstall (default: False)
**Description**: Remove all entities when uninstalling
**Purpose**: Clean up completely
**Use cases**:
- Complete removal before reinstallation
- Testing new configurations
- Troubleshooting

## Connection Modes Explained

### API Eedomus Mode (Pull)
```
Home Assistant → (Pull) → Eedomus Box
```
**Pros**:
- Full device access
- History retrieval
- Reliable polling

**Cons**:
- Requires credentials
- Network dependency

### API Proxy Mode (Push)
```
Eedomus Box → (Push via Webhook) → Home Assistant
```
**Pros**:
- Real-time updates
- No polling needed
- Lightweight

**Cons**:
- No history access
- Requires webhook configuration

## Best Practices

### For Best Performance
1. Use both modes (API Eedomus + API Proxy) for redundancy
2. Set scan_interval to 300s (5 minutes) for balance
3. Keep enable_set_value_retry enabled for reliability
4. Disable api_proxy_disable_security unless debugging

### For Troubleshooting
1. Check logs: `journalctl -u home-assistant@homeassistant -f`
2. Verify connectivity: `ping 192.168.1.100`
3. Test API credentials in Eedomus web interface
4. Disable options one by one to isolate issues

### For Security
1. Never expose Eedomus box to internet
2. Keep api_proxy_disable_security disabled
3. Use strong API credentials
4. Regularly update Home Assistant

## Troubleshooting

### Common Issues

**Issue**: Connection failed
- Check API host address
- Verify API credentials
- Ensure Eedomus box is online

**Issue**: Devices not updating
- Increase scan_interval
- Check network connectivity
- Verify device permissions in Eedomus

**Issue**: Commands not working
- Enable enable_set_value_retry
- Check device compatibility
- Verify value ranges

### Log Messages

**"Missing or empty value"**: Normal for some devices, can be ignored
**"API request failed"**: Check network and credentials
**"Cannot connect to eedomus API"**: Verify host and credentials
**"History retrieval failed"**: Check API Eedomus mode is enabled

## Support

For issues or questions:
1. Check this documentation first
2. Review logs for error messages
3. Create an issue on GitHub with:
   - Home Assistant version
   - Eedomus integration version
   - Relevant log snippets
   - Steps to reproduce

## Version History

### Current Version: 0.13.10-unstable
- ✅ History feature fully implemented
- ✅ Proper sensor entities with device attachment
- ✅ Improved UI organization
- ✅ Better error handling

### Previous Versions
- 0.13.9: Fixed RGBW mapping issues
- 0.13.8: Added dynamic peripheral support
- 0.13.7: Improved error recovery

## Technical Details

### Device Mapping
- RGBW lamps: Auto-detected by having 4+ children
- Brightness channels: Mapped as light:brightness
- Sensors: Mapped by usage_id
- Binary sensors: Motion and smoke detection

### API Endpoints
- `/periph/list`: Get all peripherals
- `/periph/value/list`: Get values
- `/periph/caract`: Get characteristics
- `/periph/set/value`: Set values

### Data Flow
1. Initial load: Full device list and values
2. Regular polling: Only characteristics (scan_interval)
3. Webhooks: Real-time updates (if enabled)
4. History: Background retrieval (if enabled)

---

**Last updated**: 2026-02-14
**Integration**: Eedomus
**Author**: Dan4Jer
**License**: MIT