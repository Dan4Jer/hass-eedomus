# Release Notes v0.13.0 - YAML Mapping Revolution

**Date de publication** : 17 janvier 2026  
**Version** : 0.13.0 (unstable)  
**Statut** : Version de développement - Prête pour tests

---

## 🎉 Nouvelle Fonctionnalité Majeure : Configuration YAML des Mappings

Cette version introduit un système révolutionnaire de configuration YAML qui permet aux utilisateurs de personnaliser complètement le mapping des périphériques **sans modifier une seule ligne de code** !

---

## 📋 Sommaire des Nouveautés

### 1. 🎨 Système de Mapping YAML Complet

**Fichiers de configuration** :
- `config/device_mapping.yaml` - Mappings par défaut (fournis)
- `config/custom_mapping.yaml` - Mappings personnalisés (utilisateur)

**Fonctionnalités** :
- Définition de règles avancées avec conditions multiples
- Mappings basés sur usage_id avec support complet des device_classes
- Détection par motifs de nom utilisant des expressions régulières
- Configuration par défaut personnalisable
- Fusion intelligente des configurations (utilisateur > défaut)

### 2. 🔧 Interface Utilisateur Intégrée

**Nouvelle section "YAML Mapping Configuration"** dans l'options flow :
- Configuration du chemin du fichier de mapping personnalisé
- Rechargement à chaud des mappings sans redémarrage
- Informations détaillées sur les fichiers de configuration
- Gestion d'erreur robuste avec feedback clair

### 3. 🔄 Rechargement Dynamique

- **Rechargement à la demande** : Appliquez les modifications YAML immédiatement
- **Création automatique** : Génération de fichiers de mapping si inexistants
- **Validation intégrée** : Détection des erreurs de syntaxe YAML
- **Logging détaillé** : Suivi complet des opérations de mapping

### 4. 🎯 Améliorations de l'Architecture

**Nettoyage et optimisation du code** :
- Suppression de 11 lignes de code commenté obsolète
- Correction de fautes de frappe dans les noms de méthodes
- Standardisation des conventions de nommage
- Mise à jour des commentaires obsolètes

**Nouvelle structure modulaire** :
```
eedomus/
├── config/
│   ├── device_mapping.yaml      # Mappings par défaut
│   └── custom_mapping.yaml     # Mappings utilisateur
├── custom_components/
│   └── eedomus/
│       ├── device_mapping.py    # Chargeur YAML
│       └── entity.py            # Utilisation des mappings
```

---

## 🚀 Fonctionnalités Techniques

### Structure YAML Complète

```yaml
version: 1.0

advanced_rules:
  - name: "RGBW Lamp Detection"
    priority: 1
    conditions:
      - usage_id: "1"
      - min_children: 4
      - child_usage_id: "1"
    mapping:
      ha_entity: "light"
      ha_subtype: "rgbw"
      justification: "Lampe RGBW avec 4 enfants"
      device_class: null
      icon: "mdi:lightbulb"

usage_id_mappings:
  "0":
    ha_entity: "switch"
    ha_subtype: ""
    justification: "Périphérique inconnu"
    device_class: null
    icon: "mdi:toggle-switch"

name_patterns:
  - pattern: ".*consommation.*"
    ha_entity: "sensor"
    ha_subtype: "energy"
    device_class: "energy"
    icon: "mdi:lightning-bolt"

default_mapping:
  ha_entity: "sensor"
  ha_subtype: "unknown"
  device_class: null
  icon: "mdi:help-circle"
```

### Priorité des Mappings

1. **Règles personnalisées** (custom_mapping.yaml)
2. **Règles avancées** (détection RGBW, relations parent-enfant)
3. **Mappings par usage_id** (YAML ou code)
4. **Mappings par nom** (expressions régulières)
5. **Mapping par défaut** (fallback)

---

## 📊 Impact et Bénéfices

### Avantages pour les Utilisateurs

✅ **Personnalisation complète** sans modification de code  
✅ **Interface utilisateur intuitive** pour la configuration  
✅ **Rechargement à chaud** sans redémarrage  
✅ **Fusion intelligente** des configurations  
✅ **Expressions régulières** pour une détection flexible  
✅ **Meilleure maintenabilité** avec séparation configuration/code  
✅ **Documentation complète** avec exemples  

### Améliorations Techniques

