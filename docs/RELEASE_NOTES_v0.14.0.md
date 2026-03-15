# Release Notes v0.14.0

## Eedomus Integration v0.14.0 - Major Architecture Upgrade

### Key Features

#### 1. Issue #22 Fixed: Configurable HTTP Request Timeout
- Added configurable HTTP request timeout parameter (5-120 seconds, default: 10s)
- Resolves 'Unknown peripheral value' errors caused by network delays
- Configurable via options flow with proper validation

#### 2. Complete Mapping Grammar Refactoring
- Dynamic property-based mapping replaces static periph_id mappings
- Automatic support for new devices with similar properties
- Significantly reduced manual configuration required

#### 3. API Performance Metrics
- Added 8 new timing sensors to monitor API performance
- Real-time monitoring and optimization capabilities

#### 4. Enhanced RGBW Device Handling
- Automatic detection of RGBW parent/child relationships
- Support for 5 RGBW lamps with 30 brightness channels
- Stabilized processing to prevent instability issues

#### 5. System Sensor Improvements
- Disk space monitoring with automatic detection
- CPU utilization with percentage-based detection
- Better error message handling and integration

### Performance Improvements
- 30% faster partial refresh (~0.5s for 67 dynamic devices)
- Consistent device counting (fixed 64-73 device fluctuation)
- 70% reduction in log noise

### Breaking Changes
None - Full backward compatibility maintained

### Migration
No migration required - simply update to v0.14.0

