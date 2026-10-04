# Spine Pair Review — hass-eedomus

Spines reviewed: `DESIGN.md` + `EXPERIENCE.md` in `ux-hass-eedomus-2026-09-27/` (FINAL, extended in place with the 4th tab « Cohérence »).
Sources extracted: EXPERIENCE frontmatter → `_bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md` (CAP-1..CAP-5 + the declared new coherence CAP); corroborated against `.memlog.md` and the pre-update `review-rubric.md` (Sep 27) to verify the update did not damage prior content.
Scope notes honored: (1) Cohérence is deliberately spine-only — not counted as a visual-reference miss; tested only against claims the spine itself makes. (2) `var(--...)` HA theme variables and `color-mix` instead of hex are the platform-inheritance convention — not counted as findings.

## Overall verdict

The 4th-tab extension is integrated cleanly: every pre-existing contract area (diff language, badge, mocks links, Responsive & Platform, the one-version state, the demonstrated restore, Flow 2, contrast criteria) survived the update intact, and all findings fixed in the previous Update pass remain fixed. The pair remains a consumable contract for architecture/story-dev: every flow, state, and token the three original tabs need is committed, and the Cohérence tab is behaviorally complete. One gap has real downstream weight: the coherence table itself has no visual spec row in DESIGN.md — and because the tab is spine-only by decision, that row is the only place a consumer can get it. Otherwise the residue is low-severity naming and state-edge hygiene.

## 1. Flow coverage — strong

What was checked: SPEC CAP-1..CAP-5 + the declared new coherence CAP (« hors des 5 du SPEC »), each mapped to a Key Flow with named protagonist, numbered steps, a climax beat, and a failure path. Flow 1 (protagonist: utilisateur HACS #28, steps 1–7, labeled climax step 6, failure path) covers CAP-1 (Foundation: sidebar, require_admin — setup capability, no flow required), CAP-2 (steps 2–3), CAP-3-form (steps 4), CAP-4 (steps 5–6), CAP-5 (step 7 — restore now demonstrated, not subjunctive). Flow 2 (same protagonist, mobile, steps 1–4, failure path) covers CAP-3-YAML including the roundtrip guarantee. Flow 3 « Dépannage express » (Dan, desktop, steps 1–6, labeled climax step 5, failure path) covers the new coherence CAP end to end: filter, popover, entity-link, « Créer une règle » variant, re-check after fix.

### Findings
- **low** Flow 2 has no labeled climax beat — step 4 carries the payoff (roundtrip preserved + nominative confirmation) but is unmarked, where Flows 1 and 3 label their climax explicitly (EXPERIENCE.md, Key Flows, Flow 2). *Fix:* mark step 4 as **Climax** for scan consistency.

## 2. Token completeness — adequate

What was checked: every frontmatter token (20 colors, 3 typography roles, 2 rounded, 5 spacing, 16 components) and every `{path.to.token}` reference in both spines, extracted mechanically. DESIGN.md: 38 distinct references, all resolve. EXPERIENCE.md: 7 cross-file references — 6 resolve by name; 1 does not (finding below). Type rules per `design-md-spec.md`: the `var(--...)` values and note-only typography follow the documented UI-system-inheritance pattern (accepted per scope note); `rounded.full: 9999px` conventional; kebab-case keys conform. Contrast targets stated for the load-bearing panel-invented combinations: diff text ≥ 4.5:1 on tinted background and chip text ≥ 4.5:1, both verified light + dark — the chip criterion correctly extends the diff criterion to the new tab.

### Findings
- **low** `{components.coherence-chip}` in EXPERIENCE.md's IA table does not resolve to any DESIGN.md token — DESIGN defines only the five variants (`coherence-chip-no-entity` / `-questionable` / `-rule` / `-retry` / `-ok`) and uses the `{components.coherence-chip-*}` family form (EXPERIENCE.md, Information Architecture, Cohérence row). *Fix:* change to `{components.coherence-chip-*}` (matching DESIGN.md's own family syntax). Counted once here; also drives the naming note in category 7.
- **low** `{colors.warning}` and `{colors.success}` are defined but never referenced by token path — prose reaches those values only as raw `var(--warning-color)` / `var(--success-color)` (DESIGN.md frontmatter vs Colors section; carried from the pre-update review). *Fix:* drop the two tokens, or one line making them the panel-wide semantic aliases with `diff-*` reserved for the history view.

## 3. Component coverage — adequate

What was checked: every component name used anywhere in either spine, verified against a DESIGN.md.Components visual row and an EXPERIENCE.md.Component Patterns behavioral row, with real rules (multi-clause, not one-word). Covered on both sides: `periph-row`, `badge-modified`, `rule-form-field`, `yaml-editor`, `diff-line-added/-removed/-modified`, `version-card`, `coherence-chip-*` (5 variants, visual; family, behavioral), `periph-popover`, `entity-link`. The new components carry real specs: popover (surface, elevation inheritance, single-open, collapsible raw section), chips (icon + text, tint discipline, cumulable), sort header (focusable, `aria-sort`, theme outline), entity link (inline text link, no button chrome).

