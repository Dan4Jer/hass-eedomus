# Configuration de l'intégration Eedomus

## Introduction

L'intégration Eedomus offre deux modes de configuration pour adapter les mappings entre vos devices Eedomus et Home Assistant :

1. **Mode Interface Graphique** - Pour une configuration visuelle et intuitive
2. **Mode Éditeur YAML** - Pour une configuration avancée avec contrôle total

## Accéder à la Configuration

1. Allez dans **Paramètres → Appareils → Eedomus → Options**
2. **Sélectionnez le mode de configuration** :
   - **Interface Graphique** : Pour une configuration visuelle et intuitive
   - **Éditeur YAML** : Pour une configuration avancée avec contrôle total
3. Cliquez sur **Soumettre** pour accéder à l'interface choisie

## Mode Interface Graphique

### Ajouter un Device

1. Cliquez sur **"Ajouter un Device"** dans la section "Devices Personnalisés"
2. Remplissez les champs :
   - **ID Eedomus** : L'identifiant unique du device dans votre box Eedomus
   - **Entité Home Assistant** : Le nom de l'entité dans Home Assistant (ex: `light.salon`)
   - **Type** : Sélectionnez le type de device dans la liste déroulante
   - **Icône** : Choisissez une icône parmi les icônes Material Design (optionnel)
   - **Pièce** : Sélectionnez la pièce ou entrez un nom personnalisé (optionnel)

### Modifier un Device

1. Cliquez sur le device dans la liste pour le développer
2. Modifiez les champs souhaités
3. Les modifications sont appliquées automatiquement

### Prévisualiser le YAML

1. Cliquez sur **"Preview YAML"** pour voir la configuration générée
2. Le YAML s'affiche dans une zone dédiée avec coloration syntaxique
3. Vérifiez que la structure est correcte avant de sauvegarder
4. Vous pouvez copier ce YAML pour référence ou modification manuelle

### Sauvegarder

1. Cliquez sur **"Sauvegarder"** pour appliquer vos modifications
2. L'intégration redémarre automatiquement
3. Les nouveaux devices apparaissent dans Home Assistant

## Mode Éditeur YAML

### Structure du YAML

```yaml
# Metadata (informations sur la version)
metadata:
  version: "1.0"
  last_modified: "2026-03-18"
  changes: []

# Règles avancées (optionnel)
custom_rules: []

# Mappings personnalisés par usage_id (optionnel)
custom_usage_id_mappings: {}

# Propriétés dynamiques des entités (optionnel)
custom_dynamic_entity_properties: {}

# Overrides spécifiques pour devices (optionnel)
custom_specific_device_dynamic_overrides: {}

# Mappings des thermostats (optionnel)
temperature_setpoint_mappings: {}

# Patterns pour les noms de devices (optionnel)
custom_name_patterns: []

# Liste de vos devices personnalisés
custom_devices:
  - eedomus_id: "12345"          # ID dans Eedomus
    ha_entity: "light.salon"     # Nom de l'entité dans HA
    type: "light"                # Type de device
    ha_subtype: "rgbw"           # Sous-type (optionnel)
    icon: "mdi:lightbulb"        # Icône (optionnel)
    room: "Salon"                # Pièce (optionnel)
  
  - eedomus_id: "67890"
    ha_entity: "sensor.temperature_chambre"
    type: "sensor"
    ha_subtype: "temperature"
    icon: "mdi:thermometer"
    room: "Chambre"
```

### Éditer le YAML

1. Modifiez directement le contenu YAML dans l'éditeur
2. La coloration syntaxique vous aide à repérer les erreurs
3. La validation automatique vérifie la syntaxe YAML

### Valider et Sauvegarder

1. Cliquez sur **"Preview"** pour valider la syntaxe YAML
2. Si des erreurs sont détectées, elles s'affichent avec des messages détaillés
3. Cliquez sur **"Save"** pour appliquer les modifications
4. Les modifications sont appliquées immédiatement sans redémarrage nécessaire

## Types de Devices Supportés

| Type Home Assistant | Description | Exemple d'utilisation |
|---------------------|-------------|----------------------|
| `light` | Lumière | Lampes, spots, LED RGBW |
| `switch` | Interrupteur | Prises, relais |
| `sensor` | Capteur | Température, humidité, mouvement |
| `climate` | Climatisation | Thermostats, climatiseurs |
| `cover` | Volet | Stores, volets roulants |
| `binary_sensor` | Capteur binaire | Détecteurs d'ouverture, mouvement |

## Sous-types (ha_subtype)

| Sous-type | Description | Utilisé avec |
|-----------|-------------|--------------|
| `rgbw` | Lumière RGBW | `light` |
| `brightness` | Lumière dimmable | `light` |
| `color_temp` | Température de couleur | `light` |
| `temperature` | Capteur de température | `sensor` |
| `humidity` | Capteur d'humidité | `sensor` |
| `motion` | Détecteur de mouvement | `binary_sensor` |

## Bonnes Pratiques

1. **Sauvegardez avant de modifier** : Faites une copie de votre configuration actuelle
2. **Testez les modifications** : Vérifiez que les nouveaux devices apparaissent dans Home Assistant
3. **Utilisez des noms clairs** : Pour les entités et les pièces
4. **Documentez vos changements** : Dans la section `metadata.changes`

## Dépannage

### Les devices n'apparaissent pas
- Vérifiez que l'ID Eedomus est correct
- Assurez-vous que le device existe dans votre box Eedomus
- Redémarrez Home Assistant
- Vérifiez les logs pour les erreurs

### Erreurs de validation
- Vérifiez la syntaxe YAML (indentation, guillemets)
- Assurez-vous que tous les champs requis sont présents
- Consultez les messages d'erreur pour des détails

### L'interface ne répond pas
- Actualisez la page
- Vérifiez la connexion à votre box Eedomus
- Redémarrez l'intégration Eedomus

## Exemples Complets

### Configuration Minimale
```yaml
custom_devices:
  - eedomus_id: "12345"
    ha_entity: "light.salon"
    type: "light"
```

### Configuration Complète
```yaml
metadata:
  version: "1.0"
  last_modified: "2026-03-18"
  changes:
    - "Ajout des lumières du salon"
    - "Configuration des capteurs de température"

custom_devices:
  - eedomus_id: "12345"
    ha_entity: "light.salon_principal"
    type: "light"
    ha_subtype: "rgbw"
    icon: "mdi:lightbulb-multiple"
    room: "Salon"
  
  - eedomus_id: "12346"
    ha_entity: "light.salon_secondaire"
    type: "light"
    ha_subtype: "brightness"
    icon: "mdi:spotlight"
    room: "Salon"
  
  - eedomus_id: "67890"
    ha_entity: "sensor.temperature_salon"
    type: "sensor"
    ha_subtype: "temperature"
    icon: "mdi:thermometer"
    room: "Salon"
```

## Migration depuis l'ancienne version

Si vous utilisiez une version précédente avec un format différent :

1. Sauvegardez votre ancien fichier `custom_mapping.yaml`
2. Utilisez le nouveau format décrit dans cette documentation
3. Les anciens champs sont automatiquement migrés si possible
4. Vérifiez les logs pour les avertissements de migration

## Support

Pour toute question ou problème :
- Consultez les [issues GitHub](https://github.com/Dan4Jer/hass-eedomus/issues)
- Ouvrez une nouvelle issue avec une description détaillée
- Incluez vos logs et votre configuration
