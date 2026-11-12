# RUBRIC WALKER review — ARCHITECTURE-SPINE.md (architecture-hass-eedomus-2026-09-27)

- **Reviewer:** RUBRIC WALKER (good-spine checklist), read-only
- **Spine under review:** `../ARCHITECTURE-SPINE.md` (+ `../.memlog.md`), status `final`, created 2026-09-27, updated 2026-09-28
- **Code baseline:** `unstable` @ `3dfa99e` (working tree clean, branch `unstable`)
- **Date of review:** 2026-11 (session date); all commit refs verified with `git log` on `unstable`

## Verdict

**STALE — CONDITIONAL PASS on decision content, FAIL on status currency.**

The *rules* of AD-1…AD-14 are still consistent with the code they govern: no AD rule was found contradicted by the current implementation, and the ones marked ADOPTED (AD-6, AD-7*, AD-8, AD-9, AD-10) are verifiably in the tree. But the spine's **status layer is stale against `unstable`**: the "État actuel vs cible" section (line 42) still describes the pre-backfill-rework reality (in-cycle import, Spook, `async_set` fantômes, state-machine progression, file-canonical mapping) although all of it has landed; AD-13/AD-14 are still marked `[CIBLE]` although implemented; the Deferred section describes the panel epic as "P.1.1–P.1.4 en vigueur" although the epic is complete; and the spine stops at AD-14 while the level below (epics, AGENTS.md, specs, `panel.py`) now runs on **AD-16 and AD-17**, which this spine does not own. A unit reading the spine today would re-open decided questions and would miss two live divergence guards.

Rubric scorecard:

| # | Rubric item | Result |
|---|---|---|
| 1 | Fixes real divergence points for epics/stories, misses none | **FAIL** — misses AD-16 (E2E two-strates) and AD-17 (panel module-graph cache-busting), both decided 2026-10-06 and referenced by AGENTS.md / spec-eedomus-simulator / panel.py |
| 2 | Every AD's Rule enforceable and prevents its divergence | **PASS with one open item** — AD-12's rule is not yet enforced in code (honestly marked "à implémenter", but the divergence is still only guarded by listener notify, `9abc03f`); AD-7's rule is literally falsified by `config_flow.py` (see F7) |
| 3 | Nothing under Deferred can let two units diverge | **PASS on divergence risk, FAIL on currency** — deferrals are stale (F6) but each has a single owner in code |
| 4 | Named tech verified-current | **FAIL** — Python floor stated three ways (F4); HA instance version stale (F5); pytest 9.x verified (`requirements.txt:14` `pytest==9.1.1`) |
| 5 | Ratifies, not contradicts, the brownfield codebase | **FAIL** — "État actuel vs cible" and `[CIBLE]` markers contradicted by current code (F1, F2, F6, plus stale sub-claim in AD-10) |
| 6 | Spec coverage (if a spec drove it) | **PASS** — `sources: []`, no spec drove the spine; memlog only touches mapping-panel SPEC CAP-4, which was amended to AD-13 (`fce3ba8`); spine covers spec-eedomus-history CAP-1..4 via AD-1..5/AD-11 |
| 7 | Every owned dimension decided/deferred/open, incl. operational envelope | **PASS with staleness** — envelope present (line 200) and repo-consistent; HAOS 18.2 / downtime / Spook 5.5.1 not verifiable from repo, no contradiction found |

## Findings

### F1 — HIGH — "État actuel vs cible" (line 42) is fully stale: AD-1…AD-5 are implemented and live

Spine line 42 claims: *"AD-1 à AD-5 sont des décisions cibles, non encore implémentées … fetch+import dans le cycle de partial refresh (195 s/196 s), import via le service Spook `recorder.import_statistics`, fallback `async_set` doublé vers des entités fantômes `sensor.eedomus_<periph_id>`, progression persistée via la state machine."*

Reality on `unstable@3dfa99e`:

