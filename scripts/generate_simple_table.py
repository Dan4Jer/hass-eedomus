#!/usr/bin/env python3
"""
Eedomus Simple Device Table Generator

Generates a simple but complete device table from eedomus API for documentation
and debugging purposes. This script connects to the eedomus API and creates:
1. A Markdown table (simple_device_table.md) with all devices
2. A JSON file (simple_device_data.json) with complete raw data

Usage:
    python generate_simple_table.py

Or with environment variables:
    export EEDOMUS_API_HOST="your_eedomus_box_ip"
    export EEDOMUS_API_USER="your_api_username"
    export EEDOMUS_API_SECRET="your_api_secret"
    python generate_simple_table.py

Author: Dan4Jer
License: MIT
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
import re
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional


# =============================================================================
# CONFIGURATION
# =============================================================================

# Default eedomus API credentials (can be overridden by environment variables)
EEDOMUS_API_HOST = os.getenv("EEDOMUS_API_HOST", "192.168.1.5")
EEDOMUS_API_USER = os.getenv("EEDOMUS_API_USER", "")
EEDOMUS_API_SECRET = os.getenv("EEDOMUS_API_SECRET", "")

# API endpoints
API_PERIPH_LIST = "/api/get/json?action=get_periph_list"
API_PERIPH_VALUE_LIST = "/api/get/json?action=get_periph_value_list"
API_PERIPH_CARACT = "/api/get/json?action=get_periph.caract&periph_id="

# Output files
MARKDOWN_TABLE_FILE = "simple_device_table.md"
JSON_DATA_FILE = "simple_device_data.json"

# Device usage ID to Home Assistant entity mapping
USAGE_ID_MAPPING = {
    # Lights
    1: ("light", "dimmable"),
    
    # Switches
    2: ("switch", "basic"),
    4: ("switch", "basic"),
    
    # Sensors - Temperature
    7: ("sensor", "temperature"),
    
    # Binary Sensors
    37: ("binary_sensor", "motion"),
    27: ("binary_sensor", "smoke"),
    36: ("binary_sensor", "moisture"),
    
    # Covers/Shutters
    48: ("cover", "shutter"),
    
    # Climate
    19: ("climate", "fil_pilote"),
    20: ("climate", "fil_pilote"),
    
    # Energy meters
    26: ("sensor", "energy"),
    
    # Humidity
    8: ("sensor", "humidity"),
    
    # Pressure
    9: ("sensor", "pressure"),
    
    # Generic sensors
    25: ("sensor", "generic"),
    
    # Rule activation (usage_id 49)
    49: ("sensor", "unknown"),
    
    # Relays
    92: ("sensor", "unknown"),
}


# =============================================================================
# API FUNCTIONS
# =============================================================================

def build_api_url(endpoint: str) -> str:
    """Build complete API URL from endpoint."""
    return f"http://{EEDOMUS_API_HOST}{endpoint}"


def make_api_request(url: str, username: str, secret: str) -> Optional[Dict[str, Any]]:
    """
    Make a request to the eedomus API.
    
    Args:
        url: Complete API URL
        username: API username
        secret: API secret
        
    Returns:
        Dictionary with API response or None on error
    """
    try:
        # Create authentication string
        auth_string = f"{username}:{secret}"
        auth_bytes = auth_string.encode('utf-8')
        base64_auth = urllib.parse.quote(auth_string)
        
        # Build URL with authentication
        full_url = f"{url}&user={base64_auth}"
        
        # Make request
        req = urllib.request.Request(
            full_url,
            headers={'User-Agent': 'eedomus-table-generator/1.0'},
            method='GET'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
            
            # Try to decode as UTF-8, fall back to other encodings
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = data.decode('iso-8859-1')
                except UnicodeDecodeError:
                    try:
                        text = data.decode('latin-1')
                    except UnicodeDecodeError:
                        text = data.decode('utf-8', errors='replace')
            
            # Parse JSON response
            if text.strip().startswith('{'):
                return json.loads(text)
            else:
                # Sometimes the response is wrapped in a callback
                # Try to extract JSON from callback
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
                else:
                    print(f"⚠️  Unexpected response format: {text[:100]}...")
                    return None
                    
    except urllib.error.URLError as e:
        print(f"❌ API request failed: {e}")
        if hasattr(e, 'reason'):
            print(f"   Reason: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def get_periph_list(username: str, secret: str) -> Optional[List[Dict[str, Any]]]:
    """Get list of all peripherals from eedomus."""
    url = build_api_url(API_PERIPH_LIST)
    response = make_api_request(url, username, secret)
    
    if response and response.get('success') == 1:
        return response.get('body', [])
    else:
        print(f"❌ Failed to get peripheral list")
        if response:
            print(f"   Response: {response}")
        return None


def get_periph_value_list(username: str, secret: str) -> Optional[List[Dict[str, Any]]]:
    """Get values for all peripherals."""
    url = build_api_url(API_PERIPH_VALUE_LIST)
    response = make_api_request(url, username, secret)
    
    if response and response.get('success') == 1:
        return response.get('body', [])
    else:
        print(f"❌ Failed to get peripheral values")
        return None


def get_periph_caract(username: str, secret: str, periph_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed characteristics for a specific peripheral."""
    url = build_api_url(API_PERIPH_CARACT + periph_id)
    response = make_api_request(url, username, secret)
    
    if response and response.get('success') == 1:
        return response.get('body', {})
    else:
        return None


