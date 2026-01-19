"""
Usage ID Mapping for eedomus devices.

Each usage_id represents a specific device type or function in the eedomus ecosystem.

Priority order for device mapping:
1. User custom mappings (from YAML)
2. Advanced rules (RGBW detection, parent-child relationships)
3. Usage ID mapping (USAGE_ID_MAPPING)
4. Name pattern matching
5. Default to sensor:unknown

Note: This mapping should be kept in sync with the device table generated
from the eedomus API to ensure consistency.

Note: Z-Wave class mapping (DEVICES_CLASS_MAPPING) is defined but not currently used.
      It's kept for potential future use or reference.
"""

import os
import logging
import re
from typing import Dict, Any, Optional, List
import yaml

# Initialize logger
_LOGGER = logging.getLogger(__name__)

# Import DOMAIN constant
from .const import DOMAIN

# Default YAML configuration paths
DEFAULT_MAPPING_FILE = "config/device_mapping.yaml"
CUSTOM_MAPPING_FILE = "config/custom_mapping.yaml"

# Global variables for mapping rules
DYNAMIC_ENTITY_PROPERTIES = {}
SPECIFIC_DEVICE_DYNAMIC_OVERRIDES = {}

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
        base_path: Base path where YAML files are located
        
    Returns:
        Merged mapping configuration
    """
    default_file = os.path.join(base_path, DEFAULT_MAPPING_FILE) if base_path else DEFAULT_MAPPING_FILE
    custom_file = os.path.join(base_path, CUSTOM_MAPPING_FILE) if base_path else CUSTOM_MAPPING_FILE
    
    # Load default mapping
    default_mapping = load_yaml_file(default_file) or {}
    
    # Load custom mapping
    custom_mapping = load_yaml_file(custom_file) or {}
    
    # Merge mappings (custom overrides default)
    merged = merge_yaml_mappings(default_mapping, custom_mapping)
    
    _LOGGER.info("Successfully merged YAML mappings (default: %s, custom: %s)", 
                bool(default_mapping), bool(custom_mapping))
    
    return merged

def merge_yaml_mappings(default_mapping: Dict[str, Any], custom_mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Merge default and custom mappings, with custom mappings taking precedence.
    
    Args:
        default_mapping: Default mapping configuration
        custom_mapping: Custom mapping configuration
        
    Returns:
        Merged mapping configuration
    """
    merged = default_mapping.copy()
    
    # Merge custom rules
    if 'custom_rules' in custom_mapping:
        custom_rules = custom_mapping['custom_rules']
        if 'advanced_rules' not in merged:
            merged['advanced_rules'] = []
        merged['advanced_rules'].extend(custom_rules)
    
    # Merge custom usage ID mappings
    if 'custom_usage_id_mappings' in custom_mapping:
        custom_usage_mappings = custom_mapping['custom_usage_id_mappings']
        if 'usage_id_mappings' not in merged:
            merged['usage_id_mappings'] = {}
        merged['usage_id_mappings'].update(custom_usage_mappings)
    
    # Merge custom name patterns
    if 'custom_name_patterns' in custom_mapping:
        custom_patterns = custom_mapping['custom_name_patterns']
        if 'name_patterns' not in merged:
            merged['name_patterns'] = []
        merged['name_patterns'].extend(custom_patterns)
    
    # Merge custom dynamic entity properties
    if 'custom_dynamic_entity_properties' in custom_mapping:
        custom_dynamic_props = custom_mapping['custom_dynamic_entity_properties']
        if 'dynamic_entity_properties' not in merged:
            merged['dynamic_entity_properties'] = {}
        merged['dynamic_entity_properties'].update(custom_dynamic_props)
    
    # Merge custom specific device dynamic overrides
    if 'custom_specific_device_dynamic_overrides' in custom_mapping:
        custom_device_overrides = custom_mapping['custom_specific_device_dynamic_overrides']
        if 'specific_device_dynamic_overrides' not in merged:
            merged['specific_device_dynamic_overrides'] = {}
        merged['specific_device_dynamic_overrides'].update(custom_device_overrides)
    
    return merged

