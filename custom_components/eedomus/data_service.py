"""Data Service for Eedomus Integration with caching and API management."""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import aiohttp_client
import aiohttp
import async_timeout

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EedomusDataService:
    """Data service with caching and periodic refresh for Eedomus API data."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the data service."""
        self.hass = hass
        self.session = aiohttp_client.async_get_clientsession(hass)
        self._cache: Dict[str, Any] = {
            'devices': None,
            'usage_ids': None,
            'peripheral_types': None,
            'last_refresh': None,
            'refresh_count': 0
        }
        self._unsubscribe_refresh = None
        self._initialized = False
        self._api_client = None
    
    async def async_init(self) -> None:
        """Initialize the data service."""
        try:
            # Set up periodic refresh (every 30 minutes)
            self._unsubscribe_refresh = async_track_time_interval(
                self.hass,
                self._async_refresh_cache,
                timedelta(minutes=30)
            )
            
            # Initial cache load
            await self._async_refresh_cache(None)
            
            self._initialized = True
            _LOGGER.info("Eedomus DataService initialized successfully")
            
        except Exception as e:
            _LOGGER.error(f"Failed to initialize DataService: {e}")
            raise
    
    async def async_shutdown(self) -> None:
        """Clean up resources."""
        if self._unsubscribe_refresh:
            self._unsubscribe_refresh()
        
        if self.session:
            await self.session.close()
        
        _LOGGER.debug("Eedomus DataService shutdown complete")
    
    async def _async_refresh_cache(self, now) -> None:
        """Refresh cached data from Eedomus API."""
        try:
            _LOGGER.debug("Starting cache refresh...")
            start_time = datetime.now()
            
            # Fetch all data in parallel
            devices_task = self._async_fetch_devices()
            usage_ids_task = self._async_fetch_usage_ids()
            peripheral_types_task = self._async_fetch_peripheral_types()
            
            # Wait for all tasks to complete
            devices, usage_ids, peripheral_types = await asyncio.gather(
                devices_task,
                usage_ids_task,
                peripheral_types_task
            )
            
            # Update cache
            self._cache = {
                'devices': devices,
                'usage_ids': usage_ids,
                'peripheral_types': peripheral_types,
                'last_refresh': datetime.now(),
                'refresh_count': self._cache.get('refresh_count', 0) + 1
            }
            
            duration = (datetime.now() - start_time).total_seconds()
            _LOGGER.info(f"Cache refresh completed in {duration:.2f}s - {len(devices)} devices, {len(usage_ids)} usage IDs")
            
        except Exception as e:
            _LOGGER.error(f"Failed to refresh cache: {e}")
    
    async def _async_fetch_devices(self) -> List[Dict]:
        """Fetch devices from Eedomus API."""
        try:
            # In a real implementation, this would call the actual Eedomus API
            # For now, we'll return mock data or use the existing API client
            
            # Try to get devices from the coordinator if available
            if hasattr(self.hass.data.get(DOMAIN, {}).get('coordinator'), 'data'):
                coordinator = self.hass.data[DOMAIN]['coordinator']
                if coordinator.data and hasattr(coordinator.data, 'get'):
                    devices = coordinator.data.get('peripherals', [])
                    return [
                        {
                            'id': str(device.get('periph_id', '')),
                            'name': device.get('name', 'Unknown'),
                            'type': device.get('type', 'unknown'),
                            'room': device.get('room_name', ''),
                            'usage_id': device.get('usage_id', '')
                        }
                        for device in devices
                        if isinstance(device, dict)
                    ]
            
            # Fallback: return empty list if no data available
            return []
            
        except Exception as e:
            _LOGGER.error(f"Failed to fetch devices: {e}")
            return []
    
    async def _async_fetch_usage_ids(self) -> Dict[str, Dict]:
        """Fetch usage ID mappings from Eedomus API."""
        try:
            # In a real implementation, this would call the actual API
            # For now, we'll return mock data or use existing mappings
            
            # Try to get usage IDs from coordinator
            if hasattr(self.hass.data.get(DOMAIN, {}).get('coordinator'), 'data'):
                coordinator = self.hass.data[DOMAIN]['coordinator']
                if coordinator.data and hasattr(coordinator.data, 'get'):
                    peripherals = coordinator.data.get('peripherals', [])
                    usage_ids = {}
                    for device in peripherals:
                        if isinstance(device, dict) and device.get('usage_id'):
                            usage_ids[str(device['usage_id'])] = {
                                'name': device.get('name', 'Unknown'),
                                'type': device.get('type', 'unknown'),
                                'device_id': str(device.get('periph_id', ''))
                            }
                    return usage_ids
            
            return {}
            
        except Exception as e:
            _LOGGER.error(f"Failed to fetch usage IDs: {e}")
            return {}
    
    async def _async_fetch_peripheral_types(self) -> Dict[str, str]:
        """Fetch peripheral type information."""
        try:
            # Return common peripheral types
            return {
                'light': 'Light',
                'switch': 'Switch',
                'sensor': 'Sensor',
                'cover': 'Cover',
                'binary_sensor': 'Binary Sensor',
                'climate': 'Climate',
                'text_sensor': 'Text Sensor'
            }
        except Exception as e:
            _LOGGER.error(f"Failed to fetch peripheral types: {e}")
            return {}
    
    async def get_devices(self, force_refresh: bool = False) -> List[Dict]:
        """Get devices with optional cache bypass."""
        if force_refresh or not self._cache.get('devices'):
            await self._async_refresh_cache(None)
        return self._cache.get('devices', [])
    
    async def get_usage_ids(self, force_refresh: bool = False) -> Dict[str, Dict]:
        """Get usage ID mappings with optional cache bypass."""
        if force_refresh or not self._cache.get('usage_ids'):
            await self._async_refresh_cache(None)
        return self._cache.get('usage_ids', {})
    
    async def get_peripheral_types(self, force_refresh: bool = False) -> Dict[str, str]:
        """Get peripheral type information with optional cache bypass."""
        if force_refresh or not self._cache.get('peripheral_types'):
            await self._async_refresh_cache(None)
        return self._cache.get('peripheral_types', {})
    
    async def get_device_suggestions(self, query: str = "") -> List[Dict]:
        """Get device suggestions for autocompletion."""
        devices = await self.get_devices()
        
        if query:
            query_lower = query.lower()
            return [
                device for device in devices
                if query_lower in device.get('name', '').lower() 
                or query_lower in device.get('id', '').lower()
            ]
        
        return devices
    
    async def get_usage_id_suggestions(self, query: str = "") -> List[Dict]:
        """Get usage ID suggestions for autocompletion."""
        usage_ids = await self.get_usage_ids()
        
        if query:
            query_lower = query.lower()
            return [
                {'id': usage_id, **data}
                for usage_id, data in usage_ids.items()
                if query_lower in usage_id.lower() 
                or query_lower in data.get('name', '').lower()
            ]
        
        return [{'id': usage_id, **data} for usage_id, data in usage_ids.items()]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'last_refresh': self._cache.get('last_refresh'),
            'refresh_count': self._cache.get('refresh_count', 0),
            'devices_count': len(self._cache.get('devices', [])),
            'usage_ids_count': len(self._cache.get('usage_ids', {})),
            'peripheral_types_count': len(self._cache.get('peripheral_types', {}))
        }
    
    async def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache = {
            'devices': None,
            'usage_ids': None,
            'peripheral_types': None,
            'last_refresh': None,
            'refresh_count': 0
        }
        _LOGGER.info("Data cache cleared")
    
    async def get_device_by_id(self, device_id: str) -> Optional[Dict]:
        """Get a specific device by ID."""
        devices = await self.get_devices()
        return next((device for device in devices if device.get('id') == str(device_id)), None)
    
    async def get_usage_id_info(self, usage_id: str) -> Optional[Dict]:
        """Get information about a specific usage ID."""
        usage_ids = await self.get_usage_ids()
        return usage_ids.get(str(usage_id))
    
    async def search_devices(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search devices by name or ID."""
        devices = await self.get_devices()
        search_lower = search_term.lower()
        
        results = [
            device for device in devices
            if search_lower in device.get('name', '').lower() 
            or search_lower in device.get('id', '').lower()
            or search_lower in device.get('room', '').lower()
        ]
        
        return results[:limit]
    
    async def get_device_types_summary(self) -> Dict[str, int]:
        """Get summary of device types."""
        devices = await self.get_devices()
        summary = {}
        
        for device in devices:
            device_type = device.get('type', 'unknown')
            summary[device_type] = summary.get(device_type, 0) + 1
        
        return summary