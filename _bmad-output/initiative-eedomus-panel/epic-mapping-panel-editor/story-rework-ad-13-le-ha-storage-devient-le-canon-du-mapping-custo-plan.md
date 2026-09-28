---
title: "P.1.8 Rework AD-13 — le HA storage devient le canon du mapping custom"
type: 'feature'
ticket: 8
created: '2026-09-28'
status: 'built'
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
baseline_revision: '0499ec2'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Le mécanisme P.1.4 (fichier config-dir = source de vérité) contredit AD-13 du spine : le runtime doit lire le HA storage (canon), le fichier YAML rester une surface d'édition manipulable par l'utilisateur, dont les modifications sont ingérées comme de nouvelles versions au chargement.

**Approach:** Implémenter AD-13 : Store `eedomus.mapping` (`current` + `file_fingerprint`) lu par tout le runtime ; ingestion en tête de `async_setup_entry` (avant toute lecture du mapping) et à l'init du ConfigManager ; save UI écrit canon + miroir + fingerprint. L'API ws (`get_mapping`/`save_mapping`) ne change pas.

</frozen-after-approval>

## Implementation Notes

Investigation (2026-09-28) :

- **Ordonnancement critique** : le coordinator cache son YAML de mapping AVANT `_async_setup_domain_services`, et le ConfigManager est réutilisé au reload d'entry (l'ingestion dans `async_init` ne rejouerait qu'au redémarrage HA). L'ingestion est donc une **fonction de module** (`config_manager.async_ingest_custom_mapping(hass)`) appelée **en tête de `async_setup_entry`** — avant le coordinator — idempotente par fingerprint, rejouée à chaque reload.
- `device_mapping` : `read_custom_mapping_file(paths)` retourne (texte, dict) — (None, None) si absent, (texte, None) si non parsable ; `async_get_canonical_custom_mapping(hass)` lit le storage d'abord, repli fichier (bootstrap avant ingestion) ; `load_custom_yaml_mappings_async` devient ce canon (badge P.1.3 et save P.1.4 suivent sans changement de code) ; le loader **sync** (`load_custom_yaml_mappings`) reste une lecture fichier (import-time, pas de hass).
- `config_manager` : `mapping_store` (`eedomus.mapping`), ingestion module-level (bootstrap fichier → canon initial ; texte ≠ fingerprint → validation → nouvelle version + archive de l'ancien canon (cap 3) ; invalide/non parsable → canon conservé + miroir régénéré + warning ; fichier absent → miroir régénéré). Save : validation → archive du canon remplacé **seulement si le contenu change** (un save sans changement ne crée pas une version) → `current` + fingerprint du texte dumpé → réécriture du miroir → au reload suivant le diff est nul (pas de double version).
- Les chemins candidats de l'ingestion : fichier config-dir d'abord (via `hass.config.config_dir`), fichier intégré en dernier recours (seed).
- Bootstrap prod : le storage `eedomus.mapping` est vide au premier boot post-rework → le fichier config-dir (migré en P.1.4) devient le canon initial → comportement inchangé.

## Review Triage Log

Review quick (self), itération 1 :

- [checked] Ingestion rejouée par reload d'entry ET par redémarrage — les deux chemins sont couverts (setup en tête + init ConfigManager), idempotence par fingerprint.
- [checked] Un save UI écrit miroir = texte dumpé = fingerprint → le reload qui suit l'auto-apply ne re-ingère rien (pas de version parasite après chaque save).
- [checked] Édition manuelle valide : le texte brut devient le fingerprint (le formatage manuel est préservé, le miroir n'est pas réécrit sur ingestion valide).
- [low, defer→P.1.6] La vue Historique lira `versions` via `async_get_mapping_versions` — l'UI reste à construire ; le socle (archivage save + ingestion manuelle) est en place.
- [low, defer→P.1.7] L'ingestion valide n'actualise pas `metadata.last_modified` (badge date) pour les éditions manuelles — le badge montre la date du dernier save UI. À trancher avec P.1.6 (afficher l'horodatage de la version à la place).
- [checked] flake8 : les findings restants du fichier sont préexistants (W293/E501/F401 legacy) ; les ajouts sont black-compliants.

## Verification

**Commands:**

- `python3 -m pytest tests/unit -q` -- expected: 146 verts (dont 9 nouveaux : 6 ingestion, 2 save/get reworkés, 1 wiring ingestion)
- `uv run --with flake8 --no-project flake8 tests/unit/test_config_manager.py tests/unit/test_init_domain_services.py` -- expected: vide

**Manual checks (déploiement requis) :**

- Boot : log « Custom mapping bootstrapped from the editable file », mapping identique (165 periphs / 100 dynamiques)
- `eedomus/get_mapping` : canon depuis le storage
- Édition manuelle du fichier sur le Pi (commentaire) + rechargement → « Custom mapping file ingested as a new version » + version archivée
- Fichier invalide + rechargement → warning, canon conservé, miroir régénéré
- Save ws à l'identique → aucune version supplémentaire
