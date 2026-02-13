# Alternative à Recorder Component pour le Suivi d'Historique

## Problème
Le Recorder component de Home Assistant n'est pas toujours disponible ou configuré, ce qui empêche le suivi de la progression de téléchargement de l'historique.

## Solution Proposée
Créer des **entités virtuelles** dédiées au suivi de la progression de téléchargement de l'historique, indépendamment du Recorder component.

## Architecture Proposée

### 1. Capteur de Progression Globale
**Entity ID** : `sensor.eedomus_history_progress`
**Type** : Sensor avec device_class "progress"
**Fonction** : Suivre la progression globale de tous les devices

**Attributs** :
- `progress` : Pourcentage global (0-100)
- `devices_total` : Nombre total de devices
- `devices_completed` : Nombre de devices terminés
- `data_points_retrieved` : Nombre total de points récupérés
- `data_points_estimated` : Estimation du nombre total de points
- `last_updated` : Timestamp de la dernière mise à jour

### 2. Capteurs de Progression par Device
**Entity ID** : `sensor.eedomus_history_progress_{periph_id}`
**Type** : Sensor avec device_class "progress"
**Fonction** : Suivre la progression pour chaque device individuel

**Attributs** :
- `progress` : Pourcentage de progression (0-100)
- `periph_name` : Nom du device
- `periph_id` : ID du device
- `data_points_retrieved` : Points récupérés pour ce device
- `data_points_estimated` : Estimation totale pour ce device
- `last_timestamp` : Dernier timestamp récupéré
- `completed` : Booléen indiquant si le téléchargement est terminé
- `last_updated` : Timestamp de la dernière mise à jour

### 3. Capteur de Statistiques d'Historique
**Entity ID** : `sensor.eedomus_history_stats`
**Type** : Sensor avec device_class "data_size"
**Fonction** : Statistiques globales sur l'historique

**Attributs** :
- `total_size` : Taille estimée totale des données (en Mo)
- `downloaded_size` : Taille téléchargée (en Mo)
- `download_speed` : Vitesse de téléchargement (Mo/s)
- `estimated_time_remaining` : Temps restant estimé
- `devices_with_history` : Nombre de devices avec historique
- `devices_without_history` : Nombre de devices sans historique

## Implémentation Technique

### 1. Modification du Coordinator

#### Nouvelle méthode : `_create_virtual_history_sensors()`
```python
async def _create_virtual_history_sensors(self) -> None:
    """Crée des capteurs virtuels pour suivre la progression de l'historique.
    
    Ces capteurs sont indépendants du Recorder component et utilisent
    uniquement les states de Home Assistant pour le stockage.
    """
    if not self.hass:
        return
    
    try:
        # 1. Créer/créer des capteurs de progression par device
        for periph_id, progress in self._history_progress.items():
            periph_name = (
                self.data.get(periph_id, {}).get("name", "Unknown")
                if self.data and periph_id in self.data
                else "Unknown"
            )
            
            # Estimer le nombre total de points
            total_points = await self.client.get_device_history_count(periph_id)
            retrieved_points = 0
            
            if progress.get("last_timestamp", 0) > 0:
                retrieved_points = max(0, min(10000, (progress["last_timestamp"] / 86400) * 100))
            
            progress_percent = min(100, (retrieved_points / max(1, total_points)) * 100) if total_points > 0 else 0
            
            # Créer le capteur de progression par device
            entity_id = f"sensor.eedomus_history_progress_{periph_id}"
            self.hass.states.async_set(
                entity_id,
                str(progress_percent),
                {
                    "device_class": "progress",
                    "state_class": "measurement",
                    "unit_of_measurement": "%",
                    "friendly_name": f"History Progress: {periph_name}",
                    "icon": "mdi:progress-clock",
                    "periph_id": periph_id,
                    "periph_name": periph_name,
                    "data_points_retrieved": retrieved_points,
                    "data_points_estimated": total_points,
                    "last_timestamp": progress.get("last_timestamp", 0),
                    "completed": progress.get("completed", False),
                    "last_updated": datetime.now().isoformat(),
                },
            )
        
        # 2. Calculer la progression globale
        total_devices = len(self._history_progress)
        completed_devices = sum(1 for p in self._history_progress.values() if p.get("completed", False))
        total_retrieved = sum(
            max(0, min(10000, (p.get("last_timestamp", 0) / 86400) * 100))
            for p in self._history_progress.values()
        )
        total_estimated = sum(
            await self.client.get_device_history_count(periph_id)
            for periph_id in self._history_progress.keys()
        )
        
        global_progress = (total_retrieved / max(1, total_estimated)) * 100 if total_estimated > 0 else 0
        
        # Créer le capteur de progression globale
        self.hass.states.async_set(
            "sensor.eedomus_history_progress",
            str(global_progress),
            {
                "device_class": "progress",
                "state_class": "measurement",
                "unit_of_measurement": "%",
                "friendly_name": "Eedomus History Progress",
                "icon": "mdi:progress-wrench",
                "devices_total": total_devices,
                "devices_completed": completed_devices,
                "data_points_retrieved": total_retrieved,
                "data_points_estimated": total_estimated,
                "last_updated": datetime.now().isoformat(),
            },
        )
        
        # 3. Créer le capteur de statistiques
        downloaded_mb = (total_retrieved * 100) / 1024  # Estimation en Mo
        total_mb = (total_estimated * 100) / 1024  # Estimation en Mo
        
        self.hass.states.async_set(
            "sensor.eedomus_history_stats",
            str(downloaded_mb),
            {
                "device_class": "data_size",
                "state_class": "measurement",
                "unit_of_measurement": "MB",
                "friendly_name": "Eedomus History Stats",
                "icon": "mdi:database-clock",
                "total_size": str(total_mb),
                "downloaded_size": str(downloaded_mb),
                "devices_with_history": completed_devices,
                "devices_without_history": total_devices - completed_devices,
                "last_updated": datetime.now().isoformat(),
            },
        )
        
        _LOGGER.info(
            "✅ Virtual history sensors created: %d device sensors, 1 global progress, 1 stats",
            len(self._history_progress)
        )
        
    except Exception as e:
        _LOGGER.error("Error creating virtual history sensors: %s", e)
```

