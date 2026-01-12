USAGE_ID_MAPPING = {
    # Format :
    # "usage_id": { #Si on a rien trouvé dans les class Zwave... on bricole avec le usage_id pour trouver le bon mapping
    #     "ha_entity": "type_d_entité_HA",
    #     "ha_subtype": "sous-type_HA" (optionnel),
    # },
    "0": {  # ??? à vérifier type télécommande à pile + détecteur d'innondation
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Not Z-Wave using usage_id=0",
    },
    "1": {  # ??? à vérifier un sensor ?
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Not Z-Wave using usage_id=1",
    },
    "1?": {  # ou lampe 1+1+1+1+1+1
        "ha_entity": "light",
        "ha_subtype": "rgbw",
        "justification": "Not Z-Wave using usage_id=1",
    },
    "2": {  # ou 1
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Not Z-Wave using usage_id=2. Appareil électrique par défaut, mais peut être mappé comme sensor si c'est un consommateur.",
    },
    "4": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Not Z-Wave using usage_id=4.",
    },
    "7": {
        "ha_entity": "sensor",
        "ha_subtype": "temperature",
        "justification": "Not Z-Wave using usage_id=7. Standard temperature sensor.",
    },
    "23": {  # Internal indicators (messages, free space, etc.)
        "ha_entity": "sensor",
        "ha_subtype": "internal_indicator",
        "justification": "Eedomus internal indicators - messages, free space, etc.",
    },
    "14": {
        "ha_entity": "cover",
        "ha_subtype": "shutter",
        "justification": "Périphérique Virtuel eedomus type groupement de volet - devrait être cover, pas select",
    },
    "15": {
        "ha_entity": "climate",
        "ha_subtype": "temperature_setpoint",
        "justification": "Périphérique Virtuel Consigne de chauffage - thermostat virtuel",
    },
    "18": {
        "ha_entity": "texte",
        "ha_subtype": "",
        "justification": "Journée en cours eedomus",
    },
    "19": {  # fil pilote
        "ha_entity": "climate",
        "ha_subtype": "fil_pilote",
        "justification": "Consigne de température eedomus - chauffage fil pilote",
    },
    "20": {  # fil pilote
        "ha_entity": "climate",
        "ha_subtype": "fil_pilote",
        "justification": "Consigne de température eedomus - chauffage fil pilote",
    },
    "22": {
        "ha_entity": "sensor",
        "ha_subtype": "moisture",
        "justification": "Sonoff SNZB-02D/SNZB-02P via Zigate",
    },
    "23": {
        "ha_entity": "sensor",
        "ha_subtype": "cpu",
        "justification": "CPU box eedomus",
    },
    "24": {  # 1+1
        "ha_entity": "sensor",
        "ha_subtype": "luminosity",
        "justification": "Not Z-Wave using usage_id=24.",
    },
    "37": {  # Motion sensors
        "ha_entity": "binary_sensor",
        "ha_subtype": "motion",
        "justification": "Motion detection sensors - usage_id=37",
    },
    "26": {
        "ha_entity": "sensor",
        "ha_subtype": "",
        "justification": "compteur eedomus virtuel de consomation. Consomètre",
    },
    "27": {  # detecteur de fumée
        "ha_entity": "sensor",
        "ha_subtype": "smoke",
        "justification": "Not Z-Wave using usage_id=27.",
    },
    "34": {
        "ha_entity": "text",
        "ha_subtype": "",
        "justification": "Phase de la journée Eedomus",
    },
    "35": {
        "ha_entity": "sensor ou text",
        "ha_subtype": "",
        "justification": "App Eedomus ex Elevation soleil/Azimut soleil/Freebox/compteur temps de fonctionnement chauffage/appel api XIAOMI/saison",
    },
    "36": {
        "ha_entity": "binary_sensor",
        "ha_subtype": "moisture",
        "justification": "Inondation ",
    },
    # Removed duplicate mapping for usage_id=37 as it's already correctly mapped in USAGE_ID_MAPPING
    # "37": { #detecteur de mouvement
    #     "ha_entity": "sensor",
    #     "ha_subtype": "motion",
    #     "justification": "Not Z-Wave using usage_id=37."
    # },
    "38": {  # fil pilote
        "ha_entity": "climate",
        "ha_subtype": "",
        "justification": "Not Z-Wave using usage_id=38.",
    },
    "42": {
        "ha_entity": "select",
        "ha_subtype": "shutter_group",
        "justification": "Centralisation des ouvertures de volets eedomus",
    },
    "43": {
        "ha_entity": "select",
        "ha_subtype": "automation",
        "justification": "Scene Eedomus (Périphérique Virtuel) - type autre",
    },
    "48": {
        "ha_entity": "cover",
        "ha_subtype": "shutter",
        "justification": "Not Z-Wave using usage_id=48 for shutters.",
    },
    "50": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Intimité caméra ??? 1518731",
    },
    "52": {
        "ha_entity": "switch",
        "ha_subtype": "",
        "justification": "Interupteur Sonoff / Télécommande",
    },
    "82": {
        "ha_entity": "select",
        "ha_subtype": "color_preset",
        "justification": "Couleurs prédéfinies pour les devices RGBW - mappé comme select entity",
    },
    "84": {
        "ha_entity": "calendar ou texte",
        "ha_subtype": "",
        "justification": "Type de journée eedomus dans le calendrier",
    },
    "114": {
        "ha_entity": "sensor",
        "ha_subtype": "",
        "justification": "App Eedomus ex Détection réseau",
    },
    "127": {
        "ha_entity": "text",
        "ha_subtype": "",
        "justification": "Not Z-Wave using usage_id=127.",
    },
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
