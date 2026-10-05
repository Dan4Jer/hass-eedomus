# hass-eedomus Test Suite

This directory contains the automated test suite for the
`hass-eedomus` Home Assistant custom integration.

The tests cover the integration core, configuration flows, API client,
device mapping, Home Assistant entities, services, webhooks, migration,
history support, fallback logic and monitoring sensors.

---

## Current test status

The values below are updated automatically by the GitHub Actions
`Run Tests` workflow after a successful test run.

<!-- TEST-STATS-START -->
- Tests: **446 passed**
- Statements: **4388**
- Covered: **3958**
- Missing: **430**
- Coverage: **90.20%**
<!-- TEST-STATS-END -->

The latest successful GitHub Actions run is the reference for the current
test and coverage status.

---

## Test layout

### Core integration

- `test_init.py`
  - Integration bootstrap
  - `get_clean_box_name`
  - `async_setup_entry`
  - `async_update_listener`
  - `async_migrate_entry`
  - `async_unload_entry`
  - `async_remove_entry`
  - ConfigEntry migration and lifecycle
  - API / Proxy setup modes
  - History and service setup
  - Entity cleanup on removal
    
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

Example for integration bootstrap:

```bash
PYTHONPATH=. python3 -m pytest scripts/tests/test_init.py -v
```

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
PYTHONPATH=. python3 -m pytest \
  scripts/tests/test_config_flow.py::test_step_user_success_api_mode \
  -v
```

---

## Test coverage

Code coverage is calculated automatically by the GitHub Actions
`Run Tests` workflow.

The same command can be executed locally:

```bash
PYTHONPATH=. python3 -m pytest \
  scripts/tests/ \
  --cov=custom_components/eedomus \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-report=html
```

The workflow generates:

- a terminal coverage report in the GitHub Actions logs;
- `coverage.xml`;
- an HTML coverage report in `htmlcov/`;
- a `coverage-summary.md` file containing the current global coverage.

The generated files are published as GitHub Actions artifacts:

- `coverage-html`
- `coverage-summary`

### HTML coverage report

Open the latest successful `Run Tests` workflow execution in GitHub Actions
and download the:

```text
coverage-html
```

artifact.

After extracting the archive, open:

```text
htmlcov/index.html
```

This report provides detailed coverage information for each source file,
including the exact lines that are not covered by the test suite.

### Coverage summary

Download the:

```text
coverage-summary
```

artifact from the latest successful workflow execution.

It contains:

```text
coverage-summary.md
```

with the current global coverage statistics.

### Local HTML report

After running the coverage command locally, the HTML report is available in:

```text
htmlcov/index.html
```

### Current reference

At the time this documentation was updated, a successful local run reported:

```text
404 tests passed
87% total coverage
```

This value is only a snapshot.

The latest successful GitHub Actions `Run Tests` workflow and its generated
artifacts are the reference for the current coverage value.

---

## Coverage snapshot by module

The following values correspond to the same successful local run mentioned
above and are not intended to remain permanently current.

<!-- COVERAGE-MODULES-START -->
Last update: **2026-10-05 12:25:20 Europe/Paris**

| Component | Statements | Missed | Coverage |
|---|---:|---:|---:|
| `__init__.py` | 258 | 3 | 98.84% |
| `api_proxy.py` | 37 | 0 | 100.00% |
| `binary_sensor.py` | 72 | 0 | 100.00% |
| `climate.py` | 403 | 118 | 70.72% |
| `config_flow.py` | 114 | 0 | 100.00% |
| `const.py` | 49 | 0 | 100.00% |
| `coordinator.py` | 595 | 114 | 80.84% |
| `cover.py` | 136 | 0 | 100.00% |
| `device_mapping.py` | 320 | 93 | 70.94% |
| `eedomus_client.py` | 251 | 26 | 89.64% |
| `endpoint_volume_sensor.py` | 93 | 0 | 100.00% |
| `entity.py` | 219 | 48 | 78.08% |
| `history_sensor.py` | 136 | 0 | 100.00% |
| `light.py` | 369 | 0 | 100.00% |
| `mapping_registry.py` | 47 | 0 | 100.00% |
| `mapping_rules.py` | 77 | 0 | 100.00% |
| `options_flow.py` | 133 | 0 | 100.00% |
| `refresh_timing_sensor.py` | 125 | 0 | 100.00% |
| `select.py` | 97 | 0 | 100.00% |
| `sensor.py` | 327 | 0 | 100.00% |
| `services.py` | 214 | 28 | 86.92% |
| `storage_mapping.py` | 62 | 0 | 100.00% |
| `switch.py` | 103 | 0 | 100.00% |
| `text_sensor.py` | 95 | 0 | 100.00% |
| `webhook.py` | 56 | 0 | 100.00% |
| **TOTAL** | **4388** | **430** | **90.20%** |
<!-- COVERAGE-MODULES-END -->

---

## GitHub Actions

The GitHub Actions workflow runs the test suite automatically and calculates
coverage.

The workflow:

- installs the development dependencies;
- runs the complete pytest suite;
- fails if a test fails;
- generates terminal, XML and HTML coverage reports;
- generates `coverage-summary.md`;
- publishes the HTML and summary reports as artifacts.

The current workflow uses:

```text
PYTHONPATH=.
```

and runs:

```bash
python3 -m pytest \
  scripts/tests/ \
  -v \
  --tb=short \
  --cov=custom_components/eedomus \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-report=html
```

The GitHub Actions environment may use newer compatible patch versions of
Python, pytest and the test dependencies than the local development
environment.

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

The current development environment automatically loads the required pytest
plugins from the active Python environment. The documented test commands
therefore do not disable pytest plugin autoloading.

---

## Development dependencies

The test environment must include the packages required by the integration
and the test suite.

In particular, coverage requires:

```text
pytest-cov
```

and the integration currently imports:

```text
async-timeout
```

The GitHub Actions workflow installs development dependencies from:

```text
requirements-dev.txt
```

Any dependency required by the automated test environment should therefore
be declared there.

Runtime dependencies required directly by the Home Assistant integration
should also be declared in the integration metadata when appropriate.

---

## Adding new tests

When adding or modifying a feature:

1. Add or update the corresponding `test_*.py` module.
2. Test both successful and error paths when relevant.
3. Mock external API or filesystem dependencies.
4. Prefer Home Assistant test fixtures when integration behaviour is being tested.
5. Keep tests independent from a real eedomus installation.
6. Add the new test module to `test_all.py` if a new file is created.
7. Run the complete suite before submitting the change.
8. Check code coverage for newly added code.
9. Check the GitHub Actions artifacts after the workflow completes.

---

## Current coverage areas

The current suite includes tests for:

- Integration bootstrap and lifecycle (`__init__.py`: setup, update listener, migration, unload, remove)
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

## Test environment snapshot

A recent successful local run used:

<!-- TEST-ENV-START -->
```text
Python 3.14.7
pytest 9.0.3
pytest-cov 7.1.0
pytest-homeassistant-custom-component 0.13.367
446 tests collected
446 tests passed
90.20% total coverage
Last test run: 2026-10-05 12:25:20 Europe/Paris
```
<!-- TEST-ENV-END -->

GitHub Actions may use newer compatible patch versions.

The latest successful `Run Tests` workflow and its generated artifacts should
be considered the current reference.