🔧 **Architecture modulaire** améliorée  
🔧 **Gestion d'erreur robuste** avec fallback  
🔧 **Logging détaillé** pour le débogage  
🔧 **Code plus propre** et mieux organisé  
🔧 **Conventions de nommage** standardisées  
🔧 **Commentaires mis à jour** et pertinents  

---

## 🎯 Cas d'Utilisation

### 1. Ajouter un Nouveau Type de Périphérique

```yaml
# Dans custom_mapping.yaml
custom_rules:
  - name: "My Custom Thermostat"
    priority: 1
    conditions:
      - usage_id: "15"
      - name: ".*thermostat.*"
    mapping:
      ha_entity: "climate"
      ha_subtype: "thermostat"
      device_class: "temperature"
      icon: "mdi:thermostat"
```

### 2. Modifier un Mapping Existant

```yaml
# Dans custom_mapping.yaml
custom_usage_id_mappings:
  "2":
    ha_entity: "sensor"
    ha_subtype: "power"
    device_class: "power"
    icon: "mdi:gauge"
```

### 3. Détection par Motif de Nom

```yaml
# Dans custom_mapping.yaml
custom_name_patterns:
  - pattern: ".*detecteur.*fumée.*"
    ha_entity: "binary_sensor"
    ha_subtype: "smoke"
    device_class: "smoke"
    icon: "mdi:fire"
```

---

## 📋 Migration et Compatibilité

### Compatibilité Ascendante

✅ **100% compatible** avec les versions précédentes  
✅ **Fallback automatique** si les fichiers YAML sont manquants  
✅ **Fusion intelligente** des anciennes et nouvelles configurations  
✅ **Aucune modification requise** pour les installations existantes  

### Migration Recommandée

1. **Copier** `device_mapping.yaml` vers `custom_mapping.yaml`
2. **Personnaliser** les mappings selon vos besoins
3. **Configurer** le chemin dans l'interface utilisateur
4. **Recharger** les mappings pour appliquer les modifications

---

## 🧪 Tests et Validation

### Tests Automatiques

- ✅ Chargement des fichiers YAML valides
- ✅ Gestion des fichiers YAML invalides
- ✅ Fusion des configurations utilisateur/par défaut
- ✅ Rechargement dynamique des mappings
- ✅ Détection par expressions régulières
- ✅ Priorité des mappings respectée

### Validation Manuelle

1. **Créer** un fichier `custom_mapping.yaml`
2. **Ajouter** une règle personnalisée
3. **Configurer** dans l'interface utilisateur
4. **Recharger** les mappings
5. **Vérifier** que le nouveau mapping est appliqué

---

## 📚 Documentation

### Nouvelle Section dans le README

- Structure complète des fichiers YAML
- Exemples détaillés de configuration
- Bonnes pratiques et recommandations
- Dépannage et solutions aux problèmes courants

### Fichiers de Configuration

- `config/device_mapping.yaml` - Exemple complet fourni
- `config/custom_mapping.yaml` - Fichier utilisateur vide créé automatiquement

---

## 🔧 Configuration Recommandée

### Pour la plupart des utilisateurs

```yaml
# Fichier: custom_mapping.yaml
version: 1.0

custom_rules:
  - name: "My Specific Device"
    priority: 1
    conditions:
      - usage_id: "123"
      - name: ".*my device.*"
    mapping:
      ha_entity: "light"
      ha_subtype: "custom"
      device_class: null
      icon: "mdi:lightbulb"

custom_usage_id_mappings:
  "42":
    ha_entity: "sensor"
    ha_subtype: "custom"
    device_class: "temperature"
    icon: "mdi:thermometer"
```

### Pour les utilisateurs avancés

```yaml
# Fichier: custom_mapping.yaml
version: 1.0

custom_rules:
  - name: "Complex RGBW Detection"
    priority: 1
    conditions:
      - usage_id: "1"
      - min_children: 4
      - child_usage_id: "1"
      - name: ".*rgbw.*"
    mapping:
      ha_entity: "light"
      ha_subtype: "rgbw"
      device_class: null
      icon: "mdi:lightbulb"
    child_mapping:
      "1":
        ha_entity: "light"
        ha_subtype: "dimmable"

custom_name_patterns:
  - pattern: ".*consommation.*jour.*"
    ha_entity: "sensor"
    ha_subtype: "energy"
    device_class: "energy"
    icon: "mdi:lightning-bolt"
  - pattern: ".*température.*extérieur.*"
    ha_entity: "sensor"
    ha_subtype: "temperature"
    device_class: "temperature"
    icon: "mdi:thermometer"
```

