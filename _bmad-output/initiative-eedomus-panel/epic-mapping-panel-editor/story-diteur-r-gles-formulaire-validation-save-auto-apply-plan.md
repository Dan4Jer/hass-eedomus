---
title: "P.1.4 Éditeur Règles — formulaire + validation + save auto-apply"
type: 'feature'
ticket: 4
created: '2026-09-27'
status: 'built'
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
baseline_revision: '7b26de6'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** L'onglet Règles est un placeholder ; aucune règle de mapping ne peut être créée, validée ni sauvegardée depuis HA, et le `config_manager` persistait dans le `.storage` HA que le pipeline de mapping ne lit jamais.

**Approach:** Onglet Règles mode Formulaire conforme au mock-02 : liste des règles + formulaire structuré (usage_id avec autocomplete, nom, plateforme, classe), validation temps réel via `eedomus/validate_config` (save désactivé tant qu'invalide), save → config_manager → auto-apply (reload de toutes les entries eedomus) avec feedback nominatif sur l'entité. Persistance **hors repo** (option B validée par l'utilisateur) : `<config_dir>/eedomus/custom_mapping.yaml`, prioritaire sur le fichier intégré ; archive des 3 versions dans le `.storage` HA (socle CAP-5, UI en P.1.6).

</frozen-after-approval>

## Implementation Notes

Investigation (2026-09-27) :

- **Persistance (décision utilisateur, option B)** : sur le Pi, `custom_components/eedomus` est un symlink vers le checkout git (`/homeassistant/custom_components/hass-eedomus`) — sauver dans le fichier intégré salirait le checkout de prod. `device_mapping.load_custom_yaml_mappings` lit désormais `<config_dir>/eedomus/custom_mapping.yaml` en priorité (via `homeassistant.core.async_get_hass`, repli fichier intégré sans HA), et `config_manager.async_save_custom_mapping` y écrit (validation schéma → archive de la version remplacée → write via executor).
- **Deux nouvelles commandes ws** (7 inscrites au total) : `eedomus/get_mapping` (mapping custom brut, jamais le mergé) et `eedomus/save_mapping` (write, admin) qui persiste puis **recharge chaque entry eedomus** (`hass.config_entries.async_reload`) — l'auto-apply est le reload, sans restart ni geste manuel.
- **Archive versions (CAP-5)** : `Store(hass, 1, "eedomus.mapping_versions")`, liste {timestamp, config} newest-first, cap 3 (la 4e purge la plus ancienne), exposée par `async_get_mapping_versions` pour l'UI P.1.6.
- **Grammaire du formulaire** : le pipeline applique réellement `custom_usage_id_mappings` → `{ha_entity, ha_subtype, justification}` ; les device_class/unit des sensors dérivent du `ha_subtype` (switch hard-codé dans sensor.py : temperature→°C, humidity→%, energy→Wh, power→W, time→h, cpu→%, disk_free_space→B, text→aucun). Le formulaire édite donc usage_id + nom (justification) + plateforme (ha_entity) + classe (ha_subtype) — la correction « capteur de température » de la discussion #28 (device_class + unité) passe par la classe. state_class/priorité du mock-02 ne sont pas portés par la grammaire appliquée : non éditables en mode formulaire (le mode YAML P.1.5 couvrira la grammaire brute).
- **Frontend** : liste des règles avec modifier/supprimer (suppression en deux gestes), formulaire avec autocomplete natif datalist (usage_id ← périphs chargés), validation à la frappe (debounce 350 ms, fragment YAML sérialisé par un mini-dumper et envoyé à `eedomus/validate_config` ; le save revalide le document complet côté serveur via config_manager), save désactivé tant qu'invalide, états « Sauvegarde… » / « Application… » / feedback nominatif (« Règle appliquée. {entity_id} est maintenant en {unit}. ») via re-fetch des périphs, erreur de save → formulaire conservé + nouvelle tentative, Échap annule, consommation du `_pendingRuleUsageId` du raccourci Périphériques (usage_id pré-rempli, purgé à l'usage).
- Le fichier custom_mapping.yaml actuel (vérifié) passe le schéma et round-trip proprement ; ses commentaires YAML seront perdus à la première sauvegarde (safe_dump ne les porte pas).

## Review Triage Log

Review quick (self), itération 1 :

- [checked] config_manager écrivait dans `.storage` (jamais lu par le pipeline) — remplacé par l'écriture fichier config-dir ; l'ancien chemin `.storage` (store `eedomus.config`, listeners wildcard, auto-save 5 min) est du code mort préexistant, candidat à la suppression en P.1.7.
- [medium, defer→P.1.7] Le reload d'entry dans le handler save recrée le ConfigManager/UIService pendant l'exécution du handler — sans effet sur la réponse (dispatchers lus dynamiquement), à surveiller si le reload échoue (feedback d'erreur actuel : message ws).
- [medium, defer→P.1.5] La validation à la frappe ne couvre que le fragment de la règle éditée ; le document complet est validé au save (config_manager) — l'éditeur YAML P.1.5 validera le document entier à la frappe.
- [low, defer→P.1.6] `metadata.last_modified` mis à jour par le save du panel ; les écritures manuelles du fichier ne le font pas (le badge date peut être périmé après édition manuelle).
- [checked] XSS : valeurs du formulaire et de la liste échappées ; usage_id en clé dict d'un objet JS (pas de YAML injection — le mini-dumper quote systématiquement en JSON).
- [checked] Les sections non éditées du mapping (custom_rules, custom_devices, temperature_setpoint_mappings...) sont transportées telles quelles par le save (clone du get_mapping, seule la section éditée change).

- [high, patch — découvert en vérification LIVE] Le **merge loader** (`load_yaml_mappings_async`/`load_yaml_mappings`, celui qui pilote le mapping réel des entités) chargeait encore le fichier custom **intégré** directement : un save du panel aurait été ignoré par le pipeline — masqué dans le round-trip live par un contenu identique. Corrigé (013a2a5) : les deux loaders passent par `load_custom_yaml_mappings[_async]` (priorité config-dir). Test de non-régression : une entrée du fichier config-dir apparaît dans le `usage_id_mappings` mergé. Live après fix : boot propre, 100 periphs dynamiques préservés, E2E 12/12. Leçon : vérifier le chemin LECTURE du pipeline, pas seulement celui d'écriture.

## Verification

**Commands:**

- `python3 -m pytest tests/unit -q` -- expected: 137 verts (dont 13 nouveaux : 8 config_manager/paths, 5 handlers)
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: OK
- `uv run --with black --no-project black --check tests/unit/...` -- expected: propre
- `uv run --with flake8 --no-project flake8 custom_components/eedomus/ui_service.py tests/unit/...` -- expected: vide

**Manual checks (déploiement requis) :**

- `eedomus/get_mapping` live : retourne le custom mapping actuel
- Save à l'identique (round-trip sans changement de comportement) : fichier créé dans `<config_dir>/eedomus/`, version archivée, entries rechargées, mapping identique
- Flux #28 par l'UI (validation utilisateur) : créer la règle capteur de température, erreur de schema → save désactivé, après save l'entité change d'unité
