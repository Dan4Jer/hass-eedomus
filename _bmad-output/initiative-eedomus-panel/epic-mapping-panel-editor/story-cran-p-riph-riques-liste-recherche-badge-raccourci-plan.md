---
title: "P.1.3 Écran Périphériques (liste, recherche, badge, raccourci)"
type: 'feature'
ticket: 3
created: '2026-09-27'
status: done
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
baseline_revision: 'b690bc4'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Le webcomponent servi (`eedomus-panel.js`) est un squelette non thémé qui n'affiche rien — aucun moyen de voir les périphériques et leur mapping depuis HA.

**Approach:** Onglet Périphériques conforme au mock-01 et à EXPERIENCE.md : liste des périphs (nom, usage_id, entité HA, mapping courant) depuis `coordinator.data` via une nouvelle commande websocket `eedomus/get_peripherals` (admin only), recherche nom/usage_id temps réel, filtre « Périphériques touchés » (aria-live), badge modifié accessible (aria-label nominatif), action « Créer une règle pour ce périphérique » basculant sur Règles avec usage_id pré-rempli. Thème HA par variables CSS uniquement, reflow mobile 360px.

</frozen-after-approval>

## Implementation Notes

Investigation (2026-09-27) :

- Backend : `eedomus/get_peripherals` (5e commande ws, `WS_COMMANDS` à 5 entrées, dispatchers module-level `@require_admin` + `@websocket_command` + `@async_response`). Le handler projette `coordinator.data` de tous les coordinators d'entry (multi-box : `hass.data[DOMAIN]` mélange services de domaine et dicts d'entry contenant `COORDINATOR`).
- Mapping courant lu depuis l'état HA réel de l'entité résolue (`coordinator._resolve_main_entity_id`, réutilise la sémantique du history : match exact `<entry>_<periph_id>` puis repli suffixé) : entity_id, platform (domaine), `device_class`, `unit_of_measurement` via `hass.states.get`.
- Badge « modifié » : config YAML mergée du coordinator (`get_yaml_config_sync`, dégradation silencieuse si non chargée) — `usage_id_mappings` direct → « mapping personnalisé {usage_id} » ; `advanced_rules` (condition.usage_id) → nom de la règle ; date = `metadata.last_modified`. La grammaire mergée vient de `load_yaml_mappings_async` (custom_usage_id_mappings → usage_id_mappings, custom_rules → advanced_rules).
- Frontend : réécriture complète de `www/eedomus-panel.js` (vanilla, shadow DOM) : 3 onglets persistants avec état dans l'URL (`location.hash` + listener `hashchange` pour retour/arrière), skeletons/vides/erreur avec bouton « Réessayer », compte de résultats en `role="status"`, filtre `aria-pressed` avec compte rafraîchi, badge `aria-label` nominatif (jamais la couleur seule), Échap vide la recherche, cibles ≥ 44px, `@media (max-width: 900px)` reflow deux niveaux (identité/mapping, action pleine largeur), échappement HTML systématique.
- Raccourci « Créer une règle » : stocke `_pendingRuleUsageId` + bascule onglet Règles ; le placeholder affiche l'usage_id pré-rempli (vérifiable en P.1.3, consommé par le formulaire en P.1.4).
- Onglets Règles/Historique : placeholders (éditeurs en P.1.4-P.1.6) ; Historique affiche déjà son état vide EXPERIENCE (« Aucune sauvegarde encore… »).

## Review Triage Log

Review quick (self), itération 1 :

- [checked] `hass.callWS` est l'API supportée pour une commande ws custom depuis un panneau (`hass` est injecté par `panel_custom`).
- [medium, defer→P.1.4] Le raccourci pré-remplit via `_pendingRuleUsageId` ; le formulaire Règles doit le consommer et le purger à l'usage.
- [low, defer→P.1.4] `get_suggestions` dynamique reste vide (data_service lit `hass.data[DOMAIN]['coordinator']` jamais posé) — sans impact ici, l'écran n'utilise pas les suggestions.
- [low, defer→P.1.7] L'état d'onglet par hash fonctionne pour retour/arrière mais n'est pas un vrai routeur HA (`hass.navigate`) ; à réévaluer quand les 3 onglets existent.
- [checked] Performance : `_resolve_main_entity_id` scanne le registry par périph (~165 × registry) — un appel one-shot au chargement de l'onglet, acceptable ; à optimiser en index unique si la commande devient un poll.
- [checked] XSS : toutes les valeurs dynamiques passent par `_escapeHtml` (nom de périphérique, entity_id, aria-label du badge).

- [high, patch — découvert en vérification LIVE] 165/165 périphs marqués « modifiés » : le badge lisait le config **mergé** (`get_yaml_config_sync`), dont `usage_id_mappings` contient aussi le mapping par défaut — donc tout match. Corrigé : le handler charge maintenant le custom mapping **brut** (`device_mapping.load_custom_yaml_mappings_async`, une fois par appel) et le badge ne reflète plus que les overrides utilisateur (`custom_usage_id_mappings` / `custom_rules`). Test ajouté : un custom mapping vide → aucun badge, quel que soit le défaut. Leçon : « mergé » ≠ « ce que l'utilisateur a modifié ».

## Verification

**Commands:**

- `python3 -m pytest tests/unit -q` -- expected: 123 verts (dont 7 nouveaux get_peripherals)
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: OK
- `uv run --with black --no-project black --check custom_components/eedomus/ui_service.py tests/unit/test_ui_service.py` -- expected: propre
- `uv run --with flake8 --no-project flake8 custom_components/eedomus/ui_service.py` -- expected: vide

**Manual checks (déploiement requis) :**

- `eedomus/get_peripherals` en live : ~165 lignes, JSON valide, entités résolues
- Onglet Périphériques dans la sidebar : liste, recherche, filtre touchés, badge, raccourci (vérification visuelle par l'utilisateur)
- Reflow mobile 360px, thème clair/sombre suivis (variables HA)
