# Eedomus Integration Tests

## 🧪 Test Structure

This directory contains comprehensive tests for all Eedomus entities:

### Test Files

- **`test_cover.py`**: Tests for cover entities (shutters, blinds)
- **`test_switch.py`**: Tests for switch entities (including consumption monitoring)
- **`test_light.py`**: Tests for light entities (RGBW, brightness, with consumption)
- **`test_sensor.py`**: Tests for sensor entities (temperature, humidity, energy, battery)
- **`test_energy_sensor.py`**: Specific tests for energy sensors (Issue #9)
- **`test_fallback.py`**: Tests for PHP fallback mechanism
- **`test_all_entities.py`**: Main test runner

### Test Coverage

#### Cover Entities
- ✅ Initialization and state management
- ✅ Open/close operations
- ✅ Position and tilt control
- ✅ Energy consumption monitoring (Issue #9)

#### Switch Entities
- ✅ Basic on/off functionality
- ✅ State management
- ✅ Consumption monitoring detection
- ✅ Automatic remapping to energy sensors

#### Light Entities
- ✅ RGBW color control
- ✅ Brightness control
- ✅ On/off operations
- ✅ Energy consumption monitoring
- ✅ Color parsing and validation

#### Sensor Entities
- ✅ Temperature sensors
- ✅ Humidity sensors
- ✅ Power sensors
- ✅ Energy sensors (Issue #9)
- ✅ Battery sensors
- ✅ Missing data handling
- ✅ Unit conversion

#### Energy Sensors (Issue #9)
- ✅ Consumption tracking
- ✅ Unit management (kWh, Wh)
- ✅ State attributes
- ✅ Parent-child aggregation

### Running Tests

#### Individual Test Files
```bash
# Run cover tests
pytest test_cover.py -v

# Run switch tests
pytest test_switch.py -v

# Run light tests
pytest test_light.py -v

# Run sensor tests
pytest test_sensor.py -v

# Run energy sensor tests
pytest test_energy_sensor.py -v
```

#### All Tests
```bash
# Run all tests
python test_all_entities.py

# Or directly with pytest
pytest test_*.py -v --tb=short
```

### Test Configuration

The `test_config.yaml` file contains example configurations for different test scenarios:

- Basic configuration
- Configuration with PHP fallback
- Energy monitoring configuration
- Example device structures

### Test Data Structure

Tests use mock data that simulates the eedomus API response structure:

```python
mock_coordinator = AsyncMock()
mock_coordinator.data = {
    "device_id": {
        "name": "Device Name",
        "value": "current_value",
        "unit": "unit_if_applicable",
        "usage_id": "device_usage_id",
        "position": 0-100,  # for covers
        "brightness": 0-255,  # for lights
        "color": "R,G,B,W",  # for RGBW lights
        "consumption": 0.0,  # for energy sensors
        "current_power": 0.0,  # for power sensors
        "children": [...]  # child devices
    }
}
```

### Test Best Practices

1. **Mocking**: All external dependencies are mocked
2. **Isolation**: Each test focuses on a specific functionality
3. **Coverage**: All major code paths are tested
4. **Documentation**: Each test has a clear docstring
5. **Consistency**: Similar test patterns across all entities

### Continuous Integration

For HACS compliance, consider adding GitHub Actions workflow:

```yaml
# .github/workflows/tests.yml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-asyncio
    - name: Run tests
      run: |
        cd custom_components/eedomus
        python test_all_entities.py
```

### Test Maintenance

- **Add new tests** when adding new features
- **Update tests** when fixing bugs
- **Run tests** before each commit
- **Review test coverage** regularly

## 🎯 Issue #9 Specific Tests

The energy sensor tests specifically address Issue #9:

- **Consumption tracking**: Verify energy values are correctly tracked
- **Unit management**: Ensure proper kWh/Wh unit handling
- **Parent-child relationships**: Test consumption aggregation
- **Automatic detection**: Verify devices with usage_id=26 are properly mapped

These tests ensure the energy monitoring functionality works correctly across all device types (lights, switches, covers).