def get_all_periph_caract(username: str, secret: str, periph_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Get characteristics for all peripherals."""
    result = {}
    for periph_id in periph_ids:
        carac = get_periph_caract(username, secret, periph_id)
        if carac:
            result[periph_id] = carac
    return result


# =============================================================================
# DEVICE MAPPING FUNCTIONS
# =============================================================================

def simplify_zwave_classes(supported_classes: str) -> str:
    """
    Simplify Z-Wave classes to base numbers only.
    
    Example: "94:2,133:2,142:3" -> "94,133,142"
    """
    if not supported_classes:
        return ""
    
    # Extract just the numbers (before colons)
    classes = []
    for part in supported_classes.split(','):
        if ':' in part:
            classes.append(part.split(':')[0])
        else:
            classes.append(part)
    
    return ",".join(classes)


def map_usage_id(usage_id: Any) -> tuple:
    """
    Map usage_id to Home Assistant entity type and subtype.
    
    Args:
        usage_id: The usage ID (can be int or string)
        
    Returns:
        Tuple of (ha_entity, ha_subtype)
    """
    try:
        usage_id_int = int(usage_id)
        if usage_id_int in USAGE_ID_MAPPING:
            return USAGE_ID_MAPPING[usage_id_int]
    except (ValueError, TypeError):
        pass
    
    # Default mapping for unknown usage_ids
    return ("sensor", "unknown")


def map_device(device: Dict[str, Any], periph_value: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Map eedomus device data to a standardized format with HA mapping.
    
    Args:
        device: Device data from get_periph_list
        periph_value: Optional device values from get_periph_value_list
        
    Returns:
        Dictionary with mapped device information
    """
    periph_id = str(device.get('periph_id', ''))
    parent_periph_id = str(device.get('parent_periph_id', ''))
    name = device.get('name', 'Unknown')
    usage_id = device.get('usage_id', '')
    usage_name = device.get('usage_name', '')
    room_id = device.get('room_id', '')
    room_name = device.get('room_name', '')
    
    # Get HA entity mapping
    ha_entity, ha_subtype = map_usage_id(usage_id)
    
    # Get supported classes and simplify
    supported_classes = device.get('SUPPORTED_CLASSES', '')
    simplified_classes = simplify_zwave_classes(supported_classes)
    
    # Get last value info
    last_value = device.get('last_value', '')
    last_value_text = device.get('last_value_text', '')
    unit = device.get('unit', '')
    
    # Build the result
    result = {
        'periph_id': periph_id,
        'parent_periph_id': parent_periph_id,
        'name': name,
        'usage_id': usage_id,
        'usage_name': usage_name,
        'room_id': room_id,
        'room_name': room_name,
        'ha_entity': ha_entity,
        'ha_subtype': ha_subtype,
        'SUPPORTED_CLASSES': simplified_classes,
        'last_value': last_value,
        'last_value_text': last_value_text,
        'unit': unit,
        'justification': 'Mapped via usage_id'
    }
    
    # Add hierarchy info
    hierarchy = f"{parent_periph_id}/{periph_id}" if parent_periph_id else periph_id
    result['hierarchy'] = hierarchy
    
    # Add entity type display
    result['entity_display'] = f"{ha_entity}:{ha_subtype}"
    
    return result


# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

def generate_markdown_table(devices: List[Dict[str, Any]]) -> str:
    """
    Generate Markdown table from device data.
    
    Args:
        devices: List of mapped device dictionaries
        
    Returns:
        Markdown table as string
    """
    if not devices:
        return "No devices found.\n"
    
    # Sort by periph_id
    sorted_devices = sorted(devices, key=lambda x: int(x.get('periph_id', 0)))
    
    # Build markdown table
    lines = []
    lines.append("# Eedomus Device Mapping Table")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total devices: {len(devices)}")
    lines.append("")
    lines.append("| parent_id/periph_id | usage_id:usage_name | SUPPORTED_CLASSES | ha_type:ha_subtype | name | room |")
    lines.append("|-------------------|--------------------|------------------|-------------------|------|------|")
    
    for device in sorted_devices:
        hierarchy = device.get('hierarchy', '')
        usage = f"{device.get('usage_id', '')}:{device.get('usage_name', '')}"
        classes = device.get('SUPPORTED_CLASSES', '')
        entity = device.get('entity_display', '')
        name = device.get('name', '')
        room = device.get('room_name', '')
        
        # Escape pipes in values
        hierarchy = hierarchy.replace('|', '\\|')
        usage = usage.replace('|', '\\|')
        classes = classes.replace('|', '\\|')
        entity = entity.replace('|', '\\|')
        name = name.replace('|', '\\|')
        room = room.replace('|', '\\|')
        
        lines.append(f"| {hierarchy} | {usage} | {classes} | {entity} | {name} | {room} |")
    
    lines.append("")
    lines.append("## Statistics")
    lines.append("")
    
    # Count by entity type
    entity_counts = {}
    for device in devices:
        entity_type = device.get('ha_entity', 'unknown')
        entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
    
    lines.append("### Devices by Home Assistant Entity Type:")
    lines.append("")
    for entity_type, count in sorted(entity_counts.items()):
        lines.append(f"- **{entity_type}**: {count}")
    
    lines.append("")
    lines.append("### Unknown Devices:")
    lines.append("")
    unknown_devices = [d for d in devices if d.get('ha_subtype') == 'unknown']
    if unknown_devices:
        for device in unknown_devices:
            lines.append(f"- `{device.get('name', 'Unknown')}` (usage_id: {device.get('usage_id', '')}) - {device.get('entity_display', '')}")
    else:
        lines.append("✅ All devices have been mapped to Home Assistant entities.")
    
    return "\n".join(lines)


def save_markdown_table(devices: List[Dict[str, Any]], filename: str) -> bool:
    """Save markdown table to file."""
    try:
        markdown = generate_markdown_table(devices)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f"✅ Markdown table saved to: {filename}")
        return True
    except Exception as e:
        print(f"❌ Failed to save markdown table: {e}")
        return False


