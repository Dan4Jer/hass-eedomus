# 🧹 Cleanup Feature Documentation

## Overview

The cleanup feature provides a way to remove unused eedomus entities from your Home Assistant installation. This helps maintain a clean entity registry and improves performance by removing entities that are no longer needed.

## What Entities Are Removed?

The cleanup process identifies and removes eedomus entities that match either of these criteria:

1. **Disabled entities**: Entities that have been manually disabled in Home Assistant
2. **Deprecated entities**: Entities whose `unique_id` contains the word "deprecated" (case-insensitive)

## How to Use the Cleanup Feature

### Method 1: Through the Options Flow (Recommended)

1. **Navigate to the eedomus integration options**:
   - Go to **Settings** > **Devices & Services**
   - Find the **eedomus** integration and click on it
   - Click **Configure** (or the gear icon)

2. **Access the cleanup menu**:
   - In the options menu, you'll see a **Cleanup** option in the menu bar
   - Click on **Cleanup** to start the process

3. **Review the results**:
   - The system will analyze all entities and identify candidates for removal
   - You'll see a summary showing how many entities were analyzed, considered, and removed
   - Detailed logs will be available in the Home Assistant logs

### Method 2: Manual Cleanup (Advanced)

For advanced users who prefer command-line access, you can create a script that calls the cleanup functionality directly. See the [Script Creation](#script-creation) section below.

## What to Expect During Cleanup

### Logging

The cleanup process generates detailed logs that help you track what's happening:

- **Info logs**: Show the start of cleanup, analysis results, and completion
- **Entity-specific logs**: Show each entity being removed with its reason (disabled/deprecated)
- **Error logs**: Show any issues encountered during removal (entities continue processing)

Example log output:
```
INFO: Starting cleanup of unused eedomus entities
INFO: Cleanup analysis complete: 150 entities analyzed, 42 eedomus entities considered, 8 entities to be removed
INFO: Removing entity eedomus.old_light_123 (reason: deprecated, unique_id: deprecated_light_123)
INFO: Removing entity eedomus.disabled_sensor_456 (reason: disabled, unique_id: sensor_456)
INFO: Cleanup completed: 8 entities removed out of 8 identified
```

### Safety Features

- **Non-destructive by default**: Only eedomus entities are considered
- **Error handling**: If an entity fails to remove, the process continues with others
- **Dry-run capability**: The analysis phase shows what would be removed before any action is taken
- **No system entities affected**: Only your eedomus integration entities are touched

## When to Use Cleanup

### Recommended Scenarios

1. **After major integration updates**: When you've updated the eedomus integration and old entities are no longer needed
2. **During troubleshooting**: If you're experiencing performance issues or entity conflicts
3. **Regular maintenance**: As part of your periodic Home Assistant maintenance routine
4. **Before backups**: To reduce backup size and complexity

### When NOT to Use Cleanup

- **During active automation runs**: Wait until automations are complete
- **Before important events**: Don't clean up right before you need your system to be stable
- **If you're unsure**: Review the entity list first or make a backup

## Technical Details

### Entity Selection Criteria

```python
# An entity is selected for removal if:
is_eedomus_entity = entity_entry.platform == "eedomus"
is_disabled = entity_entry.disabled
has_deprecated = entity_entry.unique_id and "deprecated" in entity_entry.unique_id.lower()

should_remove = is_eedomus_entity and (is_disabled or has_deprecated)
```

### Process Flow

1. **Get entity registry**: Access all entities in Home Assistant
2. **Analyze entities**: Identify eedomus entities that meet removal criteria
3. **Log analysis**: Show what will be removed
4. **Remove entities**: Safely remove identified entities
5. **Log results**: Show final summary
6. **Handle errors**: Continue if individual removals fail

## Script Creation (Advanced)

For users who want to create a standalone cleanup script:

```python
#!/usr/bin/env python3
"""Standalone cleanup script for eedomus entities."""

import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

async def cleanup_eedomus_entities(hass: HomeAssistant):
    """Clean up unused eedomus entities."""
    
    # Get entity registry
    entity_registry = await er.async_get_registry(hass)
    
    # Find entities to remove
    entities_to_remove = []
    for entity_entry in entity_registry.entities.values():
        if entity_entry.platform == "eedomus":
            is_disabled = entity_entry.disabled
            has_deprecated = entity_entry.unique_id and "deprecated" in entity_entry.unique_id.lower()
            
            if is_disabled or has_deprecated:
                entities_to_remove.append(entity_entry.entity_id)
    
    # Remove entities
    removed_count = 0
    for entity_id in entities_to_remove:
        try:
            entity_registry.async_remove(entity_id)
            removed_count += 1
            print(f"Removed: {entity_id}")
        except Exception as e:
            print(f"Failed to remove {entity_id}: {e}")
    
    print(f"Cleanup complete: {removed_count}/{len(entities_to_remove)} entities removed")
    return removed_count

# Usage example:
# hass = get_your_home_assistant_instance()
# await cleanup_eedomus_entities(hass)
```

## Troubleshooting

### Common Issues

**Issue**: No entities were removed when I expected some to be removed
- **Solution**: Check that entities are actually disabled or have "deprecated" in their unique_id
- **Solution**: Verify the entities are from the eedomus platform

**Issue**: Cleanup process hangs or takes too long
- **Solution**: Check Home Assistant logs for errors
- **Solution**: Try restarting Home Assistant and running cleanup again

**Issue**: Important entities were removed accidentally
- **Solution**: Restore from backup
- **Solution**: Re-add the entities through the eedomus integration
- **Prevention**: Review entity unique_ids before running cleanup

### Verifying Cleanup Results

1. **Check logs**: Review Home Assistant logs for cleanup entries
2. **Entity count**: Compare entity counts before and after cleanup
3. **Manual verification**: Check specific entities you expected to be removed
4. **Integration health**: Verify your eedomus integration is still working properly

## Best Practices

1. **Backup first**: Always backup your Home Assistant configuration before major cleanup operations
2. **Review entity list**: Check which entities will be removed before running cleanup
3. **Monitor logs**: Watch the logs during cleanup to catch any issues early
4. **Test after cleanup**: Verify your automations and integrations still work
5. **Document changes**: Keep notes of what was cleaned up and when
6. **Regular maintenance**: Schedule cleanup as part of your regular maintenance routine

## Performance Impact

- **Before cleanup**: More entities = slower entity registry operations
- **After cleanup**: Fewer entities = faster operations and reduced memory usage
- **During cleanup**: Minimal impact, process is designed to be non-blocking

## Future Enhancements

Potential improvements for future versions:
- **Preview mode**: Show what would be removed without actually removing
- **Selective cleanup**: Choose which specific entities to remove
- **Scheduled cleanup**: Automatic cleanup on a schedule
- **Entity age filtering**: Remove entities not used for X days
- **Size-based cleanup**: Remove largest unused entities first

## Support

If you encounter issues with the cleanup feature:

1. Check the [troubleshooting section](#troubleshooting)
2. Review Home Assistant logs for error messages
3. Consult the eedomus integration documentation
4. Create an issue on the project GitHub with detailed information

## Changelog

- **v1.0**: Initial implementation with disabled/deprecated entity detection
- **v1.1**: Added comprehensive logging and error handling
- **v1.2**: Integrated with options flow menu system

## License

This feature is part of the eedomus Home Assistant integration and is licensed under the same terms as the main project.
