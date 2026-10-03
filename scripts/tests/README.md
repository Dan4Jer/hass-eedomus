# hass-eedomus Test Suite

This directory contains the automated test suite for the
`hass-eedomus` Home Assistant custom integration.

The tests cover the integration core, configuration flows, API client,
device mapping, Home Assistant entities, services, webhooks, migration,
history support, fallback logic and monitoring sensors.

---

## Current status

Current test results:

```text
404 passed
Overall coverage: 87%
Statements: 4393
Missed statements: 557
```

The current coverage report was generated with:

```bash
PYTHONPATH=. python3 -m pytest   scripts/tests/   --cov=custom_components/eedomus   --cov-report=term-missing
```

### Coverage summary

| Component | Coverage |
|---|---:|
| `api_proxy.py` | 100% |
| `binary_sensor.py` | 100% |
| `config_flow.py` | 100% |
| `const.py` | 100% |
| `cover.py` | 100% |
| `endpoint_volume_sensor.py` | 100% |
| `history_sensor.py` | 100% |
| `light.py` | 100% |
| `mapping_registry.py` | 100% |
| `mapping_rules.py` | 100% |
| `options_flow.py` | 100% |
| `refresh_timing_sensor.py` | 100% |
| `select.py` | 100% |
| `sensor.py` | 100% |
| `storage_mapping.py` | 100% |
| `switch.py` | 100% |
| `text_sensor.py` | 100% |
| `webhook.py` | 100% |
| `eedomus_client.py` | 90% |
| `services.py` | 87% |
| `coordinator.py` | 81% |
| `entity.py` | 78% |
| `device_mapping.py` | 71% |
| `climate.py` | 63% |
| `__init__.py` | 62% |
| **TOTAL** | **87%** |

> Coverage values are a snapshot of the current test suite and should be
> updated after significant changes to the integration or its tests.

---

## Test layout

### Core integration

- `test_integration.py`
  - Integration setup and unload
  - Config entry handling
  - Coordinator registration
  - API / Proxy modes

- `test_config_flow.py`
  - Initial configuration flow
  - API Eedomus mode
  - Proxy-only mode
  - Input validation
  - Duplicate configuration detection
  - API authentication failures
  - HTTP setup requests

- `test_options_flow.py`
  - Options configuration
  - API connection validation
  - UI options
  - YAML editor
  - YAML syntax validation
  - YAML schema validation
  - Mapping save errors

- `test_migration.py`
  - Sequential ConfigEntry migration
  - Migration from legacy configuration versions

---

## API and coordinator

- `test_eedomus_client.py`
  - API client initialization
  - GET / SET requests
  - Network errors
  - Timeouts
  - JSON handling
  - API options
  - Authentication

- `test_coordinator.py`
  - Initial full refresh
  - Partial and full refresh
  - Peripheral aggregation
  - Dynamic peripheral detection
  - History handling
  - Retry handling
  - API error handling
  - Fallback behaviour
  - Set-value logic

- `test_fallback.py`
  - PHP fallback configuration
  - Successful fallback calls
  - HTTP and API failures

- `test_api_proxy.py`
  - Eedomus API Proxy behaviour
  - Request validation and forwarding

- `test_webhook.py`
  - IP security
  - Invalid JSON
  - Refresh actions
  - Partial refresh
  - Reload
  - Missing coordinator/config entry
  - Internal errors

---

## Device mapping

- `test_device_mapping.py`
  - YAML device mapping loading and processing

- `test_mapping_rules.py`
  - Mapping rules and entity selection

- `test_mapping_registry.py`
  - Mapping registry storage and reporting

- `test_storage_mapping.py`
  - Custom mapping persistence

- `test_device_mapping.yaml`
  - Test mapping data used by the mapping tests

---

## Entity platforms

- `test_entity.py`
  - Base `EedomusEntity`
  - Device information
  - Unique IDs
  - Parent / child relationships
  - Mapping helpers

- `test_sensor.py`
  - Numeric and text sensors
  - Units
  - Device classes
  - Dynamic value mapping
  - Sensor setup

- `test_text_sensor_module.py`
  - Text sensors
  - Enum mapping
  - Dynamic icons
  - Raw-value fallback
  - Extra state attributes

- `test_binary_sensor.py`
  - Binary sensor states and setup

- `test_switch.py`
  - Switch states and commands

- `test_light.py`
  - Standard lights
  - Brightness
  - Color temperature
  - RGB / RGBW
  - RGBW parent and child entities
  - Home Assistant color modes

- `test_cover.py`
  - Covers / shutters
  - Open / close / stop
  - Position
  - Tilt
  - Aggregated covers
  - Parent / child handling

- `test_climate.py`
  - Climate entities
  - Current temperature
  - Target temperature
  - Linked sensors
  - Custom mappings