- Background worker out of the refresh cycle: `coordinator.py:1460` `_ensure_backfill_worker`, `:1499` `_async_backfill_worker`, `:1484` `async_shutdown_backfill` ("Unload = await + flush (AD-2)"); `_async_partial_refresh` (`:994`) explicitly notes "AD-2 (story 1.4): the history drain lives in the background worker".
- Progression in `.storage`, keyed `<entry_id>_<periph_id>`: `coordinator.py:1816-1931` (`Store(f"{DOMAIN}.backfill_{entry_id}")` + `f"{prefix}{periph_id}"` progress doc), with schema-version migrations (`:1833-1902`). No state-machine progression remains; a one-time legacy migration from states exists (`:1894-1901`).
- Import via the official Python API only: `coordinator.py:2529` `_import_via_statistics` → `homeassistant.components.recorder.statistics.async_import_statistics` (`:2614-2710`). `grep` finds **no** Spook, no `recorder.import_statistics` service call, no `async_set` anywhere in `custom_components/eedomus` (excluding `.backup` files).
- AD-11 owner split implemented: `coordinator.py:2655-2685` filters to hours strictly before the first native statistic and logs exactly *"Nothing to import for %s: all %d hours at or after the first native statistic (AD-11)"* — the Pi log line of 2026-11-01 quoted in the review request.
- AD-3 scope: `_is_backfill_eligible` `coordinator.py:1143-1166` (sensor + numerically resolvable only). AD-4: 10,000-point chunks `async_fetch_history_chunk` `:2225`; AD-6bis value_list fingerprint persisted per periph (`:2211`, `:2247`). AD-5: docs landed in story 1.5.
- Evidence commits: `cf8b642` (2026-10-09, story 1.4 background drain + .storage), `8f71efc` (2026-10-09, bug 1.8 unit_class metadata), `f2136ae` (2026-10-10, story 1.6 E2E asserts backfilled statistics land in the recorder), `20d3639` (story 1.5 activation doc), `d0330fb` (story 1.9 seam probe). Epic `initiative-eedomus-history/epic-history-backfill` has `status: done`.

**Impact:** any epic/story reading the spine believes the history rework is still pending and may re-plan against the old in-cycle/Spook design.

### F2 — HIGH — AD-13 and AD-14 marked `[CIBLE]` (lines 131, 154) are implemented; line 42's AD-13 paragraph is stale

