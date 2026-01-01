# Select Entity Log Analysis Guide

## Expected Log Patterns for Successful Setup

### 1. Integration Startup
```
🚀 Starting eedomus integration setup - Version 0.9.4
Starting eedomus integration - API Eedomus: True, API Proxy: False/True
```

### 2. Select Entity Discovery
```
DEBUG: Creating select entity for [DEVICE_NAME] ([PERIPH_ID])
DEBUG: Initializing select entity for [DEVICE_NAME] ([PERIPH_ID])
```

### 3. Successful Option Selection
```
INFO: Selecting option '[OPTION_VALUE]' for [DEVICE_NAME] ([PERIPH_ID])
DEBUG: Successfully selected option '[OPTION_VALUE]' for [DEVICE_NAME]
```

### 4. State Updates
```
DEBUG: Updated select entity [DEVICE_NAME] ([PERIPH_ID]) - current option: [CURRENT_VALUE]
```

### 5. Error Patterns to Watch For

#### Missing value_list
```
WARNING: Device [DEVICE_NAME] ([PERIPH_ID]) mapped to select but has no value_list, skipping
```

#### API Communication Errors
```
ERROR: Failed to select option '[OPTION_VALUE]' for [DEVICE_NAME]: [ERROR_MESSAGE]
ERROR: Exception while selecting option '[OPTION_VALUE]' for [DEVICE_NAME]: [EXCEPTION_DETAILS]
```

#### Entity Availability Issues
```
WARNING: Update failed for [DEVICE_NAME] ([PERIPH_ID]) : [ERROR_DETAILS]
```

## Troubleshooting Guide

### 1. No Select Entities Created
**Symptoms**: No select entities appear in Home Assistant

**Check**:
- Verify devices have correct `usage_id` (14, 42, 43) or `PRODUCT_TYPE_ID` (999)
- Check devices have non-empty `value_list` attribute
- Look for "Creating select entity" debug logs

**Solution**:
```bash
# Check device mapping
grep -r "usage_id.*14\|usage_id.*42\|usage_id.*43\|PRODUCT_TYPE_ID.*999" /config/.storage/core.device_registry

# Check value_list
grep -r "value_list" /config/.storage/core.device_registry
```

### 2. Select Entities Unavailable
**Symptoms**: Select entities show as unavailable

**Check**:
- Look for "Update failed" warnings
- Verify eedomus API connectivity
- Check `last_value` is not empty

**Solution**:
```bash
# Test API connectivity
curl -X POST https://[EEDOMUS_HOST]/api.php \
  -d 'action=periph.value.list&periph_id=all' \
  -u "[API_USER]:[API_SECRET]"

# Check coordinator data
grep -A 10 -B 5 "select" /config/home-assistant.log
```

### 3. Option Selection Fails
**Symptoms**: Selecting options doesn't work or shows errors

**Check**:
- Look for "Failed to select option" errors
- Verify API response format
- Check option values match eedomus expectations

**Solution**:
```bash
# Test manual API call
curl -X POST https://[EEDOMUS_HOST]/api.php \
  -d 'action=periph.value.set&periph_id=[PERIPH_ID]&value=[OPTION_VALUE]' \
  -u "[API_USER]:[API_SECRET]"

# Check option format
grep -A 5 -B 5 "value_list" /config/.storage/core.device_registry | grep -A 10 -B 10 "[PERIPH_ID]"
```

## Log Analysis Commands

### Get Select Entity Logs
```bash
# Filter select entity logs
grep -i "select entity\|EedomusSelect\|async_select_option" /config/home-assistant.log

# Filter by specific device
grep "PERIPH_ID" /config/home-assistant.log | grep -i select

# Real-time monitoring
tail -f /config/home-assistant.log | grep -i select
```

### Check Entity Registry
```bash
# List all select entities
jq '.data.entities[] | select(.platform == "eedomus" and .device_class == "select")' /config/.storage/core.entity_registry

# Get specific entity details
jq '.data.entities[] | select(.unique_id == "[PERIPH_ID]_select")' /config/.storage/core.entity_registry
```

## Success Criteria Checklist

- [ ] Select entities appear in Home Assistant UI
- [ ] Each select entity shows current option correctly
- [ ] Available options are displayed in dropdown
- [ ] Option selection updates both UI and device state
- [ ] No error logs related to select entity setup
- [ ] API calls succeed (check for "success": 1 responses)
- [ ] Entity availability is stable (no frequent unavailable states)

## Common Issues and Resolutions

### Issue: "ModuleNotFoundError: No module named 'homeassistant.components.select'"
**Cause**: Old Home Assistant version without select platform support
**Solution**: Update Home Assistant to version 2021.8.0 or later

### Issue: "Invalid state encountered: [VALUE]"
**Cause**: Option value format mismatch
**Solution**: Check `value_list` format and ensure options parsing handles both list and string formats

### Issue: "Entity not available"
**Cause**: Empty `last_value` or API communication failure
**Solution**: Verify device has valid state and API connectivity

### Issue: "No entities created"
**Cause**: Device mapping not updated or devices don't match criteria
**Solution**: Check device attributes and mapping logic

## Performance Monitoring

### Memory Usage
```bash
# Check memory usage before/after
free -h

# Monitor Home Assistant memory
top -p $(pgrep -f "python.*homeassistant")
```

### Startup Time
```bash
# Measure integration startup time
grep -E "Starting eedomus|eedomus integration setup completed" /config/home-assistant.log | 
  awk '{print $1, $2, $3, $NF}' | 
  tail -2
```

## Debugging Tips

1. **Enable Debug Logging**:
```yaml
# Add to configuration.yaml
logger:
  default: info
  logs:
    custom_components.eedomus: debug
    custom_components.eedomus.select: debug
```

2. **Check Device Attributes**:
```bash
# Get device state with attributes
curl -X GET http://localhost:8123/api/states/select.[ENTITY_ID] \
  -H "Authorization: Bearer [API_TOKEN]" \
  -H "Content-Type: application/json"
```

3. **Test Entity Service**:
```bash
# Call select option service
curl -X POST http://localhost:8123/api/services/select/select_option \
  -H "Authorization: Bearer [API_TOKEN]" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "select.[ENTITY_ID]", "option": "[OPTION_VALUE]"}'
```