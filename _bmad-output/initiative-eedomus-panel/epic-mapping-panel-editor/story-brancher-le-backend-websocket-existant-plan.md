---
title: "P.1.1 Brancher le backend websocket existant"
type: 'feature'
ticket: 1
created: '2026-09-27'
status: 'built'
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
baseline_revision: '13dbdf7'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Les 4 commandes websocket du panel (`eedomus/validate_config`, `get_suggestions`, `get_schema`, `get_cache_stats`) sont mortes : `_async_init_ui_service` et les trois helpers qu'il dépend de (`config_manager`, `data_service`, `schema_service`) ne sont jamais appelés au setup. En plus, les handlers n'appellent jamais `connection.send_result`/`send_error` (le frontend attendrait indéfiniment) et le code suppose que `async_register_command` retourne une fonction de désenregistrement (il retourne None).

**Approach:** Brancher la famille de services au setup dans l'ordre des dépendances (config_manager → data_service → schema_service → ui_service), les stocker dans `hass.data[DOMAIN]` (clés de domaine attendues par `_get_schema_service` etc.), corriger les handlers pour répondre au client websocket, et rendre l'enregistrement idempotent (rechargement de l'entry sans doublon ni crash). Les commandes ne sont PAS désenregistrées à l'unload : elles sont au niveau du domaine et leurs handlers tolèrent les données absentes.

</frozen-after-approval>

## Implementation Notes

Investigation (2026-09-27) :
- `__init__.py` : les 4 helpers `_async_init_*` (lignes 76-111) n'ont AUCUN appelant. `async_setup_entry` construit entry_data (ligne 456 `hass.data[DOMAIN][entry.entry_id] = entry_data`) mais n'appelle jamais les helpers. `async_unload_entry` (ligne 615) pop l'entry du hass.data.
- `ui_service.py` : handlers `(self, hass, connection, msg)` — signature HA correcte, mais zéro `send_result`/`send_error` (grep vide). `async_register_command(hass, type, handler)` : schema optionnel = OK dans HA 2026.9.3 (vérifié dans le source, ligne 48) ; retour = None → la liste `_registered_commands` stocke des None et le shutdown no-op.
- Dépendances par lookups `hass.data[DOMAIN]['schema_service'/'data_service'/'config_manager']` (clés de DOMAINE, pas d'entry) : ui_service → schema_service → (config_manager, data_service). Donc brancher les 4, dans cet ordre.
- `schema_service.py` lit `hass.data[DOMAIN]['config_manager']` (ligne 82) et `['data_service']` (194) — mêmes clés de domaine.
- HA 2026.9.3 : ré-enregistrer une commande websocket existante lève une erreur → garder une instance de UIService dans `hass.data[DOMAIN]['ui_service']` et ne ré-enregistrer que si absente ; au reload, réutiliser l'instance existante (les handlers lisent hass.data dynamiquement).

## Review Triage Log

Review quick, 1 lens, itération 1 (7 findings) :

- [low, patch] E501 ligne 92c dans ui_service.py:82 — corrigé (string scindée).
- [medium, patch] Enregistrement en échec jamais retenté + log de succès inconditionnel — corrigé : garde is_initialized(), retry async_init si non initialisé, log prêt seulement si initialisé ; test de retry ajouté.
- [false] « Signature async_register_command invérifiable » — vérifiée directement dans le source HA 2026.9.3 (schema: None par défaut, ligne 48-53) ; sous-point valide (pas de validation d'entrée sans schema) reporté aux tickets éditeur (P.1.4).
- [medium, defer→P.1.4] data_service lit hass.data[DOMAIN]['coordinator'] (clé de domaine jamais posée — le coordinator est par entry) : les suggestions device/usage_id seront vides jusqu'à correction ; bug préexistant activé par le branchement, la correction (sémantique multi-box) appartient au travail autocomplete du ticket P.1.4.
- [maybe-false, defer→P.1.7] ConfigManager : listener wildcard "{DOMAIN}.*" possiblement invalide + lecture interne Store._data — probablement non-fatal (le wildcard ressemble à un entity_id valide), fragilité à confirmer au premier déploiement réel.
- [low, defer→P.1.7] async_shutdown jamais appelé : timers 30min/5min et listener persistent après retrait de la dernière entry — cohérent avec la décision « commandes non désenregistrées », à vérifier au déploiement.
- [false] « Diff sans les nouveaux tests » — artefact de staging, pas un défaut de code : les tests existent et sont committés avec le reste.

## Verification

**Commands:**

- `python3 -m pytest tests/unit -q` -- expected: 100 verts (dont 24 nouveaux de branchement/handlers)
- `uv run --with flake8 --no-project flake8 custom_components/eedomus/ui_service.py` -- expected: vide (propre)

**Manual checks (déploiement requis, ticket P.1.7 ou prochain deploy):**

- Websocket live vers eedomus/get_schema : réponse JSON
- Reload de l'entry : aucune erreur "already registered"
