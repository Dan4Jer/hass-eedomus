# Guide d'utilisation de l'éditeur YAML pour Eedomus

## Vue d'ensemble

L'intégration Eedomus offre maintenant une interface riche pour configurer les mappages personnalisés via un éditeur YAML natif avec coloration syntaxique et validation en temps réel.

## Prérequis

- Home Assistant 2026.3.1 ou supérieur
- Intégration Eedomus installée et configurée
- Accès à l'interface d'administration de Home Assistant

## Accéder à l'éditeur YAML

1. **Ouvrir les paramètres de l'intégration**
   - Allez dans Paramètres > Appareils et services
   - Sélectionnez l'intégration Eedomus
   - Cliquez sur "Options" ou "Configurer"

2. **Activer le mode YAML**
   - Dans l'interface des options, cochez la case "Edit YAML Configuration"
   - Cliquez sur "Soumettre" pour accéder à l'éditeur YAML

## Utilisation de l'éditeur YAML

### Interface de l'éditeur

L'éditeur YAML natif offre :
- **Coloration syntaxique** pour une meilleure lisibilité
- **Validation en temps réel** des erreurs de syntaxe
- **Boutons d'action** :
  - **Preview** : Valide le YAML avant sauvegarde
  - **Save** : Sauvegarde la configuration

### Structure du fichier YAML

```yaml
# Eedomus Custom Mapping Configuration
metadata:
  version: "1.0"
  last_modified: "YYYY-MM-DD"
  changes: []

custom_rules: []
custom_usage_id_mappings: {}
temperature_setpoint_mappings: {}
custom_name_patterns: []

custom_devices:
  # Exemple de configuration de périphérique
  - eedomus_id: "12345"
    ha_entity: "light.my_light"
    type: "light"
    name: "My Custom Light"
    ha_subtype: "dimmable"
    icon: "mdi:lightbulb"
    room: "Living Room"
    justification: "Custom mapping for special device"
```

### Champs requis pour les périphériques

Chaque périphérique dans `custom_devices` doit avoir :
- `eedomus_id` : Identifiant du périphérique dans Eedomus
- `ha_entity` : Nom de l'entité Home Assistant
- `type` : Type d'entité (light, switch, sensor, cover, binary_sensor, climate, select)
- `name` : Nom affiché du périphérique

### Champs optionnels

- `ha_subtype` : Sous-type spécifique (ex: "dimmable" pour les lumières)
- `icon` : Icône Material Design (ex: "mdi:lightbulb")
- `room` : Pièce ou emplacement
- `justification` : Commentaire expliquant la configuration

## Prévisualisation et validation

1. **Cliquez sur "Preview"** pour valider votre configuration YAML
2. L'éditeur affichera :
   - ✅ "YAML is valid" si la configuration est correcte
   - ❌ "Error: [description]" si des erreurs sont détectées
3. La prévisualisation montre le YAML formaté avec coloration syntaxique

## Sauvegarde de la configuration

1. **Cliquez sur "Save"** pour sauvegarder votre configuration
2. La configuration est validée avant sauvegarde
3. En cas d'erreur, un message d'erreur s'affiche
4. En cas de succès, la configuration est appliquée immédiatement

## Bonnes pratiques

### Organisation du fichier

```yaml
# Section 1 : Métadonnées
metadata:
  version: "1.0"
  last_modified: "2024-01-01"
  changes:
    - "Added living room lights"
    - "Fixed sensor mappings"

# Section 2 : Règles personnalisées
custom_rules:
  - pattern: ".*_temperature"
    type: "sensor"
    device_class: "temperature"

# Section 3 : Mappages de périphériques
custom_devices:
  # Lumière du salon
  - eedomus_id: "12345"
    ha_entity: "light.living_room_main"
    type: "light"
    name: "Living Room Main Light"
    ha_subtype: "dimmable"
    icon: "mdi:ceiling-light"
    room: "Living Room"

  # Capteur de température
  - eedomus_id: "67890"
    ha_entity: "sensor.outdoor_temperature"
    type: "sensor"
    name: "Outdoor Temperature"
    icon: "mdi:thermometer"
    room: "Outdoor"
```

