---
name: hass-eedomus-coding-standards
description: Load when working on hass-eedomus code to ensure compliance with project coding standards, commit conventions, versioning practices, and Home Assistant 2026+ compatibility requirements.
user-invocable: true
license: MIT
metadata:
  display-name: "Hass-Eedomus Coding Standards"
  short-description: "Code formatting, commit conventions, and versioning practices for hass-eedomus"
---

# Hass-Eedomus Coding Standards and Best Practices

## When to Load

Load this skill when you need to:
- Write or review code for the hass-eedomus integration
- Create commit messages following project conventions
- Update version numbers across project files
- Ensure Home Assistant 2026+ compatibility
- Follow established coding patterns and architecture

## Overview

This skill defines **mandatory coding standards** for the hass-eedomus Home Assistant custom component, ensuring:

1. **Consistent Code Formatting**: Black, isort, and flake8 compliance
2. **Descriptive Commit Messages**: Standardized format for git commits
3. **Semantic Versioning**: Proper version incrementation rules
4. **Home Assistant 2026+ Compatibility**: API usage and import standards
5. **Code Documentation**: Comment and docstring conventions
6. **Type Hints**: Python type annotations
7. **Error Handling**: Consistent exception management

## Project Context

**hass-eedomus** is a Home Assistant custom integration for Eedomus box synchronization.

- **Language**: Python 3.9+
- **Framework**: Home Assistant Custom Component API
- **Target**: Home Assistant 2026.3+
- **Repository**: https://github.com/Dan4Jer/hass-eedomus
- **Current Version**: 0.14.3

## 1. Code Formatting Standards

### Python Code Style

**Tools Used:**
- **black**: Code formatter (line-length: 88)
- **isort**: Import sorter (compatible with black)
- **flake8**: Linter (config in .flake8)

**Configuration Files:**
```
# .flake8
[flake8]
max-line-length = 88
exclude = .venv,venv,.git,__pycache__,.*

# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py39']

[tool.isort]
profile = "black"
line_length = 88
known_first_party = ["custom_components"]
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
```

**Enforcement:**
```bash
# Format all Python files
black custom_components/eedomus/

# Sort imports
isort custom_components/eedomus/

# Check for linting issues
flake8 custom_components/eedomus/

# Combined: Format, sort, and lint
black custom_components/eedomus/ && \
isort custom_components/eedomus/ && \
flake8 custom_components/eedomus/
```

### Line Length
- **Maximum**: 88 characters (configured in both black and isort)
- **Exceptions**: URLs in comments, long string literals
- **Rationale**: Matches Home Assistant core standards

### Naming Conventions

**Classes:**
```python
# GOOD
class EedomusLight(EedomusEntity):
class EedomusConfigManager:

# BAD
class eedomus_light:
class Eedomuslight:
```

**Functions/Methods:**
```python
# GOOD
def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
async def _async_fetch_device_data(self) -> dict:

# BAD
def setupEntry():
async def GetData():
```

**Variables:**
```python
# GOOD
eedomus_client: EedomusClient
device_mapping: dict
periph_id: str

# BAD
EedomusClient: type  # Type names should be capitalized differently
myMapping: dict
tmp: str  # Be descriptive
```

**Constants:**
```python
# GOOD (in const.py)
CONF_API_USER = "api_user"
DEFAULT_SCAN_INTERVAL = 300
PLATFORMS = [Platform.LIGHT, Platform.SWITCH]

# BAD
api_user = "api_user"  # Should be UPPER_CASE
default_scan = 300
```

**Private Members:**
```python
# GOOD
self._client: EedomusClient
self._unsubscribe: Callable | None

# BAD
self.client  # Should be private if internal
self.Unsubscribe  # Case inconsistency
```

### Type Hints

**Mandatory for:**
- All function parameters
- All function return values
- All class attributes (use dataclasses or `__post_init__`)

**Examples:**
```python
# GOOD
from typing import Any, Dict, List, Optional
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry
) -> bool:
    pass

def get_device_mapping(
    devices: List[Dict[str, Any]],
    mapping_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Dict[str, Any]]:
    pass

# BAD (missing type hints)
async def async_setup_entry(hass, entry):
    pass

def get_device_mapping(devices, mapping_config=None):
    pass
```

**Common Type Aliases:**
```python
# In typing.py or at module level
PeriphId = str
DeviceType = str
EedomusDevice = Dict[str, Any]
EntityConfig = Dict[str, Any]
```

