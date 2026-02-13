# Guide Rapide pour Activer et Tester l'Historique

## Étape 1 : Activer l'Option History

1. **Accédez à l'intégration** :
   - Allez dans **Settings** > **Devices & Services**
   - Sélectionnez **Eedomus** dans la liste

2. **Ouvrez les options** :
   - Cliquez sur les trois points (⋮) à droite de l'intégration
   - Sélectionnez **Options** dans le menu

3. **Activez l'historique** :
   - Trouvez l'option **Enable History**
   - Cochez la case pour l'activer
   - Cliquez sur **Save** en bas

4. **Confirmez** :
   - Vous devriez voir un message de confirmation
   - L'intégration va créer les capteurs virtuels automatiquement

## Étape 2 : Vérifier les Logs

### Depuis l'interface Home Assistant
1. Allez dans **Settings** > **System** > **Logs**
2. Filtrez par **custom_components.eedomus**
3. Cherchez ces messages :
   ```
   ✅ Virtual history sensors created successfully
   ✅ Virtual history sensors created: X device sensors, 1 global progress, 1 stats
   ```

### Depuis SSH (plus détaillé)
```bash
# Connexion au Raspberry Pi
ssh 192.168.1.4

# Voir les logs en temps réel
tail -f ~/mistral/rasp.log | grep eedomus

# Ou voir les 50 dernières lignes
tail -n 50 ~/mistral/rasp.log | grep eedomus
```

### Messages Attendus
✅ **Messages normaux** :
```
✅ Virtual history sensors created successfully
✅ Virtual history sensors created: 10 device sensors, 1 global progress, 1 stats
INFO: Starting to load history progress
DEBUG: Loaded progress for 123456: {'last_timestamp': 0, 'completed': False}
```

⚠️ **Messages d'avertissement (normaux si Recorder n'est pas configuré)** :
```
DEBUG: Recorder component not available. History will not be imported to database.
```

❌ **Messages d'erreur (à investiguer)** :
```
ERROR: Error creating virtual history sensors: ...
ERROR: Error loading history progress: ...
```

## Étape 3 : Vérifier les Capteurs Créés

### Depuis l'interface Home Assistant
1. Allez dans **Settings** > **Devices & Services**
2. Sélectionnez **Eedomus**
3. Cliquez sur **Entities**
4. Vous devriez voir :
   - `sensor.eedomus_history_progress` (progression globale)
   - `sensor.eedomus_history_progress_123456` (progression par device)
   - `sensor.eedomus_history_stats` (statistiques)

### Depuis SSH
```bash
# Lister toutes les entités eedomus
ha states | grep "eedomus"

# Voir les détails d'une entité spécifique
ha state show sensor.eedomus_history_progress
```

### Exemple de Sortie Attendue
```
sensor.eedomus_history_progress: 0 %
sensor.eedomus_history_progress_123456: 0 %
sensor.eedomus_history_stats: 0 MB
```

## Étape 4 : Visualiser dans un Dashboard

### Créer une carte simple
```yaml
type: entities
entities:
  - entity: sensor.eedomus_history_progress
    name: "Progression Globale"
  - entity: sensor.eedomus_history_stats
    name: "Statistiques"
```

### Créer une jauge pour la progression
```yaml
type: gauge
entity: sensor.eedomus_history_progress
name: "Téléchargement de l'Historique"
min: 0
max: 100
severity:
  green: 0
  yellow: 75
  red: 90
```

### Créer un graphique de progression
```yaml
type: history-graph
entities:
  - entity: sensor.eedomus_history_progress
hours_to_show: 24
```

## Étape 5 : Suivre la Progression

### Voir les attributs détaillés
```bash
# Voir tous les attributs d'une entité
ha state show sensor.eedomus_history_progress

# Voir les attributs d'un device spécifique
ha state show sensor.eedomus_history_progress_123456
```

### Attributs Disponibles
- `progress` : Pourcentage de progression (0-100)
- `periph_name` : Nom du device
- `data_points_retrieved` : Points récupérés
- `data_points_estimated` : Estimation totale
- `completed` : Booléen (true/false)
- `last_updated` : Timestamp de la dernière mise à jour

## Étape 6 : Tester le Fonctionnement

### Forcer un rafraîchissement
```bash
# Depuis SSH
ha service call eedomus.refresh

# Ou depuis l'interface
# Settings > Devices & Services > Eedomus > Services > Refresh
```

### Vérifier que la progression augmente
1. Attendez quelques minutes
2. Vérifiez les valeurs des capteurs
3. La progression devrait augmenter progressivement

### Vérifier les logs pendant le rafraîchissement
```bash
tail -f ~/mistral/rasp.log | grep -E "(history|Fetching|imported)"
```

### Messages Attendus Pendant le Rafraîchissement
```
INFO: Fetching history for 123456 (from 2024-01-01T00:00:00)
INFO: Successfully imported 1000 historical states for sensor.eedomus_123456
INFO: History fully fetched for 123456 (Device Name) (received 1000 entries)
```

## Étape 7 : Résoudre les Problèmes

### Problème : Capteurs non créés
**Solution** :
1. Vérifiez que l'option History est bien activée
2. Redémarrez Home Assistant
3. Vérifiez les logs pour les erreurs

### Problème : Progression ne change pas
**Solution** :
1. Vérifiez que l'API Eedomus est activée
2. Vérifiez les credentials API
3. Forcez un rafraîchissement
4. Vérifiez les logs pour les erreurs API

### Problème : Erreurs dans les logs
**Solution** :
1. Copiez le message d'erreur exact
2. Cherchez dans la documentation
3. Créez un issue sur GitHub avec les logs

## Résumé des Commandes Utiles

```bash
# Vérifier le statut
ha core info

# Voir les logs
tail -f ~/mistral/rasp.log | grep eedomus

# Lister les entités
ha states | grep "eedomus"

# Voir les détails d'une entité
ha state show sensor.eedomus_history_progress

# Forcer un rafraîchissement
ha service call eedomus.refresh

# Redémarrer Home Assistant
ha core restart
```

## Ce que Vous Devriez Observer

✅ **Après activation** :
- Capteurs virtuels créés automatiquement
- Valeurs initiales à 0%
- Messages de log indiquant la création des capteurs

✅ **Pendant le rafraîchissement** :
- Progression qui augmente
- Messages de log indiquant la récupération de l'historique
- Importation des données

✅ **Après complétion** :
- Progression à 100%
- Attribut `completed` à true
- Données historiques disponibles

## Prochaines Étapes

1. **Attendez** que le téléchargement se termine
2. **Visualisez** les données dans vos dashboards
3. **Testez** avec différents devices
4. **Donnez votre feedback** sur le fonctionnement

Bonne chance avec votre configuration ! 🎉
