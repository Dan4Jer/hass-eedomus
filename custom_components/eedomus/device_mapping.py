"""
Device Mapping for eedomus integration.

This module handles loading and merging device mappings from YAML files.
It provides the core mapping functionality between eedomus devices and Home Assistant entities.

Priority order for device mapping:
1. User custom mappings (from custom_mapping.yaml)
2. Advanced rules (RGBW detection, parent-child relationships)
3. Usage ID mapping (from device_mapping.yaml)
4. Name pattern matching
5. Default mapping
"""

import os
import logging
from typing import Dict, Any, Optional
import yaml

# Initialize logger
_LOGGER = logging.getLogger(__name__)

# Default YAML configuration paths (relative to the module directory)
DEFAULT_MAPPING_FILE = "config/device_mapping.yaml"
CUSTOM_MAPPING_FILE = "config/custom_mapping.yaml"


def get_absolute_path(relative_path: str) -> str:
    """Convert relative path to absolute path based on module location.
    
    Args:
        relative_path: Path relative to the module directory
        
    Returns:
        Absolute path to the file
    """
    import os
    import inspect
    # Get the directory where this module is located
    module_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    return os.path.join(module_dir, relative_path)

async def load_yaml_file_async(hass, file_path: str) -> Optional[Dict[str, Any]]:
    """Load YAML configuration from file asynchronously using executor job.
    
    Args:
        hass: Home Assistant instance for accessing async_add_executor_job
        file_path: Path to YAML file
        
    Returns:
        Dictionary with YAML content or None if file doesn't exist or is invalid
    """
    try:
        _LOGGER.debug("📖 Attempting to load YAML file asynchronously: %s", file_path)
        
        if not os.path.exists(file_path):
            _LOGGER.error("❌ YAML file not found: %s", file_path)
            return None
            
        _LOGGER.debug("✅ YAML file exists, attempting to parse asynchronously...")
        
        # Use executor job to avoid blocking the event loop
        def _load_yaml_sync():
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = yaml.safe_load(file)
                    
                    if content:
                        _LOGGER.debug("✅ Successfully loaded YAML mapping from %s", file_path)
                        
                        # Convert list format to dict format if needed
                        if isinstance(content, list):
                            _LOGGER.debug("⚠️  YAML file is in list format, converting to dict format")
                            # Convert list of rules to dict format
                            converted_content = {
                                'advanced_rules': content,
                                'usage_id_mappings': {},
                                'name_patterns': [],
                                'dynamic_entity_properties': {},
                                'specific_device_dynamic_overrides': {}
                            }
                            _LOGGER.debug("✅ Converted YAML to dict format")
                            _LOGGER.debug("   YAML keys after conversion: %s", list(converted_content.keys()))
                            content = converted_content
                        else:
                            _LOGGER.debug("   YAML keys: %s", list(content.keys()))
                        
                        # Critical check for dynamic properties
                        if 'dynamic_entity_properties' in content:
                            _LOGGER.debug("✅ Found dynamic_entity_properties in YAML")
                        else:
                            _LOGGER.debug("⚠️  dynamic_entity_properties section missing from YAML (will be extracted from advanced rules)")
                            
                        if 'specific_device_dynamic_overrides' in content:
                            _LOGGER.debug("✅ Found specific_device_dynamic_overrides in YAML")
                        else:
                            _LOGGER.debug("⚠️  specific_device_dynamic_overrides section missing (normal if no overrides)")
                        
                        return content
                    else:
                        _LOGGER.warning("⚠️  YAML file is empty: %s", file_path)
                        return content
                        
            except yaml.YAMLError as e:
                _LOGGER.error("❌ CRITICAL: Failed to parse YAML file %s: %s", file_path, e)
                _LOGGER.error("❌ This is likely a YAML syntax error - check file format")
                import traceback
                _LOGGER.error("YAML parsing error details: %s", traceback.format_exc())
                return None
            except Exception as e:
                _LOGGER.error("❌ CRITICAL: Error in sync YAML loading %s: %s", file_path, e)
                _LOGGER.error("❌ This prevented YAML loading - check file permissions and encoding")
                import traceback
                _LOGGER.error("Error details: %s", traceback.format_exc())
                return None
        
        return await hass.async_add_executor_job(_load_yaml_sync)
        
    except Exception as e:
        _LOGGER.error("❌ CRITICAL: Error in async YAML loading %s: %s", file_path, e)
        _LOGGER.error("❌ Async executor job failed - falling back to sync loading")
        import traceback
        _LOGGER.error("Async error details: %s", traceback.format_exc())
        # Fallback to synchronous loading if async fails
        return load_yaml_file(file_path)


