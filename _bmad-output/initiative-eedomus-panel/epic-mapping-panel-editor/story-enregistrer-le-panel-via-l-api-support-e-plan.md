---
title: "P.1.2 Enregistrer le panel via l'API supportée"
type: 'feature'
ticket: 2
created: '2026-09-27'
status: 'built'
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
baseline_revision: '20665e2'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `panel.py` appelait une API inventée (`PanelCustomConfigEntry` n'existe pas dans HA) et `frontend.yaml` n'est pas un mécanisme supporté — le panneau Eedomus n'apparaît pas dans la sidebar.

**Approach:** Réécrire `panel.py` sur l'API vérifiée dans le source HA 2026.9.3 : `http.StaticPathConfig` servant `www/`, `panel_custom.async_register_panel` (qui encapsule `frontend.async_register_built_in_panel` avec `component_name="custom"` et `_panel_custom.module_url`), `require_admin=True`. Branchement au setup (idempotent par flag dans `hass.data[DOMAIN]`), `frontend.async_remove_panel` à la suppression de la dernière entry. Supprimer `frontend.yaml` et le vieux code.

</frozen-after-approval>

## Implementation Notes

Investigation (2026-09-27) :

- Signatures vérifiées dans le source HA 2026.9.3 (GitHub tag 2026.9.3) :
  - `frontend.async_register_built_in_panel(hass, component_name, sidebar_title, sidebar_icon, sidebar_default_visible, frontend_url_path, config, require_admin, *, update, config_panel_domain, show_in_sidebar)` — lève ValueError sur écrasement (`update=False`).
  - `panel_custom.async_register_panel(hass, frontend_url_path, webcomponent_name, sidebar_title=, sidebar_icon=, module_url=, js_url=, embed_iframe=, trust_external=, config=, require_admin=, config_panel_domain=, handle_safe_area=)` — construit `config["_panel_custom"]` et appelle la précédente avec `component_name="custom"`.
  - `frontend.async_remove_panel(hass, frontend_url_path, *, warn_if_unknown=True)`.
  - `http.StaticPathConfig(url_path, path, cache_headers=True)` (définie dans `http/server.py`, réexportée par `homeassistant.components.http`) ; `hass.http.async_register_static_paths(configs)`.
- L'élément webcomponent servi est `eedomus-config-panel` (`customElements.define` dans `www/eedomus-panel.js`).
- Teardown placé dans `async_remove_entry` (pas `async_unload_entry`) : un reload décharge puis recharge l'entry, le panneau ne doit pas clignoter ; le panneau disparaît quand la dernière entry est supprimée.
- Tests : stubs `frontend`, `panel_custom` et `StaticPathConfig` ajoutés à `tests/unit/conftest.py` ; `tests/unit/test_panel.py` (7 tests) + wiring/teardown dans `test_init_domain_services.py`.

## Review Triage Log

Review quick (self), itération 1 :

- [checked] `component_name="custom"` + `_panel_custom.module_url` — sémantique confirmée dans `panel_custom/__init__.py` 2026.9.3 (async_register_panel est le wrapper officiel).
- [checked] Idempotence : `async_register_built_in_panel` lève ValueError sur écrasement → garde `panel_registered` dans `hass.data[DOMAIN]` (le reload d'entry ne re-enregistre rien).
- [checked] `cache_headers=False` sur StaticPathConfig : les assets changent à chaque release, pas d'en-tête de cache.
- [medium, defer→P.1.3] Le JS servi (`eedomus-panel.js`) est le stub existant (élément `eedomus-config-panel`) : l'écran Périphériques réel arrive au ticket P.1.3 ; P.1.2 ne couvre que l'apparition du panneau.
- [low, defer→P.1.7] `www/panel.html` et `www/eedomus-frontend-config.json` ne sont plus référencés par rien (l'html hardcodait `/local/custom_components/...`) — à supprimer au grand nettoyage P.1.7.

## Verification

**Commands:**

- `python3 -m pytest tests/unit -q` -- expected: 116 verts (dont 9 nouveaux panel/wiring)
- `uv run --with black --no-project black --check custom_components/eedomus/panel.py tests/unit/test_panel.py` -- expected: propre
- `uv run --with flake8 --no-project flake8 custom_components/eedomus/panel.py` -- expected: vide

**Manual checks (déploiement requis) :**

- Le panneau « Eedomus Config » apparaît dans la sidebar (admin only) — vérifiable via websocket `get_panels`
- `GET /local/eedomus/eedomus-panel.js` répond 200
- Aucun frontend.yaml, aucune erreur dans les logs au setup/reload
- À la suppression de la dernière entry : panneau retiré de `get_panels`
