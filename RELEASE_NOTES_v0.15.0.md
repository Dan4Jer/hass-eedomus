# Release v0.15.0

Eedomus Config panel — the full configuration panel epic, history backfill via the official statistics API, and complete EN/FR localization.

## The Eedomus Config panel (CAP-1 to CAP-9)

A new admin sidebar panel (registered via the supported panel API) with five tabs:

- **Périphériques** — peripheral list with search, result badges and create-rule shortcuts.
- **Règles** — the custom mapping editor: form mode with validation, YAML mode with syntax highlighting, save with auto-apply.
- **Historique** — mapping versions with a colored diff engine and one-click restore.
- **Cohérence** — one row per peripheral with live coherence signals (never color alone), sort, quick filter, All/To-check toggle, a rich per-peripheral detail popover, a mobile expanded row with full parity, entity navigation to the standard HA surfaces, and a raw JSON block with copy.
- **Supervision** (new in this release) — box metrics as themed inline-SVG chart cards (refresh time, API time, per-cycle eedomus API calls, peripheral counts), every value doubled by a textual equivalent, plus a link to the Coherence tab.

## Backfill queue control (CAP-5)

The history recovery queue is now exposed and steerable from the Supervision tab:

- Live queue state per peripheral (pending with position, in progress, error with message/retry/attempt count, paused, prioritized) plus the global engine state.
- Four actions, each with a nominative result: retry now (off-schedule), prioritize (head of the next drain), pause/resume per peripheral, and a global pause switch.
- Ignore is a two-gesture confirmation ("Ignorer {name} ? Sa récupération sera abandonnée."), persisted in `.storage` and reactivable; it survives restarts.
- The real-time refresh is never blocked by an action (mono-importer lock, busy = nominal refusal).

## History import (AD-11 / AD-1 / AD-2)

- Import via the official `recorder.statistics.async_import_statistics` Python API.
- Capped per-scan cadence: at most N history imports per refresh cycle so the real-time polling is never starved (configurable).

## Internationalization

- Full EN/FR backend translations (config/options flows, entity naming).
- The panel consumes a translation catalog (`eedomus/get_translations`) — zero hardcoded user-facing strings, enforced by a self-tested i18n guard.

## Frontend architecture

- The panel is real ES modules served from `www/` (no toolchain, no build step): one entry plus one module per tab and a shared core — every module under ~1 100 lines.

## Tests

- 324 unit tests, a node harness (210 assertions) and an i18n guard, and 29 live end-to-end tests against the real instance (non-destructive), all green.

## Upgrade notes

- The custom mapping file moved to a seeded example (`config/custom_mapping.yaml.example`); the mapping canon now lives in `.storage` and is migrated automatically on first start.
- New options: panel enable/disable in the Options Flow, history settings (enable, per-scan quota, retry delay).
- After upgrading, force-reload the panel page once (Cmd/Ctrl+Shift+R): the panel module URL is not cache-busted yet.
