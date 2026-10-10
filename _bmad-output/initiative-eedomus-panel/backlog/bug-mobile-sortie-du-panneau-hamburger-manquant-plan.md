---
ticket: "116"
status: built
---

# Plan — ticket 116 (mobile menu escape, issue #125)

Built 2026-10-10 inline by the orchestrator (oneshot-sized fix, plan written post-build).

## What was built

- `shared.js`: `menuButtonHtml(t)` (pure markup, aria-label from the i18n catalog, `data-action="toggle-menu"`, hamburger SVG) + `MENU_BUTTON_STYLES` (hidden by default, shown only at the 900px narrow media — same value as `COHERENCE_NARROW_PX`, equality pinned by the node test; 44px target).
- `eedomus-panel.js`: import + `${MENU_BUTTON_STYLES}` in the base styles + `${menuButtonHtml(this._t)}` as the first child of `.panel` + `_onClick` branch dispatching `new Event('hass-toggle-menu', { bubbles: true, composed: true })`.
- `panel_translations.py`: `panel.menu.aria` EN ("Open the Home Assistant menu") + FR ("Ouvrir le menu Home Assistant"); fixtures `panel-catalog.json` (both trees) and `panel-keys.json` updated (drift tests green).
- Tests: 7 node assertions (markup + styles + breakpoint equality); i18n drift checks green.

## Verification

- `python3 -m pytest tests/unit/ -q` — 432 passed.
- `node tests/js/test-coherence.js` — all green (226 PASS lines incl. the 7 new).
- Format gate (hook) — exit 0.

## Residual

- `hass-toggle-menu` is a HA-internal event name: the E2E live deploy must confirm the drawer opens on a real narrow viewport (the spine's documented check).
