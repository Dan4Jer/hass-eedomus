<!-- bmad:context -->
<!-- Verified 2026-10-04 against ce2f79f. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## hass-eedomus

Home Assistant custom integration for the Eedomus box (Python 3.9+, vanilla JS panel, no build toolchain). Planning and tickets live under `_bmad-output/` (specs, UX spines, `initiative-*/` ticket trees).

## Policy

- Deploy is git-only: push to `origin/unstable`, then `./.vibe/skills/hass-eedomus-deploy/deploy_hass_eedomus.sh`. Never scp, rsync, or edit files on the Pi.
- All text is English: log messages, docstrings, comments, and every user-facing label. French is available only as a translation, never as the hardcoded string.

## Where things are

- Core: `coordinator.py` (refresh + history import), `ui_service.py` (panel websocket commands).
- Panel frontend: `www/eedomus-panel.js` is the ES-module entry (the URL panel.py registers; it keeps the core: constructor/state, `t()` catalog loading, tab/hash navigation, `_render` shell, event delegation). It imports 7 modules from `www/panel/`: `shared.js` (cross-tab constants/helpers/mixin), one per tab — `peripheriques.js`, `regles.js`, `historique.js`, `coherence.js`, `supervision.js` — and `coherence-helpers.js` (coherence pure helpers; `coherence.js` imports and re-exports them).
- Starting a feature? Read `_bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md` (or `spec-eedomus-history/`) first — capabilities and constraints live there.

## Running and verifying

- Unit tests: `python3 -m pytest tests/unit/ -q`. Panel JS pure helpers: `node tests/js/test-coherence.js` (strict — wired into CI).
- E2E (`tests/e2e/`) needs `.env` with `HA_TOKEN` and the live Pi — never mock it.
- Formatting is enforced locally by the pinned pre-push hook and the deploy-script gate (`scripts/hooks/`, ticket 115): `uv run --no-project --with black==26.10.1 -- python -m black ...` and `isort==9.0.2` run in ephemeral uv environments. Run them over tracked Python files before committing; do not claim formatting was run unless it was.

## Conventions that differ from defaults

- User-facing strings go through HA's native i18n: backend via `strings.json` + `translations/en.json` (source of truth) and `translations/fr.json` (must stay structurally identical to en.json — today en.json lacks the `ui` section fr.json has). Custom panel strings come from a websocket strings command served by the backend, keyed by `hass.locale`, English fallback — never hardcoded in the JS.
- Commits follow `<type>(<scope>): <subject>` (see `.vibe/skills/hass-eedomus-coding-standards/`); the working tree stays clean per build.

## Known pitfalls

- The SSH log bridge (`get_rasp_logs.sh`) reports RUNNING while its stream is dead: if `~/…/rasp.log` stops moving, restart the bridge — status alone lies.
- The mapping registry is never cleared: devices re-register on every reload. Joins must be last-wins; a first-wins join shows the pre-change mapping.

<!-- /bmad:context -->

## Two E2E strates (AD-16)

- Live-Pi (`pytest tests/e2e/ -m "e2e and not e2e_sim"`): the regression truth — the real Pi, never mocked.
- Simulator (`pytest tests/e2e/ -m e2e_sim`): multi-box and destructive coverage — boots `scripts/simulateur/` on the Pi over SSH, drives the real config flow/REST/websocket APIs against a simulated box.
- The simulator strate completes the live one, never replaces it; Flask stays test-only (`requirements-test.txt`).
