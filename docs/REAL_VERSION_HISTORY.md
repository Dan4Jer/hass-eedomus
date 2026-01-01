# Historique des Versions Réel

Ce document présente l'historique réel des versions basé sur les commits Git.

## 📋 Versions et Fonctionnalités

### Version Actuelle (en développement)
**Branche**: `feature/improved-entity-mapping-and-battery-sensors`

#### Améliorations Majeures
- **Documentation complète** avec diagrammes Mermaid intégrés
- **Support natif GitHub** pour les diagrammes Mermaid
- **Configuration personnalisée** pour un rendu standardisé
- **Guide complet** pour l'utilisation de Mermaid avec GitHub

#### Fonctionnalités Clés
- **Intégration eedomus** complète avec Home Assistant
- **Mapping automatique** des entités basé sur les classes Z-Wave
- **Support des thermostats** et consignes de température
- **Gestion des capteurs** avancée avec valeurs manquantes
- **API Proxy** pour les webhooks eedomus
- **Documentation visuelle** avec 13 diagrammes d'architecture

### Historique des Commits

#### Derniers Commits (2025)
- **7094f28** - Add Mermaid configuration and guide for GitHub
- **6685951** - Refine EedomusAPI styles and feature details
- **59da6e6** - 🐛 Fix all Mermaid diagrams for GitHub compatibility
- **86104cf** - Enhance README with Eedomus integration diagrams
- **1e24b56** - 📊 Add comprehensive mapping table with visual correspondence
- **6e7476b** - 📊 Add comprehensive visual documentation with Mermaid diagrams
- **fabc6ba** - 🚀 Major entity improvements and new battery sensors
- **ba792f3** - Add comprehensive Mermaid conversion summary document

#### Commits Précédents (2025)
- **14dde7d** - Convert webhook ASCII diagram to Mermaid flowchart
- **a62134b** - Convert ASCII diagrams to beautiful Mermaid visualizations
- **e156dc7** - Update README with development methodology and diagrams
- **c8e5869** - Add comprehensive version history and release notes

## 🎯 Fonctionnalités par Version

### Version 0.12.0 (en développement)
- **Nouveaux capteurs de batterie** pour tous les périphériques
- **Amélioration des entités climate** avec détection automatique
- **Support des couleurs prédéfinies** comme sélecteurs
- **Détection intelligente** des capteurs de consommation
- **Correction du capteur** "Oeil de Chat"

### Version 0.11.0 (en développement)
- **Migration Scene→Select** pour une meilleure UX
- **Correction du mapping** avec le champ `values`
- **Interface dropdown native** pour les sélecteurs
- **Support complet** des périphériques virtuels

### Version 0.10.0 (en développement)
- **Support complet des thermostats** via plateforme climate
- **Chauffage fil pilote** et têtes thermostatiques Z-Wave
- **Contrôle précis** de température (7.0°C à 30.0°C)
- **Intégration complète** avec le tableau de bord climat

### Version 0.9.0 (en développement)
- **Système de mapping** basé sur classes Z-Wave et usage_id
- **Table de correspondance** complète pour les devices
- **Capteurs binaires** étendus (mouvement, porte, fumée, etc.)
- **Détection intelligente** basée sur les attributs

### Version 0.8.0 (en développement)
- **Support complet des scènes** eedomus
- **Groupes de volets** pour contrôle centralisé
- **Automations virtuelles** et périphériques virtuels
- **Intégration native** avec les automations HA

## 📊 Statistiques de Développement

### Diagrammes et Documentation
- **13 diagrammes Mermaid** intégrés dans le README
- **Configuration personnalisée** pour rendu cohérent
- **Guide complet** pour utilisation et personnalisation
- **Couleurs standardisées** pour Home Assistant et Eedomus