def load_yaml_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Load YAML configuration from file.
    
    Args:
        file_path: Path to YAML file
        
    Returns:
        Dictionary with YAML content or None if file doesn't exist or is invalid
        
    Note:
        This synchronous version is used ONLY during module initialization.
        It may trigger a single blocking warning during Home Assistant startup,
        which is acceptable per Home Assistant integration guidelines.
        
        The warning occurs once when the module is imported, before the event loop
        is fully active. All runtime operations use the async version via the
        coordinator, so there are no performance impacts.
        
        For async contexts, use load_yaml_file_async() instead.
    """
    try:
        _LOGGER.debug("📖 Attempting to load YAML file: %s", file_path)
        
        if not os.path.exists(file_path):
            _LOGGER.error("❌ YAML file not found: %s", file_path)
            return None
            
        _LOGGER.debug("✅ YAML file exists, attempting to parse...")
        
        # Note: File I/O during initialization is acceptable as it's not in the hot path
        # For production use, consider using hass.async_add_executor_job if available
        with open(file_path, 'r', encoding='utf-8') as file:
            content = yaml.safe_load(file)
            
            if content:
                _LOGGER.debug("✅ Successfully loaded YAML mapping from %s", file_path)
                
                # Convert list format to dict format if needed
                if isinstance(content, list):
                    _LOGGER.debug("⚠️  YAML file is in list format, converting to dict format")
                    # Convert list of rules to dict format
                    converted_content = {
                        'advanced_rules': content,
                        'usage_id_mappings': {},
                        'name_patterns': [],
                        'dynamic_entity_properties': {},
                        'specific_device_dynamic_overrides': {}
                    }
                    _LOGGER.debug("✅ Converted YAML to dict format")
                    _LOGGER.debug("   YAML keys after conversion: %s", list(converted_content.keys()))
                    content = converted_content
                else:
                    _LOGGER.debug("   YAML keys: %s", list(content.keys()))
                
                # Critical check for dynamic properties
                if 'dynamic_entity_properties' in content:
                    _LOGGER.debug("✅ Found dynamic_entity_properties in YAML")
                else:
                    _LOGGER.debug("⚠️  dynamic_entity_properties section missing from YAML (will be extracted from advanced rules)")
                    
                if 'specific_device_dynamic_overrides' in content:
                    _LOGGER.debug("✅ Found specific_device_dynamic_overrides in YAML")
                else:
                    _LOGGER.debug("⚠️  specific_device_dynamic_overrides section missing (normal if no overrides)")
                
            else:
                _LOGGER.warning("⚠️  YAML file is empty: %s", file_path)
            
            return content
            
    except yaml.YAMLError as e:
        _LOGGER.error("❌ CRITICAL: Failed to parse YAML file %s: %s", file_path, e)
        _LOGGER.error("❌ This is likely a YAML syntax error - check file format")
        import traceback
        _LOGGER.error("YAML parsing error details: %s", traceback.format_exc())
        return None
    except Exception as e:
        _LOGGER.error("❌ CRITICAL: Error loading YAML file %s: %s", file_path, e)
        _LOGGER.error("❌ This prevented YAML loading - check file permissions and encoding")
        import traceback
        _LOGGER.error("Error details: %s", traceback.format_exc())
        return None


async def load_yaml_mappings_async(hass, base_path: str = "") -> Dict[str, Any]:
    """Load and merge YAML mappings from default and custom files asynchronously.
    
    Args:
        hass: Home Assistant instance for async operations
        base_path: Base path where YAML files are located (optional)
        
    Returns:
        Merged mapping configuration
    """
    _LOGGER.debug("🔍 Starting async YAML mappings load process")
    
    # Use absolute paths if no base_path provided
    if base_path:
        default_file = os.path.join(base_path, DEFAULT_MAPPING_FILE)
        custom_file = os.path.join(base_path, CUSTOM_MAPPING_FILE)
    else:
        # Convert relative paths to absolute paths based on module location
        default_file = get_absolute_path(DEFAULT_MAPPING_FILE)
        custom_file = get_absolute_path(CUSTOM_MAPPING_FILE)
    
    _LOGGER.debug("📁 Default mapping file path: %s", default_file)
    _LOGGER.debug("📁 Custom mapping file path: %s", custom_file)
    
    # Check if files exist before loading
    if not os.path.exists(default_file):
        _LOGGER.error("❌ CRITICAL: Default YAML file not found at: %s", default_file)
        _LOGGER.error("❌ This will cause all dynamic properties to be empty!")
    else:
        _LOGGER.debug("✅ Default YAML file found")
    
    if os.path.exists(custom_file):
        _LOGGER.debug("✅ Custom YAML file found")
    else:
        _LOGGER.debug("⚠️  Custom YAML file not found (this is normal): %s", custom_file)
    
    # Load mappings asynchronously to avoid blocking warnings
    _LOGGER.debug("📖 Loading default mapping asynchronously...")
    default_mapping = await load_yaml_file_async(hass, default_file) or {}
    _LOGGER.debug("Default mapping loaded: %s", bool(default_mapping))
    
    if not default_mapping:
        _LOGGER.error("❌ CRITICAL: Default mapping could not be loaded!")
        _LOGGER.error("❌ Check file permissions and YAML syntax")
    
    _LOGGER.debug("📖 Loading custom mapping asynchronously...")
    custom_mapping = await load_yaml_file_async(hass, custom_file) or {}
    _LOGGER.debug("Custom mapping loaded: %s", bool(custom_mapping))
    
    # Merge mappings (custom overrides default)
    _LOGGER.debug("🔧 Merging mappings...")
    merged = merge_yaml_mappings(default_mapping, custom_mapping)
    
    return merged

def load_yaml_mappings(base_path: str = "") -> Dict[str, Any]:
    """Load and merge YAML mappings from default and custom files.
    
    Args:
        base_path: Base path where YAML files are located (optional)
        
    Returns:
        Merged mapping configuration
        
    Note:
        This function uses synchronous loading and may trigger blocking warnings during initialization.
        For async contexts, use load_yaml_mappings_async() instead.
    """
    _LOGGER.info("🔍 Starting YAML mappings load process")
    
    # Use absolute paths if no base_path provided
    if base_path:
        default_file = os.path.join(base_path, DEFAULT_MAPPING_FILE)
        custom_file = os.path.join(base_path, CUSTOM_MAPPING_FILE)
    else:
        # Convert relative paths to absolute paths based on module location
        default_file = get_absolute_path(DEFAULT_MAPPING_FILE)
        custom_file = get_absolute_path(CUSTOM_MAPPING_FILE)
    
    _LOGGER.info("📁 Default mapping file path: %s", default_file)
    _LOGGER.info("📁 Custom mapping file path: %s", custom_file)
    
    # Check if files exist before loading
    if not os.path.exists(default_file):
        _LOGGER.error("❌ CRITICAL: Default YAML file not found at: %s", default_file)
        _LOGGER.error("❌ This will cause all dynamic properties to be empty!")
    else:
        _LOGGER.info("✅ Default YAML file found")
    
    if os.path.exists(custom_file):
        _LOGGER.info("✅ Custom YAML file found")
    else:
        _LOGGER.debug("⚠️  Custom YAML file not found (this is normal): %s", custom_file)
    
    # Load mappings using synchronous method (async version is separate)
    _LOGGER.info("📖 Loading default mapping...")
    _LOGGER.debug("⚠️  Using synchronous loading - blocking warnings may appear during initialization")
    default_mapping = load_yaml_file(default_file) or {}
    _LOGGER.debug("Default mapping loaded: %s", bool(default_mapping))
    
    if not default_mapping:
        _LOGGER.error("❌ CRITICAL: Default mapping could not be loaded!")
        _LOGGER.error("❌ Check file permissions and YAML syntax")
    
    _LOGGER.info("📖 Loading custom mapping...")
    _LOGGER.debug("⚠️  Using synchronous loading - blocking warnings may appear during initialization")
    custom_mapping = load_yaml_file(custom_file) or {}
    _LOGGER.debug("Custom mapping loaded: %s", bool(custom_mapping))
    
    # Merge mappings (custom overrides default)
    _LOGGER.info("🔧 Merging mappings...")
    merged = merge_yaml_mappings(default_mapping, custom_mapping)
    
    # Critical checks for dynamic properties
    dynamic_props_loaded = bool(merged.get('dynamic_entity_properties'))
    specific_overrides_loaded = bool(merged.get('specific_device_dynamic_overrides'))
    
    _LOGGER.info("📊 Load summary:")
    _LOGGER.info("   ✅ Default mapping: %s", bool(default_mapping))
    _LOGGER.info("   ✅ Custom mapping: %s", bool(custom_mapping))
    _LOGGER.info("   🎯 Dynamic entity properties: %s", dynamic_props_loaded)
    _LOGGER.info("   🎯 Specific device overrides: %s", specific_overrides_loaded)
    
    if not dynamic_props_loaded:
        _LOGGER.error("❌ CRITICAL: Dynamic entity properties not loaded!")
        _LOGGER.error("❌ All devices will be treated as static - no partial refresh will work!")
        _LOGGER.error("❌ Check YAML file content and structure")
    
    if not specific_overrides_loaded:
        _LOGGER.debug("⚠️  Specific device overrides not loaded (this is normal if none defined)")
    
    # Debug logging to help diagnose loading issues
    if not default_mapping:
        _LOGGER.warning("⚠️ Default YAML mapping file could not be loaded from: %s", default_file)
    if not custom_mapping:
        _LOGGER.debug("⚠️ Custom YAML mapping file not found or empty: %s", custom_file)
    
    return merged


def merge_yaml_mappings(default_mapping: Dict[str, Any], custom_mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Merge default and custom mappings, with custom mappings taking precedence.
    
    Args:
        default_mapping: Default mapping configuration
        custom_mapping: Custom mapping configuration
        
    Returns:
        Merged mapping configuration with usage_id_mappings, advanced_rules, 
        dynamic_entity_properties, and specific_device_dynamic_overrides
    """
    # Ensure we have valid dictionaries
    if not isinstance(default_mapping, dict):
        _LOGGER.error("Default mapping is not a dictionary: %s", type(default_mapping))
        default_mapping = {}
    if not isinstance(custom_mapping, dict):
        _LOGGER.error("Custom mapping is not a dictionary: %s", type(custom_mapping))
        custom_mapping = {}
    
    merged = {}
    
    # Merge advanced rules (custom rules become advanced rules)
    # Ensure we always have a list, never None
    advanced_rules = default_mapping.get('advanced_rules', [])
    if not isinstance(advanced_rules, list):
        _LOGGER.error("Advanced rules is not a list: %s", type(advanced_rules))
        advanced_rules = []
    
    merged['advanced_rules'] = advanced_rules
    if 'custom_rules' in custom_mapping and isinstance(custom_mapping['custom_rules'], list):
        merged['advanced_rules'].extend(custom_mapping['custom_rules'])
    
    # Extract dynamic properties from advanced rules if they are in list format
    # This handles the case where YAML file has rules in list format
    if isinstance(advanced_rules, list):
        _LOGGER.info("🔍 Extracting dynamic properties from list of advanced rules")
        dynamic_props = {}
        specific_overrides = {}
        
        for rule in advanced_rules:
            if isinstance(rule, dict) and 'mapping' in rule:
                mapping = rule['mapping']
                # Extract dynamic properties from child_mapping if present
                if 'child_mapping' in rule:
                    child_mapping = rule['child_mapping']
                    for child_usage_id, child_config in child_mapping.items():
                        if child_config.get('is_dynamic', False):
                            # This rule defines dynamic children
                            pass
                
                # Check if this rule defines dynamic properties
                if mapping.get('is_dynamic', False):
                    ha_entity = mapping.get('ha_entity')
                    if ha_entity:
                        dynamic_props[ha_entity] = True
        
        # Merge extracted properties with existing properties (don't override)
        if dynamic_props:
            _LOGGER.info("✅ Extracted dynamic properties from rules: %s", dynamic_props)
            # Merge with existing dynamic properties, don't override
            existing_props = merged.get('dynamic_entity_properties', {})
            merged['dynamic_entity_properties'] = {**existing_props, **dynamic_props}
        else:
            _LOGGER.debug("⚠️  No dynamic properties found in advanced rules list")
    
    # Merge usage ID mappings (custom overrides default)
    usage_id_mappings = default_mapping.get('usage_id_mappings', {})
    if not isinstance(usage_id_mappings, dict):
        _LOGGER.error("Usage ID mappings is not a dictionary: %s", type(usage_id_mappings))
        usage_id_mappings = {}
    
    merged['usage_id_mappings'] = usage_id_mappings
    if 'custom_usage_id_mappings' in custom_mapping and isinstance(custom_mapping['custom_usage_id_mappings'], dict):
        merged['usage_id_mappings'].update(custom_mapping['custom_usage_id_mappings'])
    
    # Merge name patterns (custom extends default)
    name_patterns = default_mapping.get('name_patterns', [])
    if not isinstance(name_patterns, list):
        _LOGGER.info("Name patterns is not configured (normal for current usage): %s", type(name_patterns))
        name_patterns = []
    
    merged['name_patterns'] = name_patterns
    if 'custom_name_patterns' in custom_mapping and isinstance(custom_mapping['custom_name_patterns'], list):
        merged['name_patterns'].extend(custom_mapping['custom_name_patterns'])
    
    # Add default mapping if present
    if 'default_mapping' in default_mapping and isinstance(default_mapping['default_mapping'], dict):
        merged['default_mapping'] = default_mapping['default_mapping']
    
    # Merge dynamic entity properties (custom overrides default)
    dynamic_entity_properties = default_mapping.get('dynamic_entity_properties', {})
    if not isinstance(dynamic_entity_properties, dict):
        _LOGGER.error("Dynamic entity properties is not a dictionary: %s", type(dynamic_entity_properties))
        dynamic_entity_properties = {}
    
    merged['dynamic_entity_properties'] = dynamic_entity_properties
    if 'custom_dynamic_entity_properties' in custom_mapping and isinstance(custom_mapping['custom_dynamic_entity_properties'], dict):
        merged['dynamic_entity_properties'].update(custom_mapping['custom_dynamic_entity_properties'])
    
    # Merge specific device dynamic overrides (custom overrides default)
    specific_device_dynamic_overrides = default_mapping.get('specific_device_dynamic_overrides', {})
    if not isinstance(specific_device_dynamic_overrides, dict):
        _LOGGER.info("Specific device dynamic overrides is not a dictionary: %s", type(specific_device_dynamic_overrides))
        specific_device_dynamic_overrides = {}
    
    merged['specific_device_dynamic_overrides'] = specific_device_dynamic_overrides
    if 'custom_specific_device_dynamic_overrides' in custom_mapping and isinstance(custom_mapping['custom_specific_device_dynamic_overrides'], dict):
        merged['specific_device_dynamic_overrides'].update(custom_mapping['custom_specific_device_dynamic_overrides'])

    # Merge specific device mappings (custom overrides default)
    specific_device_mappings = default_mapping.get('specific_device_mappings', {})
    if not isinstance(specific_device_mappings, dict):
        _LOGGER.info("Specific device mappings is not a dictionary: %s", type(specific_device_mappings))
        specific_device_mappings = {}

    merged['specific_device_mappings'] = specific_device_mappings
    if 'custom_specific_device_mappings' in custom_mapping and isinstance(custom_mapping['custom_specific_device_mappings'], dict):
        merged['specific_device_mappings'].update(custom_mapping['custom_specific_device_mappings'])

    # Merge metadata (preserve metadata from default mapping)
    if 'metadata' in default_mapping and isinstance(default_mapping['metadata'], dict):
        merged['metadata'] = default_mapping['metadata']
        _LOGGER.debug("✅ Preserved metadata from default mapping: %s", default_mapping['metadata'].get('version', 'unknown'))
    
    if 'metadata' in custom_mapping and isinstance(custom_mapping['metadata'], dict):
        # Custom metadata can override or supplement default metadata
        if 'metadata' not in merged:
            merged['metadata'] = {}
        merged['metadata'].update(custom_mapping['metadata'])
        _LOGGER.debug("✅ Merged custom metadata: %s", custom_mapping['metadata'].get('version', 'unknown'))

    return merged