def convert_yaml_to_mapping_rules(yaml_config: Dict[str, Any]) -> Dict[str, Any]:
    """Convert YAML configuration to the internal mapping rules format.
    
    Args:
        yaml_config: YAML configuration dictionary
        
    Returns:
        Dictionary with mapping rules in internal format
    """
    if not yaml_config:
        return {
            'ADVANCED_MAPPING_RULES': ADVANCED_MAPPING_RULES,
            'USAGE_ID_MAPPING': USAGE_ID_MAPPING
        }
    
    # Start with default rules
    advanced_rules = ADVANCED_MAPPING_RULES.copy()
    usage_id_mappings = USAGE_ID_MAPPING.copy()
    
    # Add YAML advanced rules
    if 'advanced_rules' in yaml_config:
        for rule in yaml_config['advanced_rules']:
            rule_name = rule['name'].lower().replace(' ', '_')
            
            # Convert YAML conditions to lambda function
            conditions = rule['conditions']
            
            def create_condition_function(conds):
                def condition_func(device_data, all_devices):
                    for cond in conds:
                        if 'usage_id' in cond:
                            if device_data.get('usage_id') != cond['usage_id']:
                                return False
                        if 'min_children' in cond:
                            child_count = sum(
                                1 for child_id, child in all_devices.items()
                                if child.get('parent_periph_id') == device_data.get('periph_id') 
                                and ('child_usage_id' not in cond or child.get('usage_id') == cond['child_usage_id'])
                            )
                            if child_count < cond['min_children']:
                                return False
                        if 'name' in cond:
                            if not re.search(cond['name'], device_data.get('name', '')):
                                return False
                    return True
                return condition_func
            
            advanced_rules[rule_name] = {
                'condition': create_condition_function(conditions),
                'ha_entity': rule['mapping']['ha_entity'],
                'ha_subtype': rule['mapping']['ha_subtype'],
                'justification': rule['mapping']['justification'],
                'device_class': rule['mapping'].get('device_class'),
                'icon': rule['mapping'].get('icon'),
                'is_dynamic': rule['mapping'].get('is_dynamic', False)
            }
            
            if 'child_mapping' in rule:
                advanced_rules[rule_name]['child_mapping'] = rule['child_mapping']
    
    # Add YAML usage ID mappings
    if 'usage_id_mappings' in yaml_config:
        for usage_id, mapping in yaml_config['usage_id_mappings'].items():
            usage_id_mappings[usage_id] = {
                'ha_entity': mapping['ha_entity'],
                'ha_subtype': mapping['ha_subtype'],
                'justification': mapping['justification'],
                'device_class': mapping.get('device_class'),
                'icon': mapping.get('icon'),
                'is_dynamic': mapping.get('is_dynamic', False)
            }
    
    return {
        'ADVANCED_MAPPING_RULES': advanced_rules,
        'USAGE_ID_MAPPING': usage_id_mappings
    }

# Advanced mapping rules for complex device detection
ADVANCED_MAPPING_RULES = {
    "rgbw_lamp_with_children": {
        "condition": lambda device_data, all_devices: (
            device_data.get("usage_id") == "1" and
            sum(
                1 for child_id, child in all_devices.items()
                if child.get("parent_periph_id") == device_data.get("periph_id") and child.get("usage_id") == "1"
            ) >= 4  # Au moins 4 enfants avec usage_id=1 (Rouge, Vert, Bleu, Blanc)
        ),
        "ha_entity": "light",
        "ha_subtype": "rgbw",
        "justification": "Lampe RGBW avec 4 enfants ou plus (Rouge, Vert, Bleu, Blanc)",
        "child_mapping": {
            "1": {"ha_entity": "light", "ha_subtype": "dimmable"}
        },
        "is_dynamic": True
    },
    "rgbw_lamp_flexible": {
        "condition": lambda device_data, all_devices: (
            # Strict RGBW detection based only on technical criteria
            device_data.get("usage_id") == "1" and
            (
                # Device has SUPPORTED_CLASSES containing RGBW-related classes
                any(rgbw_class in device_data.get("SUPPORTED_CLASSES", "") 
                    for rgbw_class in ["96:3", "96:4", "96"]) or
                # Device has PRODUCT_TYPE_ID known for RGBW devices
                device_data.get("PRODUCT_TYPE_ID") in ["2304", "2306"]
            )
        ),
        "ha_entity": "light",
        "ha_subtype": "rgbw",
        "justification": "Lampe RGBW détectée par critères techniques stricts (SUPPORTED_CLASSES ou PRODUCT_TYPE_ID)",
        "child_mapping": {
            "1": {"ha_entity": "light", "ha_subtype": "dimmable"}
        },
        "is_dynamic": True
    },
    "rgbw_lamp_specific_devices": {
        "condition": lambda device_data, all_devices: (
            device_data.get("periph_id") in ["1269454"]  # Add specific device IDs here
        ),
        "ha_entity": "light",
        "ha_subtype": "rgbw",
        "justification": "Lampe RGBW spécifique - périphérique connu nécessitant un mapping RGBW",
        "child_mapping": {
            "1": {"ha_entity": "light", "ha_subtype": "dimmable"}
        },
        "is_dynamic": True
    },
    "shutter_with_tilt": {
        "condition": lambda device_data, all_devices: (
            device_data.get("usage_id") == "48" and
            any(
                child.get("usage_id") == "48" 
                for child_id, child in all_devices.items()
                if child.get("parent_periph_id") == device_data.get("periph_id")
            )
        ),
        "ha_entity": "cover",
        "ha_subtype": "shutter",
        "justification": "Volet avec contrôle d'inclinaison des lamelles",
        "child_mapping": {
            "48": {"ha_entity": "cover", "ha_subtype": "shutter"}
        },
        "is_dynamic": True
    }
}