**Optional Types:**
```python
# GOOD
from typing import Optional

def get_value(key: str) -> Optional[str]:
    pass

# Also acceptable (Python 3.10+)
def get_value(key: str) -> str | None:
    pass
```

**Collections:**
```python
# GOOD
from typing import List, Dict, Set, Tuple, Any

def process_devices(devices: List[Dict[str, Any]]) -> None:
    pass

# Python 3.9+ can use built-in types
def process_devices(devices: list[dict[str, Any]]) -> None:
    pass
```

### Import Organization

**Grouping:**
1. Future imports
2. Standard library imports
3. Third-party imports
4. Home Assistant imports
5. Local imports (relative)

**Example:**
```python
# GOOD
from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import requests
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .eedomus_client import EedomusClient

# BAD (mixed imports)
import json
from homeassistant.core import HomeAssistant
import requests
from typing import Any
from .const import DOMAIN
```

**Lazy Imports:**
Use for heavy dependencies or to avoid circular imports:
```python
# GOOD - At module level with try/except for optional dependencies
try:
    from homeassistant.components.light import ColorMode
    HAS_COLOR_MODE = True
except ImportError:
    HAS_COLOR_MODE = False

# GOOD - Inside function to avoid circular imports
def process_data(data: Any) -> None:
    from .data_service import EedomusDataService
    service = EedomusDataService()
```

## 2. Commenting and Documentation

### Docstrings

**Format**: Google-style docstrings

**Classes:**
```python
class EedomusClient:
    """Client for interacting with the Eedomus API.
    
    This client handles all communication with the Eedomus API, including
    authentication, device listing, and state updates.
    
    Attributes:
        api_user: The Eedomus API username.
        api_secret: The Eedomus API secret key.
        session: The aiohttp session for making requests.
        base_url: The base URL for the Eedomus API.
    """
```

**Functions/Methods:**
```python
def async_get_devices(self) -> List[Dict[str, Any]]:
    """Fetch all devices from the Eedomus API.
    
    Returns:
        List of device dictionaries, each containing device metadata
        and current state information.
        
    Raises:
        EedomusConnectionError: If the connection to Eedomus fails.
        EedomusAuthenticationError: If authentication credentials are invalid.
    """
```

**Async Functions:**
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Eedomus integration from a config entry.
    
    This is the main setup function called by Home Assistant when
    the integration is configured.
    
    Args:
        hass: The Home Assistant instance.
        entry: The configuration entry for this integration.
        
    Returns:
        True if setup was successful, False otherwise.
    """
```

### Inline Comments

**Purpose**: Explain **why**, not **what**

**Examples:**
```python
# GOOD - Explains why we're doing something non-obvious
# We use async_add_executor_job to avoid blocking the event loop
# with synchronous file I/O operations
await self.hass.async_add_executor_job(self._save_config_to_file, config)

# GOOD - Documents a workaround
# Home Assistant 2026.3+ changed the API, so we check both old and new methods
if hasattr(hass.components, 'frontend'):
    # New API
    await async_register_built_in_panel(hass, ...)
else:
    # Fallback for older versions
    await register_panel(hass, ...)

# BAD - States the obvious
# Call the API
response = await self._api.get_devices()

# BAD - Redundant with well-named code
i = i + 1  # Increment counter
```

**TODOs and FIXMEs:**
```python
# TODO: Handle rate limiting from Eedomus API
# FIXME: This will fail if device has no usage_id
# XXX: Temporarily disabled due to HA 2026.3 compatibility issues
```

### File Headers

**Standard Header for All Python Files:**
```python
"""Module description here.

If the module contains classes, describe the main class.
If it contains utility functions, describe their purpose.
"""

from __future__ import annotations

import logging
from typing import Any

# Third-party imports
# Home Assistant imports
# Local imports

_LOGGER = logging.getLogger(__name__)
```

**Examples:**
```python
# For entity.py
"""Eedomus entity implementations.

This module contains the base entity class and platform-specific
entity implementations (Light, Switch, Cover, Sensor, etc.).
"""

# For coordinator.py
"""Eedomus data update coordinator.

