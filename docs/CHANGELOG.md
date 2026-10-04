# Changelog

Historical release notes are preserved in the [docs/](docs/) folder. This page is the version index.

## 0.15.0 (unstable - in development)

- Multi-box support: per-instance entity/unique_id prefixing and service routing (PR #104, #105)
- Options flow fixed: submitting the form now correctly persists all options
  (previously raised `AttributeError` and options were never saved)
- Custom mapping rules (`custom_rules`) are now merged with default rules:
  same-name rules override, new rules are appended (previously custom rules were dropped)
- Dependabot dependency updates (setuptools, requirements)
- New "Cohérence" tab in the configuration panel: per-peripheral fused view
  (`eedomus/get_coherence` websocket command) joining the mapping registry,
  live HA state and raw API fields, with one chip per coherence signal
  (sans entité, douteux, règle active, en erreur)
- Coherence table: column sort with aria-sort cycle, instant search and
  a "Tout afficher" / "À vérifier" view toggle, result counts announced
  to screen readers
- Coherence detail surfaces: desktop popover and mobile expanded row share
  the same detail body (live state, mapping identity, raw API fields)
- Entity navigation: entity links in the coherence table open the standard
  Home Assistant more-info dialog (web and mobile)
- New test suites: 186 unit tests (mapping rules, API client, options flow,
  YAML merging, coherence), 20 E2E tests against a live instance
  (connectivity, refresh, set_value, options flow, coherence) and a
  Node-run JS suite for the coherence panel helpers, wired into CI

## 0.14.3

- YAML backup mechanism before version upgrades
- Configuration panel temporarily hidden
- Release notes: [release_notes_v0.14.2.md](release_notes_v0.14.2.md) and GitHub releases

## 0.14.2

- Options flow dynamic configuration (scan_interval configurable without reinstall)
- Entity cleanup feature (`eedomus.cleanup_unused_entities`)
- Release notes: [release_notes_v0.14.2.md](release_notes_v0.14.2.md)

## 0.14.0

- Major architecture upgrade, configurable API timeout
- Release notes: [RELEASE_NOTES_v0.14.0.md](RELEASE_NOTES_v0.14.0.md)

## 0.13.x

- YAML mapping system, RGBW detection, performance improvements
- Release notes: [RELEASE_NOTES_v0.13.0.md](RELEASE_NOTES_v0.13.0.md),
  [RELEASE_NOTES_v0.13.3.md](RELEASE_NOTES_v0.13.3.md),
  [TECHNICAL_RELEASE_NOTES_v0.13.3.md](TECHNICAL_RELEASE_NOTES_v0.13.3.md),
  [RELEASE_NOTES_v0.13.10-unstable_FR.md](RELEASE_NOTES_v0.13.10-unstable_FR.md)

## 0.12.0

- Configurable scan interval, immediate effect without restart
- Release notes: [RELEASE_NOTES_v0.12.0.md](RELEASE_NOTES_v0.12.0.md)

## Versioning policy

- **Stable releases**: even minor numbers (`0.14.0`), tagged from `main`
- **Unstable releases**: odd minor numbers (`0.15.0`), tagged from `unstable`
