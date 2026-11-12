---
title: "Fix 123 — cleanup_unused_entities : protéger disabled_by:user + dry_run (issue #136 follow-up)"
type: 'bugfix'
ticket: 123
created: 2026-11-01
status: done
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['lens-123-quick']
review_loop_iteration: 0
context: []
baseline_revision: '50a6914'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Issue #136 follow-up (comment 2026-11-12): `eedomus.cleanup_unused_entities` removes ALL disabled entities, including `disabled_by: user`. Deleting a registry entry erases the disable flag, so at the next setup the peripheral recreates its entity ENABLED — on the reporter's install ~576 deliberately-disabled peripherals would resurrect at once (renamed "[Invisible]" periphs, manually disabled History Progress sensors, HA→eedomus mirror entities whose re-enablement would create a feedback loop).

**Approach:** in the cleanup handler, skip registry entries whose `disabled_by == "user"` and count them separately in the response (`skipped_user_disabled: N`); entries disabled by the integration itself are still cleaned. Add a `dry_run` boolean field to the service (services.yaml + strings.json + translations en/fr) that lists what would be removed without removing anything, with `dry_run: true` in the response. Unit tests pin all three behaviors.

</frozen-after-approval>

## Implementation Notes

Oneshot rationale : ~30 lines in the handler (`custom_components/eedomus/services.py:339-532`), one field in `services.yaml`, the same field label in `strings.json` + `translations/en.json` + `translations/fr.json` (mechanical, drift tests enforce structural identity), ~60 lines of tests in the existing `tests/unit/test_cleanup_unused_entities.py`. One user-facing goal, all edits small and mechanical.

Key decisions:
- Skip rule: `entity_entry.disabled_by == "user"` → never in `entities_to_remove`; counted in a separate `skipped_user_disabled` tally and returned in the response. `disabled_by == "integration"` or None-but-disabled stays removable (integration's own choice). The mass-deletion guard keeps counting only real removals.
- `dry_run` field: `services.yaml` `cleanup_unused_entities.fields.dry_run` (boolean, default false, not required); handler reads `call.data.get("dry_run", False)`; when true, skip the removal loop entirely, log the would-be list, return `dry_run: True` plus the counts.
- i18n: add `fields.dry_run.name/description` under `cleanup_unused_entities` in `strings.json`, `translations/en.json`, `translations/fr.json` — structurally identical in all three (test_translations_structure.py enforces it). FR text: « Exécuter sans rien supprimer (liste uniquement) ».
- Response shape gains `skipped_user_disabled` and (only meaningful with dry_run) `dry_run` — additive keys, no breakage.
- Do NOT touch: the orphan/remap-duplicate logic from the #136 fix, the mass-deletion guard, cleanup_unused_devices.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/test_cleanup_unused_entities.py tests/unit/test_translations_structure.py -q` — new tests pass (user-disabled skipped + counted, dry_run removes nothing and says so, guard unaffected), structure drift green.
- `python3 -m pytest tests/unit/ -q` — full suite green.
- `node tests/js/test-coherence.js` + `node tests/js/test-i18n-guard.js` — green (no panel change).
- `bash scripts/hooks/pre-push` — exit 0 (black/isort).
- Manual (post-deploy Pi): run the action with `dry_run: true`, confirm the response lists `skipped_user_disabled` and removes 0; then a real run confirms user-disabled entities survive.

## Review Triage Log

Lens `lens-123-quick` (auto, quick) — 5 findings:

1. **Response keys unreachable** — handler returned a report dict but the service was registered without `supports_response`, so HA would never send it back. **Fixed:** registered with `supports_response=SupportsResponse.OPTIONAL` (`services.py`); conftest stub upgraded to a real `SimpleNamespace(NONE/OPTIONAL/ONLY)`; two test-side `async_register` lambdas gained `**kwargs`.
2. **FR wording in plan ≠ shipped FR label** — cosmetic drift between this plan's sketch (« Exécuter sans rien supprimer (liste uniquement) ») and the shipped `translations/fr.json` text (« Simulation » / « Lister les entités correspondantes sans rien supprimer »). **Accepted** — shipped text is the source of truth; plan note only.
3. **`dry_run` truthiness trap** — without a boolean selector, a string `"false"` from the UI would be truthy. **Fixed:** `selector: boolean:` in `services.yaml` + `bool(call.data.get("dry_run", False))` in the handler.
4. **dry_run + mass-guard refusal logged no list** — on refusal with `dry_run: true` the would-be removals were only in the response, not the log. **Fixed:** the refusal branch now logs each would-be removal when `dry_run` is set.
5. **Verified clean** — skip-before-orphan ordering (user-disabled entries short-circuit before orphan/remap checks), mass-deletion guard untouched and counting only real removals, `cleanup_unused_devices` untouched, i18n drift tests green, English-only repo text respected.

**Final verification (post-fix):** `pytest tests/unit/ -q` = 481 passed; `test-coherence.js` + `test-i18n-guard.js` + `test-regles-styles.js` all green; black 26.10.1 + isort 9.0.2 clean; `scripts/hooks/pre-push` exit 0.