### Conseils

1. **Utilisez des commentaires** pour documenter vos configurations
2. **Indentez correctement** (2 espaces par niveau)
3. **Validez fréquemment** avec le bouton Preview
4. **Sauvegardez des copies** avant les modifications majeures
5. **Testez les modifications** une par une

## Dépannage

### Erreurs courantes

1. **Erreur de syntaxe YAML**
   - Vérifiez l'indentation
   - Assurez-vous que les deux-points sont suivis d'un espace
   - Vérifiez les guillemets

2. **Champ requis manquant**
   - Assurez-vous que chaque périphérique a `eedomus_id`, `ha_entity`, `type` et `name`

3. **Type d'entité invalide**
   - Types valides : light, switch, sensor, cover, binary_sensor, climate, select

4. **Problèmes de sauvegarde**
   - Vérifiez les permissions du fichier `custom_mapping.yaml`
   - Consultez les logs de Home Assistant pour plus de détails

### Vérification des logs

Les erreurs et informations sont enregistrées dans les logs de Home Assistant :

```bash
# Via l'interface utilisateur
Développement > Outils > Logs

# Via SSH
tail -f /config/home-assistant.log | grep eedomus
```

## Exemples complets

### Configuration de base

```yaml
metadata:
  version: "1.0"
  last_modified: "2024-01-01"

custom_devices:
  - eedomus_id: "12345"
    ha_entity: "light.kitchen"
    type: "light"
    name: "Kitchen Light"
    room: "Kitchen"
```

### Configuration avancée

```yaml
metadata:
  version: "1.1"
  last_modified: "2024-01-15"
  changes:
    - "Added temperature sensors"
    - "Configured climate control"

custom_rules:
  - pattern: "temperature_.*"
    type: "sensor"
    device_class: "temperature"

temperature_setpoint_mappings:
  "living_room_thermostat": "climate.living_room"

custom_devices:
  # Lumière principale
  - eedomus_id: "12345"
    ha_entity: "light.living_room"
    type: "light"
    name: "Living Room Light"
    ha_subtype: "dimmable"
    icon: "mdi:ceiling-light"
    room: "Living Room"

  # Thermostat
  - eedomus_id: "67890"
    ha_entity: "climate.living_room"
    type: "climate"
    name: "Living Room Thermostat"
    icon: "mdi:thermostat"
    room: "Living Room"

  # Capteur de température extérieur
  - eedomus_id: "54321"
    ha_entity: "sensor.outdoor_temp"
    type: "sensor"
    name: "Outdoor Temperature"
    icon: "mdi:thermometer"
    room: "Outdoor"
```

## Migration depuis l'ancienne configuration

Si vous utilisiez l'ancienne méthode de configuration :

1. **Sauvegardez** votre ancien fichier `custom_mapping.yaml`
2. **Ouvrez l'éditeur YAML** via l'interface
3. **Copiez-collez** votre ancienne configuration
4. **Validez et sauvegardez**
5. **Testez** chaque périphérique pour vous assurer qu'il fonctionne correctement

## Support

Pour obtenir de l'aide supplémentaire :
- Consultez la [documentation officielle](https://github.com/Dan4Jer/hass-eedomus)
- Ouvrez une issue sur GitHub avec vos logs et configuration
- Rejoignez la communauté Home Assistant pour obtenir de l'aide

## Notes techniques

- Le fichier de configuration est stocké dans `custom_components/eedomus/config/custom_mapping.yaml`
- Les modifications sont appliquées immédiatement après sauvegarde
- Un redémarrage de Home Assistant n'est pas nécessaire
- La configuration est validée à la fois côté client et côté serveur