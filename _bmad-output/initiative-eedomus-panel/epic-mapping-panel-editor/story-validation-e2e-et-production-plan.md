---
title: "P.1.7 Validation E2E et production"
type: 'story'
ticket: 7
created: '2026-09-28'
status: 'built'
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
baseline_revision: '5440932'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** La suite E2E ne couvre pas le panel ; le code contient des couches mortes accumulées (config_manager legacy .storage, data_service fantôme, assets www orphelins, scripts scp interdits par AD-10).

**Approach:** Suite E2E étendue (panel, commandes ws, save+auto-apply non destructif) + grand nettoyage production : suppression du code mort identifié au fil des tickets, sans toucher aux 7 commandes ws vivantes.

</frozen-after-approval>

## Implementation Notes

- **E2E (`tests/e2e/test_e2e_panel.py`, 8 tests)** : panneau dans `get_panels` (component custom, admin), asset JS servi, `get_peripherals` (retry — un reload d'entry concurrent vide `coordinator.data` quelques secondes, découvert quand les tests OptionsFlow de l'autre fichier rechargeaient l'entry), `get_mapping`, `get_mapping_versions`, `validate_config` sur le mapping courant, et le round-trip **save à l'identique** (persiste + recharge l'entry + ne change rien + n'archive rien — skip-if-identical vérifié). Fixture `ws_call` ajoutée au conftest E2E.
- **Supprimé** : `data_service.py` (entièrement mort : lisait `hass.data[DOMAIN]['coordinator']` jamais posé + `.get('peripherals')` inexistant — le cache stats renvoyait des zéros factices), la commande `eedomus/get_cache_stats` et son dispatcher (7 commandes restantes, toutes vivantes), `schema_service.get_dynamic_suggestions` simplifié en statique, `_async_load_custom_schemas` (aucun appelant réel, dépendait de config_manager mort).
- **config_manager dépoussiéré** : suppression du Store legacy `eedomus.config`, des listeners wildcard `{DOMAIN}.*`, de l'auto-save 5 min (le « Configuration saved successfully » fantôme des logs), et de toutes les méthodes mortes (save/get/update/yaml_content/reset/backup/restore). `async_init` = ingestion AD-13 + flag. Le save valide via la fonction de module `_validate_mapping_config`.
- **Supprimé** : `www/panel.html`, `www/eedomus-rich-editor.js`, `www/eedomus-frontend-config.json`, `www/manifest.json` (orphelins, seul `eedomus-panel.js` est servi), `scripts/deploy_history_fix.sh` + `scripts/deploy_and_analyze.py` (scp — violation AD-10, backlog 100).
- **Greffé en cours de ticket** (demande utilisateur) : le gate `enable_panel` vit dans le même déploiement (ticket P.1.10).
- Le teardown live du panneau (suppression de la dernière entry en prod) reste non testé en live (destructif) — couvert par les tests unit du ticket P.1.2.

## Review Triage Log

Review quick (self), itération 1 :

- [checked] Aucune commande ws vivante supprimée : le panel consomme validate/suggestions/schema/peripherals/mapping/save/versions — cache_stats était la seule morte et sa donnée était factice.
- [checked] `get_suggestions` survit (statique, plus de dépendance data_service) — l'API ws reste à 7 commandes enregistrées, tests de registration mis à jour.
- [checked] Les assets www supprimés ne sont référencés nulle part (module_url = eedomus-panel.js uniquement) ; le test d'assets vérifie désormais le seul fichier servi.
- [medium, defer→histoire #28 restante] Le parcours #28 a été validé par l'utilisateur en P.1.4 (flux complet) — la « cinématique complète en profondeur » que l'utilisateur veut tester reste un chantier manuel ouvert au-delà de l'épique.
- [low] `eedomus.config` storage existant sur les instances n'est pas purgé (fichier .storage orphelin, inoffensif) — pas de migration destructrice.

## Verification

**Commands:**

- `python3 -m pytest tests/unit -q` -- expected: 152 verts (registration 7 commandes, wiring 3 services)
- `python3 -m pytest tests/e2e -q` -- expected: 19 verts (12 + 8 panel, save auto-apply inclus)
- `uv run --with flake8 --no-project flake8 custom_components/eedomus/ui_service.py` -- expected: vide

**Manual checks (déploiement requis) :**

- Boot propre sans « Configuration saved successfully » fantôme ni « DataService initialized »
- 165 periphs / 100 dynamiques inchangés, E2E complète verte en prod