### Findings
- **medium** `coherence-table` has a behavioral row in EXPERIENCE.md.Component Patterns but no visual row in DESIGN.md.Components — the table *container* is unspecified: row separation (filet vs none), sticky-header treatment when scrolled (background/elevation over passing content), cell padding/density, and the visual treatment of the mobile expanded row. The individual cells' contents (chips, sort header, entity link) are specified, the container is not — and because the Cohérence tab is spine-only by decision, there is no mock to fall back on; an implementer must invent these visuals (EXPERIENCE.md Component Patterns « Tableau de cohérence »; DESIGN.md Components, absent). *Fix:* add a `coherence-table` row (or a short table-primitives note) in DESIGN.md.Components covering separators, sticky-header chrome, and density; the mobile expanded row can defer to the popover's flat-surface rule already written in Elevation & Depth.
- **low** `sort-header` has a DESIGN.md visual row but no EXPERIENCE.md.Component Patterns row — its behavior is specified, but in Interaction Primitives (« Tri de colonnes ») rather than the component table (DESIGN.md Components « En-tête de tri »; EXPERIENCE.md Component Patterns, absent). *Fix:* add a one-line row, or an explicit cross-reference from the coherence-table row.

## 4. State coverage — adequate

What was checked: walk of all four IA surfaces plus global states. Périphériques: empty ✓, cold-load ✓ (skeletons), search-empty ✓ (microcopy « Aucun périphérique ne correspond »), websocket error ✓. Règles: empty ✓, validation error ✓, saving ✓, applying ✓, save error with retry ✓. Historique: empty ✓, one version ✓ (kept from the Update pass), websocket error ✓. Cohérence: positive empty ✓, deferred cold-load ✓ (dedicated skeleton row), command error ✓ (dedicated « Réessayer » row, half-loaded table never shown as complete). Focus ✓ (Accessibility Floor), loading-vs-error discipline ✓ (« jamais de spinner infini » everywhere).

### Findings
- **low** Rule deletion behavior is unspecified — creation and modification are fully specified, deletion is named only in the IA (« création, modification, suppression ») with no confirmation/undo rule anywhere (EXPERIENCE.md, Information Architecture, Règles row; carried from the pre-update review). *Fix:* one clause in the Formulaire de règle row (confirm-or-trust, and what happens to the badge/history).
- **low** The coherence quick-filter zero-result state is unstated — the Périphériques search has a named empty treatment, the Cohérence table's text filter does not (EXPERIENCE.md, State Patterns, absent for Cohérence filter). *Fix:* reuse the « Aucun périphérique ne correspond » pattern in a state row or in the coherence-table behavioral row.
- **low** Permission-denied and offline are still not named as states — offline is folded into « Erreur de commande websocket » by inference, and non-admin access is left to `require_admin` without the spine saying so (EXPERIENCE.md, State Patterns; known deferred item recorded in `.memlog.md`). *Fix:* one clause each, or keep as a recorded deferral — but the deferral should live in the spine, not only the memlog.

## 5. Visual reference coverage — strong

What was checked: inventory of `mockups/` (3 files), `imports/` (empty), `wireframes/` (absent); `.working/` contains working copies and the coherence source extraction — correctly not linked. Both spines link all three mocks inline at « Références visuelles », each with what it illustrates (Périphériques list/filter/badge; Règles form/YAML toggle/validation; Historique versions/restore/diff), and both state spines-win-on-conflict (« Les spines priment sur tout mock en cas de conflit »). No orphans, no unspecific references. The Cohérence spine-only decision is stated in both spines — per the scope note it is not a miss here; the one place it has teeth is the category 3 medium (the table container has no visual spec anywhere).

### Findings

(none)

## 6. Bloat & overspecification — strong

