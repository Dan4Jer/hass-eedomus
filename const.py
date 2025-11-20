#PLATFORMS = ["sensor", "switch", "binary_sensor", "light", "cover"]
#PLATFORMS = ["sensor", "switch"]
#SCAN_INTERVAL = 300 #seconds

"""Constants for the eedomus integration."""
from homeassistant.const import Platform

# Configuration
CONF_API_USER = "api_user"
CONF_API_SECRET = "api_secret"
CONF_API_HOST = "api_host"
CONF_ENABLE_HISTORY = "History retrieval mode"
DEFAULT_API_HOST = "192.168.1.2"
DEFAULT_API_USER = "4pYrgk"
DEFAULT_API_SECRET = "ChJKkudDrYhoh2NR"
DEFAULT_CONF_ENABLE_HISTORY = True
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes

# Platforms
PLATFORMS = [
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.COVER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

# Attributes
ATTR_VALUE_LIST = "value_list"
ATTR_HISTORY = "history"
ATTR_PERIPH_ID = "periph_id"
ATTR_CARACT_ID = "caract_id"
ATTR_LAST_UPDATED = "last_updated"

# Domain
DOMAIN = "eedomus"
COORDINATOR = "coordinator"


# Device classes for sensors
SENSOR_DEVICE_CLASSES = {
    "temperature": "temperature",
    "humidity": "humidity",
    "power": "power",
    "energy": "energy",
    "voltage": "voltage",
    "current": "current",
}

# Schema for config flow (do not modify)
STEP_USER_DATA_SCHEMA = {
    "api_host": str,
    "api_user": str,
    "api_secret": str,
}