def save_json_data(devices: List[Dict[str, Any]], raw_data: Dict[str, Any], filename: str) -> bool:
    """Save complete data to JSON file."""
    try:
        # Add metadata
        output_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_devices': len(devices),
                'source': f'eedomus@{EEDOMUS_API_HOST}',
                'script_version': '1.0'
            },
            'devices': devices,
            'raw_data': raw_data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON data saved to: {filename}")
        return True
    except Exception as e:
        print(f"❌ Failed to save JSON data: {e}")
        return False


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """Main function to generate device tables."""
    print("🔍 Eedomus Simple Device Table Generator")
    print("=" * 50)
    print()
    
    # Check credentials
    if not EEDOMUS_API_USER or not EEDOMUS_API_SECRET:
        print("⚠️  API credentials not provided!")
        print()
        print("Please set environment variables:")
        print(f"  export EEDOMUS_API_HOST=\"{EEDOMUS_API_HOST}\"")
        print("  export EEDOMUS_API_USER=\"your_username\"")
        print("  export EEDOMUS_API_SECRET=\"your_secret\"")
        print()
        print("Or edit this script to set default credentials.")
        print()
        return False
    
    print(f"📊 Connecting to eedomus at: {EEDOMUS_API_HOST}")
    print(f"👤 User: {EEDOMUS_API_USER}")
    print()
    
    # Step 1: Get peripheral list
    print("📥 Step 1/3: Getting peripheral list...")
    periph_list = get_periph_list(EEDOMUS_API_USER, EEDOMUS_API_SECRET)
    
    if not periph_list:
        print("❌ Failed to get peripheral list")
        return False
    
    print(f"✅ Found {len(periph_list)} peripherals")
    print()
    
    # Step 2: Get peripheral values
    print("📥 Step 2/3: Getting peripheral values...")
    periph_values = get_periph_value_list(EEDOMUS_API_USER, EEDOMUS_API_SECRET)
    
    if not periph_values:
        print("⚠️  Failed to get peripheral values (continuing anyway)")
        periph_values = []
    else:
        print(f"✅ Found {len(periph_values)} peripheral values")
    print()
    
    # Step 3: Get peripheral characteristics (this can be slow for many devices)
    print("📥 Step 3/3: Getting peripheral characteristics...")
    periph_ids = [str(p.get('periph_id', '')) for p in periph_list if p.get('periph_id')]
    periph_caract = get_all_periph_caract(EEDOMUS_API_USER, EEDOMUS_API_SECRET, periph_ids)
    
    print(f"✅ Got characteristics for {len(periph_caract)} peripherals")
    print()
    
    # Process devices
    print("🔄 Processing devices...")
    mapped_devices = []
    
    # Create a lookup for values by periph_id
    values_by_id = {}
    if periph_values:
        for value_item in periph_values:
            periph_id = str(value_item.get('periph_id', ''))
            if periph_id:
                values_by_id[periph_id] = value_item
    
    for device in periph_list:
        periph_id = str(device.get('periph_id', ''))
        value_data = values_by_id.get(periph_id, {})
        
        # Merge device data with characteristics
        full_device = {**device, **periph_caract.get(periph_id, {})}
        
        mapped_device = map_device(full_device, value_data)
        mapped_devices.append(mapped_device)
    
    print(f"✅ Processed {len(mapped_devices)} devices")
    print()
    
    # Generate output
    print("📤 Generating output files...")
    
    # Save markdown table
    markdown_success = save_markdown_table(mapped_devices, MARKDOWN_TABLE_FILE)
    
    # Save JSON data
    raw_data = {
        'periph_list': periph_list,
        'periph_values': periph_values,
        'periph_caract': periph_caract
    }
    json_success = save_json_data(mapped_devices, raw_data, JSON_DATA_FILE)
    
    print()
    
    if markdown_success and json_success:
        print("✅ Table generation completed successfully!")
        print()
        print("📊 Summary:")
        print(f"   - Total devices: {len(mapped_devices)}")
        print(f"   - Markdown table: {MARKDOWN_TABLE_FILE}")
        print(f"   - JSON data: {JSON_DATA_FILE}")
        print()
        print("💡 Next steps:")
        print(f"   1. View the table: cat {MARKDOWN_TABLE_FILE}")
        print(f"   2. Analyze the data: python -c \"import json; data=json.load(open('{JSON_DATA_FILE}')); print(f'Total devices: {{len(data[\"devices\"])}}')\"")
        print()
        return True
    else:
        print("❌ Failed to generate some output files")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