Manages periodic data fetching from Eedomus API and coordinates
updates across all entities.
"""
```

## 3. Commit Message Conventions

### Format

**Standard Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(light): Add RGBW color support` |
| `fix` | Bug fix | `fix(sensor): Handle None values in battery sensors` |
| `docs` | Documentation | `docs: Update README with new config options` |
| `style` | Formatting (no code change) | `style: Format code with black` |
| `refactor` | Code refactoring | `refactor: Extract device mapping to separate class` |
| `perf` | Performance improvement | `perf: Optimize API call batching` |
| `test` | Test-related changes | `test: Add unit tests for coordinator` |
| `chore` | Maintenance tasks | `chore: Update dependencies` |
| `revert` | Revert a commit | `revert: Revert "feat: Add experimental feature"` |

**Scopes:**
- Component: `light`, `sensor`, `cover`, `switch`, `climate`, `binary_sensor`, `select`, `text_sensor`
- Module: `coordinator`, `entity`, `config_flow`, `options_flow`, `services`, `webhook`, `api_proxy`
- Core: `const`, `manifest`, `init`
- Frontend: `frontend`, `www`, `panel`
- Scripts: `scripts`
- Global: (no scope) for project-wide changes

### Subject Line
- **Length**: 50-72 characters
- **Format**: Imperative mood ("Add" not "Added", "Fix" not "Fixed")
- **Capitalization**: First letter lowercase
- **Punctuation**: No period at the end

**Examples:**
```
# GOOD
fix(light): handle None color_mode attribute
feat(sensor): add history retrieval for all device types
refactor(coordinator): extract API client to separate class
docs: update installation instructions for HA 2026+

# BAD
Fixed the bug with light entities  # Past tense, too vague
Adding new feature for sensors   # Present continuous, period
Fix: sensor history issue         # Missing scope, colon
```

### Commit Body
- **When**: Required for complex changes
- **Content**: Explain **what** changed and **why**
- **Format**: Bullet points or paragraphs
- **Line Length**: 72 characters max

**Examples:**
```
feat(history_sensor): add support for peripheral history retrieval

- Add new HistoryProgressSensor class to track import progress
- Implement async_import_history method for batch peripheral processing
- Add history_retry_delay and history_peripherals_per_scan options
- Handle rate limiting from Eedomus API with exponential backoff

Breaking Change: Enabling history will now process peripherals
incrementally to avoid API rate limits.
```

```
fix(coordinator): prevent blocking calls in event loop

The async_track_state_change was causing blocking call warnings
in Home Assistant 2026.3+. This change:

- Replaces async_track_state_change with async_track_state_change_event
- Uses async_add_executor_job for all synchronous operations
- Ensures all callbacks are properly wrapped with async_callback

Fixes: #27, #28
```

### Commit Footer
- **Breaking Changes**: `BREAKING CHANGE: <description>`
- **Related Issues**: `Fixes #<issue>`, `Closes #<issue>`, `Related to #<issue>`
- **See Also**: `See: <url>`

**Examples:**
```
BREAKING CHANGE: Custom mapping configuration format has changed.
Users must migrate their custom_mapping.yaml files.

Fixes #27
Related to #22, #26
```

### Special Commit Types

**Version Bump:**
```
chore: bump version to 0.14.3

- Update version in pyproject.toml
- Update version in manifest.json
- Add changelog entry
```

**Dependency Update:**
```
chore(deps): update aiohttp from 3.13.3 to 3.14.0

Bump aiohttp to address security vulnerability CVE-2024-XXXX.
```

**Merge Commit:**
```
Merge branch 'fix/ha-2026-compatibility' into unstable
```

### Git Workflow

**Branching Strategy:**
```
main (protected) ← unstable ← feature/*
                          ← fix/*
                          ← hotfix/*
```

**Branch Naming:**
- `main`: Production-ready code
- `unstable`: Development branch
- `fix/<issue>-<description>`: Bug fixes (e.g., `fix/27-history-import`)
- `feat/<description>`: New features (e.g., `feat/rich-editor`)
- `refactor/<description>`: Code refactoring
- `docs/<description>`: Documentation updates

**Pull Request Titles:** Same format as commit messages

**Pull Request Descriptions:**
- Reference related issues
- Describe changes in detail
- Include screenshots if UI changes
- Note breaking changes

## 4. Versioning Practices

### Semantic Versioning

**Format**: `MAJOR.MINOR.PATCH`

| Version | When to Increment | Example Changes |
|---------|-------------------|-----------------|
| MAJOR | Breaking changes, major rewrites | New config format, removed features |
| MINOR | Backward-compatible new features | New entity types, new services |
| PATCH | Backward-compatible bug fixes | Bug fixes, small improvements |

**Current Version**: 0.14.3 (from pyproject.toml)

### Version Files

**Files to Update on Version Bump:**

1. `pyproject.toml` (primary source):
```toml
[project]
name = "hass-eedomus"
version = "0.14.3"  # Update here
```

2. `custom_components/eedomus/manifest.json`:
```json
{
    "domain": "eedomus",
    "name": "Eedomus Integration",
    "version": "0.14.3",  # Update here
    ...
}
```

3. `README.md` (version badge):
```markdown
[![Version](https://img.shields.io/badge/version-0.14.3-blue.svg)](https://github.com/Dan4Jer/hass-eedomus/releases/tag/v0.14.3)
```

### Version Bump Procedure

**For PATCH Version (0.14.2 → 0.14.3):**
```bash
# 1. Update version files
sed -i 's/version = "0.14.2"/version = "0.14.3"/' pyproject.toml
sed -i 's/"version": "0.14.2"/"version": "0.14.3"/' custom_components/eedomus/manifest.json

# 2. Update README badge
sed -i 's/version-0.14.2/version-0.14.3/' README.md
sed -i 's/v0.14.2/v0.14.3/' README.md

# 3. Create git tag
git add pyproject.toml custom_components/eedomus/manifest.json README.md
git commit -m "chore: bump version to 0.14.3"
git tag -a v0.14.3 -m "Release v0.14.3"

# 4. Push tag
git push origin v0.14.3

# 5. Create GitHub release (manual step)
```

**For MINOR Version (0.14.3 → 0.15.0):**
```bash
# Same procedure, but update to 0.15.0
# Also update release notes
```

**For MAJOR Version (0.x.x → 1.0.0):**
```bash
# Requires additional steps:
# - Migration code for breaking changes
# - Documentation of breaking changes
# - Community announcement
```

### Pre-Release Versions

**Format**: `MAJOR.MINOR.PATCH-<suffix>`

**Suffixes:**
- `alpha`: Early development, may be unstable
- `beta`: Feature-complete, testing phase
- `rc`: Release candidate, near-final

**Example:**
```toml
version = "0.15.0-beta.1"
```

### Release Notes

**Template:**
```markdown
## 🚀 Version 0.14.3 (2026-09-05)

### ✨ New Features
- Feature description with link to documentation

### 🐛 Bug Fixes
- Bug fix description (Fixes #27)

### 📝 Changes
- Change description

### ⚠️ Breaking Changes
- Description of breaking change and migration steps

### 📚 Documentation
- New or updated documentation

### 🤝 Contributors
- @contributor1
- @contributor2
```

## 5. Home Assistant 2026+ Compatibility

### API Changes

**Import Changes:**
```python
# OLD (pre-2026)
from homeassistant.helpers.event import async_track_state_change

# NEW (2026+)
from homeassistant.helpers.event import async_track_state_change_event
```

**Storage API:**
```python
# OLD
from homeassistant.helpers import storage
store = storage.Store(hass, 1, "eedomus.config")

# NEW
from homeassistant.helpers.storage import Store
store = Store(hass, 1, "eedomus.config")
```

**Frontend Registration:**
```python
# OLD
from homeassistant.components.frontend import (
    register_built_in_panel,
    register_panel,
)

# NEW
from homeassistant.components.frontend import async_register_built_in_panel
```

**WebSocket API:**
```python
# OLD
from homeassistant.components.websocket import WSType

# NEW (2026.02+)
# WSType removed, use standard asyncio protocols
```

### Deprecated APIs to Avoid

| Old API | New API | Notes |
|---------|---------|-------|
| `async_track_state_change` | `async_track_state_change_event` | Event-based tracking |
| `hass.components.frontend` | `hass.components.frontend` | Still exists but check for None |
| `WSType` | N/A | Removed in 2026.02 |
| `Store.async_save()` | `await store.async_save()` | Coroutine now |
| `@callback` decorator | `@callback` | Still used but with proper typing |

### Compatibility Checks

**Version Detection:**
```python
from homeassistant.const import __version__ as HA_VERSION

def is_ha_2026_or_newer() -> bool:
    """Check if running Home Assistant 2026 or newer."""
    if HA_VERSION is None:
        return False
    major, minor, _ = HA_VERSION.split('.')[:3]
    return int(major) >= 2026 or (int(major) == 2026 and int(minor) >= 0)
```

**Fallback Patterns:**
```python
# For optional features
if is_ha_2026_or_newer():
    # Use new API
    await async_register_built_in_panel(hass, ...)
else:
    # Use old API
    register_panel(hass, ...)
```

### Type Hinting for HA Types

**Use proper type annotations for Home Assistant types:**
```python
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    config: ConfigType = None,
) -> bool:
    pass
```

## 6. Error Handling

### Exception Hierarchy

**Custom Exceptions:**
```python
# In exceptions.py or at module level
class EedomusError(Exception):
    """Base exception for Eedomus errors."""

class EedomusConnectionError(EedomusError):
    """Connection to Eedomus API failed."""

class EedomusAuthenticationError(EedomusError):
    """Authentication with Eedomus API failed."""

class EedomusRateLimitError(EedomusError):
    """API rate limit exceeded."""

class EedomusConfigurationError(EedomusError):
    """Configuration error."""
```

**Usage:**
```python
if not await self._api.async_connect():
    raise EedomusConnectionError("Failed to connect to Eedomus API")

try:
    data = await self._api.async_get_devices()
except EedomusConnectionError as e:
    _LOGGER.error("Connection error: %s", e)
    raise
```

### Logging

**Log Levels:**
- `DEBUG`: Detailed information for debugging
- `INFO`: Important runtime information (integration setup, updates)
- `WARNING`: Unexpected but recoverable situations
- `ERROR`: Serious problems that prevent functionality
- `CRITICAL`: Fatal errors that crash the integration

**Examples:**
```python
# GOOD
_LOGGER.debug("Fetching devices from Eedomus API, params: %s", params)
_LOGGER.info("Eedomus integration setup complete, %d entities created", entity_count)
_LOGGER.warning("Device %s has invalid usage_id: %s", device_id, usage_id)
_LOGGER.error("Failed to connect to Eedomus API: %s", error)

# BAD - Too verbose for INFO
_LOGGER.info("Processing device: %s", device_id)  # Should be DEBUG

# BAD - Missing context
_LOGGER.error("Failed")  # What failed? Why?
```

**Exception Logging:**
```python
# GOOD
try:
    await self._async_update_data()
except EedomusConnectionError as err:
    _LOGGER.error(
        "Error fetching data from Eedomus API: %s", 
        err, 
        exc_info=True  # Include traceback for errors
    )
    # Don't raise, allow retry

# GOOD - For critical errors
except EedomusAuthenticationError as err:
    _LOGGER.critical(
        "Invalid Eedomus credentials. Please check your configuration. "
        "Error: %s", 
        err
    )
    raise ConfigEntryAuthFailed from err
```

### Retry Logic

**Exponential Backoff:**
```python
import asyncio
from homeassistant.helpers import aiohttp_client

async def async_fetch_with_retry(
    self,
    url: str,
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> Any:
    """Fetch data with exponential backoff."""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            async with self._session.get(url) as response:
                return await response.json()
        except aiohttp.ClientError as err:
            last_error = err
            delay = initial_delay * (2 ** attempt)
            _LOGGER.warning(
                "Attempt %s/%s failed for %s. Retrying in %ss. Error: %s",
                attempt + 1,
                max_retries,
                url,
                delay,
                err,
            )
            await asyncio.sleep(delay)
    
    _LOGGER.error(
        "All %s attempts failed for %s. Last error: %s",
        max_retries,
        url,
        last_error,
    )
    raise EedomusConnectionError(f"Failed after {max_retries} attempts") from last_error
```

## 7. Code Structure

### Module Organization

**custom_components/eedomus/ Structure:**
```
custom_components/eedomus/
├── __init__.py              # Main integration setup
├── const.py                 # Constants
├── config_flow.py           # Configuration flow
├── options_flow.py          # Options flow
├── coordinator.py           # Data coordinator
├── eedomus_client.py        # API client
├── entity.py                # Base entity class
├── light.py                 # Light platform
├── switch.py                # Switch platform
├── cover.py                 # Cover platform
├── sensor.py                # Sensor platform
├── binary_sensor.py         # Binary sensor platform
├── select.py                # Select platform
├── climate.py               # Climate platform
├── text_sensor.py           # Text sensor platform
├── history_sensor.py         # History tracking sensors
├── refresh_timing_sensor.py # Timing sensors
├── endpoint_volume_sensor.py # Volume sensors
├── scene.py                 # Scene support
├── webhook.py               # Webhook handler
├── api_proxy.py             # API proxy
├── services.py              # Custom services
├── services.yaml            # Service definitions
├── schema_service.py        # Schema validation
├── data_service.py          # Data management
├── mapping_registry.py      # Device mapping
├── mapping_rules.py         # Mapping rules engine
├── device_mapping.py        # Device type detection
├── config_manager.py         # Configuration management
├── ui_service.py            # UI service for frontend
├── panel.py                 # Configuration panel
├── frontend.yaml            # Frontend resources
├── manifest.json            # Integration manifest
└── www/                     # Frontend assets
    ├── eedomus-rich-editor.js
    ├── eedomus-panel.js
    └── manifest.json
```

### Class Structure

**Entity Classes:**
```python
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

class EedomusEntity(CoordinatorEntity):
    """Base class for all Eedomus entities."""
    
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: EedomusDataUpdateCoordinator,
        device: Dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"eedomus_{device['periph_id']}"

class EedomusLight(EedomusEntity, LightEntity):
    """Light entity for Eedomus."""
    
    @property
    def is_on(self) -> bool | None:
        return self._device.get("value")
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._api.async_set_value(self._device["periph_id"], True)
```

**Service Classes:**
```python
class EedomusDataService:
    """Service for managing Eedomus data."""
    
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._data: Dict[str, Any] = {}
        self._last_update: datetime | None = None
    
    async def async_update(self) -> None:
        """Update all data from Eedomus API."""
        pass
```

### Configuration Management

**YAML Configuration:**
```yaml
# custom_mapping.yaml
# Device-specific overrides
device_overrides:
  "12345":  # periph_id
    name: "Custom Device Name"
    entity_type: "light"  # Override detected type
    device_class: "battery"
    usage_id: "96:3"  # Custom usage_id
    
  "67890":
    disabled: true  # Disable this device
    ignore: true   # Don't create entity

# Global settings
global_settings:
  default_scan_interval: 300
  enable_history: false
  history_peripherals_per_scan: 1
```

## 8. Testing

### Test Structure

```
/tests/
├── test_entity_creation.py
├── test_device_mapping.py
├── test_history_retrieval.py
├── test_config_migration.py
└── conftest.py  # Pytest fixtures
```

### Test Conventions

**Naming:**
```python
# Test functions
def test_device_creation_with_valid_data():
    pass

def test_device_creation_with_missing_periph_id():
    pass

async def test_async_update_data():
    pass

# Test classes
class TestEedomusLight:
    pass

class TestDeviceMapping:
    pass
```

**Fixtures:**
```python
# conftest.py
import pytest
from homeassistant.core import HomeAssistant

@pytest.fixture
def hass():
    """Create a mock HomeAssistant instance."""
    return HomeAssistant()

@pytest.fixture
def mock_device():
    """Create a mock Eedomus device."""
    return {
        "periph_id": "12345",
        "name": "Test Device",
        "usage_id": "37:2",
        "value": True,
    }
```

### Code Validation

**Pre-commit Hooks (recommended):**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.3.0
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pycqa/pylint
    rev: v3.1.0
    hooks:
      - id: pylint
```

**Run Checks:**
```bash
# Format and lint
black custom_components/eedomus/
isort custom_components/eedomus/
flake8 custom_components/eedomus/

# Type checking (requires mypy)
mypy custom_components/eedomus/

# Run tests
pytest tests/
```

## 9. Code Review Checklist

### Before Committing

- [ ] Code follows PEP 8 and project style guidelines
- [ ] All functions have type hints
- [ ] All public classes and functions have docstrings
- [ ] Line lengths are <= 88 characters
- [ ] Imports are properly grouped and sorted
- [ ] No sensitive information (API keys, passwords) in code
- [ ] Commit message follows conventions
- [ ] All tests pass

### Before Creating Pull Request

- [ ] Branch follows naming conventions
- [ ] All commits have descriptive messages
- [ ] Code is properly formatted (black, isort)
- [ ] Linting passes (flake8)
- [ ] Tests pass
- [ ] Documentation updated (if applicable)
- [ ] Version numbers updated (if applicable)
- [ ] PR title follows commit message format
- [ ] PR description references related issues

### Before Merging

- [ ] All CI checks pass
- [ ] Code review completed
- [ ] Breaking changes documented
- [ ] Migration path defined (if breaking changes)
- [ ] Version bump committed (if releasing)
- [ ] Release notes updated

## 10. Common Patterns

### Singleton Pattern

```python
from typing import ClassVar

class EedomusClient:
    """Singleton client for Eedomus API."""
    
    _instance: ClassVar["EedomusClient | None"] = None
    
    def __new__(cls, *args: Any, **kwargs: Any) -> "EedomusClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### Caching

```python
from functools import lru_cache
from datetime import datetime, timedelta

class EedomusDataService:
    """Service with caching."""
    
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    @lru_cache(maxsize=128)
    def get_device(self, periph_id: str) -> Dict[str, Any]:
        """Get device from cache or API."""
        if periph_id in self._cache:
            if datetime.now() < self._cache_expiry[periph_id]:
                return self._cache[periph_id]
        
        device = await self._fetch_device(periph_id)
        self._cache[periph_id] = device
        self._cache_expiry[periph_id] = datetime.now() + self._cache_ttl
        return device
```

### Event Handling

```python
from homeassistant.core import Event, callback
from homeassistant.helpers.event import async_track_state_change_event

class EedomusCoordinator:
    """Coordinator with event handling."""
    
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._unsubscribe: Callable | None = None
    
    async def async_setup(self) -> None:
        """Set up event listeners."""
        @callback
        def _handle_state_change(event: Event) -> None:
            self.hass.async_create_task(self._async_handle_state_change(event))
        
        self._unsubscribe = async_track_state_change_event(
            self.hass,
            [some_entity_id],
            _handle_state_change,
        )
    
    async def async_shutdown(self) -> None:
        """Clean up event listeners."""
        if self._unsubscribe:
            self._unsubscribe()
```

### Property-based Sensors

```python
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_DEVICE_CLASS

class EedomusSensor(SensorEntity):
    """Sensor entity for Eedomus."""
    
    @property
    def native_value(self) -> StateType | None:
        """Return the state of the sensor."""
        return self._device.get("last_value")
    
    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self._device.get("unit")
    
    @property
    def device_class(self) -> str | None:
        """Return the device class."""
        return self._device.get("device_class")
```

## 11. Anti-Patterns

### ❌ Avoid These

**Mutable Default Arguments:**
```python
# BAD
def process_devices(devices: List[Dict] = []):  # MUTABLE DEFAULT
    pass

# GOOD
def process_devices(devices: List[Dict] | None = None):
    if devices is None:
        devices = []
```

**Bare Except Clauses:**
```python
# BAD
try:
    do_something()
except:  # Catches ALL exceptions, including KeyboardInterrupt
    pass

# GOOD
try:
    do_something()
except EedomusError as e:
    _LOGGER.error("Error: %s", e)
```

**Silent Failures:**
```python
# BAD
try:
    await self._api.async_get_data()
except Exception:
    pass  # Silent failure - very bad!

# GOOD
try:
    await self._api.async_get_data()
except EedomusConnectionError as e:
    _LOGGER.error("API connection failed: %s", e)
    raise
```

**Nested Functions Without Decorators:**
```python
# BAD - Missing @callback for event handlers
async def async_setup(hass: HomeAssistant):
    def handle_event(event):  # This can block the event loop!
        heavy_computation()
    
# GOOD
async def async_setup(hass: HomeAssistant):
    @callback
    def handle_event(event):
        hass.async_create_task(heavy_computation())
```

**Blocking Calls in Event Loop:**
```python
# BAD
@callback
async def handle_event(event):
    with open("file.txt", "r") as f:  # Blocking I/O!
        data = f.read()

# GOOD
@callback
async def handle_event(event):
    await hass.async_add_executor_job(_read_file)
```

## 12. Home Assistant Specific Patterns

### Entity Registration

```python
# In __init__.py or platform setup
from homeassistant.helpers.entity_platform import async_get_current_platform

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    platform = await async_get_current_platform()
    
    for device in devices:
        entity = EedomusLight(coordinator, device)
        await platform.async_register_entity(entity)
```

### Service Registration

```python
# In services.py
from homeassistant.core import ServiceCall
from homeassistant.helpers.service import async_register_admin_service

async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up custom services."""
    
    async def handle_reload(call: ServiceCall) -> None:
        """Handle reload service call."""
        await hass.helpers.service.async_reload_config_entry(call)
    
    await async_register_admin_service(
        hass,
        DOMAIN,
        "reload",
        handle_reload,
        schema=RELOAD_SERVICE_SCHEMA,
    )
