# Eedomus Integration Tests

This directory contains the test suite for the hass-eedomus integration.

## Test Files

### Entity Tests
- `test_cover.py` - Tests for cover entities (shutters, blinds)
- `test_switch.py` - Tests for switch entities
- `test_light.py` - Tests for light entities
- `test_sensor.py` - Tests for sensor entities
- `test_energy_sensor.py` - Tests for energy monitoring sensors

### Integration Tests
- `test_integration.py` - Tests for overall integration functionality
- `test_fallback.py` - Tests for fallback mechanisms

### Specialized Tests
- `test_color_mode_fix.py` - Tests for RGBW color mode fix (NEW!)

## Running Tests

### Run All Tests
```bash
python test_all_entities.py
```

### Run Specific Test
```bash
python -m pytest test_light.py -v
```

### Run RGBW Color Mode Fix Test
```bash
python test_color_mode_fix.py
```

## Test Structure

Each test file follows this structure:

1. **Imports**: Required modules and dependencies
2. **Mock Setup**: Mock objects for testing
3. **Test Functions**: Individual test cases with `test_` prefix
4. **Assertions**: Verification of expected behavior

## Writing New Tests

When adding new tests:

1. **Follow existing patterns**: Use similar structure to existing tests
2. **Use mocks**: Mock external dependencies (API calls, etc.)
3. **Test edge cases**: Include normal and error scenarios
4. **Add to test_all_entities.py**: Include new test files in the main test runner

## RGBW Color Mode Fix Test

The `test_color_mode_fix.py` test verifies:

- RGBW fallback logic for devices without 4 children
- Proper `supported_color_modes` property implementation
- Correct `color_mode` property behavior
- RGBW color parameter handling
- Updated warning messages

This test ensures that devices mapped as RGBW but without the traditional 4-child structure still work correctly and don't generate warning messages.

## Test Coverage

The test suite covers:

- ✅ Entity initialization and configuration
- ✅ State changes and updates
- ✅ Color mode handling (RGBW, brightness, color temp)
- ✅ Fallback mechanisms
- ✅ Error handling and recovery
- ✅ API communication (mocked)
- ✅ Integration with Home Assistant core

## Continuous Integration

Tests are automatically run in CI/CD pipelines:
- On every commit
- On pull requests
- Before releases

## Requirements

- Python 3.13+
- pytest
- pytest-asyncio
- Home Assistant dependencies

Install requirements:
```bash
pip install -r ../../requirements.txt
```

## Contributing

When contributing tests:
1. Add tests for new features
2. Update existing tests for modified features
3. Ensure all tests pass before submitting PRs
4. Add test documentation when appropriate