- Line 42: *"AD-13 est une décision cible : le mapping custom est encore porté par le fichier config-dir (option B du ticket P.1.4, `f5f0e43`)"* — but `fce3ba8` (2026-09-28, same day as the spine's `updated:`) implements AD-13 and `5e3cad5` marks P.1.8 done.
- Code: `config_manager.py:38` `Store(hass, 1, "eedomus.mapping")` canon with `current` + `file_fingerprint` + `config_schema_version` (`:112`, `:285-305`); version archive cap 3 (`:41`, `:227-260`); ordered pure migrations `_async_migrate_mapping_document` (`:159-215`, AD-14bis); mirror-file ingest with text-vs-fingerprint comparison, invalid-YAML-keeps-canon, self-healing mirror (`:267-356`, AD-13bis/ter/quater); domain-level init in `async_init` (`:46-58`, the AD-13 resserrage). AD-14: `051c6b4` (2026-09-28) — seed as example + migration base; `config_schema_version` stamping present throughout.
- Spec side: `spec-eedomus-mapping-panel/SPEC.md` CAP-4 (line 29-31) was amended to the storage canon — consistent with the code, contradicting the spine's marker.

### F3 — HIGH — Spine stops at AD-14; the level below now runs on AD-16 / AD-17 that the spine does not own (rubric 1 miss)

- `AGENTS.md` managed context block (verified 2026-11-01): "Two strates (AD-16): live-Pi … never mocked; the simulator … completes the live strate".
- `_bmad-output/specs/spec-eedomus-simulator/SPEC.md:13,39` and `.memlog.md:9`: "AD-16 (revue architecture Winston 2026-10-06, validée utilisateur)" — two-strate E2E rule.
- `custom_components/eedomus/panel.py:50,67`: "cache-busting, AD-17" / "AD-17 (story 106)"; backlog story `story-cache-busting-du-graphe-de-modules-du-panneau.md` shows AD-17 only busts the entry URL and the module graph needed a follow-up (`0572863`, ticket 118, v0.15.7).
- The spine's Invariants & Rules end at AD-14 (line 154) and its Deferred/panel bullet (line 204) does not mention either. Two units can cite AD numbers the spine never ratified; the spine should either adopt AD-15…AD-17 (or record where they live) so the altitude owns all live divergence guards.

### F4 — MEDIUM — Python floor contradiction across artifacts (rubric 4 / cross-artifact)

- Spine Stack line 177: "Python 3.11+ (runtime HA ; tests locaux sous 3.14)".
- `AGENTS.md:6`: "Python 3.9+". `pyproject.toml` `[tool.black] target-version = ['py39']`.
- CI (the enforced floor): all four workflows pin `python-version: '3.11'`, bumped from 3.9 by `7b8aad2` (2026-11-01, "Ubuntu 26.04 runners dropped 3.9").
- Additionally, line 178 claims "cible compat ≥ 2026.3" but `custom_components/eedomus/manifest.json` declares **no** `homeassistant` min-version key — the compat floor is not ratified in code.

### F5 — MEDIUM — Stack HA version stale: instance is on HA 2026.11, not 2026.9.3 (rubric 4)

- Spine line 178: "Home Assistant 2026.9.3 (vérifié sur l'instance ; … schema recorder 53)".
- Evidence the Pi moved to 2026.11: `docs/release_notes_v0.15.3.md:60,138` (HA 2026.11 deprecation handling), `coordinator.py:2697-2699` comment "unit_class is required metadata from HA **2026.11**", commit `8f71efc` (bug 1.8: unit_class breaking in HA 2026.11), `f13ad3d` ("derive unit_class from the recorder unit map (HA 2026.9)"). "schema recorder 53" is not verifiable from the repo.

### F6 — MEDIUM — Deferred section (lines 202-209) stale (rubric 3/5)

- Line 204: panel "en cours dans l'épic `epic-mapping-panel-editor` (P.1.1–P.1.4 en vigueur)" — the epic is **complete**: `epic-mapping-panel-editor-retrospective.md` (2026-10-03, verdict accepted-with-open-items, "10 tickets, 10 done").
- Line 205: "Ordonnancement fin de la tâche de fond (intervalle, **priorisation des périphs**) — à l'implémentation de AD-2" — prioritisation and the CAP-5 actions are implemented: `coordinator.py:1936` `async_backfill_retry_now`, `:2012` `async_backfill_prioritize`, `:2044` `async_backfill_reset_progress`, `:2082` `async_backfill_set_paused`, `:2114` `async_backfill_set_ignored` (spec-eedomus-history CAP-5).
- Line 207: "Webhook / api_proxy — rôle futur non décidé" — both views are registered (`__init__.py:594-607`) and api_proxy is behind an `enable_api_proxy` option; the "no growth without a new decision" constraint is fine, the "rôle futur" framing is not.
- Divergence risk itself is low (single owners in code), but the spine presents decided items as open.

### F7 — LOW — AD-7's Rule is literally falsified by `config_flow.py` (rubric 2)

- Spine line 82-86: "aucun module hors `eedomus_client` (appelé par le coordinator) n'émet de requête eedomus".
- `config_flow.py:291` instantiates `EedomusClient` and `:340` calls `client.auth_test()` during options/config validation — a one-shot credential check, arguably within the spirit of AD-7 (no shared state, no rate-limit contention), but the rule as written is false in the code. Amend the rule to exempt config-flow validation, or scope it to runtime state.

### F8 — LOW — AD-12 remains unenforced in code (rubric 2 open item)

- Spine line 112 honestly marks AD-12 "[ADOPTED, à implémenter]", and indeed no unique merge primitive exists: the optimistic set still does a direct mutation `self.data[periph_id]["last_value"] = value` (`coordinator.py:2888`). The divergence AD-12 prevents (refresh overwriting the optimistic value) is currently guarded only by listener notification (`9abc03f`, "Notify listeners after successful set_value"). Enforceable, not yet enforced — flag so stories don't assume it's done.

### F9 — LOW — Structural Seed (lines 183-201) drifts from the tree; tracked junk ships to the Pi (rubric 5)

- Seed omits `value_resolver.py` (the AD-6 resolution helpers), `refresh_timing_sensor.py`, `endpoint_volume_sensor.py`, `config/`, `brand/`, `panel_translations.py`, `log.py`, `private_const.py`.
- Git-tracked files inside the deployed component: `custom_components/eedomus/services.py.backup`, `custom_components/eedomus/config/device_mapping.yaml.backup`, `custom_components/eedomus/test_config.yaml` (plus untracked `*.backup*`/`__pycache__`). With git-only deploy (`AD-10`), these land on the Pi.

### F10 — LOW — Cross-artifact contradiction outside the spine: panel epic/initiative still describe CAP-4 as file-based

- `epic-mapping-panel-editor-retrospective.md` (spec-reconciliation finding): `epic-mapping-panel-editor.md` and `initiative-eedomus-panel.md` Requirements still say "CAP-4 : Sauvegarde dans custom_mapping.yaml via config_manager" while the SPEC was amended (`fce3ba8`) and the code implements AD-13/14 storage canon. The spine agrees with spec+code; the epic files contradict them. (Recorded here because rubric 5/6 ask for cross-artifact contradictions; the fix belongs to the epic files, not the spine.)

### F11 — LOW — Stale sub-claim inside AD-10 (line 100-104)

- AD-10 says "L'écart E2E actuel (aucune couverture history/statistics) est un manque à combler à l'implémentation de AD-1" — now closed: `f2136ae` (story 1.6 E2E assertions on backfilled statistics) plus the simulator strate (`6c26543`, `a32bb8e`). The legacy scp scripts it orders deleted are gone (`b8b5b44`; story 100 closed `698ff35`), so that part is correctly ratified.

## What checked out (positive evidence)

- **AD-6** `[ADOPTED, à resserrer]`: resolution + frozen `value_list` fingerprint implemented (`coordinator.py:2211`, `:2247`, `:2505-2528`; `value_resolver.py`).
- **AD-8**: `entity.py:216` `unique_id = f"{entry_prefix}_{periph_id}"`; registry-exact resolution for statistics targets (`coordinator.py:2452` `_resolve_main_entity_id`; `a879bd8` bug 1.11 drops periphs after persistent registry misses).
- **AD-9**: `entity.py:35` `_get_config_value`.
- **AD-10**: git-only deploy policy in `AGENTS.md` (managed block) + `docs/DEPLOYMENT_GUIDE.md`; no `scp`/`paramiko` left in `scripts/`; purge 30 consistent (`DEPLOYMENT_GUIDE.md:17`).
- **AD-2 storage key** exactly as specified: `<config_entry_id>_<periph_id>` (`coordinator.py:1904-1931`).
- **pytest 9.x** verified: `requirements.txt:14` / `requirements_dev.txt:16` pin `pytest==9.1.1`.
- **Spec coverage (rubric 6):** spine `sources: []` — no driving spec; spec-eedomus-history CAP-1..4 map onto AD-1..5/AD-11 and are implemented; CAP-5 queue/actions implemented in coordinator and surfaced by the panel (stories 110/112) per the spine's Deferred split. spec-eedomus-mapping-panel CAP-4 amended to AD-13. No uncovered spec capability found.
- **Operational envelope (rubric 7, line 200):** present and repo-consistent; HAOS 18.2 / downtime 2-4 min / Spook 5.5.1 presence are not verifiable from the repo — no contradiction found.

## Recommended actions (not applied — read-only review)

1. Update-run the spine: re-mark AD-1..AD-5, AD-11, AD-13, AD-14 as `[ADOPTED/IMPLÉMENTÉ]` with commit refs (`cf8b642`, `8f71efc`, `fce3ba8`, `051c6b4`, …) and rewrite "État actuel vs cible" (line 42) to the post-rework reality.
2. Adopt or re-home AD-16/AD-17 (architecture review 2026-10-06) into the spine so the altitude owns them.
3. Refresh Deferred (lines 204-207) and the AD-10 E2E sub-claim; reconcile Python floor (spine 3.11+ vs AGENTS.md 3.9+ vs black py39 vs CI 3.11) and add the `homeassistant` min-version key to `manifest.json`; bump Stack HA to 2026.11.
4. Amend AD-7's rule text to exempt config-flow validation; keep AD-12 as an explicit open item until the merge primitive exists.
