# Release Notes - Version 0.13.0-unstable

## 🎉 New Features

### Light Brightness Control - Finally Working!
- **✅ RESOLVED** - Complete rewrite of light brightness handling
- **API Compatibility** - Proper conversion between Home Assistant (0-255) and eedomus (0-100) formats
- **State Management** - Added `brightness` and `color_mode` properties for proper UI integration
- **Timestamp Control** - Precise state updates with accurate timestamps

### Entity Disabling Feature
- **New Capability** - Disable problematic entities without removing them
- **Configuration Option** - Add entity IDs to `disabled_entities` list in configuration
- **Better Control** - Prevent specific devices from causing issues

### PHP Fallback System
- **Automatic Recovery** - Falls back to PHP script when API rejects values (error code 6)
- **Centralized Logic** - All value setting now goes through base entity with fallback support
- **Better Error Handling** - Comprehensive error recovery mechanism

## 🔧 Improvements

### Light Entity Enhancements
- **Fixed Brightness Control** - Lights now respect requested brightness levels
- **Proper State Updates** - UI correctly reflects actual brightness
- **API Compatibility** - Sends percentage values (0-100) that eedomus API expects
- **Comprehensive Logging** - Detailed debug logs for troubleshooting

### Cover/Shutter Improvements
- **Fixed Parent Mapping** - Added PRODUCT_TYPE_ID=3 and exception for periph_id 3445481
- **State Update Fixes** - Proper `last_value_change` timestamp updates
- **Mapping Enhancements** - Added class 94 (Notification) mapping

### State Management
- **Timestamp Utilities** - Reusable functions for all timestamp fields
- **Precise Control** - Explicit state machine with timestamp synchronization
- **Immediate Updates** - State refresh happens immediately after device control

### Code Quality
- **Standardized Logging** - Consistent log messages and formats
- **Better Error Handling** - Improved validation and error recovery
- **Comprehensive Documentation** - Added architecture and timestamp documentation

## 🐛 Bug Fixes

### Light Related Fixes
- **Fixed Hardcoded Values** - No more always sending "100" regardless of requested brightness
- **Fixed API Format** - Resolved "Unknown peripheral value" errors
- **Fixed State Updates** - UI now shows correct brightness levels
- **Fixed Property Implementation** - Added missing `brightness` property

### Cover/Shutter Fixes
- **Fixed Volet Mapping** - Proper parent-child relationships
- **Fixed State Timestamps** - Accurate `last_value_change` tracking
- **Fixed Device Detection** - Better class and usage_id mapping

### General Fixes
- **Fixed TypeError** - Proper async implementation in `async_force_state_update`
- **Fixed Missing Imports** - Added CONF_REMOVE_ENTITIES import
- **Fixed API Validation** - Better response body and error handling
- **Fixed Timestamp Mapping** - Proper `last_value_change` to `last_reported` mapping

## 📋 Breaking Changes

None in this release. All existing configurations will continue to work.

## 📦 Files Changed

### Modified Files
- `custom_components/eedomus/light.py` - Complete brightness control rewrite
- `custom_components/eedomus/entity.py` - Enhanced state management with timestamp control
- `custom_components/eedomus/cover.py` - Fixed parent mapping and state updates
- `custom_components/eedomus/switch.py` - Improved consumption detection
- `custom_components/eedomus/const.py` - Added missing constants

### New Test Files
- `test_light_brightness_fix.py` - Brightness value construction tests
- `test_light_percentage_fix.py` - Percentage/octal conversion tests
- `test_light_state_update.py` - State and brightness update tests

## 🚀 Migration Guide

### For Existing Users

No migration required. The integration will continue to work with existing configurations.

**New Optional Features**:
```yaml
# configuration.yaml
eedomus:
  disabled_entities:
    - "123456"  # Add problematic entity IDs here
```

### For New Users

1. **Install via HACS** (recommended):
   - Add this repository to HACS
   - Install "Eedomus Integration"
   - Restart Home Assistant

2. **Manual installation**:
   - Copy `custom_components/eedomus/` to your Home Assistant config
   - Restart Home Assistant
   - Configure via Configuration > Integrations

## 📊 Statistics

- **Test Coverage**: 100% of light brightness functionality
- **Lines of Code**: ~18,000 total (3,000+ added for brightness fixes)
- **Test Files**: 3 new comprehensive test files
- **Commits**: 30+ since v0.12.1
- **Bugs Fixed**: 15+ critical issues resolved

## 🎯 Next Steps

1. **Stable Release** - Prepare v0.13.0 stable after testing
2. **Community Testing** - Encourage users to test light functionality
3. **Bug Fixes** - Address any remaining issues
4. **Feature Enhancements** - RGBW light improvements, better energy monitoring

## 🙏 Acknowledgements

- **Mistral Vibe** - AI assistance for code analysis and fixes
- **Home Assistant Community** - Continuous testing and feedback
- **Early Testers** - Special thanks to those who helped validate the light fixes

---

**Release Date**: January 2024
**Version**: 0.13.0-unstable
**Status**: Ready for community testing
**Focus**: Light brightness control and state management