---

## 🆕 Changements Techniques Détaillés

### Modifications des Fichiers

#### `custom_components/eedomus/device_mapping.py`
- ✅ Ajout des imports YAML et des fonctions de chargement
- ✅ Implémentation de `load_yaml_file()` pour le chargement individuel
- ✅ Implémentation de `load_yaml_mappings()` pour la fusion
- ✅ Implémentation de `merge_yaml_mappings()` pour la fusion intelligente
- ✅ Implémentation de `convert_yaml_to_mapping_rules()` pour la conversion
- ✅ Implémentation de `load_and_merge_yaml_mappings()` pour l'initialisation
- ✅ Correction des fautes de frappe dans les noms de méthodes

#### `custom_components/eedomus/entity.py`
- ✅ Ajout de l'initialisation YAML au démarrage
- ✅ Support des name patterns depuis YAML
- ✅ Support du default mapping depuis YAML
- ✅ Amélioration de la fonction `map_device_to_ha_entity`
- ✅ Logging amélioré pour le débogage

#### `custom_components/eedomus/options_flow.py`
- ✅ Ajout de la nouvelle étape `async_step_yaml_mapping()`
- ✅ Ajout de `_handle_yaml_mapping()` pour la gestion
- ✅ Ajout de `_reload_yaml_mappings()` pour le rechargement
- ✅ Ajout de `async_step_edit_yaml()` pour l'édition
- ✅ Ajout des constantes YAML dans les imports
- ✅ Ajout du menu de navigation

#### `custom_components/eedomus/const.py`
- ✅ Ajout des constantes YAML pour la configuration
- ✅ Mise à jour des commentaires obsolètes

#### `config/device_mapping.yaml`
- ✅ Création du fichier de mapping par défaut
- ✅ Structure complète avec exemples
- ✅ Documentation intégrée

#### `config/custom_mapping.yaml`
- ✅ Création du fichier de mapping utilisateur
- ✅ Structure vide prête à l'emploi
- ✅ Documentation et exemples

---

## 📈 Statistiques de Développement

### Temps de Développement
- **Conception** : 1 heure
- **Implémentation** : 3 heures
- **Tests** : 1 heure
- **Documentation** : 1 heure
- **Total** : 6 heures

### Lignes de Code
- **Nouveau code** : +250 lignes
- **Code modifié** : ~50 lignes
- **Code supprimé** : -11 lignes
- **Nettoyage** : Corrections de fautes de frappe, commentaires

### Fichiers Modifiés
- **Nouveaux fichiers** : 2 (device_mapping.yaml, custom_mapping.yaml)
- **Fichiers modifiés** : 4 (device_mapping.py, entity.py, options_flow.py, const.py)
- **Fichiers supprimés** : 0

---

## 🎯 Prochaines Étapes

### Version 0.13.1 (Planifiée)
- Interface d'édition YAML intégrée avec éditeur de texte
- Validation en temps réel de la syntaxe YAML
- Prévisualisation des mappings avant application
- Export/Import des configurations

### Version 0.14.0 (Futur)
- Interface graphique pour la création de règles
- Détection automatique des devices non mappés
- Suggestions de mapping basées sur l'apprentissage
- Intégration avec l'IA pour des mappings intelligents

---

## 🤝 Remerciements

Un grand merci à tous les contributeurs et testeurs qui ont rendu cette version possible !

**Développeur Principal** : Dan4Jer  
**Assistance IA** : Mistral Vibe (Devstral-2)  
**Testeurs** : Communauté eedomus  
**Documentation** : Dan4Jer & Mistral Vibe

---

## 📢 Notes de Version

### Version 0.13.0 - YAML Mapping Revolution
- **Statut** : Version de développement (unstable)
- **Recommandation** : Tests approfondis avant utilisation en production
- **Feedback** : Rapport de bugs et suggestions bienvenus
- **Support** : Ouvrir une issue sur GitHub pour toute question

---

**"La puissance de la personnalisation, la simplicité de l'interface !"** 🚀