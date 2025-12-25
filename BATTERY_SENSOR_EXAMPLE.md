# Exemple de Capteur de Batterie Eedomus

## 📋 Exemple de Fonctionnement

Ce document montre comment le module `battery.py` crée des capteurs de batterie pour les périphériques eedomus.

## 🔋 Exemple de Périphérique avec Batterie

### Données API Eedomus (exemple réel)

```json
{
  "periph_id": "1090995",
  "name": "Mouvement Oeil de chat Salon",
  "usage_name": "Motion Sensor",
  "usage_id": "37",
  "product_type_id": "3074",
  "battery": "100",
  "value": "0",
  "last_updated": "2025-12-23T10:30:00",
  "children": [
    {
      "periph_id": "1090995-Battery",
      "name": "Mouvement Oeil de chat Salon Battery",
      "usage_name": "Battery Level",
      "usage_id": "25",
      "battery": "100"
    }
  ]
}
```

### Ce que le code fait

1. **Détecte** que le périphérique a un champ `"battery": "100"`
2. **Valide** que "100" est un nombre valide entre 0 et 100
3. **Crée** un capteur de batterie avec les propriétés suivantes :

### Entité Home Assistant créée

```yaml
# Nom de l'entité
entity_id: sensor.mouvement_oeil_de_chat_salon_battery

# Nom affiché
friendly_name: "Mouvement Oeil de chat Salon Battery"

# Valeur principale
state: 100
unit_of_measurement: "%"

# Device class pour intégration native
device_class: battery

# Attributs supplémentaires
attributes:
  device_name: "Mouvement Oeil de chat Salon"
  device_id: "1090995"
  device_type: "Motion Sensor"
  battery_status: "High"
  friendly_name: "Mouvement Oeil de chat Salon Battery"

# Icône automatique (grâce à device_class: battery)
icon: mdi:battery
```

### Affichage dans Home Assistant

