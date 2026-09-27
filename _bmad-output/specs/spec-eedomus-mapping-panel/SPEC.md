---
id: SPEC-eedomus-mapping-panel
companions: [../../planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md]
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Side panel Eedomus — éditeur UI du mapping custom avec aide à la saisie

## Why

**Douleur à résoudre (discussion #28) + dette technique existante.** Un utilisateur demande des outils pour paramétrer les périphériques détectés (types de sensors, unités de mesure). La réponse actuelle est le mapping YAML custom (`custom_mapping.yaml`) — puissant mais uniquement éditable à la main, ce qui exclut les utilisateurs non techniques. Le code contient déjà un panneau et un backend d'aide à la saisie, mais les deux sont **débranchés** : `panel.py` n'est jamais appelé et repose sur une API HA inexistante (`panel_custom.async_register_panel`), `_async_init_ui_service` n'est jamais invoqué, les assets `www/` sont des squelettes non thémés, et `frontend.yaml` n'est pas un mécanisme HA réel. HA 2026.9.3 offre un mécanisme de panneau supporté et éprouvé (`async_register_built_in_panel` + `StaticPathConfig`, pattern utilisé par 412 intégrations custom), vérifié dans le source. Les AD cités sont ceux du companion `ARCHITECTURE-SPINE.md`.

## Capabilities

- **CAP-1 — Panneau dans la barre latérale**
  - **intent:** Un panneau « Eedomus Config » apparaît dans la barre latérale de HA, réservé aux administrateurs, enregistré par le mécanisme supporté et retiré proprement au déchargement.
  - **success:** Après le setup de l'intégration, le panneau s'affiche dans la sidebar et fonctionne ; à l'unload il disparaît ; aucune erreur dans les logs ; aucun `frontend.yaml`.

- **CAP-2 — Liste des périphériques**
  - **intent:** Le panneau liste les périphériques eedomus avec leur `usage_id`, leur nom et leur mapping courant (entité HA, `device_class`, unité), lu depuis `coordinator.data`.
  - **success:** Les ~165 périphériques de l'instance s'affichent avec leur mapping, recherche/filtrage par nom ou `usage_id` fonctionnel.

- **CAP-3 — Édition du mapping avec aide à la saisie**
  - **intent:** L'utilisateur crée, modifie et supprime des règles de mapping custom depuis l'UI, dans les deux modes — formulaire structuré par règle et édition YAML brut — avec autocomplete (`usage_id`, `device_class`, unité) et validation temps réel via les commandes websocket existantes (`ui_service.py` : validate / suggestions / schema).
  - **success:** La règle « capteur de température » de la discussion #28 se crée entièrement par l'UI ; une règle invalide est signalée avant sauvegarde, jamais silencieusement acceptée.

- **CAP-4 — Sauvegarde et application automatique**
  - **intent:** La sauvegarde persiste les règles dans `custom_mapping.yaml` via `config_manager` puis auto-applique : le rechargement de l'intégration est déclenché, le mapping prend effet immédiatement.
  - **success:** Une règle sauvée survit à un redémarrage HA et change effectivement l'entité concernée (ex. : une unité corrigée s'affiche corrigée dans HA après sauvegarde).

- **CAP-5 — Historique et restauration des 3 dernières versions**
  - **intent:** Chaque sauvegarde archive la version précédente du mapping (horodatée) dans le `.storage` HA ; le panel affiche les 3 dernières versions et permet de restaurer l'une d'elles en un clic — la restauration emprunte le chemin d'application de CAP-4 et archive la version qu'elle remplace ; seules les 3 dernières sont conservées.
  - **success:** Après 3+ sauvegardes, le panel montre exactement 3 versions horodatées ; restaurer la version précédente remet son contenu et l'applique ; la 4e sauvegarde purge la plus ancienne.

## Constraints

- Enregistrement du panneau **exclusivement** via l'API supportée HA 2026.9.3 — `async_register_built_in_panel(component_name="custom", config={"_panel_custom": {"module_url": ...}})` + `StaticPathConfig` pour servir les assets depuis le répertoire de l'intégration. Jamais d'API inventée ; `panel.py` actuel et `frontend.yaml` sont remplacés.
- Frontend thémé HA : variables CSS de HA (`--primary-text-color`, etc.), pas de style codé en dur ; custom element JS vanilla **sans toolchain de build**, servi depuis le répertoire de l'intégration.
- Réutilisation du backend existant — brancher, ne pas réinventer : les commandes websocket `ui_service.py` (`eedomus/validate_config`, `eedomus/get_suggestions`, `eedomus/get_schema`, cache stats) et `config_manager.py` pour la persistance.
- Le `coordinator` reste l'unique point d'accès aux données eedomus (AD-7) ; la lecture de config passe par `_get_config_value` (AD-9).
- `require_admin: true` sur le panneau et sur toute commande websocket d'écriture.

## Non-goals

- Pas un éditeur YAML généraliste : seule la grammaire du mapping custom est éditable.
- Pas d'édition de l'entity registry (noms, icônes, zones HA).
- Pas d'UI pour l'historique/backfill (épique séparé `eedomus-history`).
- Aucune écriture vers la box eedomus depuis le panneau (lecture `coordinator.data` + mapping uniquement).
- Pas de toolchain de build JS (webpack, npm) — assets vanilla livrés dans le repo.

## Success signal

Un utilisateur comme celui de la discussion #28 corrige le type et l'unité d'un capteur depuis la barre latérale de HA, sans jamais ouvrir un fichier YAML, et voit le changement appliqué immédiatement.

## Assumptions

- La grammaire du mapping YAML custom (conditions `usage_id`/regex, `mapping` ha_entity/device_class/unit/state_class/priority — documentée dans la discussion #28) reste la source de vérité ; le panneau l'édite, ne la remplace pas.
- Instance HA 2026.9.3+ (API panel vérifiée dans le source de cette version).
