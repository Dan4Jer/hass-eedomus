"""Constants for the eedomus integration."""

# Ensure required imports are available
import voluptuous as vol
from homeassistant.const import Platform

"""
from homeassistant.helpers import config_validation as cv
"""

try:
    from .private_const import DEFAULT_API_HOST, DEFAULT_API_SECRET, DEFAULT_API_USER
except ImportError:
    # Valeurs par défaut pour les configurations non définies dans private_const.py
    # Ces valeurs seront utilisées si le fichier private_const.py n'existe pas
    DEFAULT_API_HOST = "xxx.XXX.xxx.XXX"
    DEFAULT_API_USER = ""
    DEFAULT_API_SECRET = ""

# Numéro de version cible de la configuration (ConfigEntry)
CONFIG_VERSION = 4

# Configuration
CONF_API_HOST = "api_host"
CONF_API_USER = "api_user"
CONF_API_SECRET = "api_secret"
CONF_ENABLE_HISTORY = "history"
CONF_ENABLE_API_EEDOMUS = "enable_api_eedomus"
CONF_ENABLE_API_PROXY = "enable_api_proxy"
CONF_ENABLE_SET_VALUE_RETRY = "enable_set_value_retry"
CONF_ENABLE_WEBHOOK = "enable_webhook"
CONF_HISTORY_RETRY_DELAY = "history_retry_delay_hours"
CONF_HISTORY_PERIPHERALS_PER_SCAN = "history_peripherals_per_scan"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_REMOVE_ENTITIES = "remove_entities"
CONF_API_PROXY_DISABLE_SECURITY = "api_proxy_disable_security"
CONF_HTTP_REQUEST_TIMEOUT = "http_request_timeout"

CONF_PHP_FALLBACK_ENABLED = "php_fallback_enabled"
CONF_PHP_FALLBACK_SCRIPT_NAME = "php_fallback_script_name"
CONF_PHP_FALLBACK_TIMEOUT = "php_fallback_timeout"

# YAML Mapping Configuration
DEFAULT_CONF_ENABLE_API_EEDOMUS = True  # Enable Eedomus API integration
DEFAULT_CONF_ENABLE_API_PROXY = False  # API Proxy disabled by default in options
DEFAULT_CONF_ENABLE_HISTORY = False  # History disabled by default (temporarily)
DEFAULT_ENABLE_HISTORY = False  # History disabled by default (temporarily)
DEFAULT_HISTORY_RETRY_DELAY = (
    24  # 24 hours  # History retry delay in hours (24 hours by default)
)
DEFAULT_HISTORY_PERIPHERALS_PER_SCAN = (
    1  # History: 1 peripheral per scan interval by default
)
DEFAULT_ENABLE_SET_VALUE_RETRY = True  # Set value retry enabled by default
DEFAULT_ENABLE_WEBHOOK = True  # Webhook enabled by default
DEFAULT_REMOVE_ENTITIES = False  # Remove entities on uninstall disabled by default


DEFAULT_API_PROXY_DISABLE_SECURITY = False  # Security enabled by default
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes
DEFAULT_PHP_FALLBACK_ENABLED = False  # PHP fallback disabled by default
DEFAULT_PHP_FALLBACK_SCRIPT_NAME = "fallback.php"  # Default script name
DEFAULT_PHP_FALLBACK_TIMEOUT = 5  # 5 seconds timeout for PHP fallback script
DEFAULT_HTTP_REQUEST_TIMEOUT = 10  # 10 seconds timeout for HTTP requests to eedomus API

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

# Domain
DOMAIN = "eedomus"
COORDINATOR = "coordinator"

# Schema for config flow (do not modify)
STEP_USER_DATA_SCHEMA = {
    "api_host": str,
    "api_user": str,
    "api_secret": str,
}

# YAML Mapping Configuration Constants
CONF_YAML_CONTENT = "yaml_content"

"""
# Device Mapping Schema
DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("eedomus_id"): str,
        vol.Required("ha_entity"): str,
        vol.Required("type"): vol.In(
            ["light", "switch", "sensor", "cover", "binary_sensor", "climate", "select"]
        ),
        vol.Required("name"): str,
        vol.Optional("ha_subtype", default=""): str,
        vol.Optional("icon"): cv.icon,
        vol.Optional("room", default=""): str,
        vol.Optional("justification", default=""): str,
    }
)
"""

# Schema for YAML files
YAML_MAPPING_SCHEMA = vol.Schema(
    {
        vol.Optional("metadata"): dict,
        vol.Optional("advanced_rules"): list,
        vol.Optional("usage_id_mappings"): dict,
        vol.Optional("dynamic_entity_properties"): dict,
        vol.Optional("specific_device_dynamic_overrides"): dict,
        vol.Optional("specific_device_mappings"): dict,
        vol.Optional("name_patterns"): list,
    }
)