USAGE_ID_MAPPING = {
    # Format :
    # "usage_id": { #Si on a rien trouvé dans les class Zwave... on bricole avec le usage_id pour trouver le bon mapping
    #     "ha_entity": "type_d_entité_HA",
    #     "ha_subtype": "sous-type_HA" (optionnel),
    #     "justification": "explication claire du mapping"
    # },
    "0": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Unknown device type - default to switch",
        "is_dynamic": True
    },
    "1": {
        "ha_entity": "light",
        "ha_subtype": "dimmable",
        "justification": "Light device - usage_id=1 typically represents lamps and lighting",
        "advanced_rules": ["rgbw_lamp_with_children", "rgbw_lamp_flexible"],
        "is_dynamic": True
    },
    "2": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Generic switch - usage_id=2 for basic on/off devices",
        "is_dynamic": True
    },
    "4": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Generic switch - usage_id=4 for electrical appliances",
        "is_dynamic": True
    },
    "7": {
        "ha_entity": "sensor",
        "ha_subtype": "temperature",
        "justification": "Temperature sensor - usage_id=7 for temperature monitoring",
        "is_dynamic": False
    },
    "14": {
        "ha_entity": "select",
        "ha_subtype": "shutter_group",
        "justification": "Virtual device for shutter grouping and Alexa integration",
        "is_dynamic": False
    },
    "15": {
        "ha_entity": "climate",
        "ha_subtype": "temperature_setpoint",
        "justification": "Virtual thermostat for heating setpoint control",
        "is_dynamic": False
    },
    "18": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Current day information from eedomus",
        "is_dynamic": False
    },
    "19": {
        "ha_entity": "climate",
        "ha_subtype": "fil_pilote",
        "justification": "Fil pilote heating system control - usage_id=19",
        "is_dynamic": False
    },
    "20": {
        "ha_entity": "climate",
        "ha_subtype": "fil_pilote",
        "justification": "Fil pilote heating system control - usage_id=20",
        "is_dynamic": False
    },
    "22": {
        "ha_entity": "sensor",
        "ha_subtype": "moisture",
        "justification": "Moisture sensor - Sonoff SNZB-02D/SNZB-02P via Zigate",
        "is_dynamic": False
    },
    "23": {
        "ha_entity": "sensor",
        "ha_subtype": "cpu",
        "justification": "CPU usage monitor - eedomus internal system monitoring",
        "is_dynamic": False
    },
    "24": {
        "ha_entity": "sensor",
        "ha_subtype": "illuminance",
        "justification": "Luminosity sensor - usage_id=24 for light level monitoring",
        "is_dynamic": False
    },
    "26": {
        "ha_entity": "sensor",
        "ha_subtype": "energy",
        "justification": "Energy consumption meter - virtual eedomus consumption counter",
        "is_dynamic": False
    },
    "27": {
        "ha_entity": "binary_sensor",
        "ha_subtype": "smoke",
        "justification": "Smoke detector - usage_id=27 for fire/smoke detection",
        "is_dynamic": True
    },
    "34": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Day phase information from eedomus",
        "is_dynamic": False
    },
    "35": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Miscellaneous eedomus app data (sun elevation, azimuth, etc.)",
        "is_dynamic": False
    },
    "36": {
        "ha_entity": "binary_sensor",
        "ha_subtype": "moisture",
        "justification": "Flood/water detector - usage_id=36 for water leakage detection",
        "is_dynamic": True
    },
    "37": {
        "ha_entity": "binary_sensor",
        "ha_subtype": "motion",
        "justification": "Motion detector - usage_id=37 for movement detection",
        "is_dynamic": True
    },
    "38": {
        "ha_entity": "climate",
        "ha_subtype": "fil_pilote",
        "justification": "Fil pilote heating control - usage_id=38",
        "is_dynamic": False
    },
    "42": {
        "ha_entity": "select",
        "ha_subtype": "shutter_group",
        "justification": "Shutter centralization control - eedomus virtual device",
        "is_dynamic": False
    },
    "43": {
        "ha_entity": "select",
        "ha_subtype": "automation",
        "justification": "Eedomus scene trigger - virtual device for automation",
        "is_dynamic": False
    },
    "48": {
        "ha_entity": "cover",
        "ha_subtype": "shutter",
        "justification": "Shutter/blind control - usage_id=48 for window coverings",
        "advanced_rules": ["shutter_with_tilt"],
        "is_dynamic": True
    },
    "50": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Camera privacy control - usage_id=50 for camera intimacy",
        "is_dynamic": True
    },
    "52": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Sonoff switch/remote control - usage_id=52",
        "is_dynamic": True
    },
    "82": {
        "ha_entity": "select",
        "ha_subtype": "color_preset",
        "justification": "RGBW color preset selection - usage_id=82",
        "is_dynamic": False
    },
    "84": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Calendar day type information from eedomus",
        "is_dynamic": False
    },
    "114": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Network detection status - eedomus app data",
        "is_dynamic": False
    },
    "127": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Miscellaneous text data - usage_id=127",
        "is_dynamic": False
    },
    # Additional common usage_ids that may be encountered
    "999": {
        "ha_entity": "select",
        "ha_subtype": "virtual",
        "justification": "Virtual device - eedomus scene triggers and automation",
        "is_dynamic": False
    },
}