```

### Configuration Flow

```python
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.data_entry_flow import FlowResult

class EedomusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eedomus."""
    
    VERSION = 1
    
    async def async_step_user(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
            )
        
        errors = {}
        
        # Validate input
        if not await self._validate_input(user_input):
            errors["base"] = "invalid_input"
        
        if errors:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors,
            )
        
        # Create config entry
        return self.async_create_entry(
            title=user_input[CONF_API_USER],
            data=user_input,
        )
```

## 13. Migration Guidelines

### Configuration Versioning

```python
from homeassistant.config_entries import ConfigEntry

VERSION = 4  # Current config version

async def async_migrate_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry
) -> bool:
    """Migrate config entry to current version."""
    
    if config_entry.version < 4:
        # Migrate from version 3 to 4
        new_data = {**config_entry.data}
        # Make necessary changes
        new_data["new_field"] = "default_value"
        
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            version=4,
        )
        return True
    
    return False
```

### Data Migration

```python
# Migration for custom_mapping.yaml
async def async_migrate_mapping(
    hass: HomeAssistant,
    old_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Migrate old mapping format to new format."""
    new_config = {}
    
    # Convert old format to new format
    for device_id, settings in old_config.items():
        new_config[device_id] = {
            "device_overrides": settings.get("overrides", {}),
            "entity_settings": settings.get("entity", {}),
        }
    
    return new_config