What was checked: pixel specs vs tokens, source restatement, prose-vs-table, unreadable sections, decorative narrative. DESIGN.md stays rigorously delta-only and keeps its editorial voice (allowed); every refusal is written down (Interdit clauses, Do's and Don'ts updated with the chip rules). EXPERIENCE.md is table-first with behavior rules, not prose; backend identifiers (`eedomus/get_coherence`, `eedomus/validate_config`, AD-13) are traceability to the SPEC/architecture contract, and the coherence data contract is explicitly framed as behavioral (« sans préscrire l'implémentation backend »). `[ASSUMPTION]` markers (12 % tint, chip glyphs, spacing scale, mono font, YAML highlight mapping) keep implementation choices deferred rather than overspecified.

### Findings
- **low** The IA Cohérence row carries backend join detail (« cross-join registry × `eedomus/get_peripherals` sur `periph_id`, côté backend ») — implementation traceability inside a UX surface table; the same fact already lives, better framed, in the coherence-table behavioral row (EXPERIENCE.md, Information Architecture, Cohérence row). *Fix:* compress the IA row to the user-facing surface contract and leave the join to the behavioral row.

## 7. Inheritance discipline — adequate

What was checked: `sources` frontmatter resolves (`_bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md` — verified present); requirement names verbatim (CAP-4 named in the restore path; the coherence extension explicitly labeled « nouveau CAP, hors des 5 du SPEC »); glossary consistent across spines and sources (périphérique, `usage_id`, `periph_id`, mapping, règle, version); component names identical across all sections; EXPERIENCE token references resolving to DESIGN tokens by name. Pre-existing content integrity verified against the pre-update review: all previously fixed findings (component name alignment, Responsive & Platform, Flow 2, one-version state, demonstrated restore, contrast criteria) are intact, and the update added rather than displaced. Frontmatter hygiene: both spines `status: final`, `updated: 2026-10-04`; DESIGN description updated to name the coherence layer.

### Findings
- **low** No CAP → surface/flow traceability: only CAP-4 and the new coherence CAP are ever named; CAP-1/2/3/5 are covered behaviorally but a consumer must infer the mapping (carried from the pre-update review; EXPERIENCE.md Foundation/IA). *Fix:* a five-to-six-line CAP map (CAP-N → tab/flow) in Foundation or IA.
- **low** Chip family naming is not identical across the two files — EXPERIENCE.md uses bare `coherence-chip` (IA + Component Patterns rows), DESIGN.md defines and uses only the five `coherence-chip-<signal>` variants plus the `{components.coherence-chip-*}` family form. Same root as the category 2 unresolved reference, counted there. *Fix:* adopt the `coherence-chip-*` family form in both files.

## 8. Shape fit — strong

What was checked: canonical section order and required defaults. DESIGN.md body: Références visuelles (invented — earns its place, it carries the mock links) → Brand & Style → Colors → Typography → Layout & Spacing → Elevation & Depth → Shapes → Components → Do's and Don'ts — canonical order preserved; no dropped defaults. EXPERIENCE.md: all eight required defaults present (Foundation, Information Architecture, Voice and Tone, Component Patterns, State Patterns, Interaction Primitives, Accessibility Floor, Key Flows) plus Responsive & Platform (required-when-applicable: desktop+mobile parity — present and extended to the new tab with the popover/expanded-row parity contract) plus Références visuelles (earns its place). Inspiration not triggered — no external reference products; HA itself is the inherited platform. Invented sections are two and both load-bearing.

### Findings

(none)

## Mechanical notes

- Token resolution (mechanical extraction): DESIGN.md — 38 distinct `{path.to.token}` references, all resolve to frontmatter tokens (20 colors, 3 typography, 2 rounded, 5 spacing, 16 components). EXPERIENCE.md — 7 cross-file references; 6 resolve (`{colors.error}`, `{components.badge-modified}`, `{components.diff-line-added}`, `{components.diff-line-removed}`, `{components.diff-line-modified}`, `{components.entity-link}`); 1 does not (`{components.coherence-chip}`, category 2 finding).
- Frontmatter completeness: DESIGN.md carries name, description, status, updated, and all five token groups; type rules conform to the design-md spec's UI-system-inheritance pattern (`var(--...)` references accepted per scope note; `typography.body`/`label` are note-only tokens — valid platform-convention form; `rounded.full: 9999px` conventional). EXPERIENCE.md carries name, status, updated, sources. No Mermaid diagrams in either spine — nothing to syntax-check.
- Raw CSS-variable usage in prose (`var(--primary-color)`, `var(--ha-card-box-shadow)`, `var(--code-font-family)`) is deliberate theme inheritance, consistent with the token comments; not token-path misses.
- Visual inventory: `mockups/` = 3 files, all linked inline in both spines with what each illustrates; `imports/` = 0 files; no `wireframes/`; no orphans; spines-win-on-conflict stated once in each spine. `.working/` (mock drafts + `source-extraction-coherence.md`) correctly unlinked.
- Pre-existing content integrity: verified line-level against the pre-update `review-rubric.md` (Sep 27) and `.memlog.md` — diff language and C1 fix, badge, mock links, Voice table, all prior State Patterns rows, Responsive & Platform, Flow 1/2, the one-version state, and the demonstrated restore are all intact; the update added (coherence tokens ×5, components ×6, IA row, 4 component-pattern rows, 3 state rows, 3 primitives, responsive bullet, a11y rules, Flow 3) without displacing anything.
- The prior `review-rubric.md` (Sep 27, pre-FINAL pass) has been overwritten by this report per instruction; `review-accessibility.md`, `validation-report.md/.html` are from the previous run and not refreshed.
- Severity = downstream impact on architecture/story-dev consumption, not fix difficulty.

Finding counts: 0 critical, 0 high, 1 medium, 9 low.