### Plateformes Supportées
- **Light** : Lampes, RGBW, variateurs
- **Switch** : Interrupteurs et consommateurs
- **Cover** : Volets et stores (Fibaro, génériques)
- **Sensor** : Température, humidité, consommation, etc.
- **Binary Sensor** : Mouvement, porte, fumée, etc.
- **Climate** : Thermostats et consignes de température
- **Select** : Groupes de volets et automations virtuelles

### Devices Mappés
- **6+ types** de base (version 0.8.0)
- **8+ types** avec classes Z-Wave (version 0.9.0)
- **10+ types** avec thermostats (version 0.10.0)
- **12+ types** avec capteurs avancés (version 0.11.0)
- **14+ types** avec sélecteurs optimisés (version 0.12.0)

## 🔄 Stratégie de Versionnement

### Cycle de Développement
1. **Feature Branches** : Développement dans des branches dédiées
2. **Pull Requests** : Revue de code et tests
3. **Merge vers Main** : Intégration des fonctionnalités stables
4. **Release Tags** : Versionnement sémantique (v0.8.0, v0.9.0, etc.)

### Branches Actives
- **main** : Version stable actuelle
- **feature/improved-entity-mapping-and-battery-sensors** : Développement en cours
- **feature/scene-to-select-refactor** : Migration Scene→Select
- **feature/dual-api-modes** : Support des modes API duales

## 📋 Roadmap Future

### Prochaines Améliorations
- **Version 0.13.0** : Support des scènes avancées et automations
- **Version 0.14.0** : Intégration avec les tableaux de bord énergie
- **Version 0.15.0** : Support des notifications et alertes
- **Version 1.0.0** : Version stable avec documentation complète

### Fonctionnalités Planifiées
- **Amélioration des performances** pour les grands systèmes
- **Support étendu** des périphériques Z-Wave
- **Intégration** avec d'autres systèmes domotiques
- **Tableau de bord** de surveillance avancé

## 🎯 Recommandations

### Pour les Utilisateurs
- **Utilisez la branche main** pour une expérience stable
- **Testez les feature branches** pour les nouvelles fonctionnalités
- **Signalez les bugs** via les issues GitHub
- **Consultez la documentation** pour la configuration

### Pour les Développeurs
- **Créez des feature branches** pour les nouvelles fonctionnalités
- **Suivez le guide de contribution** pour la cohérence
- **Documentez** les changements et les nouvelles fonctionnalités
- **Testez** avant de créer une pull request

## 🔒 Versionnement Sémantique

Nous suivons le versionnement sémantique [SemVer](https://semver.org/):
- **MAJOR** : Changements incompatibles
- **MINOR** : Ajout de fonctionnalités rétrocompatibles
- **PATCH** : Corrections de bugs rétrocompatibles

## 📊 Historique des Releases

| Version | Date | Statut | Changements Majeurs |
|---------|------|--------|---------------------|
| 0.12.0 | 2025 | Dev | Capteurs batterie, climate amélioré |
| 0.11.0 | 2025 | Dev | Migration Scene→Select |
| 0.10.0 | 2025 | Dev | Support des thermostats |
| 0.9.0 | 2025 | Dev | Refonte du mapping |
| 0.8.0 | 2025 | Dev | Support des scènes |

## 📋 Notes de Migration

### Depuis les Versions Précédentes
1. **Vos configurations** continueront de fonctionner
2. **Testez d'abord** dans un environnement de développement
3. **Surveillez les logs** pour les messages de mapping
4. **Ajustez si nécessaire** pour les périphériques spécifiques

### Recommandations de Migration
- **Lisez la documentation** pour les nouvelles fonctionnalités
- **Consultez le guide** de migration spécifique
- **Testez chaque étape** avant la mise en production
- **Faites des sauvegardes** avant les mises à jour majeures

## 🎉 Conclusion

Ce projet suit un développement actif avec des améliorations continues.
Les diagrammes Mermaid et la documentation complète facilitent la compréhension
et l'utilisation de l'intégration eedomus avec Home Assistant.

Pour les dernières mises à jour, consultez toujours le dépôt GitHub officiel.