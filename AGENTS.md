<!-- bmad:context -->
<!-- Verified 2026-11-01 against 9636e1b. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## hass-eedomus

Home Assistant custom integration for the Eedomus box (Python 3.9+, vanilla JS panel, no build toolchain). Planning and tickets live under `_bmad-output/` (specs, UX spines, `initiative-*/` ticket trees).

## Policy

- Deploy is git-only: push to `origin/unstable`, then `./.vibe/skills/hass-eedomus-deploy/deploy_hass_eedomus.sh`. Never scp, rsync, or edit files on the Pi.
- Every release cut fast-forwards `main` to the tagged state — Dependabot alerts scan the default branch (policy recorded in `docs/CHANGELOG.md`).
- All text is English: log messages, docstrings, comments, and every user-facing label. French is available only as a translation, never as the hardcoded string.

## Where things are

- Core: `coordinator.py` (refresh + history import), `ui_service.py` (panel websocket commands).
- Panel frontend: `custom_components/eedomus/www/eedomus-panel.js` is the ES-module entry (the URL panel.py registers; it keeps the core: constructor/state, `t()` catalog loading, tab/hash navigation, `_render` shell, event delegation). It imports 7 modules from `custom_components/eedomus/www/panel/`: `shared.js` (cross-tab constants/helpers/mixin), one per tab — `peripheriques.js`, `regles.js`, `historique.js`, `coherence.js`, `supervision.js` — and `coherence-helpers.js` (coherence pure helpers; `coherence.js` imports and re-exports them).
- Starting a feature? Read `_bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md` (or the sibling specs: history, i18n, simulator, docs) first — capabilities and constraints live there.

## Running and verifying

- Unit tests: `python3 -m pytest tests/unit/ -q`. Panel JS pure helpers: `node tests/js/test-coherence.js` (strict — wired into CI).
- E2E (`tests/e2e/`) needs `.env` with `HA_TOKEN` and the live Pi — never mock it. Two strates (AD-16): live-Pi (`pytest tests/e2e/ -m "e2e and not e2e_sim"`) is the regression truth, never mocked; the simulator (`-m e2e_sim`) covers multi-box and destructive — it completes the live strate, never replaces it; Flask stays test-only (`requirements-test.txt`).
- 2 live-Pi E2E tests are state-dependent: they require a non-empty backfill queue; on an up-to-date (drained) box they fail — expected, not regressions.
- `ha core logs` over plain SSH returns unauthorized — use `sudo -i ha core logs` or the log-bridge scripts (`get_rasp_logs.sh`, `watch_logs.sh`).
- Formatting is enforced locally by the pinned pre-push hook and the deploy-script gate (`scripts/hooks/`, ticket 115): `uv run --no-project --with black==26.10.1 -- python -m black ...` and `isort==9.0.2` run in ephemeral uv environments. Run them over tracked Python files before committing; do not claim formatting was run unless it was.
- Release: pushing a `v*` tag triggers the HACS release build (`release.yml`); the GitHub release is born with an empty body — patch it with `docs/release_notes_vX.md` after the build.

## Conventions that differ from defaults

- User-facing strings go through HA's native i18n: backend via `strings.json` + `translations/en.json` (source of truth) and `translations/fr.json` (must stay structurally identical to en.json). Custom panel strings come from the websocket strings command, keyed by `hass.locale`, English fallback — never hardcoded in the JS.
- A new panel string lands in three places: `panel_translations.py` (EN + FR), `tests/fixtures/panel-catalog.json` and `tests/fixtures/panel-keys.json` — the drift tests in `test_ui_service.py` fail on any miss.
- Commits follow `<type>(<scope>): <subject>` (see `.vibe/skills/hass-eedomus-coding-standards/`); the working tree stays clean per build.

## Known pitfalls

- The SSH log bridge (`get_rasp_logs.sh`) reports RUNNING while its stream is dead: if `~/…/rasp.log` stops moving, restart the bridge — status alone lies.
- Only the entry URL is cache-busted (`?v=<manifest version>`): a NEW import the entry needs must live in the entry itself — a new export in a panel module breaks against browsers' cached copy (live SyntaxError in 0.15.5; real fix tracked in ticket 118).
- The mapping registry is pruned per entry at unload and devices re-register on every reload: joins must be last-wins; a first-wins join shows the pre-change mapping.

<!-- /bmad:context -->