# Common device patterns for additional mapping logic
COMMON_DEVICE_PATTERNS = {
    "motion": ["mouvement", "motion", "détection"],
    "smoke": ["fumée", "smoke", "incendie"],
    "flood": ["inondation", "flood", "eau"],
    "temperature": ["température", "temperature", "thermostat"],
    "shutter": ["volet", "shutter", "store", "rideau"],
    "light": ["lumière", "light", "lampe", "spot"],
}

DEVICES_CLASS_MAPPING = {
    # Format :
    # "classe_zwave": {
    #     "GENERIC": [liste des valeurs GENERIC applicables],
    #     "PRODUCT_TYPE_ID": {
    #         "valeur_PRODUCT_TYPE_ID": {
    #             "ha_entity": "type_d_entité_HA",
    #             "ha_subtype": "sous-type_HA" (optionnel),
    #             "justification": "Explication spécifique au PRODUCT_TYPE_ID",
    #         },
    #     },
    #     "ha_entity": "type_d_entité_HA",  # Valeur par défaut si PRODUCT_TYPE_ID non trouvé
    #     "ha_subtype": "sous-type_HA" (optionnel),
    #     "exceptions": [
    #         {
    #             "condition": "description_de_la_condition_d_exception",
    #             "ha_entity": "type_d_entité_HA_corrigé",
    #             "ha_subtype": "sous-type_HA_corrigé" (optionnel),
    #             "example_periph_id": ["exemple1", "exemple2"],
    #         },
    #     ],
    #     "justification": "Explication de la règle",
    # },
    # --- Notification (94) ---
    "94": {
        "GENERIC": ["11"],
        "PRODUCT_TYPE_ID": {
            "258": {
                "ha_entity": "light",
                "ha_subtype": "dimmable",
                "justification": "Classe 94 (Notification) with GENERIC=11 and PRODUCT_TYPE_ID=258 maps to light for Spots Cuisine (periph_id=1145719)",
            },
            "3": {
                "ha_entity": "cover",
                "ha_subtype": "shutter",
                "justification": "Classe 94 (Notification) with GENERIC=11 and PRODUCT_TYPE_ID=3 maps to cover for Volet parent (periph_id=3445481)",
            },
        },
        "ha_entity": "light",
        "ha_subtype": "dimmable",
        "exceptions": [
            {
                "condition": "periph_id == '3445481'",
                "ha_entity": "cover",
                "ha_subtype": "shutter",
                "justification": "Volet parent Chambre parent - forcer mapping à cover malgré class 94",
            },
        ],
        "justification": "Classe 94 (Notification) with GENERIC=11 defaults to light/dimmable",
    },
    # --- SwitchMultilevel (38) ---
    "38": {
        "GENERIC": ["11"],
        "PRODUCT_TYPE_ID": {
            "770": {  # Volets Fibaro (ex: FGR-223)
                "ha_entity": "cover",
                "ha_subtype": "shutter",
                "justification": "PRODUCT_TYPE_ID=770 corresponds to Fibaro FGR-223 shutters.",
            },
            "2304": {  # Modules RGBW Fibaro (ex: FGWPE/F-102)
                "ha_entity": "light",
                "ha_subtype": "rgbw",
                "justification": "PRODUCT_TYPE_ID=2304 correspond aux modules RGBW Fibaro (ex:  FGRGBWM-441-RGBW).",
            },
            "2306": {  # Modules RGBW Fibaro
                "ha_entity": "light",
                "ha_subtype": "rgbw",
                "justification": "PRODUCT_TYPE_ID=2306 correspond aux modules RGBW Fibaro - RGBW Controller 2 (FGRGBW-442).",
            },
            "258": {  # Interrupteurs muraux Fibaro (ex: FGS-224)
                "ha_entity": "switch",
                "ha_subtype": None,
                "exceptions": [
                    {
                        "condition": "usage_id == '1' or usage_id == '26'",
                        "ha_entity": "light",
                        "ha_subtype": "dimmable",
                        "justification": "PRODUCT_TYPE_ID=258 with usage_id=1 or 26 should be light (spots/lamps), not switch",
                        "example_periph_id": ["1145719", "1145721"],
                    },
                ],
                "justification": "PRODUCT_TYPE_ID=258 correspond aux interrupteurs muraux Fibaro (ex: FGS-224).",
            },
        },
        "ha_entity": "light",
        "ha_subtype": "dimmable",
        "exceptions": [
            {
                "condition": "SPECIFIC=6 (volets)",
                "ha_entity": "cover",
                "ha_subtype": "shutter",
                "example_periph_id": ["1078123", "1078129", "1078120", "1078843"],
            },
            {
                "condition": "SUPPORTED_CLASSES contient '96:3' (RGB)",
                "ha_entity": "light",
                "ha_subtype": "rgbw",
                "example_periph_id": [
                    "1077644",
                    "1077645",
                    "1077646",
                    "1077647",
                    "1077648",
                ],
            },
        ],
        "justification": "Classe 38 = SwitchMultilevel. GENERIC=11 pour les lumières/volets. PRODUCT_TYPE_ID permet de distinguer les modèles spécifiques (ex: volets Fibaro, modules RGBW).",
    },
    # --- SwitchBinary (37) ---
    "37": {
        "GENERIC": ["10", "11"],
        "PRODUCT_TYPE_ID": {
            "2049": {  # Capteurs de mouvement Fibaro (ex: FGMS-001)
                "ha_entity": "binary_sensor",
                "ha_subtype": "motion",
                "justification": "PRODUCT_TYPE_ID=2049 correspond aux capteurs de mouvement Fibaro (ex: FGMS-001).",
            },
            "256": {  # Prises intelligentes (ex: FGWP102)
                "ha_entity": "switch",
                "ha_subtype": None,
                "justification": "PRODUCT_TYPE_ID=256 correspond aux prises intelligentes (ex: FGWP102).",
            },
            "3074": {  # Détecteurs de fumée Fibaro (ex: FGSD-002)
                "ha_entity": "binary_sensor",
                "ha_subtype": "smoke",
                "justification": "PRODUCT_TYPE_ID=3074 correspond aux détecteurs de fumée Fibaro (ex: FGSD-002).",
            },
        },
        "ha_entity": "switch",
        "ha_subtype": None,
        "exceptions": [
            {
                "condition": "usage_id=37 (Motion detection)",
                "ha_entity": "binary_sensor",
                "ha_subtype": "motion",
                "example_periph_id": ["1090995"],  # Oeil de chat
                "justification": "usage_id=37 indicates motion detection sensor regardless of Z-Wave class",
            },
            {
                "condition": "GENERIC=7 (SensorNotification) + SPECIFIC=1 (Mouvement)",
                "ha_entity": "binary_sensor",
                "ha_subtype": "motion",
                "example_periph_id": ["1090995"],
            },
            {
                "condition": "Nom contient 'Inondation' ou 'Fumée'",
                "ha_entity": "binary_sensor",
                "ha_subtype": "flood",
                "example_periph_id": ["3415417"],  # Inondation seulement
            },
            {
                "condition": "Nom contient 'Fumée' ou 'Smoke'",
                "ha_entity": "binary_sensor",
                "ha_subtype": "smoke",
                "example_periph_id": ["2486570"],  # Fumée seulement
            },
        ],
        "justification": "Classe 37 = SwitchBinary. GENERIC=10/11 pour les interrupteurs. PRODUCT_TYPE_ID permet de distinguer les capteurs (ex: mouvement) des interrupteurs.",
    },
    # --- SensorMultilevel (49) ---
    "49": {
        "GENERIC": [],
        "PRODUCT_TYPE_ID": {
            "3": {  # Capteurs de température extérieurs (ex: FGK-101)
                "ha_entity": "sensor",
                "ha_subtype": "temperature",
                "justification": "PRODUCT_TYPE_ID=3 correspond aux capteurs de température extérieurs (ex: FGK-101).",
            },
            "2049": {  # Capteurs multi-fonctions (ex: FGMS-001)
                "ha_entity": "sensor",
                "ha_subtype": "temperature",  # ou "illuminance" selon le canal
                "justification": "PRODUCT_TYPE_ID=2049 correspond aux capteurs multi-fonctions (ex: FGMS-001). Le sous-type dépend du canal.",
            },
        },
        "ha_entity": "sensor",
        "ha_subtype": None,
        "exceptions": [
            {
                "condition": "SPECIFIC=1 (Température) ou unit='°C'",
                "ha_entity": "sensor",
                "ha_subtype": "temperature",
                "example_periph_id": ["1090996", "1077374"],
            },
            {
                "condition": "SPECIFIC=3 (Luminosité) ou unit='Lux'",
                "ha_entity": "sensor",
                "ha_subtype": "illuminance",
                "example_periph_id": ["1090999", "1091579"],
            },
            {
                "condition": "unit='%' et nom contient 'Humidité'",
                "ha_entity": "sensor",
                "ha_subtype": "humidity",
                "example_periph_id": ["3381721", "3387331"],
            },
            {
                "condition": "nom contient 'Consigne' et unit='°C'",
                "ha_entity": "climate",
                "ha_subtype": "temperature_setpoint",
                "example_periph_id": ["1252440", "1252441", "1252442"],
                "justification": "Capteurs de consigne de température qui devraient être des thermostats.",
            },
        ],
        "justification": "Classe 49 = SensorMultilevel. PRODUCT_TYPE_ID permet de distinguer les capteurs spécifiques (ex: FGK-101 pour la température).",
    },
    # --- Meter (32, 50) ---
    "32": {
        "GENERIC": [],
        "ha_entity": "sensor",
        "ha_subtype": "energy",
        "exceptions": [
            {
                "condition": "usage_id=37 (Motion sensor)",
                "ha_entity": "binary_sensor",
                "ha_subtype": "motion",
                "example_periph_id": ["1090995"],  # Mouvement Oeil de chat
                "justification": "Classe 32 avec usage_id=37 est un capteur de mouvement, pas d'énergie",
            }
        ],
        "justification": "Classe 32 = Meter (énergie). Sauf usage_id=37 (mouvement).",
    },
    "50": {
        "GENERIC": [],
        "ha_entity": "sensor",
        "ha_subtype": "power",
        "exceptions": [],
        "justification": "Classe 50 = Meter (puissance). Toujours mappé à un capteur de puissance (W).",
    },
    # --- Thermostat SetPoint (67) ---
    "67": {
        "GENERIC": ["8"],
        "PRODUCT_TYPE_ID": {
            "4": {  # Têtes thermostatiques (ex: FGT-001)
                "ha_entity": "climate",
                "ha_subtype": "thermostat",
                "justification": "PRODUCT_TYPE_ID=4 correspond aux têtes thermostatiques (ex: FGT-001).",
            },
        },
        "ha_entity": "climate",
        "ha_subtype": "thermostat",
        "exceptions": [],
        "justification": "Classe 67 = Thermostat SetPoint. GENERIC=8 pour les thermostats. PRODUCT_TYPE_ID=4 pour les têtes thermostatiques.",
    },
    # --- SensorBinary (48) ---
    "48": {
        "GENERIC": ["7"],
        "PRODUCT_TYPE_ID": {
            "2049": {  # Capteurs de mouvement (ex: FGMS-001)
                "ha_entity": "binary_sensor",
                "ha_subtype": "motion",
                "justification": "PRODUCT_TYPE_ID=2049 correspond aux capteurs de mouvement (ex: FGMS-001).",
            },
            "3074": {  # Détecteurs de fumée (ex: FGSD-002)
                "ha_entity": "binary_sensor",
                "ha_subtype": "smoke",
                "justification": "PRODUCT_TYPE_ID=3074 correspond aux détecteurs de fumée (ex: FGSD-002).",
            },
        },
        "ha_entity": "binary_sensor",
        "ha_subtype": None,
        "exceptions": [
            {
                "condition": "SPECIFIC=1 (Mouvement)",
                "ha_entity": "binary_sensor",
                "ha_subtype": "motion",
                "example_periph_id": ["1090995"],
            },
            {
                "condition": "SPECIFIC=5 (Inondation)",
                "ha_entity": "binary_sensor",
                "ha_subtype": "flood",
                "example_periph_id": ["3415417"],
            },
        ],
        "justification": "Classe 48 = SensorBinary. GENERIC=7 pour les capteurs binaires. PRODUCT_TYPE_ID permet de distinguer les modèles (ex: FGMS-001 pour le mouvement).",
    },
    # --- Périphériques virtuels (PRODUCT_TYPE_ID=999) ---
    "999": {
        "GENERIC": [],
        "PRODUCT_TYPE_ID": {
            "999": {  # Périphériques virtuels eedomus
                "ha_entity": "select",
                "ha_subtype": "virtual",
                "justification": "PRODUCT_TYPE_ID=999 correspond aux périphériques virtuels eedomus pour déclenchement de scènes.",
            },
        },
        "ha_entity": "select",
        "ha_subtype": "virtual",
        "exceptions": [],
        "justification": "Périphériques virtuels eedomus (PRODUCT_TYPE_ID=999) pour scènes et automations.",
    },
    # --- Classes non fonctionnelles (ignorées) ---
    "132": {
        "ha_entity": None,
        "exceptions": [],
        "justification": "Classe 132 = WakeUp (non fonctionnelle).",
    },
    "114": {
        "ha_entity": None,
        "exceptions": [],
        "justification": "Classe 114 = Configuration (non fonctionnelle).",
    },
    "134": {
        "ha_entity": None,
        "exceptions": [],
        "justification": "Classe 134 = Version (non fonctionnelle).",
    },
    "115": {
        "ha_entity": None,
        "exceptions": [],
        "justification": "Classe 115 = ManufacturerSpecific (non fonctionnelle).",
    },
    "142": {
        "ha_entity": None,
        "exceptions": [],
        "justification": "Classe 142 = CRC-16 Encapsulation (non fonctionnelle).",
    },
}

