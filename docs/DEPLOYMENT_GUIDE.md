# Deployment Guide for History Feature

## Overview

This guide provides instructions for deploying and testing the history feature implementation on your Raspberry Pi running Home Assistant.

## Prerequisites

### 1. Home Assistant Configuration

Ensure your `configuration.yaml` includes the recorder component:

```yaml
# configuration.yaml
recorder:
  db_url: !secret recorder_db_url
  purge_keep_days: 30
  # Optional: Include only eedomus entities
  include:
    domain: sensor
    entity_id: "sensor.eedomus_*"
```

### 2. Required Secrets

Create or update your `secrets.yaml`:

```yaml
# secrets.yaml
recorder_db_url: sqlite:////config/home-assistant_v2.db
api_user: your_eedomus_api_user
api_secret: your_eedomus_api_secret
```

### 3. Eedomus API Credentials

Ensure you have:
- Eedomus API user (found in your eedomus account settings)
- Eedomus API secret (generated in your eedomus account settings)

## Deployment Instructions

### Method 1: Using Deployment Script (Recommended)

```bash
# From your development machine
cd /Users/danjer/mistral
git checkout unstable
./deploy_on_rasp.sh
```

This script will:
1. Connect to your Raspberry Pi via SSH
2. Pull the latest code from the unstable branch
3. Restart Home Assistant

### Method 2: Manual Deployment

```bash
# SSH into your Raspberry Pi
ssh 192.168.1.4

# Navigate to the integration directory
cd /homeassistant/custom_components/hass-eedomus

# Pull the latest code
git checkout unstable
git pull origin unstable

# Restart Home Assistant
ha core restart
```

### Method 3: Using HACS (If Installed via HACS)

1. Go to **HACS** > **Integrations**
2. Find **Eedomus**
3. Click on the three dots (⋮) and select **Update**
4. Restart Home Assistant

## Post-Deployment Verification

### Step 1: Check Home Assistant Logs

```bash
# SSH into your Raspberry Pi
ssh 192.168.1.4

# Check Home Assistant logs
tail -n 100 ~/mistral/rasp.log

# Or use the Home Assistant UI:
# Settings > System > Logs
```

Look for these messages:
```
✅ Eedomus services registered successfully
✅ History progress sensors created for all devices
✅ Recorder component available
```

### Step 2: Verify Services

```bash
# Check that eedomus services are available
ha service list | grep eedomus

# Expected output:
eedomus.refresh
eedomus.set_value
eedomus.reload
```

### Step 3: Check History Progress Sensors

```bash
# List all eedomus entities
ha states | grep "eedomus"

# Look for history progress sensors
ha states | grep "eedomus.history_progress"

# Expected output:
eedomus.history_progress_123456 0 %
eedomus.history_progress_789012 0 %
```

### Step 4: Enable History Feature

1. **In Home Assistant UI**:
   - Go to **Settings** > **Devices & Services**
   - Select **Eedomus** integration
   - Click on the three dots (⋮) and select **Options**
   - Enable **Enable History** checkbox
   - Save the configuration

2. **Via Service Call** (alternative):
   ```bash
   ha service call eedomus.reload
   ```

## Testing the History Feature

### Test 1: History Progress Sensor Creation

1. Check that history progress sensors exist
2. Verify they show 0% initially
3. Check attributes include:
   - `completed`: false
   - `periph_name`: device name
   - `data_points_retrieved`: 0
   - `estimated_total`: estimated count
   - `last_timestamp`: 0

### Test 2: History Retrieval

1. Wait for the next scheduled refresh (or trigger manually)
2. Check logs for history retrieval messages:
   ```
   Fetching history for {periph_id} (from {timestamp})
   History fully fetched for {periph_id} ({name}) (received {count} entries)
   ```
3. Monitor history progress sensors
4. Verify progress increases over time
5. Check that sensors eventually show 100% and completed: true

### Test 3: CPU Sensor Data

1. Find the CPU sensor entity:
   ```bash
   ha states | grep "sensor.eedomus_*cpu"
   ```
2. Check the sensor attributes
3. Create a graph in your dashboard
4. Add the CPU sensor entity to the graph
5. Verify historical data is displayed
6. Check that the graph shows trends over time

### Test 4: Recorder Component Availability

1. Check that recorder component is loaded:
   ```bash
   ha core info | grep recorder
   ```
2. Verify history progress sensors are created
3. Check that history data is being stored in the database

## Troubleshooting

### Issue 1: Recorder Component Not Available

**Symptoms**:
- Warning: "Recorder component not available. Cannot load history progress."
- No history progress sensors created

**Solutions**:
1. Ensure recorder is enabled in configuration.yaml
2. Restart Home Assistant
3. Check that recorder component is loaded
4. Verify database connection

**Commands**:
```bash
# Check recorder status
ha core info | grep recorder

# Check configuration
grep -A 5 "recorder:" /config/configuration.yaml
```

### Issue 2: History Progress Sensors Not Created

