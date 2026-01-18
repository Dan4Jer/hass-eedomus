#!/usr/bin/env python3
"""
Final optimization of remaining sensor:unknown devices based on usage_id patterns
"""

import re
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_device_table(filename: str) -> List[Dict[str, Any]]:
    """Load device table from markdown file"""
    devices = []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        logger.error(f"File {filename} not found")
        return []
    
    # Skip header lines
    header_lines = 0
    for i, line in enumerate(lines):
        if line.startswith('| parent_id/periph_id'):
            header_lines = i + 1
            break
    
    # Parse device lines
    for line in lines[header_lines:]:
        if line.strip() and line.startswith('|'):
            # Parse markdown table line
            parts = line.split('|')
            if len(parts) >= 6:
                device = {
                    'parent_id/periph_id': parts[1].strip(),
                    'usage_id:usage_name': parts[2].strip(),
                    'supported_classes': parts[3].strip(),
                    'ha_type:ha_subtype': parts[4].strip(),
                    'name': parts[5].strip(),
                    'room': parts[6].strip() if len(parts) > 6 else ''
                }
                devices.append(device)
    
    logger.info(f"Loaded {len(devices)} devices from {filename}")
    return devices

def apply_final_mappings(devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply final mappings based on usage_id patterns"""
    
    # Define final mapping rules based on our analysis
    mapping_rules = {
        # Temperature setpoints should be climate entities
        '15': {
            'ha_entity': 'climate',
            'ha_subtype': 'temperature_setpoint',
            'reason': 'Temperature setpoint control - should be climate entity'
        },
        # Camera entities
        '0': {
            'ha_entity': 'camera',
            'ha_subtype': 'generic',
            'reason': 'Camera entity - should be camera platform'
        },
        # Camera privacy
        '50': {
            'ha_entity': 'switch',
            'ha_subtype': 'privacy',
            'reason': 'Camera privacy control - should be switch'
        },
        # Image capture
        '127': {
            'ha_entity': 'button',
            'ha_subtype': 'camera_snapshot',
            'reason': 'Image capture - should be button for snapshot'
        },
        # Humidity sensors
        '22': {
            'ha_entity': 'sensor',
            'ha_subtype': 'humidity',
            'reason': 'Humidity sensor - standard humidity mapping'
        },
        # Shutter centralization
        '42': {
            'ha_entity': 'select',
            'ha_subtype': 'shutter_group',
            'reason': 'Shutter group control - should be select entity'
        }
    }
    
    fixed_count = 0
    
    for device in devices:
        if device['ha_type:ha_subtype'] == 'sensor:unknown':
            usage_info = device['usage_id:usage_name']
            
            # Extract usage_id
            if ':' in usage_info:
                usage_id = usage_info.split(':')[0]
            else:
                usage_id = usage_info
            
            # Apply mapping if rule exists
            if usage_id in mapping_rules:
                rule = mapping_rules[usage_id]
                device['ha_type:ha_subtype'] = f"{rule['ha_entity']}:{rule['ha_subtype']}"
                logger.info(f"✅ Fixed {device['name']} ({device['parent_id/periph_id']}): {rule['reason']}")
                fixed_count += 1
    
    logger.info(f"Applied final mappings to {fixed_count} devices")
    return devices

def save_final_optimized_table(devices: List[Dict[str, Any]], filename: str):
    """Save final optimized devices to markdown table"""
    
    # Sort devices by periph_id
    def sort_key(device):
        try:
            periph_id = device['parent_id/periph_id'].split('/')[0]
            return int(periph_id) if periph_id.isdigit() else 0
        except:
            return 0
    
    devices.sort(key=sort_key)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("""# Complete Eedomus Device Table - Fully Optimized Mappings

| parent_id/periph_id | usage_id:usage_name | SUPPORTED_CLASSES | ha_type:ha_subtype | name | room |
|---------------------|---------------------|-------------------|-------------------|------|------|
""")
        
        for device in devices:
            f.write(f"| {device['parent_id/periph_id']} | {device['usage_id:usage_name']} | {device['supported_classes']} | {device['ha_type:ha_subtype']} | {device['name']} | {device['room']} |\n")
    
    logger.info(f"Saved fully optimized table to {filename}")

def main():
    """Main function"""
    logger.info("🚀 Starting final mapping optimization")
    
    # Load devices
    devices = load_device_table('device_table_final_optimized.md')
    
    if not devices:
        logger.error("❌ No devices loaded")
        return 1
    
    # Count current unknown sensors
    current_unknown = sum(1 for d in devices if d['ha_type:ha_subtype'] == 'sensor:unknown')
    logger.info(f"Current sensor:unknown count: {current_unknown}")
    
    # Apply final mappings
    fixed_devices = apply_final_mappings(devices)
    
    # Save final table
    save_final_optimized_table(fixed_devices, 'device_table_fully_optimized.md')
    
    # Count remaining unknown sensors
    remaining_unknown = sum(1 for d in fixed_devices if d['ha_type:ha_subtype'] == 'sensor:unknown')
    
    if remaining_unknown == 0:
        logger.info("🎉 All sensor:unknown devices have been optimized!")
    else:
        logger.info(f"⚠️  {remaining_unknown} devices still mapped as sensor:unknown")
    
    logger.info(f"✅ Final optimization complete!")
    logger.info("📄 Saved fully optimized table to device_table_fully_optimized.md")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())