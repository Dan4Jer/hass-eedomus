---
report: architecture-spine-validation
target: planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md
date: 2026-11-01
verdict: not-clean — spine rules match code, but status layer is stale and 6 live divergence holes found
gate: lint 0 findings; rubric walker STALE; reality PASS-with-findings; adversary DIVERGENT (6 holes)
---

# Validation report — ARCHITECTURE-SPINE (hass-eedomus, 2026-09-27)

Gate verdict: **the AD-1…AD-14 rules still match the code on `unstable@3dfa99e`, but the spine no longer works as a contract** — its status layer contradicts the tree, it stops before AD-16/AD-17, and the adversarial lens found 6 holes where two AD-compliant units still build incompatibly. Needs an **Update** run, not just a status refresh.

## Critical / High

1. **[HIGH — rubric] "État actuel vs cible" is stale** (SPINE:42): claims AD-1…AD-5 unimplemented (in-cycle import, Spook, `async_set` ghosts, state-machine progress). Reality on unstable: background drain worker + `.storage` progress keyed `<entry_id>_<periph_id>` (coordinator.py:1460,1499,1816-1931), import via `async_import_statistics` only (coordinator.py:2529-2710), AD-11 filter live in Pi logs 2026-11-01. Commits cf8b642, 8f71efc, f2136ae, 20d3639. History epic done.
2. **[HIGH — rubric] AD-13/AD-14 marked `[CIBLE]` but implemented** (SPINE:131,154): config_manager.py:38-356 (Store eedomus.mapping, fingerprint, schema version, cap-3 versions, migrations, mirror ingest/self-heal); commits fce3ba8+5e3cad5 (P.1.8 done), 051c6b4. Status markers must flip to ADOPTED.
3. **[HIGH — rubric] Spine stops at AD-14; the level below runs on AD-16/AD-17** which the spine does not own: AD-16 (two E2E strates, AGENTS.md), AD-17 (panel cache-busting, panel.py:50,67 — extended to the module graph by ticket 118 today). Either extend the spine or reference where they live.
4. **[HIGH — reality] Python floor incoherent across artifacts**: spine Stack "3.11+" vs AGENTS.md "3.9+" vs pyproject black `py39` vs CI/venv 3.11 vs actual runtime 3.14 (`REQUIRED_PYTHON_VER=(3,14,2)` in HA 2026.9.3 const.py; rasp.log all python3.14). Four different floors; pick one truth and align all artifacts.
5. **[HIGH — adversary F1, AD-12] No merge primitive exists; `coordinator.data` has 5 writers** — wholesale `self.data=` (coordinator.py:463/991), blind `.update()` (:1102), untimestamped optimistic set (:2888), platform setup `.update()` (light/switch/cover/sensor/binary_sensor). The 9abc03f regression is still live (services.py:167 refreshes right after set). AD-12's binds cover only the coordinator; panel ws commands bypass it.

## Medium

- **[MED — adversary F2, AD-11]** clip `stat.start < first_native_start` only when native stats exist (coordinator.py:2667-2683); zero-native case writes the recorder-owned current hour + TOCTOU window before `async_import_statistics`. Fix: `min(first_native, current_hour)` + serialization vs compiler.
- **[MED — adversary F5, AD-13]** ingestion runs per entry (`__init__.py:181`, forbidden by the AD) → multi-box double-ingest; save UI rewrites the mirror without re-reading → concurrent user edit silently clobbered; runtime file fallback still exists (device_mapping.py:983/388).
- **[MED — adversary F3, AD-8]** worker starts at first refresh before platforms forward (coordinator.py:208 vs __init__.py:366/617); `last_timestamp` advances before registry resolution; 3 misses drop persisted progress (:2406) — frontier loss.
- **[MED — adversary F4, AD-2]** storage key enforced on `.storage` path only; legacy migration parses global `eedomus.history_progress_*` with `split("_")[-1]` (:1649) → cross-box bleed. AD-9 secondary: direct option reads at __init__.py:453, coordinator.py:2168/2746.
- **[MED — rubric/reality] HA compat floor not enforced**: "compat ≥ 2026.3" claimed but manifest.json has no `homeassistant` key; instance is on 2026.11 (spine's "2026.9.3" stale).
- **[MED — reality] pytest "9.x" in Stack vs `pytest>=7.0.0` in requirements-test.txt** (CI installs the latter).
- **[MED — rubric] Deferred section stale**: panel epic complete (retro 2026-10-03, 10/10), backfill pause/ignore/reset/priority implemented (coordinator.py:1936…2114), webhook/api_proxy registered (__init__.py:594-607).

## Low / tail

- AD-7 literally falsified by config_flow.py:291,340 (`auth_test` calls the API outside the coordinator) — rubric.
- Structural Seed omits current modules (value_resolver.py…) and ships stray tracked files (`services.py.backup`, `test_config.yaml`) — rubric.
- Epic/initiative files still describe CAP-4 as file-based, contradicting the amended SPEC — rubric.
- Instance-only claims unconfirmable from repo: Spook 5.5.1, `purge_keep_days: 30` — reality.
- eedomus 10 000 pts/call verified (doc + code) but code never reads `history_overflow`, uses `len<10000` heuristic — reality LOW.
- Cross-artifact: AGENTS.md "Python 3.9+" vs spine (see HIGH-4).

## What passes

- Deterministic lint: 0 findings (no placeholders, no duplicate AD IDs, all Binds/Prevents/Rule present, stack pinned).
- AD rules 6/7/8/9/10 verifiably in tree; adversary confirmed no AD *rule* contradicted by code.
- eedomus API pagination claim verified; HA 2026.9.3 tag exists; black 26.10.1 exists.

## Reviewer reports

- `reviews/review-RUBRIC.md` — verdict STALE (conditional pass on AD content)
- `reviews/review-REALITY.md` — verdict PASS WITH FINDINGS (1 HIGH, 3 MED)
- `reviews/review-ADVERSARY.md` — verdict DIVERGENT (6 holes)

## Recommended next

Roll these into an **Update** run of the spine (memlog resume, AD IDs stable): flip AD-1…AD-5/AD-13/AD-14 to ADOPTED with commit refs, add AD-15? no — register AD-16/AD-17 (or link their owners), tighten AD-12/AD-11/AD-13/AD-8/AD-2 per the adversary holes, fix the Python floor once across spine/AGENTS/pyproject/CI.
