# Eedomus Integration for Home Assistant

## Overview
The Eedomus integration connects your eedomus home automation box to Home Assistant, allowing you to control and monitor all your Z-Wave, Zigbee, and virtual devices.

## Features
- **30+ Z-Wave devices** support (lights, switches, sensors)
- **4-5 Zigbee devices** via ZigGate
- **Virtual devices** management
- **Energy consumption** monitoring (Issue #9)
- **Automatic entity mapping** based on device types
- **Battery level** monitoring
- **PHP fallback** mechanism for rejected values

## Installation
1. Add this repository to HACS
2. Install via HACS or manually copy to `custom_components/eedomus/`
3. Restart Home Assistant
4. Configure via Configuration > Integrations

## Configuration
```yaml
# Example configuration.yaml entry
eedomus:
  api_host: "your.eedomus.box.ip"
  api_user: "your_username"
  api_secret: "your_api_secret"
```

## Supported Entities
- **Lights** (with RGBW support)
- **Switches** (with consumption monitoring)
- **Sensors** (temperature, humidity, energy, power)
- **Covers** (shutters, blinds)
- **Binary Sensors** (motion, smoke, flood)
- **Climate** (heating control)
- **Select** (scenes and modes)

## Screenshots
![Eedomus Integration](https://raw.githubusercontent.com/Dan4Jer/hass-eedomus/main/icons/eedomus.png)

## Troubleshooting
- Check logs for API connection issues
- Verify your eedomus box is accessible
- Ensure API credentials are correct

## Development
- Tests: `pytest scripts/tests/`
- Linting: `black` and `flake8`
- Documentation: Update README.md and INFO.md