![Exemple de capteur de batterie](https://www.home-assistant.io/images/screenshots/battery-sensor.png)

Le capteur s'affichera avec :
- **Icône de batterie** automatique
- **Valeur en pourcentage** (100%)
- **Indicateur visuel** du niveau
- **Attributs** accessibles dans les cartes

## 📊 Exemples de Périphériques Compatibles

### 1. Détecteur de Mouvement (usage_id=37)
```json
{
  "name": "Mouvement Oeil de chat Salon",
  "usage_id": "37",
  "battery": "85"
}
```
→ `sensor.mouvement_oeil_de_chat_salon_battery` (85%)

### 2. Capteur de Température (usage_id=7)
```json
{
  "name": "Température Oeil de chat Salon",
  "usage_id": "7",
  "battery": "90"
}
```
→ `sensor.temperature_oeil_de_chat_salon_battery` (90%)

### 3. Détecteur de Fumée (usage_id=1)
```json
{
  "name": "Fumée Cuisine",
  "usage_id": "1",
  "battery": "75"
}
```
→ `sensor.fumee_cuisine_battery` (75%, statut: "Medium")

### 4. Détecteur d'Inondation (usage_id=2)
```json
{
  "name": "Inondation Salle de bain",
  "usage_id": "2",
  "battery": "60"
}
```
→ `sensor.inondation_salle_de_bain_battery` (60%, statut: "Medium")

## 🎯 Statut de la Batterie

Le code détermine automatiquement le statut :

| Niveau (%) | Statut | Recommandation |
|------------|--------|----------------|
| 75-100 | High | 🟢 Batterie en bonne santé |
| 50-74 | Medium | 🟡 Surveillance recommandée |
| 25-49 | Low | 🟠 Prévoir le remplacement |
| 0-24 | Critical | 🔴 Remplacement urgent |
| Invalide | Unknown | ❓ Vérifier le périphérique |

## 🔧 Comment Vérifier que ça Marche

### 1. Vérifier les logs
```bash
# Activez les logs de debug
yaml
# configuration.yaml
logger:
  default: warn
  logs:
    custom_components.eedomus: debug
    custom_components.eedomus.battery: debug
```

### 2. Rechercher les messages
```
# Dans les logs, cherchez:
DEBUG: Creating battery sensor for Mouvement Oeil de chat Salon (1090995) with battery level: 100%
DEBUG: Initializing battery sensor for Mouvement Oeil de chat Salon Battery (1090995_battery)
```

### 3. Vérifier les entités
Dans Home Assistant :
1. Allez dans **Paramètres → Appareils et services**
2. Sélectionnez l'intégration eedomus
3. Vérifiez les entités créées
4. Filtrez par "battery" pour voir tous les capteurs

## 🐛 Dépannage

### Problème : Aucun capteur de batterie créé
**Solutions** :
1. Vérifiez que le périphérique a bien un champ `"battery"` dans l'API
2. Assurez-vous que la valeur est numérique (pas "N/A" ou "Unknown")
3. Vérifiez les logs pour voir si le périphérique est détecté
4. Redémarrez Home Assistant pour forcer un nouveau scan

### Problème : Valeur de batterie incorrecte
**Solutions** :
1. Vérifiez la valeur dans l'API eedomus
2. Assurez-vous que c'est un nombre entre 0 et 100
3. Vérifiez que le périphérique n'a pas de valeur "battery" vide ou invalide

### Problème : Capteur toujours "unavailable"
**Solutions** :
1. Vérifiez que le périphérique est accessible via l'API
2. Assurez-vous que la valeur de batterie est bien numérique
3. Vérifiez la connexion à la box eedomus
4. Redémarrez l'intégration eedomus

## 📋 Exemple de Configuration YAML

Si vous utilisez la configuration YAML (au lieu de l'UI) :

```yaml
# configuration.yaml
sensor:
  - platform: eedomus
    host: 192.168.1.2
    api_user: votre_utilisateur
    api_secret: votre_cle_secrete
    # Les capteurs de batterie sont créés automatiquement
    # pour tous les périphériques avec information de batterie
```

## 🎉 Avantages de cette Implémentation

✅ **Création automatique** - Pas de configuration manuelle nécessaire
✅ **Intégration native** - Utilise la device_class `battery` de Home Assistant
✅ **Attributs utiles** - Fournit des informations supplémentaires sur le périphérique
✅ **Statut intelligent** - Indique quand remplacer les batteries
✅ **Compatibilité** - Fonctionne avec tous les périphériques eedomus ayant une batterie

## 📊 Statistiques

Avec cette implémentation, vous pouvez :
- **Surveiller** tous vos périphériques sur batterie
- **Recevoir des alertes** quand les batteries sont faibles
- **Planifier** les remplacements de batterie
- **Visualiser** l'état global de votre système

## 🔗 Intégration avec d'autres composants

### 1. Tableau de bord Énergie
```yaml
# Dans un tableau de bord Lovelace
views:
  - title: Batteries
    cards:
      - type: entities
        title: Niveau des Batteries
        show_header_toggle: false
        entities:
          - sensor.mouvement_oeil_de_chat_salon_battery
          - sensor.temperature_oeil_de_chat_salon_battery
          - sensor.fumee_cuisine_battery
```

### 2. Automations
```yaml
# Exemple d'automatisation pour alerte batterie faible
automation:
  - alias: "Alerte batterie faible"
    trigger:
      - platform: numeric_state
        entity_id:
          - sensor.mouvement_oeil_de_chat_salon_battery
          - sensor.temperature_oeil_de_chat_salon_battery
        below: 25
    action:
      - service: notify.notify
        data:
          message: "⚠️ Batterie faible : {{ trigger.to_state.name }} ({{ trigger.to_state.state }}%)"
          title: "Alerte Batterie"
```

### 3. Template pour statut global
```yaml
# Capteur template pour le statut global des batteries
sensor:
  - platform: template
    sensors:
      batteries_status:
        friendly_name: "Statut Global des Batteries"
        value_template: >
          {% set batteries = states.sensor
            | selectattr('entity_id', 'contains', 'battery')
            | map(attribute='state')
            | map('int')
            | list %}
          {% if batteries | min > 75 %}
            Tous les capteurs ont un bon niveau de batterie
          {% elif batteries | min > 50 %}
            Certains capteurs approchent du niveau moyen
          {% elif batteries | min > 25 %}
            ⚠️ Certains capteurs ont un niveau faible
          {% else %}
            ❌ Attention : batteries critiques détectées
          {% endif %}
```

## 🎯 Conclusion

Le module `battery.py` est une implémentation robuste qui :
1. **Détecte automatiquement** les périphériques avec batterie
2. **Crée des capteurs natifs** dans Home Assistant
3. **Fournit des informations utiles** pour la maintenance
4. **S'intègre parfaitement** avec l'écosystème Home Assistant

Pour voir des exemples concrets, vérifiez vos périphériques eedomus qui ont des informations de batterie et observez les capteurs créés automatiquement !

Si vous avez des périphériques spécifiques qui ne fonctionnent pas comme prévu, nous pouvons ajuster le code pour les supporter.