- `test_select.py`
  - Select entities
  - Dynamic options
  - Mapping fallback

---

## Services and monitoring

- `test_services.py`
  - `refresh`
  - `set_value`
  - `reload`
  - `set_climate_temperature`
  - `cleanup_unused_entities`
  - `cleanup_unused_devices`

- `test_history_sensor.py`
  - History progress sensors

- `test_refresh_timing_sensor.py`
  - Refresh duration and timing sensors

- `test_endpoint_volume_sensor.py`
  - API endpoint data-volume monitoring

---

## Running the tests

Run commands from the project root.

### Run the complete test suite

```bash
PYTHONPATH=. python3 -m pytest scripts/tests/
```

For verbose output with short tracebacks:

```bash
PYTHONPATH=. python3 -m pytest scripts/tests/ -v --tb=short
```

The repository also contains a dedicated test runner:

```bash
PYTHONPATH=. python3 scripts/tests/test_all.py
```

`test_all.py` explicitly runs all supported test modules.

---

## Run one test module

Example for lights:

```bash
PYTHONPATH=. python3 -m pytest scripts/tests/test_light.py -v
```

Example for the coordinator:

```bash
PYTHONPATH=. python3 -m pytest scripts/tests/test_coordinator.py -v
```

Example for the configuration flow:

```bash
PYTHONPATH=. python3 -m pytest scripts/tests/test_config_flow.py -v
```

Example for the options flow:

```bash
PYTHONPATH=. python3 -m pytest scripts/tests/test_options_flow.py -v
```

---

## Run one individual test

```bash
PYTHONPATH=. python3 -m pytest   scripts/tests/test_config_flow.py::test_step_user_success_api_mode   -v
```

---

## Coverage

### Terminal coverage report

Use the command validated for the current development environment:

```bash
PYTHONPATH=. python3 -m pytest   scripts/tests/   --cov=custom_components/eedomus   --cov-report=term-missing
```

This runs the complete test suite and displays:

- number of statements,
- number of missed statements,
- coverage percentage,
- exact missing lines for each module.

### HTML coverage report

```bash
PYTHONPATH=. python3 -m pytest   scripts/tests/   --cov=custom_components/eedomus   --cov-report=term-missing   --cov-report=html
```

The HTML report is generated in:

```text
htmlcov/index.html
```

### Coverage for one module

Example for the coordinator tests:

```bash
PYTHONPATH=. python3 -m pytest   scripts/tests/test_coordinator.py   --cov=custom_components/eedomus/coordinator.py   --cov-report=term-missing
```

For a global integration coverage measurement, prefer the complete suite
command shown above.

---

## Testing strategy

The suite uses a combination of:

- `pytest`
- `pytest-asyncio`
- `pytest-cov`
- `pytest-homeassistant-custom-component`
- `MockConfigEntry`
- `MagicMock`
- `AsyncMock`
- `aioclient_mock`

External eedomus API communication is mocked during tests.

Tests should not depend on a real eedomus box or external network
connectivity.

Some integration-level tests intentionally use Home Assistant's real
ConfigEntry and setup mechanisms while mocking the underlying HTTP
responses.

The current development environment automatically loads the required
pytest plugins from the active Python environment. The documented test
commands therefore do not disable pytest plugin autoloading.

---

## Adding new tests

When adding or modifying a feature:

1. Add or update the corresponding `test_*.py` module.
2. Test both successful and error paths when relevant.
3. Mock external API or filesystem dependencies.
4. Prefer Home Assistant test fixtures when integration behaviour is
   being tested.
5. Keep tests independent from a real eedomus installation.
6. Add the new test module to `test_all.py` if a new file is created.
7. Run the complete suite before submitting the change.
8. Check code coverage for newly added code.
9. Update the coverage snapshot in this README when the global value changes.

---

## Current coverage areas

The current suite includes tests for:

- Config flow and Options flow
- API and Proxy connection modes
- Eedomus API client
- Coordinator refresh logic
- YAML and device mapping
- Mapping registry and storage
- Entity creation and state handling
- Sensors and text sensors
- Binary sensors
- Switches
- Lights, including RGBW
- Covers and aggregated covers
- Climate entities
- Select entities
- History support
- Integration services
- Webhooks
- Retry and PHP fallback mechanisms
- Refresh timing monitoring
- Endpoint volume monitoring
- ConfigEntry migration
- Error and recovery paths

---

## Current test environment snapshot

The latest full coverage run used:

```text
Python 3.14.3
pytest 9.0.3
pytest-cov 7.1.0
pytest-homeassistant-custom-component 0.13.367
404 tests collected
404 tests passed
87% total coverage
```

These versions describe the latest measured test run and are not intended
as hard requirements for every development environment.