**Symptoms**:
- History feature enabled but no sensors appear
- No progress tracking

**Solutions**:
1. Check that CONF_ENABLE_HISTORY is True
2. Verify recorder component is available
3. Check logs for sensor creation messages
4. Manually trigger sensor creation:
   ```bash
   ha service call eedomus.reload
   ```

**Commands**:
```bash
# Check history option
ha config options eedomus

# Check for sensor creation logs
grep "history progress sensor" ~/mistral/rasp.log
```

### Issue 3: History Retrieval Fails

**Symptoms**:
- Error: "Failed to fetch history: {error}"
- History progress doesn't increase

**Solutions**:
1. Check API Eedomus credentials
2. Verify API Eedomus mode is enabled
3. Check eedomus API status
4. Review API response for details

**Commands**:
```bash
# Check API credentials
ha config entry eedomus

# Check API mode
ha config options eedomus | grep enable_api_eedomus
```

### Issue 4: CPU Sensor Not Showing Data

**Symptoms**:
- CPU sensor exists but shows no data
- No historical data in graphs

**Solutions**:
1. Verify CPU Box device is mapped correctly (usage_id=23)
2. Check that device is reporting data to eedomus
3. Verify history retrieval is working
4. Check sensor entity attributes

**Commands**:
```bash
# Check CPU sensor
ha states | grep "sensor.eedomus_*cpu"

# Check device mapping
ha config options eedomus | grep -A 10 "usage_id_mappings"
```

## Monitoring and Debugging

### Enable Debug Logging

Add to your `configuration.yaml`:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.eedomus: debug
    custom_components.eedomus.coordinator: debug
    custom_components.eedomus.eedomus_client: debug
```

### Check Specific Logs

```bash
# Check eedomus logs
grep "eedomus" ~/mistral/rasp.log | tail -50

# Check history-related logs
grep "history" ~/mistral/rasp.log | tail -50

# Check recorder-related logs
grep "recorder" ~/mistral/rasp.log | tail -50
```

### Check Database

```bash
# Check database size
ls -lh /config/home-assistant_v2.db

# Check recent database activity
tail -n 100 ~/mistral/rasp.log | grep "recorder"
```

## Expected Behavior

### Normal Operation (Recorder Enabled)

1. **On Startup**:
   - Integration loads
   - History progress sensors are created
   - Sensors show 0% progress

2. **During Refresh**:
   - History is retrieved in chunks
   - Progress sensors update
   - Data is imported into recorder

3. **When Complete**:
   - Sensors show 100% progress
   - Completed flag is set to true
   - Historical data is available in graphs

### Normal Operation (Recorder Disabled)

1. **On Startup**:
   - Warning message appears
   - History progress sensors are not created
   - Normal device operation continues

2. **During Refresh**:
   - History retrieval is skipped
   - No progress tracking
   - Normal device updates continue

## Performance Considerations

### Database Impact

- History data increases database size
- Consider setting `purge_keep_days` appropriately
- Monitor database performance
- Consider using MariaDB for large installations

### API Impact

- History retrieval uses eedomus API
- Large history datasets may take time to retrieve
- Consider limiting history retrieval to essential sensors
- Monitor API rate limits

### Memory Usage

- History chunks are processed in memory
- Large chunks may increase memory usage temporarily
- Monitor memory usage during history retrieval
- Consider increasing swap space if needed

## Best Practices

### For Production Use

1. **Start with limited history**: Enable history for a few devices first
2. **Monitor performance**: Check database and API usage
3. **Set appropriate retention**: Configure `purge_keep_days` based on needs
4. **Use efficient queries**: Create graphs with appropriate time ranges
5. **Backup regularly**: Ensure database is backed up

### For Testing

1. **Enable debug logging**: Get detailed information
2. **Test with one device**: Start with CPU sensor
3. **Monitor logs closely**: Watch for errors and warnings
4. **Check progress regularly**: Verify sensors are updating
5. **Test visualization**: Create graphs and check data

## Rollback Instructions

If issues arise, you can rollback:

```bash
# SSH into Raspberry Pi
ssh 192.168.1.4

# Rollback to previous version
cd /homeassistant/custom_components/hass-eedomus
git checkout main
git pull origin main

# Restart Home Assistant
ha core restart
```

## Support

### Getting Help

1. **Check logs**: Review Home Assistant logs for errors
2. **Review documentation**: Check this guide and HISTORY_IMPLEMENTATION_SUMMARY.md
3. **Search issues**: Check GitHub issues for similar problems
4. **Create issue**: Open a new GitHub issue with logs and details

### Reporting Issues

When reporting issues, please include:
- Home Assistant version
- Integration version
- Relevant logs
- Steps to reproduce
- Expected vs actual behavior

## Conclusion

The history feature provides valuable insights into your device data over time. With proper configuration and monitoring, it can enhance your Home Assistant setup significantly.

Start with a small deployment, monitor performance, and expand as needed. The feature is designed to be robust and handle errors gracefully, ensuring your integration continues to work even if history retrieval encounters issues.
