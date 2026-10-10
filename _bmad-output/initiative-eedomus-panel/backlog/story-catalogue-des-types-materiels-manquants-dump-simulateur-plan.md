---
title: 'Catalog of missing eedomus hardware types in the simulator dump (ticket 114)'
type: 'feature'
ticket: '114'
created: '2026-10-10'
status: done
baseline_revision: 'a5f43c3'
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: 'auto'
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: true
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

- Plan Code Map error corrected during review: the shipped dump does NOT have zero parent/child peripherals — the explorer looked for a `parent_id` key, but the dump's key is `parent_periph_id` (10 parents, 29 parented periphs). The generator read the real key from the start; only this plan's Code Map inherited the error. Only the RGBW 4-children shape is actually unreachable.

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

## Auto Run Result

**Summary.** Ticket 114 built: `scripts/simulateur/03_catalog.py` (static, deterministic, fail-loud generator), the committed `scripts/simulateur/CATALOG.md` (27 handled-but-absent usage_ids prioritized in 4 tiers, 4 present-but-unmapped ids, structural gaps incl. RGBW and cover-slats tier 1, the dangling button mapping, the thermostat finding), README section 17 + workflow step 9, and 13 pinning unit tests. The "how to add a type" flow (00/01/02 + CAP-5 privacy pass) stays a documented human step — no dump data was added.

**Files changed.** `scripts/simulateur/03_catalog.py` (NEW), `scripts/simulateur/CATALOG.md` (NEW, generated), `scripts/simulateur/README.md`, `tests/unit/test_simulator_catalog.py` (NEW), this plan.

**Review findings breakdown.** Thorough review (4 lenses), 29 findings: 0 high, 5 medium, 23 low, 1 false. 10 patch groups applied by the implementer (commits `ac67b22`, format pass `c7538c1`): switch control-children row rescoped to switch parents (medium), RGBW threshold semantics corrected to all-children and the 82 hint fixed (medium), rubric-miss fail-loud test added (medium), rules block fail-loud + findings for absent setpoints and missing file, input-validation guards (non-dict entries, non-UTF-8, OSError, null fields, falsy value_type, duplicate periph_id), phantom-parent finding, tier-4 keyed off the mapping entry, French labels glossed + 127 blocked marker, README workflow step 9 + CLI overrides documented + hermetic test args. 3 rejected (line-number anchoring enhancement; default-mapping section out of intent scope; tautological test docstring). 1 false rejected (the "zero parent_id" claim was this plan's own Code Map error, not the change's — see Implementation Notes).

**Follow-up review recommendation.** `true` — three medium entries were patched on this first pass. Named unverified risk: the priority tiers remain documented static reasoning (no coverage tool exists in the repo to measure them), and the enriched-dump + e2e_sim surface (AC2/AC3) is unexercised by design — it activates only when someone (fmo01/user) provides a new dump through the extraction flow.

**Verification performed.** `python3 -m pytest tests/unit/ -q` — 431 passed, 2 warnings (pre-existing). `node tests/js/test-coherence.js` — green. `03_catalog.py --check` — catalog up to date; second full run byte-identical. `bash scripts/hooks/pre-push` — exit 0 (the ticket-115 format gate caught the implementation's non-conforming files twice; black/isort passes committed as `befca77` and `c7538c1`). Tree clean on `unstable`, commits `78f25e7` + `ac67b22` + `0f2c5cb` + `befca77` + `c7538c1`, not pushed.

**Residual risks.** The hitl step is open by design: extraction of new dump cases (real box, credentials, CAP-5 privacy pass) — the catalog now tells you exactly what to extract and in what order. Rubric tiers would benefit from real coverage tooling one day (rejected finding recorded). Line-number citations in the catalog drift with platform code evolution; refresh at regeneration.
