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

def load_yaml_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Load YAML configuration from file.
    
    Args:
        file_path: Path to YAML file
        
    Returns:
        Dictionary with YAML content or None if file doesn't exist or is invalid
    """
    try:
        if not os.path.exists(file_path):
            _LOGGER.debug("YAML file not found: %s", file_path)
            return None
            
        with open(file_path, 'r', encoding='utf-8') as file:
            content = yaml.safe_load(file)
            if content:
                _LOGGER.info("Successfully loaded YAML mapping from %s", file_path)
            return content
            
    except yaml.YAMLError as e:
        _LOGGER.error("Failed to parse YAML file %s: %s", file_path, e)
        return None
    except Exception as e:
        _LOGGER.error("Error loading YAML file %s: %s", file_path, e)
        return None


def load_yaml_mappings(base_path: str = "") -> Dict[str, Any]:
    """Load and merge YAML mappings from default and custom files.
    
    Args:
        base_path: Base path where YAML files are located (optional)
        
    Returns:
        Merged mapping configuration
    """
    # Use absolute paths if no base_path provided
    if base_path:
        default_file = os.path.join(base_path, DEFAULT_MAPPING_FILE)
        custom_file = os.path.join(base_path, CUSTOM_MAPPING_FILE)
    else:
        # Convert relative paths to absolute paths based on module location
        default_file = get_absolute_path(DEFAULT_MAPPING_FILE)
        custom_file = get_absolute_path(CUSTOM_MAPPING_FILE)
    
    _LOGGER.debug("Loading default mapping from: %s", default_file)
    _LOGGER.debug("Loading custom mapping from: %s", custom_file)
    
    # Load default mapping
    default_mapping = load_yaml_file(default_file) or {}
    
    # Load custom mapping
    custom_mapping = load_yaml_file(custom_file) or {}
    
    # Merge mappings (custom overrides default)
    merged = merge_yaml_mappings(default_mapping, custom_mapping)
    
    _LOGGER.info("Successfully loaded YAML mappings (default: %s, custom: %s)", 
                bool(default_mapping), bool(custom_mapping))
    
    # Debug logging to help diagnose loading issues
    if not default_mapping:
        _LOGGER.warning("⚠️ Default YAML mapping file could not be loaded from: %s", default_file)
    if not custom_mapping:
        _LOGGER.debug("Custom YAML mapping file not found or empty: %s", custom_file)
    
    return merged


def merge_yaml_mappings(default_mapping: Dict[str, Any], custom_mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Merge default and custom mappings, with custom mappings taking precedence.
    
    Args:
        default_mapping: Default mapping configuration
        custom_mapping: Custom mapping configuration
        
    Returns:
        Merged mapping configuration with only usage_id_mappings and advanced_rules
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
        _LOGGER.error("Name patterns is not a list: %s", type(name_patterns))
        name_patterns = []
    
    merged['name_patterns'] = name_patterns
    if 'custom_name_patterns' in custom_mapping and isinstance(custom_mapping['custom_name_patterns'], list):
        merged['name_patterns'].extend(custom_mapping['custom_name_patterns'])
    
    # Add default mapping if present
    if 'default_mapping' in default_mapping and isinstance(default_mapping['default_mapping'], dict):
        merged['default_mapping'] = default_mapping['default_mapping']
    
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
        - default_mapping: Fallback mapping
    """
    try:
        # Load and merge YAML mappings
        yaml_config = load_yaml_mappings(base_path)
        
        if yaml_config:
            _LOGGER.info("Successfully loaded YAML mappings")
            _LOGGER.debug("Advanced rules count: %d", len(yaml_config.get('advanced_rules', [])))
            _LOGGER.debug("Usage ID mappings count: %d", len(yaml_config.get('usage_id_mappings', {})))
            _LOGGER.debug("Name patterns count: %d", len(yaml_config.get('name_patterns', [])))
            return yaml_config
        else:
            _LOGGER.warning("No YAML mappings found, using empty configuration")
            return {
                'advanced_rules': [],
                'usage_id_mappings': {},
                'name_patterns': [],
                'default_mapping': {
                    'ha_entity': 'sensor',
                    'ha_subtype': 'unknown',
                    'justification': 'Default fallback mapping for unknown devices'
                }
            }
            
    except Exception as e:
        _LOGGER.error("Failed to load YAML mappings: %s", e)
        _LOGGER.warning("Falling back to minimal configuration")
        return {
            'advanced_rules': [],
            'usage_id_mappings': {},
            'name_patterns': [],
            'default_mapping': {
                'ha_entity': 'sensor',
                'ha_subtype': 'unknown',
                'justification': 'Default fallback mapping for unknown devices'
            }
        }
