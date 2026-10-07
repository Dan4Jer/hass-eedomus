# Eedomus integration for Home Assistant

[![HACS Validated](https://img.shields.io/badge/HACS-Validated-green.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-0.15.1-blue.svg)](https://github.com/Dan4Jer/hass-eedomus/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/Dan4Jer/hass-eedomus/blob/main/LICENSE)
[![Release](https://img.shields.io/github/v/release/Dan4Jer/hass-eedomus?label=latest)](https://github.com/Dan4Jer/hass-eedomus/releases/latest)

**hass-eedomus** synchronizes your **eedomus** box with **Home Assistant**: eedomus peripherals (Z-Wave, Zigbee...) appear as native Home Assistant entities (sensors, lights, covers, climate...), without replacing the box. States and commands are synchronized through the eedomus API, with a YAML mapping system to adapt each peripheral to your needs.

[Version française](README.fr.md)

## Features

- **Native entities**: sensors, binary sensors, lights, covers, climate, selects, scenes
- **Multi-box support**: install the integration once per eedomus box (each instance is prefixed and routed independently)
- **Dual connection modes**: pull (eedomus API) and/or push (webhook proxy) - can be combined
- **YAML device mapping**: override default device mappings without touching code
- **History retrieval**: import historical values from the eedomus cloud (optional, rate-limited)
- **PHP fallback**: automatic retry mechanism for values rejected by the box
- **Diagnostic sensors**: API timing, data volume per endpoint, processing time
- **Services**: refresh, set_value, reload, climate temperature, entity cleanup
- **Full configuration from the UI**: config flow and options flow, no YAML required

## Installation

### Via HACS (recommended)

1. Install [HACS](https://hacs.xyz/docs/setup/download) if not already done, restart Home Assistant
2. In HACS, add a custom repository: `https://github.com/Dan4Jer/hass-eedomus`
3. Search "Eedomus" in **HACS** > **Integrations**, install, restart Home Assistant

### Manual

1. Download the latest [release](https://github.com/Dan4Jer/hass-eedomus/releases)
2. Extract into `custom_components/eedomus/`
3. Restart Home Assistant

## Configuration

**Settings** > **Devices & Services** > **Add Integration** > search "Eedomus":

| Field | Required | Description |
|-------|----------|-------------|
| `api_host` | yes | IP address of your eedomus box (e.g. `192.168.1.2`) |
| `api_user` | for API mode | eedomus API user (see eedomus box settings) |
| `api_secret` | for API mode | eedomus API secret |
| `api_eedomus` | yes | Enable pull mode (API) |
| `enable_api_proxy` | yes | Enable push mode (webhook) |

At least one of `api_eedomus` / `enable_api_proxy` must be enabled.

### Connection modes

- **API Eedomus (pull)**: Home Assistant polls the box. Requires API credentials. Full functionality including history.
- **API Proxy (webhook, push)**: the box pushes updates to Home Assistant in near real time. Limited functionality (no history).
- **Combined (recommended)**: both modes together for redundancy and responsiveness.

## Options

**Settings** > **Devices & Services** > Eedomus > **Configure**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `api_eedomus` | boolean | `true` | Pull mode via eedomus API |
| `enable_api_proxy` | boolean | `false` | Push mode via webhook |
| `enable_webhook` | boolean | `true` | Register the webhook endpoint (needed by proxy mode) |
| `enable_history` | boolean | `false` | Import historical values from the eedomus cloud |
| `history_peripherals_per_scan` | integer | `5` | Peripherals processed per history scan (rate limiting) |
| `scan_interval` | integer | `300` | Polling interval in seconds |
| `enable_set_value_retry` | boolean | `true` | Retry values rejected by the box |
| `api_proxy_disable_security` | boolean | `false` | Disable IP validation of webhook calls (debug only, not recommended) |
| `php_fallback_enabled` | boolean | `false` | PHP script fallback for rejected values |
| `php_fallback_script_name` | string | `fallback.php` | Fallback script name on the box |
| `php_fallback_timeout` | integer | `5` | Fallback request timeout (seconds) |
| `http_request_timeout` | integer | `10` | Timeout for eedomus API requests (seconds) |

Recommended `scan_interval`: 30-60s for testing, 300s (default) for production, 600-900s for large installations.

## Multi-box

You can install several instances of the integration, one per eedomus box (e.g. a house and a secondary residence). Each instance:

- gets its own config entry and its own API credentials
- prefixes its entities and unique IDs to avoid collisions
- has its own options (connection modes, scan interval, etc.)
- routes services (`set_value`, `refresh`...) to its own box

Services accept a target: pass the entity or config entry to select which box receives the command.

## YAML device mapping

Device mappings are defined in YAML and loaded at startup:

- `custom_components/eedomus/config/device_mapping.yaml` - default mapping (do not edit, updated by releases)
- `custom_components/eedomus/config/custom_mapping.yaml` - your overrides (preserved on updates)

Mapping priority: advanced rules (conditions on parent/children, usage IDs, names) > `usage_id_mappings` > `name_patterns` > `default_mapping`.

```yaml
# custom_mapping.yaml
custom_usage_id_mappings:
  99:
    ha_entity: sensor
    ha_subtype: custom
    icon: mdi:custom-icon
```

Custom rules override default rules with the same name; new rules are added. See [YAML_UI_MAPPING_GUIDE.md](docs/YAML_UI_MAPPING_GUIDE.md) for the complete rule grammar.

## Services

| Service | Description |
|---------|-------------|
| `eedomus.refresh` | Force a full refresh of all peripherals |
| `eedomus.set_value` | Set a peripheral value (`device_id`, `value`) |
| `eedomus.reload` | Reload the integration |
| `eedomus.set_climate_temperature` | Set a climate entity temperature |
| `eedomus.cleanup_unused_entities` | Remove disabled/orphaned eedomus entities |
| `eedomus.cleanup_unused_devices` | Remove orphaned eedomus devices |

## Tests

The test suite runs locally without a Home Assistant installation:

```bash
pip install -r requirements-test.txt

# Unit tests (56): mapping rules, API client, options flow, YAML merging
python3 -m pytest tests/unit/ -v

# E2E tests (12): live instance via REST API - connectivity, refresh,
# set_value, options flow. Requires HA_TOKEN in .env and a reachable HA instance
python3 -m pytest tests/e2e/ -v
```

The E2E suite is non-destructive: it toggles the test peripheral and restores its initial state.

## Troubleshooting

- **Integration fails to load**: check API credentials and box IP, then look at the logs (filter `custom_components.eedomus`)
- **Values not applied**: for dimmable peripherals, the box expects numeric values (`0` = off, `100` = on)
- **Entities missing**: run `eedomus.cleanup_unused_entities`, then reload; check the mapping table in the logs
- **History sensors unavailable**: enable the `enable_history` option and wait for the first scan cycle

## Documentation

- [README.fr.md](README.fr.md) - French documentation
- [CHANGELOG.md](docs/CHANGELOG.md) - Version history
- [configuration_documentation.md](docs/configuration_documentation.md) - Detailed configuration (EN)
- [configuration_documentation_fr.md](docs/configuration_documentation_fr.md) - Detailed configuration (FR)
- [OPTIONS_DOCUMENTATION.md](docs/OPTIONS_DOCUMENTATION.md) - Options reference
- [YAML_UI_MAPPING_GUIDE.md](docs/YAML_UI_MAPPING_GUIDE.md) - Mapping rule grammar

## License

MIT - see [LICENSE](LICENSE)

---

Created and maintained by [@Dan4Jer](https://github.com/Dan4Jer)