```

## 14. Security Considerations

### Sensitive Data

**Never Commit:**
- API keys and secrets
- Passwords and credentials
- SSH keys
- Personal information
- Home Assistant tokens

**Use Secrets:**
```yaml
# configuration.yaml
recorder:
  db_url: !secret recorder_db_url

eedomus:
  api_user: !secret eedomus_api_user
  api_secret: !secret eedomus_api_secret
```

### Input Validation

```python
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

# Define schema for configuration
CONFIG_SCHEMA = vol.Schema({
    CONF_API_USER: cv.string,
    CONF_API_SECRET: cv.string,
    CONF_SCAN_INTERVAL: vol.All(
        vol.Coerce(int), 
        vol.Range(min=30, max=3600)
    ),
    CONF_ENABLE_HISTORY: cv.boolean,
})

# Validate input
def validate_input(user_input: Dict[str, Any]) -> None:
    """Validate user input."""
    CONFIG_SCHEMA(user_input)  # Raises vol.Invalid if invalid
```

### Rate Limiting

```python
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    """Simple rate limiter."""
    
    def __init__(self, max_calls: int, period: timedelta) -> None:
        self.max_calls = max_calls
        self.period = period
        self.calls: List[datetime] = []
    
    async def async_acquire(self) -> None:
        """Acquire a rate limit token."""
        now = datetime.now()
        
        # Remove old calls
        self.calls = [call for call in self.calls if now - call < self.period]
        
        if len(self.calls) >= self.max_calls:
            oldest = self.calls[0]
            wait_time = (oldest + self.period - now).total_seconds()
            await asyncio.sleep(max(0, wait_time))
            self.calls = self.calls[1:]
        
        self.calls.append(now)
