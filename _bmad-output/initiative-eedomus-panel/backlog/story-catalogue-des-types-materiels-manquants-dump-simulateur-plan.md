---
title: 'Catalog of missing eedomus hardware types in the simulator dump (ticket 114)'
type: 'feature'
ticket: '114'
created: '2026-10-10'
status: 'in-review'
baseline_revision: 'a5f43c3'
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: 'auto'
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The simulator's shipped anonymized dump (69 peripherals, 23 distinct usage_ids, zero parent_id children) leaves whole platforms unreachable in the e2e_sim strate — no climate entity is ever created (15/19/20/38 absent), cover/color/RGBW, flood, power and energy paths are dead — and nobody has a prioritized list of what hardware cases to add.

**Approach:** A static generator (`scripts/simulateur/03_catalog.py`, following the 00/01/02 script pattern) computes the catalog from the shipped dump vs the integration's mapping: handled-but-absent usage_ids (from `device_mapping.yaml` `usage_id_mappings`), present-but-unmapped usage_ids, structural gaps (parent/child, value_type variants), each with platform and a documented priority. The committed artifact `scripts/simulateur/CATALOG.md` plus a README pointer; a unit test pins the catalog's consistency. The catalog documents how to add a case (00/01/02 extraction → anonymization → CAP-5 privacy pass), which stays a human step — no new dump data in this build.

## Boundaries & Constraints

**Always:**
- The catalog is computed statically from `eedomus_dump.json` + `config/device_mapping.yaml` — no box access, no network.
- Deterministic: same inputs → identical CATALOG.md (committed, regenerable).
- Priority rubric documented in CATALOG.md: platform code with no unit coverage and most unreachable branches ranks first (no coverage tool exists in the repo — the rubric is static reasoning, say so).
- English throughout (the 00_extract.py French prints are pre-existing, untouched).
- The "how to add a type" section points to the 00/01/02 flow and the mandatory privacy pass (CAP-5), and marks extraction as a human step.

**Never:**
- No new dump data, no edits to `eedomus_dump.json` / `thermostat_rules.json` (human step: extraction needs a real box + credentials + privacy pass).
- No changes to `simulator.py` endpoints.
- No new platform files (the 127 → `button/camera_trigger` mapping references a `button.py` that does not exist — the catalog FLAGS it, creating the platform is out of scope).
- No fix of the 109 (Volets) → sensor/text mismatch — cataloged as a finding for a later decision.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Generate | Shipped dump + YAML map | CATALOG.md written: missing ids (usage, platform, priority), unmapped-present ids, structural gaps | No error expected |
| Regenerate | Same inputs, existing CATALOG.md | Byte-identical output (no spurious diff) | No error expected |
| Enriched dump | A future dump with climate periphs added | Missing-climate rows disappear on regen; present-but-unmapped updates | New unmapped ids appear, not an error |
| Missing YAML key | device_mapping.yaml without usage_id_mappings | Clear error, exit non-zero | Fail loud, no partial catalog |

</intent-contract>

## Code Map

