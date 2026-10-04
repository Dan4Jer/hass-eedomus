---
id: SPEC-eedomus-i18n
companions: [../../AGENTS.md]
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Eedomus integration i18n — audit and migration to Home Assistant's native translation mechanisms

## Why

**Policy vs reality.** `AGENTS.md` now requires all text in English, with French available only as a translation through HA's native mechanisms. The integration violates its own policy: the panel carries ~42 user-facing strings hardcoded in French (microcopy, chips, statuses, aria-labels) with no locale mechanism at all; `translations/en.json` lacks the `ui` section `fr.json` has; service descriptions are English-only outside any translation mechanism; entity fallbacks are hardcoded English; logs and docstrings are heavily French. A user running HA in English sees French labels — exactly what the policy forbids.

## Capabilities

- **CAP-1 — i18n inventory**
  - **intent:** Every user-facing string of the integration is catalogued — its surface (panel, config/options flow, services, entity fallbacks, logs), its target mechanism (backend `translations/`, panel websocket strings command, plain-English source), and its key.
  - **success:** Every user-facing string in the repo appears in the inventory with mechanism + key; a cross-check grep finds no hardcoded user-facing string the inventory missed.

- **CAP-2 — Backend translations complete and structurally identical**
  - **intent:** `translations/en.json` is the source of truth and `translations/fr.json` reproduces its exact key tree (including the `ui` section missing today); service descriptions go through the `services` section of `strings.json`; entity fallback names (e.g. `Unknown Device`) are localized.
  - **success:** `en.json` and `fr.json` share the same key tree (asserted by a test); services and entity fallbacks render in the HA display language.

- **CAP-3 — Panel strings via websocket**
  - **intent:** The backend serves a localized string catalog through a websocket command (single source on the Python side); the panel loads it per the user's locale (`hass.locale`) and embeds no user-facing hardcoded string; English fallback when a locale is not covered.
  - **success:** No user-facing hardcoded string in `www/eedomus-panel.js` (grep); the panel renders in English under an English HA and in French under a French HA.

- **CAP-4 — English-first source**
  - **intent:** The integration's log messages, docstrings, and comments are in English.
  - **success:** No French log message or docstring in `custom_components/eedomus` (grep); the live instance's logs read in English.

## Constraints

- Native HA mechanisms only: `strings.json` + `translations/*.json` for the backend; no third-party translation library in the panel (vanilla JS, no build); the panel's strings live in one place — the Python-served websocket catalog — never duplicated in the JS.
- The frozen response shapes of `eedomus/get_peripherals` and `eedomus/get_coherence` do not change during the migration — only display strings move; eedomus peripherals keep their cloud names (data, not labels).

## Non-goals

- No new features: the Historique tab rename and the box-info tab are separate UX/spec work.
- No multi-language infrastructure beyond en/fr.
- No translation of user data (cloud names, values).
- The panel never forces a locale — it follows HA.

## Success signal

A user running Home Assistant in English sees zero French text on any surface of the integration — panel, config/options flows, services, entity fallbacks, logs; a user in French sees complete French, with the FR translation complete before shipping.

## Assumptions

- The FR translation will be authored from the English source (EN is the source of truth, per AGENTS.md and the user's fallback decision).
- The websocket strings command follows the existing `ui_service` dispatcher pattern (`require_admin`, `eedomus/<verb>`), like `get_coherence`.
- Existing French logs and docstrings migrate in **one full pass** inside the i18n epic (user decision, 2026-10-04) — no migrate-on-touch.