```

## 15. Performance Optimization

### Lazy Loading

```python
# Instead of importing everything at module level
class EedomusEntity:
    """Entity with lazy-loaded dependencies."""
    
    @property
    def some_property(self) -> Any:
        # Import only when needed
        from .heavy_module import heavy_function
        return heavy_function()
```

### Dataclasses

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class DeviceInfo:
    """Device information container."""
    periph_id: str
    name: str
    usage_id: str
    value: Any = None
    room_name: str | None = None
    last_updated: datetime | None = None
```

### Async Context Managers

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def async_api_session(hass: HomeAssistant) -> AsyncIterator[aiohttp.ClientSession]:
    """Create and manage an aiohttp session."""
    session = aiohttp_client.async_get_clientsession(hass)
    try:
        yield session
    finally:
        await session.close()

# Usage
async with async_api_session(hass) as session:
    async with session.get(url) as response:
        data = await response.json()
```

## Summary

This skill defines the coding standards for the hass-eedomus project. Always:

1. **Format**: Use black (88 chars), isort, flake8
2. **Type**: Add type hints to everything
3. **Document**: Use Google-style docstrings
4. **Comment**: Explain why, not what
5. **Commit**: Follow standardized commit message format
6. **Version**: Update all version files together
7. **Compatibility**: Target Home Assistant 2026.3+
8. **Test**: Write tests for new functionality
9. **Review**: Follow the code review checklist

**Questions?** Check existing code for patterns or ask in the project discussions.

---

**Last Updated**: 2026-09-05
**Version**: 1.0.0
**Skill Author**: Mistral Vibe (for Dan4Jer/hass-eedomus)