def load_and_merge_yaml_mappings(base_path: str = "") -> Dict[str, Any]:
    """Load YAML mappings and return merged configuration.
    
    This function loads YAML configuration files and merges them.
    It should be called during initialization to get the complete mapping configuration.
    
    Args:
        base_path: Base path where YAML files are located
        
    Returns:
        Dictionary with merged mapping configuration containing:
        - advanced_rules: List of advanced mapping rules
        - usage_id_mappings: Dictionary of usage_id to entity mappings
        - name_patterns: List of name pattern mappings
        - dynamic_entity_properties: Dictionary of entity types to dynamic status
        - specific_device_dynamic_overrides: Dictionary of periph_id to dynamic status overrides
        - default_mapping: Fallback mapping
    """
    try:
        _LOGGER.info("🔍 Starting YAML mappings load and merge process")
        
        # Load and merge YAML mappings
        yaml_config = load_yaml_mappings(base_path)
        
        _LOGGER.debug("YAML mappings loaded: %s", bool(yaml_config))
        
        if yaml_config:
            _LOGGER.info("✅ Successfully loaded YAML mappings")
            
            # Log YAML metadata if present
            if yaml_config and yaml_config.get('metadata'):
                metadata = yaml_config['metadata']
                _LOGGER.info("📋 YAML Metadata - Version: %s, Last Modified: %s",
                           metadata.get('version', 'unknown'),
                           metadata.get('last_modified', 'unknown'))
                if metadata.get('changes'):
                    for change in metadata['changes']:
                        _LOGGER.info("  📝 %s", change)
            
            # Debug: Log all the important sections
            dynamic_props = yaml_config.get('dynamic_entity_properties', {})
            specific_overrides = yaml_config.get('specific_device_dynamic_overrides', {})
            specific_mappings = yaml_config.get('specific_device_mappings', {})
            
            _LOGGER.debug("Advanced rules count: %d", len(yaml_config.get('advanced_rules', [])))
            _LOGGER.debug("Usage ID mappings count: %d", len(yaml_config.get('usage_id_mappings', {})))
            _LOGGER.debug("Specific device mappings count: %d", len(specific_mappings))
            _LOGGER.debug("Specific device mappings: %s", specific_mappings)
            _LOGGER.debug("Name patterns count: %d", len(yaml_config.get('name_patterns', [])))
            _LOGGER.debug("Dynamic entity properties: %s", dynamic_props)
            _LOGGER.debug("Specific device dynamic overrides: %s", specific_overrides)
            _LOGGER.debug("Specific device mappings: %s", specific_mappings)
            
            # Critical check: if dynamic properties are empty, this is a problem
            if not dynamic_props:
                _LOGGER.error("❌ CRITICAL: dynamic_entity_properties is empty! This will cause all devices to be treated as static.")
                _LOGGER.error("❌ Check if YAML file contains dynamic_entity_properties section")
                _LOGGER.error("❌ Check if YAML file is being loaded correctly")
            else:
                _LOGGER.info("✅ Dynamic entity properties loaded successfully: %s", dynamic_props)
            
            if not specific_overrides:
                _LOGGER.debug("⚠️  specific_device_dynamic_overrides is empty (this is normal if no overrides are defined)")
            else:
                _LOGGER.info("✅ Specific device dynamic overrides loaded: %s", specific_overrides)
            
            return yaml_config
        else:
            _LOGGER.error("❌ CRITICAL: No YAML mappings found! Falling back to empty configuration")
            _LOGGER.error("❌ This means load_yaml_mappings() returned None or empty dict")
            _LOGGER.error("❌ Check file paths and YAML parsing")
            
            # Return minimal configuration with error tracking
            minimal_config = {
                'advanced_rules': [],
                'usage_id_mappings': {},
                'name_patterns': [],
                'dynamic_entity_properties': {},
                'specific_device_dynamic_overrides': {},
                'default_mapping': {
                    'ha_entity': 'sensor',
                    'ha_subtype': 'unknown',
                    'justification': 'Default fallback mapping for unknown devices'
                },
                '_load_error': 'YAML mappings not loaded - check logs for details'
            }
            
            _LOGGER.error("❌ Returning minimal configuration: %s", minimal_config)
            return minimal_config
            
    except Exception as e:
        _LOGGER.error("❌ CRITICAL: Failed to load YAML mappings: %s", e)
        _LOGGER.error("❌ This exception prevented YAML loading - check stack trace")
        import traceback
        _LOGGER.error("Exception stack trace: %s", traceback.format_exc())
        _LOGGER.warning("⚠️  Falling back to minimal configuration")
        
        # Return minimal configuration with error tracking
        minimal_config = {
            'advanced_rules': [],
            'usage_id_mappings': {},
            'name_patterns': [],
            'dynamic_entity_properties': {},
            'specific_device_dynamic_overrides': {},
            'default_mapping': {
                'ha_entity': 'sensor',
                'ha_subtype': 'unknown',
                'justification': 'Default fallback mapping for unknown devices'
            },
            '_load_error': f'Exception during YAML loading: {str(e)}'
        }
        
        return minimal_config