- `scripts/simulateur/eedomus_dump.json` — input; 69 periphs, keys periph_list/value_list/caract; 23 distinct usage_ids (7×13, 1×10, 0×9, 52×5, 35×4, 26×4, 22×3, 23×3, 43×3, 109×2, and 37/24/34/84/18/32/16/114/4/27/41/119/2 ×1); all `parent_id: None`; value_type variants: list 35, float 31, string 2, "" 1.
- `custom_components/eedomus/config/device_mapping.yaml:54` — `usage_id_mappings` (the handled set): 0/2/4/50/52→switch, 1→light/dimmable, 7→sensor/temperature, 14/42→select/shutter_group, 15→climate/temperature_setpoint, 18/34/84→sensor/text, 19/20→climate/fil_pilote, 22→sensor/moisture, 23→sensor/cpu, 26/29→sensor/energy, 27→binary_sensor/smoke, 28→sensor/power, 35→sensor/text, 36→binary_sensor/moisture, 37→binary_sensor/motion, 38→climate/heating, 43→select/automation, 48→cover/shutter, 82→select/color_preset, 100-114→sensor/text, 127→button/camera_trigger, 999→select/virtual.
- Platform anchors (for the rubric's coverage reasoning; no unit test imports any platform module): `climate.py:184,187,299,306,440` (15 setpoint, 19/20/38 fil pilote), `light.py:88-102` (RGBW needs ha_subtype rgbw + ≥4 children usage 1), `cover.py:47,61` (48 slats child), `binary_sensor.py:69,75,81` (children 7/24/36), `switch.py:78-84` (control children 1/2/4/52), `sensor.py:397` + `coordinator.py:1155` (parse float/int/integer — dump has no int/integer).
- Known findings to carry in the catalog: no `button.py` platform file exists (127 mapping dangling); dump's usage 109 (Volets) maps to sensor/text (`device_mapping.yaml:298-301`); `thermostat_rules.json` ids (thermostat/thermostat_temp/thermostat_switch) exist in the dump but no climate entity is created from it (`climate.py:32-36` filters ha_entity == climate).
- `scripts/simulateur/00_extract.py` / `01_create_renom.py` / `02_apply_renom.py` — the extraction/anonymization flow the catalog's "how to add" section documents (env EEDOMUS_HOST/EEDOMUS_API_USER/EEDOMUS_API_SECRET; 01 emits renom.csv; 02 writes new_* files, never merges into shipped files).
- `scripts/simulateur/README.md` — gets a pointer section and its file-tree listing gains `03_catalog.py` + `CATALOG.md`.
- Script pattern to follow: numbered prefix, `#!/usr/bin/env python3` shebang, argparse with env-var defaults, deterministic committed output.
- Tests: `tests/unit/` runs without HA (conftest stubs); `test_simulator_history.py` is the neighbor for a generator test. Generator must be importable/runnable with plain python3 + stdlib (yaml is available — used by device_mapping tests).

## Tasks & Acceptance

**Execution:**
- [x] `scripts/simulateur/03_catalog.py` -- create the generator: load dump + usage_id_mappings, compute handled-but-absent, present-but-unmapped, structural gaps (parent/child count, value_type variants, dangling platform mappings), apply the documented priority rubric, render CATALOG.md -- the single source, regenerable
- [x] `scripts/simulateur/CATALOG.md` -- generated committed artifact with: findings table (missing usage_id, platform, priority, what to extract), structural gaps, the rubric, and the "how to add a type" section (00/01/02 + privacy pass, human step) -- the deliverable fmo01 asked for
- [x] `scripts/simulateur/README.md` -- add the catalog section + file-tree entries -- discoverability
- [x] `tests/unit/test_simulator_catalog.py` -- run the generator against the shipped dump (temp output or stdout mode), assert consistency: every "missing" id exists in the YAML map, climate and parent/child structure rank in the top priority tier, regeneration is byte-stable -- makes the catalog machine-checked

**Acceptance Criteria:**
- Given the shipped dump and YAML map, when 03_catalog.py runs, then CATALOG.md lists every handled-but-absent usage_id with its platform and priority, every present-but-unmapped id, and the structural gaps
- Given the priority rubric, when priorities are read, then climate and parent/child color structures rank first, and the rubric's static-reasoning basis is stated
- Given regeneration with unchanged inputs, when the catalog is rebuilt, then the output is byte-identical
- Given the unit suite, when it runs, then the catalog consistency test passes alongside the existing suite

## Implementation Notes

## Plan Change Log

## Review Triage Log

## Verification

**Commands:**
- `python3 scripts/simulateur/03_catalog.py` -- expected: writes/refreshes CATALOG.md deterministically, exit 0
- `python3 scripts/simulateur/03_catalog.py && git diff --stat scripts/simulateur/CATALOG.md` -- expected: no diff on second run (byte-stable)
- `python3 -m pytest tests/unit/ -q` -- expected: full suite green including test_simulator_catalog.py
- `node tests/js/test-coherence.js` -- expected: green (untouched, sanity)

**Results (2026-10-10):**
- `03_catalog.py` exit 0; `--check` confirms the committed file is current.
- Full unit suite: 430 passed (includes the 12 new catalog tests); no diff on regeneration.
- `test-coherence.js`: all coherence tests passed.

## Review Triage Log

### 2026-10-10 — Review pass (thorough)
- verdicts: 29 findings — high 0, medium 5, low 23, false 1, maybe-false 0
- findings:
  - `[medium]` `[patch]` CATALOG.md switch control-children row claims "covered" while its own detail reports usage 2/4 at 0, and counts are not scoped to switch parents (switch.py:78-84 inspects children of switch-mapped parents only) — recompute scoped, status "partially covered", accurate detail (blind-hunter #1, #2, grouped)
  - `[medium]` `[patch]` RGBW threshold semantics wrong: light.py:88-102 counts ALL children (≥4), not usage-1 children only, and the usage-82 color preset is NOT structurally required (light.py:63-64: 82 child mapping removed, standalone select) — count all children, fix detail and the 82 extraction hint (blind-hunter #3 + edge-case #11, #12, grouped)
  - `[medium]` `[patch]` priority_for's rubric-miss fail-loud raise has no test — future mapping additions can silently get arbitrary tiers; add test_unknown_missing_usage_id_fails_loud (verification-gap #1)
  - `[low]` `[patch]` thermostat_rules.json parsed with bare json.loads (raw traceback on malformed input), non-list rules silently treated as zero, absent setpoint_id skipped silently, missing rules file invisible — wrap in CatalogError, fail loud on non-list, emit findings for absent setpoints and missing rules file (blind-hunter #4, #5 + edge-case #3, #10 + verification-gap other, grouped)
  - `[low]` `[patch]` input validation fail-loud gaps: non-dict periph entries, null/scalar mapping entries, non-UTF-8 files, OSError on output write/read, null usage_id/usage_name becoming literal "None" rows, falsy value_type (0/False) counted as "(empty)" — guards + CatalogError (edge-case #1, #2, #4, #5, #6, #7, grouped)
  - `[low]` `[patch]` duplicate periph_id silently last-wins in periphs_by_id — fail loud (edge-case #9)
  - `[low]` `[patch]` children referencing a parent absent from the dump silently inflate the parents/children counts — emit a finding and exclude from counts (edge-case #8)
  - `[low]` `[patch]` priority_for tier 4 is a magic 100-113 range regardless of the entry's actual mapping — key tier 4 off the mapping entry (sensor/text) instead of the numeric range (blind-hunter #6)
  - `[low]` `[patch]` catalog presentation: raw French dump labels in section 2 get English glosses (policy consistency with the Volets finding), and the 127 row gains an explicit "blocked on button.py" marker (blind-hunter #8, #10)
  - `[low]` `[patch]` README wiring: section 15 workflow ends without the regenerate-catalog step (drift committed by verbatim followers), the -d/-m/-o CLI override surface (preview on new_* datasets) is undocumented, tests invoking main() rely on argparse env-var defaults (hermeticity), and --check on a missing file says "out of date" instead of "not generated" (blind-hunter #11, #12, #13, grouped)
  - `[low]` `[reject]` structural-gap citations carry hard line numbers that will drift — symbol-name anchoring is an enhancement, not a defect; citations were verified accurate today and are refreshed at regeneration
  - `[low]` `[reject]` no "default/fallback mappings" section for usage-0 periphs — outside the intent's scope ("types manquants": default-mapped present periphs are neither missing nor unmapped); re-raising is a future ticket's call
  - `[low]` `[reject]` test_every_missing_id_is_handled is tautological under analyze's construction — harmless; docstring nuance only
  - `[false]` `[reject]` "the shipped dump has zero parent_id children" — false as a finding against this change: the diff's own CATALOG.md reports the true structure (10 parents, 29 parented periphs via parent_periph_id); the error lives in this plan's Code Map (inherited from a mis-keyed exploration), corrected in Implementation Notes — and per triage rules a finding whose fix edits the plan is rejected