def get_dynamic_entity_properties() -> Dict[str, bool]:
    """Get the dynamic entity properties."""
    return DYNAMIC_ENTITY_PROPERTIES

def get_specific_device_dynamic_overrides() -> Dict[str, bool]:
    """Get the specific device dynamic overrides."""
    return SPECIFIC_DEVICE_DYNAMIC_OVERRIDES


def load_and_merge_yaml_mappings(base_path: str = "") -> None:
    """Load YAML mappings and update global mapping rules.
    
    This function loads YAML configuration files and merges them with the default
    mapping rules. It should be called during initialization to allow user
    customizations to override default mappings.
    
    Args:
        base_path: Base path where YAML files are located
    """
    global ADVANCED_MAPPING_RULES, USAGE_ID_MAPPING, DYNAMIC_ENTITY_PROPERTIES, SPECIFIC_DEVICE_DYNAMIC_OVERRIDES
    
    try:
        # Load and merge YAML mappings
        yaml_config = load_yaml_mappings(base_path)
        
        if yaml_config:
            # Convert YAML to internal format
            mapping_rules = convert_yaml_to_mapping_rules(yaml_config)
            
            # Update global variables
            ADVANCED_MAPPING_RULES = mapping_rules['ADVANCED_MAPPING_RULES']
            USAGE_ID_MAPPING = mapping_rules['USAGE_ID_MAPPING']
            
            # Load dynamic entity properties
            DYNAMIC_ENTITY_PROPERTIES = yaml_config.get('dynamic_entity_properties', {})
            _LOGGER.info("Loaded dynamic entity properties: %s", DYNAMIC_ENTITY_PROPERTIES)
            
            # Load specific device dynamic overrides
            SPECIFIC_DEVICE_DYNAMIC_OVERRIDES = yaml_config.get('specific_device_dynamic_overrides', {})
            _LOGGER.info("Loaded specific device dynamic overrides: %s", SPECIFIC_DEVICE_DYNAMIC_OVERRIDES)
            
            _LOGGER.info("Successfully loaded and merged YAML mappings")
            _LOGGER.debug("Advanced rules count: %d", len(ADVANCED_MAPPING_RULES))
            _LOGGER.debug("Usage ID mappings count: %d", len(USAGE_ID_MAPPING))
            _LOGGER.debug("Dynamic entity properties: %s", DYNAMIC_ENTITY_PROPERTIES)
        else:
            _LOGGER.info("No YAML mappings found, using default mappings")
            # Set default dynamic properties
            DYNAMIC_ENTITY_PROPERTIES = {
                "light": True,
                "switch": True,
                "binary_sensor": True,
                "sensor": False,
                "climate": False,
                "cover": True,
                "select": False,
                "scene": False
            }
            _LOGGER.info("Using default dynamic entity properties: %s", DYNAMIC_ENTITY_PROPERTIES)
            
            # Set default specific device overrides
            SPECIFIC_DEVICE_DYNAMIC_OVERRIDES = {}
            _LOGGER.info("Using default specific device dynamic overrides: %s", SPECIFIC_DEVICE_DYNAMIC_OVERRIDES)
            
    except Exception as e:
        _LOGGER.error("Failed to load YAML mappings: %s", e)
        _LOGGER.info("Falling back to default mappings")
        # Set default dynamic properties on error
        DYNAMIC_ENTITY_PROPERTIES = {
            "light": True,
            "switch": True,
            "binary_sensor": True,
            "sensor": False,
            "climate": False,
            "cover": True,
            "select": False,
            "scene": False
        }
        
        # Set default specific device overrides on error
        SPECIFIC_DEVICE_DYNAMIC_OVERRIDES = {}