### 2. Modification de l'Initialisation

Remplacer les appels à `_load_history_progress()` et `_save_history_progress()` par l'appel à `_create_virtual_history_sensors()` dans `__init__.py` :

```python
# Dans __init__.py, remplacer:
if coordinator.config_entry.data.get(CONF_ENABLE_HISTORY, False):
    try:
        for periph_id in coordinator.data.keys():
            await coordinator._create_history_progress_sensor(periph_id)
        _LOGGER.info("✅ History progress sensors created for all devices")
    except Exception as err:
        _LOGGER.error("Failed to create history progress sensors: %s", err)

# Par:
if coordinator.config_entry.data.get(CONF_ENABLE_HISTORY, False):
    try:
        await coordinator._create_virtual_history_sensors()
        _LOGGER.info("✅ Virtual history sensors created successfully")
    except Exception as err:
        _LOGGER.error("Failed to create virtual history sensors: %s", err)
```

### 3. Modification du Fetch History

Dans `async_fetch_history_chunk()`, remplacer l'appel à `_save_history_progress()` par :

```python
# Après la récupération du chunk:
await self._create_virtual_history_sensors()
```

### 4. Suppression des Dépendances au Recorder

Supprimer ou commenter les vérifications de recorder dans :
- `_load_history_progress()`
- `_save_history_progress()`
- `async_import_history_chunk()`

Remplacer par des appels à `_create_virtual_history_sensors()`.

## Avantages de cette Solution

### 1. **Indépendance du Recorder**
- Fonctionne même si Recorder n'est pas configuré
- Pas de dépendance à la base de données
- Utilise uniquement les states de Home Assistant

### 2. **Visualisation en Temps Réel**
- Capteurs mis à jour en temps réel
- Visualisation dans les dashboards
- Alertes possibles sur la progression

### 3. **Statistiques Complètes**
- Progression globale et par device
- Estimation de la taille des données
- Temps restant estimé

### 4. **Intégration Native**
- Compatible avec toutes les fonctionnalités Home Assistant
- Graphiques et historique disponibles
- Alertes et automations possibles

## Exemple de Dashboard

```yaml
# Exemple de carte pour afficher la progression
type: vertical-stack
cards:
  - type: gauge
    entity: sensor.eedomus_history_progress
    name: "Progression Globale de l'Historique"
    min: 0
    max: 100
    severity:
      green: 0
      yellow: 75
      red: 90

  - type: entities
    title: "Progression par Device"
    entities:
      - entity: sensor.eedomus_history_stats
        name: "Statistiques"
        secondary_info: last_updated
      - type: divider
      - entity: sensor.eedomus_history_progress_123456
      - entity: sensor.eedomus_history_progress_789012
      # ... autres devices

  - type: history-graph
    entities:
      - entity: sensor.eedomus_history_progress
    hours_to_show: 24
```

## Migration depuis la Solution Recorder

Si vous avez déjà utilisé la solution avec Recorder, la migration est automatique :

1. Les nouvelles entités virtuelles seront créées
2. Les anciennes entités Recorder peuvent être supprimées
3. Les données historiques déjà récupérées seront perdues (mais pas les données actuelles)

## Limites

### 1. Pas de Persistance des Données Historiques
- Les entités virtuelles ne stockent pas les données historiques
- Elles ne remplacent pas le Recorder pour le stockage long terme
- Seule la progression de téléchargement est suivie

### 2. Dépendance aux States
- Les entités dépendent des states de Home Assistant
- Un redémarrage de HA efface les states (mais pas les données historiques)
- Les states sont sauvegardés dans le fichier `.storage`

### 3. Estimation des Données
- Le nombre total de points est estimé
- L'estimation peut ne pas être précise à 100%
- La taille en Mo est une estimation

## Conclusion

Cette solution alternative permet de :
- ✅ Suivre la progression de téléchargement sans Recorder
- ✅ Visualiser les données dans les dashboards
- ✅ Obtenir des statistiques complètes
- ✅ Utiliser toutes les fonctionnalités Home Assistant

Elle est idéale pour les utilisateurs qui :
- Ne veulent pas configurer Recorder
- Voulent une solution plus légère
- Préfèrent une visualisation en temps réel
- Souhaitent utiliser les automations Home Assistant

## Prochaines Étapes

1. Implémenter la solution proposée
2. Tester avec quelques devices
3. Vérifier la visualisation dans les dashboards
4. Ajouter des automations si nécessaire
5. Documenter l'utilisation

Cette solution offre une alternative robuste et flexible au Recorder component pour le suivi de la progression de téléchargement de l'historique.
