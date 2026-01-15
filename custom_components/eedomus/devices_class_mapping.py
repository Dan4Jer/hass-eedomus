"""
Usage ID Mapping for eedomus devices.

This mapping is used when Z-Wave class mapping fails or is not available.
Each usage_id represents a specific device type or function in the eedomus ecosystem.

Priority order for device mapping:
1. Advanced rules (RGBW detection, parent-child relationships)
2. Usage ID mapping (USAGE_ID_MAPPING)
3. Z-Wave class mapping (DEVICES_CLASS_MAPPING)
4. Name pattern matching
5. Default to sensor:unknown

Note: This mapping should be kept in sync with the device table generated
from the eedomus API to ensure consistency.
"""

# Advanced mapping rules for complex device detection
ADVANCED_MAPPING_RULES = {
    "rgbw_lamp_with_children": {
        "condition": lambda device_data, all_devices: (
            device_data.get("usage_id") == "1" and
            any(
                child.get("usage_id") == "1" 
                for child_id, child in all_devices.items()
                if child.get("parent_periph_id") == device_data.get("periph_id")
            )
        ),
        "ha_entity": "light",
        "ha_subtype": "rgbw",
        "justification": "Lampe RGBW avec enfants (Rouge, Vert, Bleu, Blanc)",
        "child_mapping": {
            "1": {"ha_entity": "light", "ha_subtype": "dimmable"}
        }
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
        }
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
    },
    "1": {
        "ha_entity": "light",
        "ha_subtype": "dimmable",
        "justification": "Light device - usage_id=1 typically represents lamps and lighting",
        "advanced_rules": ["rgbw_lamp_with_children"]
    },
    "2": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Generic switch - usage_id=2 for basic on/off devices",
    },
    "4": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Generic switch - usage_id=4 for electrical appliances",
    },
    "7": {
        "ha_entity": "sensor",
        "ha_subtype": "temperature",
        "justification": "Temperature sensor - usage_id=7 for temperature monitoring",
    },
    "14": {
        "ha_entity": "select",
        "ha_subtype": "shutter_group",
        "justification": "Virtual device for shutter grouping and Alexa integration",
    },
    "15": {
        "ha_entity": "climate",
        "ha_subtype": "temperature_setpoint",
        "justification": "Virtual thermostat for heating setpoint control",
    },
    "18": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Current day information from eedomus",
    },
    "19": {
        "ha_entity": "climate",
        "ha_subtype": "fil_pilote",
        "justification": "Fil pilote heating system control - usage_id=19",
    },
    "20": {
        "ha_entity": "climate",
        "ha_subtype": "fil_pilote",
        "justification": "Fil pilote heating system control - usage_id=20",
    },
    "22": {
        "ha_entity": "sensor",
        "ha_subtype": "moisture",
        "justification": "Moisture sensor - Sonoff SNZB-02D/SNZB-02P via Zigate",
    },
    "23": {
        "ha_entity": "sensor",
        "ha_subtype": "cpu",
        "justification": "CPU usage monitor - eedomus internal system monitoring",
    },
    "24": {
        "ha_entity": "sensor",
        "ha_subtype": "illuminance",
        "justification": "Luminosity sensor - usage_id=24 for light level monitoring",
    },
    "26": {
        "ha_entity": "sensor",
        "ha_subtype": "energy",
        "justification": "Energy consumption meter - virtual eedomus consumption counter",
    },
    "27": {
        "ha_entity": "binary_sensor",
        "ha_subtype": "smoke",
        "justification": "Smoke detector - usage_id=27 for fire/smoke detection",
    },
    "34": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Day phase information from eedomus",
    },
    "35": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Miscellaneous eedomus app data (sun elevation, azimuth, etc.)",
    },
    "36": {
        "ha_entity": "binary_sensor",
        "ha_subtype": "moisture",
        "justification": "Flood/water detector - usage_id=36 for water leakage detection",
    },
    "37": {
        "ha_entity": "binary_sensor",
        "ha_subtype": "motion",
        "justification": "Motion detector - usage_id=37 for movement detection",
    },
    "38": {
        "ha_entity": "climate",
        "ha_subtype": "fil_pilote",
        "justification": "Fil pilote heating control - usage_id=38",
    },
    "42": {
        "ha_entity": "select",
        "ha_subtype": "shutter_group",
        "justification": "Shutter centralization control - eedomus virtual device",
    },
    "43": {
        "ha_entity": "select",
        "ha_subtype": "automation",
        "justification": "Eedomus scene trigger - virtual device for automation",
    },
    "48": {
        "ha_entity": "cover",
        "ha_subtype": "shutter",
        "justification": "Shutter/blind control - usage_id=48 for window coverings",
        "advanced_rules": ["shutter_with_tilt"]
    },
    "50": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Camera privacy control - usage_id=50 for camera intimacy",
    },
    "52": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Sonoff switch/remote control - usage_id=52",
    },
    "82": {
        "ha_entity": "select",
        "ha_subtype": "color_preset",
        "justification": "RGBW color preset selection - usage_id=82",
    },
    "84": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Calendar day type information from eedomus",
    },
    "114": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Network detection status - eedomus app data",
    },
    "127": {
        "ha_entity": "sensor",
        "ha_subtype": "text",
        "justification": "Miscellaneous text data - usage_id=127",
    },
    # Additional common usage_ids that may be encountered
    "999": {
        "ha_entity": "select",
        "ha_subtype": "virtual",
        "justification": "Virtual device - eedomus scene triggers and automation",
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