class EedomusConfigManager:
    """Configuration manager for eedomus device mapping and dynamic properties.
    
    Manages YAML-based configuration and provides access to configuration data.
    Note: This is not a frontend panel in HA 2026.02+, just a configuration manager.
    """
    
    def __init__(self, hass=None):
        """Initialize the configuration manager."""
        self.hass = hass
        self.current_config = "default"
        self.available_configs = ["default", "custom"]
        self.config_data = {
            "default": self._load_default_config(),
            "custom": self._load_custom_config()
        }
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load the default configuration from device_mapping.yaml."""
        try:
            config = load_yaml_mappings()
            if not config:
                config = {
                    "dynamic_entity_properties": {
                        "light": True,
                        "switch": True,
                        "binary_sensor": True,
                        "sensor": False,
                        "climate": False,
                        "cover": True,
                        "select": False,
                        "scene": False
                    },
                    "specific_device_dynamic_overrides": {}
                }
            return config
        except Exception as e:
            _LOGGER.error("Failed to load default config: %s", e)
            return {
                "dynamic_entity_properties": {
                    "light": True,
                    "switch": True,
                    "binary_sensor": True,
                    "sensor": False,
                    "climate": False,
                    "cover": True,
                    "select": False,
                    "scene": False
                },
                "specific_device_dynamic_overrides": {}
            }
    
    def _load_custom_config(self) -> Dict[str, Any]:
        """Load the custom configuration from custom_mapping.yaml."""
        try:
            # Load custom mappings
            custom_config = {}
            if os.path.exists(CUSTOM_MAPPING_FILE):
                with open(CUSTOM_MAPPING_FILE, 'r', encoding='utf-8') as file:
                    custom_config = yaml.safe_load(file) or {}
            
            # Merge with default to get complete structure
            default_config = self._load_default_config()
            merged_config = default_config.copy()
            
            # Apply custom overrides
            if 'custom_dynamic_entity_properties' in custom_config:
                merged_config['dynamic_entity_properties'].update(custom_config['custom_dynamic_entity_properties'])
            
            if 'custom_specific_device_dynamic_overrides' in custom_config:
                merged_config['specific_device_dynamic_overrides'].update(
                    custom_config['custom_specific_device_dynamic_overrides']
                )
            
            return merged_config
        except Exception as e:
            _LOGGER.error("Failed to load custom config: %s", e)
            return self._load_default_config()
    
    def switch_config(self, config_name: str) -> bool:
        """Switch to a different configuration."""
        if config_name in self.available_configs:
            self.current_config = config_name
            _LOGGER.info("Switched to %s configuration", config_name)
            return True
        return False
    
    def get_current_config(self) -> Dict[str, Any]:
        """Get the current active configuration."""
        return self.config_data[self.current_config]
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all available configurations."""
        return self.config_data
    
    def update_dynamic_entity_property(self, entity_type: str, is_dynamic: bool) -> bool:
        """Update dynamic property for an entity type."""
        try:
            config = self.get_current_config()
            config['dynamic_entity_properties'][entity_type] = is_dynamic
            _LOGGER.info("Updated dynamic property for %s: %s", entity_type, is_dynamic)
            return True
        except Exception as e:
            _LOGGER.error("Failed to update dynamic property: %s", e)
            return False
    
    def update_specific_device_override(self, periph_id: str, is_dynamic: bool) -> bool:
        """Update dynamic override for a specific device."""
        try:
            config = self.get_current_config()
            config['specific_device_dynamic_overrides'][periph_id] = is_dynamic
            _LOGGER.info("Updated dynamic override for device %s: %s", periph_id, is_dynamic)
            return True
        except Exception as e:
            _LOGGER.error("Failed to update device override: %s", e)
            return False
    
    def remove_specific_device_override(self, periph_id: str) -> bool:
        """Remove dynamic override for a specific device."""
        try:
            config = self.get_current_config()
            if periph_id in config['specific_device_dynamic_overrides']:
                del config['specific_device_dynamic_overrides'][periph_id]
                _LOGGER.info("Removed dynamic override for device %s", periph_id)
                return True
            return False
        except Exception as e:
            _LOGGER.error("Failed to remove device override: %s", e)
            return False
    
    def reload_configuration(self) -> bool:
        """Reload all configurations from files."""
        try:
            self.config_data = {
                "default": self._load_default_config(),
                "custom": self._load_custom_config()
            }
            _LOGGER.info("Reloaded configurations from files")
            return True
        except Exception as e:
            _LOGGER.error("Failed to reload configurations: %s", e)
            return False
    
    def get_device_dynamic_status(self, periph_id: str, ha_entity: str) -> Dict[str, Any]:
        """Get the dynamic status and reasoning for a specific device."""
        config = self.get_current_config()
        
        # Check specific overrides first
        if periph_id in config['specific_device_dynamic_overrides']:
            return {
                "is_dynamic": config['specific_device_dynamic_overrides'][periph_id],
                "reason": "specific_override",
                "source": "custom" if self.current_config == "custom" else "default"
            }
        
        # Check entity type properties
        if ha_entity in config['dynamic_entity_properties']:
            return {
                "is_dynamic": config['dynamic_entity_properties'][ha_entity],
                "reason": "entity_type",
                "source": "custom" if self.current_config == "custom" else "default"
            }
        
        # Fallback to default
        return {
            "is_dynamic": False,
            "reason": "fallback",
            "source": "default"
        }
    
    def get_all_devices_dynamic_status(self, coordinator_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get dynamic status for all devices."""
        devices_status = []
        config = self.get_current_config()
        
        for periph_id, periph_data in coordinator_data.items():
            if not isinstance(periph_data, dict) or "periph_id" not in periph_data:
                continue
                
            ha_entity = periph_data.get("ha_entity")
            device_status = self.get_device_dynamic_status(periph_id, ha_entity)
            device_status.update({
                "periph_id": periph_id,
                "name": periph_data.get("name", "Unknown"),
                "ha_entity": ha_entity,
                "usage_id": periph_data.get("usage_id")
            })
            devices_status.append(device_status)
        
        return devices_status


async def async_setup_config_manager(hass=None):
    """Set up the configuration manager.
    
    Note: This does not register a frontend panel in HA 2026.02+.
    It only sets up the configuration management system.
    """
    # Create configuration manager instance
    config_manager = EedomusConfigManager(hass)
    
    # Store in hass data for access from other components
    if hass is not None:
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        hass.data[DOMAIN]["config_manager"] = config_manager
        
        # Add method to update from options flow
        async def update_from_options(options: dict) -> None:
            """Update configuration from options flow changes."""
            try:
                if "yaml_mapping" in options:
                    yaml_config = options["yaml_mapping"]
                    if "custom_mapping_file" in yaml_config:
                        # Update the custom mapping file path
                        config_manager._custom_mapping_file = yaml_config["custom_mapping_file"]
                        _LOGGER.info("Updated custom mapping file path from options: %s", 
                                    config_manager._custom_mapping_file)
                        
                        # Reload configuration if needed
                        if yaml_config.get("reload_mapping", False):
                            await config_manager.reload_configuration()
                            _LOGGER.info("Configuration reloaded from options flow")
            except Exception as e:
                _LOGGER.error("Failed to update from options flow: %s", e)
        
        # Store update method for external access
        hass.data[DOMAIN]["update_config_from_options"] = update_from_options
    
    _LOGGER.info("Eedomus configuration manager initialized")
    _LOGGER.info("Configuration options:")
    _LOGGER.info("  1. YAML files (device_mapping.yaml, custom_mapping.yaml) - RECOMMENDED")
    _LOGGER.info("  2. Integration options flow (Settings → Devices & Services → Eedomus)")
    
    return config_manager
