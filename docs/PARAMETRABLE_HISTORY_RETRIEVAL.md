# Récupération Historique Paramétrable

## 🎯 Nouvelle Fonctionnalité

La récupération historique est maintenant **paramétrable** pour contrôler le nombre de périphériques traités par intervalle de scan.

## 🔧 Configuration

### Nouvelle Option

**Nom**: `history_peripherals_per_scan`
**Type**: Entier
**Valeur par défaut**: 1
**Description**: Nombre de périphériques à traiter par intervalle de scan

### Où la Configurer

1. **Interface UI**: Dans les options de l'intégration eedomus
2. **Configuration YAML**: Dans le fichier `configuration.yaml`
3. **Options Flow**: Via l'interface d'options de Home Assistant

## ✅ Utilisation

### Par Défaut (1 périphérique par scan)

```yaml
# Par défaut, 1 périphérique est traité par scan interval
# Avec un scan_interval de 300 secondes (5 minutes)
# Cela signifie qu'un périphérique est traité toutes les 5 minutes
```

### Configuration Personnalisée

```yaml
# Traiter 2 périphériques par scan interval
# Cela accélère la récupération mais augmente la charge
options:
  history_peripherals_per_scan: 2

# Traiter 5 périphériques par scan interval
# Pour une récupération rapide (recommandé pour les petits systèmes)
options:
  history_peripherals_per_scan: 5

# Désactiver la limite (tous les périphériques en une fois)
# Attention: Peut surcharger le système
options:
  history_peripherals_per_scan: 0
```

## 📊 Comportement

### Priorisation

Les périphériques sont traités dans l'ordre de leur **dernier timestamp** (les plus anciens en premier):

```
Périphérique 1130749 (timestamp: 0) → Traité en premier
Périphérique 1090995 (timestamp: 100) → Traité ensuite
Périphérique 1143944 (timestamp: 200) → Traité après
...
```

### Exemple avec 2 périphériques par scan

| Scan Interval | Périphériques Traités |
|---------------|---------------------|
| Scan 1 | 1130749, 1090995 |
| Scan 2 | 1143944, 1143945 |
| Scan 3 | 1145719, 1145720 |
| ... | ... |

## 📈 Calcul du Temps de Récupération

### Formule

```
Temps total = (Nombre de périphériques × Scan interval) / Nombre de périphériques par scan
```

### Exemples

| Configuration | Temps pour 17 périphériques |
|---------------|----------------------------|
| 1 périphérique/scan (300s) | 85 minutes |
| 2 périphériques/scan (300s) | 42 minutes |
| 5 périphériques/scan (300s) | 17 minutes |
| 10 périphériques/scan (300s) | 8 minutes |

## 💡 Recommandations

### Pour les Petits Systèmes (< 50 périphériques)

```yaml
# Configuration recommandée
options:
  history_peripherals_per_scan: 5
  scan_interval: 300
```

### Pour les Grands Systèmes (> 100 périphériques)

```yaml
# Configuration recommandée
options:
  history_peripherals_per_scan: 2
  scan_interval: 300
```

### Pour une Récupération Rapide (Test)

```yaml
# Configuration pour tester rapidement
options:
  history_peripherals_per_scan: 10
  scan_interval: 60
```

## 🔍 Vérification

### Vérifier la Configuration

```bash
# Vérifier les options actuelles
tail -f ~/mistral/rasp.log | grep "Limiting history retrieval"

# Vérifier le nombre de périphériques traités
tail -f ~/mistral/rasp.log | grep "Performing partial refresh"
```

### Vérifier les Logs

```bash
# Voir la progression
tail -f ~/mistral/rasp.log | grep -E "(Limiting history|Performing partial|Fetching history)"

# Exemple de sortie:
# INFO: Limiting history retrieval to 2 peripherals per scan interval (total: 17)
# INFO: Performing partial refresh for 2 peripherals (history retrieval: True)
# INFO: Fetching history for 1130749 (from start)
# INFO: Fetching history for 1090995 (from start)
```

## 📊 Exemple de Configuration Complète

```yaml
# configuration.yaml

# Configuration eedomus
eedomus:
  api_user: !secret eedomus_api_user
  api_secret: !secret eedomus_api_secret
  api_host: !secret eedomus_api_host
  scan_interval: 300
  
# Options personnalisées
options:
  history: true
  history_retry_delay: 24
  history_peripherals_per_scan: 2
  scan_interval: 300
```

## ⚠️ Avertissements

### Surcharge du Système

- **Trop de périphériques par scan** peut surcharger l'API eedomus
- **Recommandation**: Ne pas dépasser 10 périphériques par scan
- **Symptômes**: Temps de réponse lent, erreurs API, timeouts

### Limite de l'API

- L'API eedomus a des limites de taux
- **Recommandation**: Respecter un délai entre les appels
- **Valeur par défaut**: 1 périphérique par scan interval (300s)

## 🎯 Résultats Attendus

✅ **Contrôle fin** sur la vitesse de récupération
✅ **Adaptabilité** à la taille du système
✅ **Flexibilité** pour les tests et la production
✅ **Optimisation** de la charge du système

## 📚 Documentation Complémentaire

- **SIMPLIFIED_HISTORY_APPROACH.md** - Approche simplifiée de la récupération
- **HISTORY_RETRIEVAL_STATUS.md** - État de la récupération des données
- **DEVICE_NAMES_REPORT.md** - Liste complète des périphériques

## 🚀 Déploiement

### 1. Configurer l'Option

```bash
# Accéder aux options de l'intégration
hassio addon options eedomus

# Ou via l'interface:
# Settings → Devices & Services → Eedomus → Options
```

### 2. Redémarrer Home Assistant

```bash
ha core restart
```

### 3. Surveiller les Logs

```bash
tail -f ~/mistral/rasp.log | grep -E "(Limiting history|Performing partial|Fetching history)"
```

### 4. Vérifier la Progression

```bash
# Vérifier les capteurs
ha states | grep "eedomus_history"

# Vérifier le capteur global
ha state show sensor.eedomus_history_progress
```

## 🎉 Conclusion

La récupération historique paramétrable permet:
- ✅ **Contrôler la vitesse** de récupération
- ✅ **Adapter la charge** du système
- ✅ **Optimiser les performances**
- ✅ **Personnaliser l'expérience**

Le système est maintenant prêt pour une utilisation en production avec un contrôle fin sur la récupération des données historiques.