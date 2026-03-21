"""Schema Service for Eedomus Integration with advanced validation and dynamic schema management."""

import logging
from typing import Dict, Any, List, Optional, Tuple

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import YAML_MAPPING_SCHEMA, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SchemaService:
    """Advanced schema validation and management service."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the schema service."""
        self.hass = hass
        self.base_schema = YAML_MAPPING_SCHEMA
        self._custom_validators = {}
        self._initialized = False
    
    async def async_init(self) -> None:
        """Initialize the schema service."""
        try:
            # Register custom validators
            self._register_custom_validators()
            
            # Load any additional schemas from config
            await self._async_load_custom_schemas()
            
            self._initialized = True
            _LOGGER.info("Eedomus SchemaService initialized successfully")
            
        except Exception as e:
            _LOGGER.error(f"Failed to initialize SchemaService: {e}")
            raise
    
    def _register_custom_validators(self) -> None:
        """Register custom validators for specific fields."""
        # Entity ID validator
        def validate_entity_id(value: str) -> str:
            if not isinstance(value, str):
                raise vol.Invalid("Entity ID must be a string")
            if '.' not in value:
                raise vol.Invalid("Entity ID must contain a dot (.)")
            if value.count('.') > 1:
                raise vol.Invalid("Entity ID can only contain one dot (.)")
            return value
        
        # Device type validator
        def validate_device_type(value: str) -> str:
            valid_types = [
                'light', 'switch', 'sensor', 'cover',
                'binary_sensor', 'climate', 'select', 'text_sensor'
            ]
            if value not in valid_types:
                raise vol.Invalid(f"Invalid device type: {value}. Must be one of: {', '.join(valid_types)}")
            return value
        
        # Usage ID validator
        def validate_usage_id(value: str) -> str:
            if not isinstance(value, str):
                raise vol.Invalid("Usage ID must be a string")
            if len(value) > 50:
                raise vol.Invalid("Usage ID too long (max 50 characters)")
            return value
        
        self._custom_validators = {
            'entity_id': validate_entity_id,
            'device_type': validate_device_type,
            'usage_id': validate_usage_id
        }
    
    async def _async_load_custom_schemas(self) -> None:
        """Load custom schemas from configuration if available."""
        try:
            # Check if ConfigManager is available
            if DOMAIN in self.hass.data and 'config_manager' in self.hass.data[DOMAIN]:
                config_manager = self.hass.data[DOMAIN]['config_manager']
                config = await config_manager.async_get_configuration()
                
                # Check for custom schemas in configuration
                if 'custom_schemas' in config:
                    _LOGGER.debug(f"Loaded {len(config['custom_schemas'])} custom schemas")
        except Exception as e:
            _LOGGER.error(f"Failed to load custom schemas: {e}")
    
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration against base schema."""
        try:
            # Validate against base schema
            validated = self.base_schema(config)
            
            _LOGGER.debug("Configuration validation successful")
            return validated
        except vol.Invalid as e:
            _LOGGER.error(f"Validation error: {e}")
            raise
        except Exception as e:
            _LOGGER.error(f"Unexpected validation error: {e}")
            raise
    
    def validate_section(self, section: str, data: Any) -> Any:
        """Validate a specific section of the configuration."""
        try:
            # Get schema for specific section
            section_schema = self._get_section_schema(section)
            if section_schema:
                return section_schema(data)
            return data
        except vol.Invalid as e:
            _LOGGER.error(f"Validation error in section {section}: {e}")
            raise
    
    def _get_section_schema(self, section: str) -> Optional[vol.Schema]:
        """Get schema for a specific configuration section."""
        # Extract section schema from base schema
        if section not in self.base_schema.schema:
            return None
        
        section_def = self.base_schema.schema[section]
        
        # Handle optional sections
        if isinstance(section_def, vol.Optional):
            section_def = section_def.schema
        
        # Handle array sections
        if isinstance(section_def, list):
            # For arrays, return the item schema
            if len(section_def) > 0 and hasattr(section_def[0], 'schema'):
                return section_def[0].schema
        
        # Handle dict sections
        if isinstance(section_def, dict) and 'schema' in section_def:
            return section_def['schema']
        
        return None
    
    def get_field_schema(self, section: str, field: str) -> Optional[vol.Schema]:
        """Get schema for a specific field in a section."""
        try:
            section_schema = self._get_section_schema(section)
            if section_schema and hasattr(section_schema, 'schema'):
                field_schema = section_schema.schema.get(field)
                if field_schema and hasattr(field_schema, 'schema'):
                    return field_schema.schema
                return field_schema
            return None
        except Exception as e:
            _LOGGER.error(f"Failed to get field schema for {section}.{field}: {e}")
            return None
    
    def validate_field(self, section: str, field: str, value: Any) -> Any:
        """Validate a specific field value."""
        try:
            field_schema = self.get_field_schema(section, field)
            if field_schema:
                return field_schema(value)
            return value
        except vol.Invalid as e:
            _LOGGER.error(f"Field validation error for {section}.{field}: {e}")
            raise
    
    def get_suggestions(self, field_type: str, query: str = "") -> List[Dict[str, Any]]:
        """Get suggestions for autocompletion based on field type."""
        suggestions_map = {
            'device_type': ['light', 'switch', 'sensor', 'cover', 'binary_sensor', 'climate', 'select', 'text_sensor'],
            'state': ['on', 'off', 'unavailable'],
            'ha_entity_pattern': ['light.', 'switch.', 'sensor.', 'binary_sensor.', 'climate.', 'cover.'],
            'icon_pattern': ['mdi:', 'hass:', 'material:']
        }
        
        if field_type in suggestions_map:
            all_suggestions = suggestions_map[field_type]
            if query:
                return [
                    {'value': s, 'label': s}
                    for s in all_suggestions 
                    if query.lower() in s.lower()
                ]
            return [{'value': s, 'label': s} for s in all_suggestions]
        
        return []
    
    async def get_dynamic_suggestions(self, field_type: str, query: str = "", context: Dict = None) -> List[Dict[str, Any]]:
        """Get dynamic suggestions based on current configuration and data."""
        suggestions = []
        
        try:
            # Get suggestions from DataService if available
            if DOMAIN in self.hass.data and 'data_service' in self.hass.data[DOMAIN]:
                data_service = self.hass.data[DOMAIN]['data_service']
                
                if field_type == 'device_id':
                    suggestions = await data_service.get_device_suggestions(query)
                elif field_type == 'usage_id':
                    suggestions = await data_service.get_usage_id_suggestions(query)
                elif field_type == 'device_type':
                    device_types = await data_service.get_device_types_summary()
                    suggestions = [{'value': dt, 'label': f"{dt} ({count})"} 
                                  for dt, count in device_types.items()]
            
            # Add static suggestions as fallback
            if not suggestions:
                suggestions = self.get_suggestions(field_type, query)
            
            return suggestions
        except Exception as e:
            _LOGGER.error(f"Failed to get dynamic suggestions for {field_type}: {e}")
            return self.get_suggestions(field_type, query)
    
    def validate_yaml_content(self, yaml_content: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate YAML content and return validation result."""
        import yaml
        
        try:
            # Parse YAML
            config = yaml.safe_load(yaml_content) or {}
            
            # Validate against schema
            validated = self.validate_configuration(config)
            
            return True, validated
        except yaml.YAMLError as e:
            _LOGGER.error(f"YAML parsing error: {e}")
            return False, {'error': str(e), 'type': 'yaml_error'}
        except vol.Invalid as e:
            _LOGGER.error(f"Schema validation error: {e}")
            return False, {'error': str(e), 'type': 'schema_error'}
        except Exception as e:
            _LOGGER.error(f"Unexpected validation error: {e}")
            return False, {'error': str(e), 'type': 'unknown_error'}
    
    def get_validation_errors(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get detailed validation errors for a configuration."""
        errors = []
        
        try:
            self.validate_configuration(config)
        except vol.Invalid as e:
            if hasattr(e, 'error_message'):
                errors.append({
                    'path': str(e.path) if hasattr(e, 'path') else 'unknown',
                    'message': e.error_message,
                    'type': 'validation_error'
                })
            if hasattr(e, 'errors') and e.errors:
                for error in e.errors:
                    errors.append({
                        'path': str(error.path) if hasattr(error, 'path') else 'unknown',
                        'message': error.error_message if hasattr(error, 'error_message') else str(error),
                        'type': 'validation_error'
                    })
        except Exception as e:
            errors.append({
                'path': 'unknown',
                'message': str(e),
                'type': 'unknown_error'
            })
        
        return errors
    
    def generate_schema_documentation(self) -> Dict[str, Any]:
        """Generate documentation for the configuration schema."""
        documentation = {
            'sections': {},
            'field_types': {}
        }
        
        # Document each section
        for section_name in self.base_schema.schema:
            section_def = self.base_schema.schema[section_name]
            section_info = {'type': 'unknown', 'description': '', 'fields': {}}
            
            # Determine section type
            if isinstance(section_def, vol.Optional):
                section_info['type'] = 'optional'
                section_def = section_def.schema
            
            if isinstance(section_def, list):
                section_info['type'] = 'array'
                if len(section_def) > 0:
                    item_schema = section_def[0]
                    if hasattr(item_schema, 'schema') and isinstance(item_schema.schema, dict):
                        for field_name, field_def in item_schema.schema.items():
                            section_info['fields'][field_name] = self._get_field_documentation(field_name, field_def)
            elif isinstance(section_def, dict) and 'schema' in section_def:
                section_info['type'] = 'object'
                if isinstance(section_def['schema'], dict):
                    for field_name, field_def in section_def['schema'].items():
                        section_info['fields'][field_name] = self._get_field_documentation(field_name, field_def)
            
            documentation['sections'][section_name] = section_info
        
        return documentation
    
    def _get_field_documentation(self, field_name: str, field_def) -> Dict[str, Any]:
        """Get documentation for a specific field."""
        field_info = {'type': 'unknown', 'required': False, 'description': ''}
        
        if isinstance(field_def, vol.Required):
            field_info['required'] = True
            field_def = field_def.schema
        elif isinstance(field_def, vol.Optional):
            field_info['required'] = False
            field_def = field_def.schema
        
        # Determine field type
        if field_def is str:
            field_info['type'] = 'string'
        elif field_def is int:
            field_info['type'] = 'integer'
        elif field_def is float:
            field_info['type'] = 'float'
        elif field_def is bool:
            field_info['type'] = 'boolean'
        elif isinstance(field_def, list):
            field_info['type'] = 'array'
        elif isinstance(field_def, dict):
            field_info['type'] = 'object'
        elif hasattr(field_def, '__name__'):
            field_info['type'] = field_def.__name__
        
        # Add common field descriptions
        if field_name == 'eedomus_id':
            field_info['description'] = 'Unique Eedomus device identifier'
        elif field_name == 'ha_entity':
            field_info['description'] = 'Home Assistant entity ID (e.g., light.living_room)'
        elif field_name == 'type':
            field_info['description'] = 'Device type (light, switch, sensor, etc.)'
        elif field_name == 'usage_id':
            field_info['description'] = 'Eedomus usage identifier'
        elif field_name == 'icon':
            field_info['description'] = 'Material Design icon (e.g., mdi:lightbulb)'
        
        return field_info
    
    def create_partial_schema(self, sections: List[str]) -> vol.Schema:
        """Create a schema with only specified sections."""
        partial_schema = {}
        
        for section in sections:
            if section in self.base_schema.schema:
                partial_schema[section] = self.base_schema.schema[section]
        
        return vol.Schema(partial_schema)
    
    def extend_schema(self, extensions: Dict[str, Any]) -> vol.Schema:
        """Extend the base schema with additional fields."""
        extended_schema = dict(self.base_schema.schema)
        extended_schema.update(extensions)
        return vol.Schema(extended_schema)
    
    async def validate_with_context(self, config: Dict[str, Any], context: Dict = None) -> Dict[str, Any]:
        """Validate configuration with additional context."""
        try:
            # Basic validation
            validated = self.validate_configuration(config)
            
            # Context-aware validation
            if context:
                validated = await self._async_apply_context_validation(validated, context)
            
            return validated
        except Exception as e:
            _LOGGER.error(f"Context-aware validation failed: {e}")
            raise
    
    async def _async_apply_context_validation(self, config: Dict[str, Any], context: Dict) -> Dict[str, Any]:
        """Apply context-aware validation rules."""
        # Check for duplicate device IDs
        if 'custom_devices' in config:
            device_ids = [device.get('eedomus_id') for device in config['custom_devices'] if device.get('eedomus_id')]
            if len(device_ids) != len(set(device_ids)):
                duplicates = [device_id for device_id in device_ids if device_ids.count(device_id) > 1]
                raise vol.Invalid(f"Duplicate device IDs found: {', '.join(duplicates)}")
        
        # Check for duplicate HA entity IDs
        if 'custom_devices' in config:
            ha_entities = [device.get('ha_entity') for device in config['custom_devices'] if device.get('ha_entity')]
            if len(ha_entities) != len(set(ha_entities)):
                duplicates = [entity for entity in ha_entities if ha_entities.count(entity) > 1]
                raise vol.Invalid(f"Duplicate HA entity IDs found: {', '.join(duplicates)}")
        
        return config
    
    def get_schema_version(self) -> str:
        """Get the current schema version."""
        return "1.1.0"  # Version matching our YAML schema
    
    async def check_schema_compatibility(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check if configuration is compatible with current schema."""
        result = {
            'compatible': True,
            'issues': [],
            'warnings': []
        }
        
        try:
            # Check for deprecated fields
            deprecated_fields = ['old_field', 'legacy_setting']
            for field in deprecated_fields:
                if self._field_exists_in_config(field, config):
                    result['warnings'].append(f"Field '{field}' is deprecated and will be removed in future versions")
            
            # Check for required new fields
            required_fields = ['metadata']
            for field in required_fields:
                if field not in config:
                    result['issues'].append(f"Required field '{field}' is missing")
                    result['compatible'] = False
            
            return result
        except Exception as e:
            _LOGGER.error(f"Schema compatibility check failed: {e}")
            result['compatible'] = False
            result['issues'].append(str(e))
            return result
    
    def _field_exists_in_config(self, field_path: str, config: Dict[str, Any]) -> bool:
        """Check if a field exists in configuration (supports dot notation)."""
        parts = field_path.split('.')
        current = config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False
        
        return True