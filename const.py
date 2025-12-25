"""Constants for the eedomus integration."""
from typing import Dict, Any
from homeassistant.const import Platform
#Ensure required imports are available
from homeassistant.components.light import (
    ColorMode,
    LightEntityFeature,
)

try:
    from .private_const import (
        DEFAULT_API_HOST,
        DEFAULT_API_USER,
        DEFAULT_API_SECRET,
    )
except ImportError:
    # Valeurs par défaut (ou lève une erreur si requis)
    DEFAULT_API_HOST = "xxx.XXX.xxx.XXX"
    DEFAULT_API_USER = ""
    DEFAULT_API_SECRET = ""

# Configuration
CONF_API_USER = "api_user"
CONF_API_SECRET = "api_secret"
CONF_API_HOST = "api_host"
CONF_ENABLE_HISTORY = "history"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLE_API_EEDOMUS = "enable_api_eedomus"
CONF_ENABLE_API_PROXY = "enable_api_proxy"
CONF_API_PROXY_DISABLE_SECURITY = "api_proxy_disable_security"
CONF_ENABLE_SET_VALUE_RETRY = "enable_set_value_retry"
CONF_PHP_FALLBACK_ENABLED = "php_fallback_enabled"
CONF_PHP_FALLBACK_SCRIPT_NAME = "php_fallback_script_name"
CONF_PHP_FALLBACK_TIMEOUT = "php_fallback_timeout"
CONF_PHP_FALLBACK_LOG_ENABLED = "php_fallback_log_enabled"
DEFAULT_CONF_ENABLE_API_EEDOMUS = True
DEFAULT_CONF_ENABLE_API_PROXY = False
DEFAULT_ENABLE_SET_VALUE_RETRY = True  # Set value retry enabled by default
DEFAULT_API_PROXY_DISABLE_SECURITY = False  # Security enabled by default
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes
DEFAULT_PHP_FALLBACK_ENABLED = False  # PHP fallback disabled by default
DEFAULT_PHP_FALLBACK_SCRIPT_NAME = "eedomus_fallback"  # Default script name
DEFAULT_PHP_FALLBACK_TIMEOUT = 5  # 5 seconds timeout for PHP fallback script
DEFAULT_PHP_FALLBACK_LOG_ENABLED = False  # Logging disabled by default

# Platforms
PLATFORMS = [
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.COVER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.CLIMATE,
    # Battery sensors are implemented as SENSOR platform with device_class="battery"
]

# Attributes
ATTR_VALUE_LIST = "value_list"
ATTR_HISTORY = "history"
ATTR_PERIPH_ID = "periph_id"
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


# Table de correspondance entre les classes eedomus et les entités Home Assistant
CLASS_MAPPING: Dict[str, Dict[str, Any]] = {
    "39:1": {"ha_entity": "light", "attributes": {"color_mode": "brightness"}},
    "96:3": {"ha_entity": "light", "attributes": {"color_mode": "rgbw"}},
    "96:4": {"ha_entity": "light", "attributes": {"color_mode": "rgbw"}},
    "38:1": {"ha_entity": "sensor", "attributes": {"device_class": "humidity"}},
    "38:3": {"ha_entity": "sensor", "attributes": {"device_class": "humidity"}},
    "50:2": {"ha_entity": "sensor", "attributes": {"device_class": "pressure"}},
    "50:3": {"ha_entity": "sensor", "attributes": {"device_class": "pressure"}},
    "49:2": {"ha_entity": "sensor", "attributes": {"device_class": "wind_speed"}},
    "51:1": {"ha_entity": "sensor", "attributes": {"device_class": "illuminance"}},
    "114:1": {"ha_entity": "sensor", "attributes": {"device_class": "temperature"}},
    "134:1": {"ha_entity": "sensor", "attributes": {"device_class": "battery"}},
    "133:2": {"ha_entity": "binary_sensor", "attributes": {"device_class": "moisture"}},
    "37:1": {"ha_entity": "switch", "attributes": {}},
    "48:1": {"ha_entity": "binary_sensor", "attributes": {"device_class": "motion"}},
    "32:1": {"ha_entity": "switch", "attributes": {}},
    "142:2": {"ha_entity": "cover", "attributes": {}},
    # ... (ajoute les autres classes ici)
}

