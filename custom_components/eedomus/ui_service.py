"""UI Service for Eedomus Integration with WebSocket API for frontend communication."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.components.websocket_api import (
    async_register_command,
)
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Define WebSocket command types
WS_TYPE_EEDOMUS_VALIDATE = f"{DOMAIN}/validate_config"
WS_TYPE_EEDOMUS_SUGGESTIONS = f"{DOMAIN}/get_suggestions"
WS_TYPE_EEDOMUS_SCHEMA = f"{DOMAIN}/get_schema"
WS_TYPE_EEDOMUS_CACHE_STATS = f"{DOMAIN}/get_cache_stats"


class EedomusUIService:
    """UI service with WebSocket API for frontend communication."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the UI service."""
        self.hass = hass
        self._registered_commands = []
        self._initialized = False
    
    async def async_init(self) -> None:
        """Initialize the UI service and register WebSocket commands."""
        try:
            # Register WebSocket commands with proper command types
            self._registered_commands = [
                async_register_command(self.hass, WS_TYPE_EEDOMUS_VALIDATE, self._handle_validate_config),
                async_register_command(self.hass, WS_TYPE_EEDOMUS_SUGGESTIONS, self._handle_get_suggestions),
                async_register_command(self.hass, WS_TYPE_EEDOMUS_SCHEMA, self._handle_get_schema),
                async_register_command(self.hass, WS_TYPE_EEDOMUS_CACHE_STATS, self._handle_get_cache_stats)
            ]
            
            self._initialized = True
            _LOGGER.info("Eedomus UIService initialized successfully - WebSocket commands registered")
            
        except Exception as e:
            _LOGGER.error(f"Failed to initialize UIService: {e}")
            raise
    
    async def async_shutdown(self) -> None:
        """Clean up resources."""
        # Unregister WebSocket commands
        for unregister_func in self._registered_commands:
            try:
                unregister_func()
            except Exception as e:
                _LOGGER.error(f"Failed to unregister WebSocket command: {e}")
        
        self._registered_commands = []
        self._initialized = False
        _LOGGER.debug("Eedomus UIService shutdown complete")
    
    async def _handle_validate_config(
        self, 
        hass: HomeAssistant, 
        connection, 
        msg: dict
    ) -> dict:
        """Handle validate configuration WebSocket command."""
        try:
            yaml_content = msg.get('yaml_content', '')
            
            # Get SchemaService
            schema_service = self._get_schema_service()
            if not schema_service:
                return self._create_error_response("SchemaService not available")
            
            # Validate YAML content
            is_valid, result = await schema_service.validate_yaml_content(yaml_content)
            
            if is_valid:
                return self._create_success_response({
                    'valid': True,
                    'validated_config': result
                })
            else:
                return self._create_error_response(result.get('error', 'Validation failed'), 
                                                  result.get('type', 'validation_error'))
            
        except Exception as e:
            _LOGGER.error(f"Validation error: {e}")
            return self._create_error_response(str(e))
    
    async def _handle_get_suggestions(
        self, 
        hass: HomeAssistant, 
        connection, 
        msg: dict
    ) -> dict:
        """Handle get suggestions WebSocket command."""
        try:
            field_type = msg.get('field_type', '')
            query = msg.get('query', '')
            context = msg.get('context', {})
            
            # Get SchemaService for suggestions
            schema_service = self._get_schema_service()
            if not schema_service:
                return self._create_error_response("SchemaService not available")
            
            # Get suggestions
            suggestions = await schema_service.get_dynamic_suggestions(field_type, query, context)
            
            return self._create_success_response({
                'suggestions': suggestions,
                'field_type': field_type,
                'query': query
            })
            
        except Exception as e:
            _LOGGER.error(f"Suggestions error: {e}")
            return self._create_error_response(str(e))
    
    async def _handle_get_schema(
        self, 
        hass: HomeAssistant, 
        connection, 
        msg: dict
    ) -> dict:
        """Handle get schema WebSocket command."""
        try:
            section = msg.get('section', '')
            
            # Get SchemaService
            schema_service = self._get_schema_service()
            if not schema_service:
                return self._create_error_response("SchemaService not available")
            
            if section:
                # Get specific section schema
                section_schema = schema_service._get_section_schema(section)
                if section_schema:
                    return self._create_success_response({
                        'section': section,
                        'schema': str(section_schema)
                    })
                else:
                    return self._create_error_response(f"Section '{section}' not found")
            else:
                # Get full schema documentation
                documentation = schema_service.generate_schema_documentation()
                return self._create_success_response({
                    'schema_version': schema_service.get_schema_version(),
                    'documentation': documentation
                })
            
        except Exception as e:
            _LOGGER.error(f"Schema error: {e}")
            return self._create_error_response(str(e))
    
    async def _handle_get_cache_stats(
        self, 
        hass: HomeAssistant, 
        connection, 
        msg: dict
    ) -> dict:
        """Handle get cache statistics WebSocket command."""
        try:
            # Get DataService
            data_service = self._get_data_service()
            if not data_service:
                return self._create_error_response("DataService not available")
            
            # Get cache statistics
            stats = data_service.get_cache_stats()
            
            return self._create_success_response({
                'cache_stats': stats,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            _LOGGER.error(f"Cache stats error: {e}")
            return self._create_error_response(str(e))
    
    def _get_schema_service(self):
        """Get SchemaService instance."""
        if DOMAIN in self.hass.data and 'schema_service' in self.hass.data[DOMAIN]:
            return self.hass.data[DOMAIN]['schema_service']
        return None
    
    def _get_data_service(self):
        """Get DataService instance."""
        if DOMAIN in self.hass.data and 'data_service' in self.hass.data[DOMAIN]:
            return self.hass.data[DOMAIN]['data_service']
        return None
    
    def _get_config_manager(self):
        """Get ConfigManager instance."""
        if DOMAIN in self.hass.data and 'config_manager' in self.hass.data[DOMAIN]:
            return self.hass.data[DOMAIN]['config_manager']
        return None
    
    def _create_success_response(self, result: Dict) -> dict:
        """Create a success response."""
        return {
            'type': 'result',
            'success': True,
            'result': result
        }
    
    def _create_error_response(self, error: str, error_type: str = 'error') -> dict:
        """Create an error response."""
        return {
            'type': 'result',
            'success': False,
            'error': error,
            'error_type': error_type
        }
    
    async def get_validation_endpoint(self) -> str:
        """Get the WebSocket endpoint for configuration validation."""
        return WS_TYPE_EEDOMUS_VALIDATE
    
    async def get_suggestions_endpoint(self) -> str:
        """Get the WebSocket endpoint for suggestions."""
        return WS_TYPE_EEDOMUS_SUGGESTIONS
    
    async def get_schema_endpoint(self) -> str:
        """Get the WebSocket endpoint for schema information."""
        return WS_TYPE_EEDOMUS_SCHEMA
    
    async def get_cache_stats_endpoint(self) -> str:
        """Get the WebSocket endpoint for cache statistics."""
        return WS_TYPE_EEDOMUS_CACHE_STATS
    
    async def validate_config_via_websocket(self, yaml_content: str) -> Dict:
        """Validate configuration using WebSocket API."""
        try:
            # This would typically be called from the frontend
            # For testing purposes, we can call the handler directly
            mock_connection = None
            mock_msg = {'yaml_content': yaml_content}
            
            result = await self._handle_validate_config(
                self.hass, 
                mock_connection, 
                mock_msg
            )
            
            return result
        except Exception as e:
            _LOGGER.error(f"WebSocket validation error: {e}")
            return self._create_error_response(str(e))
    
    async def get_suggestions_via_websocket(self, field_type: str, query: str = "", context: Dict = None) -> Dict:
        """Get suggestions using WebSocket API."""
        try:
            mock_connection = None
            mock_msg = {
                'field_type': field_type,
                'query': query,
                'context': context or {}
            }
            
            result = await self._handle_get_suggestions(
                self.hass, 
                mock_connection, 
                mock_msg
            )
            
            return result
        except Exception as e:
            _LOGGER.error(f"WebSocket suggestions error: {e}")
            return self._create_error_response(str(e))
    
    async def test_websocket_connection(self) -> bool:
        """Test WebSocket connection and service availability."""
        try:
            # Test SchemaService
            schema_service = self._get_schema_service()
            if not schema_service:
                return False
            
            # Test DataService
            data_service = self._get_data_service()
            if not data_service:
                return False
            
            # Test ConfigManager
            config_manager = self._get_config_manager()
            if not config_manager:
                return False
            
            return True
        except Exception as e:
            _LOGGER.error(f"WebSocket test failed: {e}")
            return False
    
    async def get_available_endpoints(self) -> List[Dict[str, str]]:
        """Get list of available WebSocket endpoints."""
        return [
            {
                'name': 'Validate Configuration',
                'endpoint': WS_TYPE_EEDOMUS_VALIDATE,
                'description': 'Validate YAML configuration content'
            },
            {
                'name': 'Get Suggestions',
                'endpoint': WS_TYPE_EEDOMUS_SUGGESTIONS,
                'description': 'Get autocompletion suggestions for fields'
            },
            {
                'name': 'Get Schema',
                'endpoint': WS_TYPE_EEDOMUS_SCHEMA,
                'description': 'Get schema information and documentation'
            },
            {
                'name': 'Get Cache Stats',
                'endpoint': WS_TYPE_EEDOMUS_CACHE_STATS,
                'description': 'Get data cache statistics'
            }
        ]


# Utility functions for WebSocket API
async def get_eedomus_ui_service(hass: HomeAssistant) -> Optional[EedomusUIService]:
    """Get Eedomus UIService instance."""
    if DOMAIN in hass.data and 'ui_service' in hass.data[DOMAIN]:
        return hass.data[DOMAIN]['ui_service']
    return None


async def validate_config(hass: HomeAssistant, yaml_content: str) -> Dict:
    """Validate configuration using UIService."""
    ui_service = await get_eedomus_ui_service(hass)
    if ui_service:
        return await ui_service.validate_config_via_websocket(yaml_content)
    return {'success': False, 'error': 'UIService not available'}


async def get_suggestions(hass: HomeAssistant, field_type: str, query: str = "", context: Dict = None) -> Dict:
    """Get suggestions using UIService."""
    ui_service = await get_eedomus_ui_service(hass)
    if ui_service:
        return await ui_service.get_suggestions_via_websocket(field_type, query, context)
    return {'success': False, 'error': 'UIService not available'}