def load_custom_yaml_mappings():
    """Load custom mappings from custom_mapping.yaml file.
    
    This function loads user-specific mappings that should not be in the main
    device_mapping.yaml file. This includes temperature sensor mappings and other
    installation-specific configurations.
    
    Returns:
        dict: Custom mappings or None if file doesn't exist or can't be loaded
        
    Note:
        This synchronous version may trigger blocking warnings during initialization.
        For async contexts, use load_custom_yaml_mappings_async() instead.
    """
    import os
    import yaml
    
    try:
        # Get the directory where the current file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        custom_mapping_path = os.path.join(current_dir, 'config', 'custom_mapping.yaml')
        
        if not os.path.exists(custom_mapping_path):
            _LOGGER.debug("Custom mapping file not found at %s", custom_mapping_path)
            return None
            
        # Load custom mappings using synchronous file I/O
        with open(custom_mapping_path, 'r', encoding='utf-8') as f:
            content = f.read()
            custom_mappings = yaml.safe_load(content) or {}
            _LOGGER.debug("Loaded custom mappings from %s", custom_mapping_path)
            return custom_mappings
            
    except Exception as e:
        _LOGGER.warning("Failed to load custom mappings: %s", e)
        return None


async def load_custom_yaml_mappings_async(hass):
    """Load custom mappings from custom_mapping.yaml file asynchronously.
    
    This async version avoids blocking the event loop by using hass.async_add_executor_job.
    
    Args:
        hass: Home Assistant instance for accessing async_add_executor_job
        
    Returns:
        dict: Custom mappings or None if file doesn't exist or can't be loaded
    """
    def _load_sync():
        return load_custom_yaml_mappings()
    
    return await hass.async_add_executor_job(_load_sync)
