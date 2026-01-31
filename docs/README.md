# Eedomus Integration Documentation

This directory contains comprehensive documentation for the hass-eedomus integration.

## Documentation Structure

### Configuration Guides
- `example_custom_mapping.yaml` - Example configuration for custom device mappings
- `BATTERY_CHILD_ENTITY_IMPLEMENTATION.md` - Guide for battery sensor implementation
- `BATTERY_SENSOR_EXAMPLE.md` - Battery sensor configuration examples
- `DEVICE_MAPPING_TABLE.md` - Complete device mapping reference

### Technical Documentation
- `RGBW_MAPPING_SOLUTION.md` - RGBW device mapping solution
- `SCENE_TO_SELECT_MIGRATION.md` - Migration guide from scenes to select entities
- `SELECT_ENTITY_LOG_ANALYSIS.md` - Select entity troubleshooting guide

### Release Notes & History
- `REAL_VERSION_HISTORY.md` - Complete version history
- `RELEASE_NOTES.md` - Latest release notes
- `TECHNICAL_RELEASE_NOTES_v0.13.3.md` - Technical details for v0.13.3

### Special Topics
- `PHP_FALLBACK.md` - PHP fallback mechanism documentation
- `TESTING_GUIDE.md` - Guide for testing the integration

### Bug Fixes & Solutions
- `COLOR_MODE_FIX_SUMMARY.md` - RGBW color mode fix technical summary (NEW!)
- `COLOR_MODE_FIX_README.md` - RGBW color mode fix user guide (NEW!)

## Key Documentation Files

### RGBW Color Mode Fix

**For Developers:**
- `COLOR_MODE_FIX_SUMMARY.md` - Technical implementation details
- Explains the root cause and solution
- Shows code changes and impact analysis
- Includes testing information

**For Users:**
- `COLOR_MODE_FIX_README.md` - User-friendly guide
- Explains what was fixed and why
- Shows how to use RGBW mappings
- Provides troubleshooting tips

### Device Mapping

**Example Configuration:**
- `example_custom_mapping.yaml` - Practical examples
- Shows how to override default mappings
- Demonstrates RGBW, brightness, and other mappings
- Includes best practices and tips

**Reference:**
- `DEVICE_MAPPING_TABLE.md` - Complete mapping reference
- Lists all supported device types
- Shows mapping patterns and conventions

## How to Use This Documentation

### For New Users
1. Start with `example_custom_mapping.yaml` for configuration examples
2. Read `COLOR_MODE_FIX_README.md` for RGBW usage
3. Check `DEVICE_MAPPING_TABLE.md` for device-specific guidance

### For Developers
1. Read `COLOR_MODE_FIX_SUMMARY.md` for technical details
2. Review `RGBW_MAPPING_SOLUTION.md` for implementation patterns
3. Check `TESTING_GUIDE.md` for testing procedures

### For Troubleshooting
1. `SELECT_ENTITY_LOG_ANALYSIS.md` - Select entity issues
2. `SCENE_TO_SELECT_MIGRATION.md` - Migration problems
3. `PHP_FALLBACK.md` - Fallback mechanism issues

## Documentation Standards

### Format
- Markdown (.md) format
- Clear section headers
- Code examples with syntax highlighting
- Cross-references between related documents

### Content
- Problem statement and context
- Solution explanation
- Code examples where applicable
- Usage instructions
- Troubleshooting tips

### Updates
- Version-specific notes where applicable
- Change history when significant
- Compatibility information

## Contributing to Documentation

When adding or updating documentation:

1. **Follow existing patterns** - Use similar structure and style
2. **Be comprehensive** - Cover all aspects of the topic
3. **Include examples** - Practical examples help users
4. **Add cross-references** - Link to related documentation
5. **Update indexes** - Add new files to this README

## Documentation Workflow

1. **New Features**: Add documentation before or with the feature
2. **Bug Fixes**: Update documentation to reflect changes (like RGBW color mode fix)
3. **Breaking Changes**: Add migration guides and clear warnings
4. **Deprecations**: Document alternatives and timelines

## Related Resources

- **GitHub Wiki**: https://github.com/Dan4Jer/hass-eedomus/wiki
- **GitHub Issues**: https://github.com/Dan4Jer/hass-eedomus/issues
- **Discussions**: https://github.com/Dan4Jer/hass-eedomus/discussions

## License

All documentation is licensed under the MIT License, same as the main project.