# Intégration eedomus pour Home Assistant

[![HACS Validated](https://img.shields.io/badge/HACS-Validated-green.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-0.15.1-blue.svg)](https://github.com/Dan4Jer/hass-eedomus/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/Dan4Jer/hass-eedomus/blob/main/LICENSE)
[![Release](https://img.shields.io/github/v/release/Dan4Jer/hass-eedomus?label=latest)](https://github.com/Dan4Jer/hass-eedomus/releases/latest)

**hass-eedomus** synchronise votre box **eedomus** avec **Home Assistant** : les périphériques eedomus (Z-Wave, Zigbee...) remontent comme des entités natives Home Assistant (sensors, lights, covers, climate...), sans remplacer la box. Les états et commandes passent par l'API eedomus, avec un système de mapping YAML pour adapter chaque périphérique à vos besoins.

[English version](README.md)

## Fonctionnalités

- **Entités natives** : sensors, binary sensors, lights, covers, climate, selects, scenes
- **Multi-box** : installez l'intégration une fois par box eedomus (chaque instance est préfixée et routée indépendamment)
- **Modes de connexion duaux** : pull (API eedomus) et/ou push (webhook proxy) - combinables
- **Mapping YAML des périphériques** : surchargez les mappings par défaut sans toucher au code
- **Récupération d'historique** : import des valeurs historiques du cloud eedomus (optionnel, cadencé)
- **Fallback PHP** : mécanisme de retry automatique pour les valeurs rejetées par la box
- **Capteurs de diagnostic** : temps API, volume de données par endpoint, temps de traitement
- **Services** : refresh, set_value, reload, température climate, nettoyage d'entités
- **Configuration 100% interface** : config flow et options flow, aucun YAML requis

## Installation

### Via HACS (recommandé)

1. Installez [HACS](https://hacs.xyz/docs/setup/download) si nécessaire, redémarrez Home Assistant
2. Dans HACS, ajoutez un dépôt personnalisé : `https://github.com/Dan4Jer/hass-eedomus`
3. Recherchez "Eedomus" dans **HACS** > **Intégrations**, installez, redémarrez Home Assistant

### Manuel

1. Téléchargez la dernière [release](https://github.com/Dan4Jer/hass-eedomus/releases)
2. Extrayez dans `custom_components/eedomus/`
3. Redémarrez Home Assistant

## Configuration

**Réglages** > **Appareils et Services** > **Ajouter une intégration** > recherchez "Eedomus" :

| Champ | Requis | Description |
|-------|--------|-------------|
| `api_host` | oui | Adresse IP de votre box eedomus (ex. `192.168.1.2`) |
| `api_user` | mode API | Utilisateur API eedomus (dans les réglages de la box) |
| `api_secret` | mode API | Secret API eedomus |
| `api_eedomus` | oui | Activer le mode pull (API) |
| `enable_api_proxy` | oui | Activer le mode push (webhook) |

Au moins un des modes `api_eedomus` / `enable_api_proxy` doit être activé.

### Modes de connexion

- **API Eedomus (pull)** : Home Assistant interroge la box. Nécessite les identifiants API. Fonctionnalité complète, y compris l'historique.
- **API Proxy (webhook, push)** : la box pousse ses mises à jour vers Home Assistant en quasi temps réel. Fonctionnalités limitées (pas d'historique).
- **Combiné (recommandé)** : les deux modes ensemble, redondance et réactivité.

## Options

**Réglages** > **Appareils et Services** > Eedomus > **Configurer** :

| Option | Type | Défaut | Description |
|--------|------|--------|-------------|
| `api_eedomus` | booléen | `true` | Mode pull via l'API eedomus |
| `enable_api_proxy` | booléen | `false` | Mode push via webhook |
| `enable_webhook` | booléen | `true` | Enregistre l'endpoint webhook (requis par le mode proxy) |
| `enable_history` | booléen | `false` | Import des valeurs historiques du cloud eedomus |
| `history_peripherals_per_scan` | entier | `5` | Périphériques traités par scan d'historique (cadencement) |
| `scan_interval` | entier | `300` | Intervalle de polling en secondes |
| `enable_set_value_retry` | booléen | `true` | Retry des valeurs rejetées par la box |
| `api_proxy_disable_security` | booléen | `false` | Désactive la validation IP des webhooks (debug uniquement, déconseillé) |
| `php_fallback_enabled` | booléen | `false` | Fallback par script PHP pour les valeurs rejetées |
| `php_fallback_script_name` | texte | `fallback.php` | Nom du script de fallback sur la box |
| `php_fallback_timeout` | entier | `5` | Timeout des requêtes de fallback (secondes) |
| `http_request_timeout` | entier | `10` | Timeout des requêtes vers l'API eedomus (secondes) |

`scan_interval` recommandé : 30-60 s pour tester, 300 s (défaut) en production, 600-900 s pour les grosses installations.

## Multi-box

Vous pouvez installer plusieurs instances de l'intégration, une par box eedomus (ex. résidence principale et secondaire). Chaque instance :

- possède sa propre config entry et ses propres identifiants API
- préfixe ses entités et unique IDs pour éviter les collisions
- a ses propres options (modes de connexion, intervalle, etc.)
- route les services (`set_value`, `refresh`...) vers sa propre box

Les services acceptent une cible : passez l'entité ou la config entry pour choisir la box concernée.

## Mapping YAML des périphériques

Les mappings sont définis en YAML et chargés au démarrage :

- `custom_components/eedomus/config/device_mapping.yaml` - mapping par défaut (ne pas modifier, écrasé par les releases)
- `custom_components/eedomus/config/custom_mapping.yaml` - vos surcharges (préservées lors des mises à jour)

Priorité des mappings : règles avancées (conditions parent/enfants, usage IDs, noms) > `usage_id_mappings` > `name_patterns` > `default_mapping`.

```yaml
# custom_mapping.yaml
custom_usage_id_mappings:
  99:
    ha_entity: sensor
    ha_subtype: custom
    icon: mdi:custom-icon
```

Les règles custom surchargent les règles par défaut de même nom ; les nouvelles règles s'ajoutent. Voir [YAML_UI_MAPPING_GUIDE.md](docs/YAML_UI_MAPPING_GUIDE.md) pour la grammaire complète.

## Services

| Service | Description |
|---------|-------------|
| `eedomus.refresh` | Force un refresh complet de tous les périphériques |
| `eedomus.set_value` | Définit une valeur de périphérique (`device_id`, `value`) |
| `eedomus.reload` | Recharge l'intégration |
| `eedomus.set_climate_temperature` | Définit la température d'une entité climate |
| `eedomus.cleanup_unused_entities` | Supprime les entités eedomus désactivées/orphelines |
| `eedomus.cleanup_unused_devices` | Supprime les devices eedomus orphelins |

## Tests

La suite de tests tourne en local, sans installation de Home Assistant :

```bash
pip install -r requirements-test.txt

# Tests unitaires (56) : règles de mapping, client API, options flow, fusion YAML
python3 -m pytest tests/unit/ -v

# Tests E2E (12) : instance réelle via API REST - connectivité, refresh,
# set_value, options flow. Nécessite HA_TOKEN dans .env et une instance HA joignable
python3 -m pytest tests/e2e/ -v
```

La suite E2E est non destructive : elle bascule le périphérique de test et restaure son état initial.

## Dépannage

- **L'intégration ne se charge pas** : vérifiez les identifiants API et l'IP de la box, puis les logs (filtre `custom_components.eedomus`)
- **Valeurs non appliquées** : pour les périphériques dimmable, la box attend des valeurs numériques (`0` = éteint, `100` = allumé)
- **Entités manquantes** : lancez `eedomus.cleanup_unused_entities`, puis rechargez ; vérifiez la table de mapping dans les logs
- **Capteurs history indisponibles** : activez l'option `enable_history` et attendez le premier cycle de scan

## Documentation

- [README.md](README.md) - Documentation en anglais
- [CHANGELOG.md](docs/CHANGELOG.md) - Historique des versions
- [configuration_documentation.md](docs/configuration_documentation.md) - Configuration détaillée (EN)
- [configuration_documentation_fr.md](docs/configuration_documentation_fr.md) - Configuration détaillée (FR)
- [OPTIONS_DOCUMENTATION.md](docs/OPTIONS_DOCUMENTATION.md) - Référence des options
- [YAML_UI_MAPPING_GUIDE.md](docs/YAML_UI_MAPPING_GUIDE.md) - Grammaire des règles de mapping

## Licence

MIT - voir [LICENSE](LICENSE)

---

Créée et maintenue par [@Dan4Jer](https://github.com/Dan4Jer)
