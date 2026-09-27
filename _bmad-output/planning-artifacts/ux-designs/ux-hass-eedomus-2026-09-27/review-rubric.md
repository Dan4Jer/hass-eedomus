# Spine Pair Review — hass-eedomus

Spines reviewed: `DESIGN.md` + `EXPERIENCE.md` in `ux-hass-eedomus-2026-09-27/`.
Sources extracted: EXPERIENCE frontmatter → `SPEC.md` (CAP-1..CAP-5); corroborated against `.memlog.md`.
Scope note honored: colors intentionally use `var(--...)` HA theme variables — absence of hex is an accepted inheritance decision and is not counted as a finding.

## Overall verdict

The pair is close to a consumable contract: token discipline is excellent (every `{path.to.token}` in both files resolves to a DESIGN.md frontmatter token, including EXPERIENCE.md's cross-file references), and the delta-only "HA theme is the design system" posture is consistently maintained. But it is not yet complete: EXPERIENCE.md is missing its **Responsive & Platform** section even though desktop+mobile parity is a committed, load-bearing decision, the two files' component tables do not share names, and the YAML editing mode — half of CAP-3 — has no key flow. One structural addition plus naming alignment before handing to architecture/story-dev.

---

## 1. Flow coverage — verdict: adequate

Extraction: one Key Flow, "Flow 1 — Corriger une unité erronée" (protagonist: "l'utilisateur HACS type de la discussion #28", steps 1–7, explicit climax at step 6, failure path present). It exercises CAP-1 (sidebar panel), CAP-2 (list + search), CAP-3-form (rule creation + validation), CAP-4 (save + auto-apply + feedback), and CAP-5 (history view + conditional restore). Named protagonist present (persona reference, not a proper name — acceptable), numbered steps, climax beat, and failure path all present.

Findings:

- [medium] No key flow exercises the raw YAML editing mode or the form ↔ YAML roundtrip ("Bascule formulaire ↔ YAML sans perte", EXPERIENCE.md Component Patterns / Éditeur YAML row). This is half of CAP-3 and a committed behavioral guarantee; a story-dev consumer has no witness journey showing the roundtrip preserving state or handling YAML that cannot round-trip cleanly. Fix: add a compact Flow 2 (YAML-mode edit → validation → save), or a failure-path annex to Flow 1.
- [low] Restoration appears only conditionally ("S'il s'était trompé, un clic sur « Restaurer » remettrait la version précédente", Flow 1 step 7) — subjunctive, not demonstrated. CAP-5's restore is a first-class action with archive semantics; it deserves a shown beat, not a hypothetical. Fix: make step 7 a real action in the flow or add a two-step restore flow.
- (Mobile editing gap folded into finding H1 below — same root cause.)

## 2. Token completeness — verdict: strong

Extraction: frontmatter defines 15 colors, 3 typography roles, 2 rounded, 5 spacing, 8 components. Every `{path.to.token}` reference in DESIGN.md prose (Colors, Typography, Layout, Elevation, Shapes, Components sections), every reference inside the `components` frontmatter objects, and every cross-file reference in EXPERIENCE.md (`{components.badge-modified}`, `{components.diff-line-added/removed/modified}`, `{colors.diff-added/removed/modified}`, `{colors.error}`) resolves to a defined token. `{spacing.1}`–`{spacing.5}`, `{rounded.DEFAULT}`, `{rounded.full}`, `{typography.code.fontFamily}` all resolve. Contrast for theme-inherited colors is delegated to the theme with an explicit statement ("la lisibilité clair/sombre est vérifiée via les variables", EXPERIENCE.md Accessibility Floor) — acceptable under the inheritance decision.

Findings:

- [medium] The one contrast-critical combination the panel itself creates — diff text in `{colors.diff-*}` on a `color-mix(... 12%, var(--card-background-color))` tinted background — has no contrast target. Theme inheritance cannot vouch for this pair because the tint is panel-invented. The 12% ratio is flagged `[ASSUMPTION]` (DESIGN.md Colors) but no acceptance threshold (e.g., WCAG AA 4.5:1 for diff text on its tint) is stated, so a story-dev cannot write a test. Fix: add a contrast target to the diff-line component spec and name it as the implementation-time check for the 12% assumption.
- [low] `{colors.success}` and `{colors.warning}` are defined in frontmatter but never referenced in any prose; they duplicate the values of `{colors.diff-added}` / `{colors.diff-modified}`. A consumer cannot tell which token to use for a non-diff success/warning signal. Fix: either drop them or add one line stating they are the panel-wide semantic aliases, with diff-* reserved for the history view.

## 3. Component coverage — verdict: adequate

Extraction: DESIGN.md.Components rows = periph-row, badge-modified, rule-form-field, yaml-editor, diff-line-added/removed/modified, version-card. EXPERIENCE.md Component Patterns rows = Liste de périphériques, Formulaire de règle, Éditeur YAML, Vue diff type git, Carte de version avec restauration. All rows carry real rules (multi-clause behavioral rules; multi-token visual specs) — no one-word descriptions. Behavioral rules present for: device list (search, badge, per-row action, mobile reflow), rule form, YAML editor, diff view, version cards.

Findings:

- [medium] Component names are not identical across the two files, and granularity differs: `periph-row` ("Ligne de périphérique") vs "Liste de périphériques" (row vs list); `rule-form-field` ("Champ de formulaire de règle") vs "Formulaire de règle" (field vs form); `diff-line-*` vs "Vue diff type git" (lines vs view). A consumer building from EXPERIENCE.md's table must guess the pairing to reach DESIGN.md's visual specs. Only `yaml-editor` ↔ "Éditeur YAML" and `version-card` ↔ "Carte de version" are near-verbatim. Fix: add the DESIGN token name in parentheses to each EXPERIENCE row (or align names outright).
- [low] `badge-modified` has a visual row in DESIGN.md but no dedicated behavioral row in EXPERIENCE.md — its behavior is folded into the "Liste de périphériques" row. The badge carries the load-bearing "touché par la dernière règle" semantics (memlog decision 1); it deserves its own row stating when it appears, clears, and survives a reload. Fix: extract a badge row with appearance/clearing rules.
- [low] The search field has specified behavior (Interaction Primitives: real-time filter, case-insensitive, counted results) but no visual home — it is not in DESIGN.md.Components and its inheritance from HA input styling is implied (via `rule-form-field`) but unstated. Fix: one line in DESIGN.md stating the search field inherits HA input styling (rule-form-field tokens).

## 4. State coverage — verdict: adequate

Walk of IA surfaces and applicable states: Périphériques (empty ✓, cold-load ✓ via "Tous" skeletons, search-empty ✓ — covered in Voice and Tone « Aucun périphérique ne correspond »), Règles (empty ✓, validation error ✓, saving ✓, post-save apply ✓, save error ✓, websocket error ✓), Historique (empty ✓, websocket error ✓), plus keyboard focus ✓ (Accessibility Floor).

Findings:

- [medium] The one-version state of Historique is unspecified. The diff is defined "entre la version sélectionnée et la précédente" (IA, Component Patterns) — with exactly one archived version there is no previous, and State Patterns covers only zero versions ("Aucune sauvegarde encore"). A story-dev will hit this on the first real save. Fix: add a state row: 1 version → no diff available, card shows summary only (or diff disabled with explanation).
- [low] Permission-denied is not covered as a state. The panel is `require_admin` (Foundation), and HA presumably hides the sidebar entry, but the spine never says so — a consumer cannot distinguish "handled by HA" from "not considered". Fix: one line in State Patterns: non-admins never see the panel; HA's require_admin handles access; no in-panel denial screen.
- [low] Offline is never named as a state; it is implicitly folded into "Erreur de commande websocket" (message + retry, no infinite spinner). Adequate by construction, but the mapping is left to inference. Fix: one clause naming network loss as a websocket-error case.
- [low] Rule deletion has no specified behavior anywhere (creation ✓, modification implied, deletion named only in IA "création, modification, suppression"). No confirmation or undo rule, no state pattern. Fix: add deletion behavior to the Formulaire de règle row (confirm or trust-the-user, per Drift precedent).

## 5. Visual reference coverage — verdict: strong (vacuously clean)

Extraction: `mockups/` and `wireframes/` do not exist; `imports/` exists and is empty (mocks follow the gate, per scope note). Neither spine links to any visual file, so there are no dangling references, no orphans, and no unspecific references. Clean by construction.

Findings: none.

## 6. Bloat & overspecification — verdict: strong

DESIGN.md is rigorously delta-only: it specifies exactly the two layers HA does not provide (diff language, modified badge) and refuses everything else, with the refusal written down (Do's and Don'ts, "Interdit" clauses). EXPERIENCE.md carries backend identifiers (`eedomus/get_suggestions`, `eedomus/get_schema`, `eedomus/validate_config`, `.storage`, `custom_mapping.yaml`, "chemin CAP-4") — this is traceability to the SPEC contract, not bloat; it is what makes the spine consumable by story-dev. Deferred implementation choices are consistently marked `[ASSUMPTION]` (spacing scale, mono font, 12% tint, YAML syntax-highlight token mapping, vendor lib) rather than overspecified.

Findings: none.

## 7. Inheritance discipline — verdict: adequate

Sources frontmatter resolves (`_bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md`, relative to repo root — verified present). EXPERIENCE.md token references resolve to DESIGN.md tokens by name, 100% (see category 2). DESIGN.md correctly omits a `sources` key per the design-md spec's frontmatter rules. Component names across files: not identical (see category 3 finding — counted once there).

Findings:

- [low] Requirement names are not carried verbatim: the SPEC's capabilities are "CAP-1 — Panneau dans la barre latérale" … "CAP-5 — Historique et restauration des 3 dernières versions", but only CAP-4 is ever named in EXPERIENCE.md ("Restaurer applique le chemin CAP-4"). CAP-1/2/3/5 are covered behaviorally but a consumer cannot map capability → surface/flow without inferring. Fix: add a four-line traceability note (CAP-N → tab/section) to the IA or Foundation section.

## 8. Shape fit — verdict: thin

DESIGN.md: body sections present in canonical order (Brand & Style → Colors → Typography → Layout & Spacing → Elevation & Depth → Shapes → Components → Do's and Don'ts) — conforms. Frontmatter carries extra keys (`status`, `updated`) beyond the design-md spec's token set; harmless metadata, noted for completeness. EXPERIENCE.md: Foundation ✓, Information Architecture ✓, Voice and Tone ✓, Component Patterns ✓, State Patterns ✓, Interaction Primitives ✓, Accessibility Floor ✓, Key Flows ✓ — but two required defaults are absent.

Findings:

- [high] **Responsive & Platform is missing** from EXPERIENCE.md — and desktop+mobile parity is a committed, load-bearing decision (memlog: "l'édition de mapping doit être confortable sur téléphone aussi, pas seulement consultable"; Foundation repeats it in bold). What exists is scattered and partial: periph-row mobile reflow (Component Patterns), tabs kept on mobile (IA), 44px targets (Accessibility Floor). There is no breakpoint contract, no per-surface mobile behavior, and — most damaging — no mobile treatment of the two hardest surfaces: the YAML editor and the autocomplete popup on a phone keyboard. A story-dev asked to deliver "confortable sur téléphone" has nothing to build or test against. This gap also swallows the mobile witness journey (no flow edits on a phone). Fix: add the Responsive & Platform section: breakpoints (or HA panel-width behavior), per-tab mobile layout, YAML editor behavior on small viewports, autocomplete-on-touch, and what is explicitly deferred to read-only on mobile if anything.
- [medium] **Inspiration & Anti-patterns is missing.** Its anti-pattern half is partially covered by "Interdit partout" (Interaction Primitives) and the Voice Do/Don't, but the inspirations/precedents that anchor judgment calls (diff-view precedents, HA panel conventions followed) are nowhere. Fix: add a short section — even three bullets (HA panel conventions lifted; git-diff convention; rejected alternatives) — or fold "Interdit partout" into it explicitly.

---

## Mechanical notes

- Sources extracted from EXPERIENCE.md frontmatter: `SPEC.md` only. `.memlog.md` is not listed as a source (working log, not contract) — acceptable; all memlog decisions were nevertheless verified present in the spines (both color decisions, 3-tab IA, mobile parity, witness journey, shortcut list→règles, deferred assumptions).
- Flow 1 coverage map (inferred, since no CAP traceability exists — see finding 7): step 2 → CAP-1/CAP-2; steps 3–4 → CAP-2/CAP-3; steps 5–6 → CAP-4; step 7 → CAP-5.
- Token resolution detail: `{colors.text-secondary}` is referenced in DESIGN.md prose (Colors bullet); `{colors.accent-contrast}` resolves via the badge component spec; `typography.body`/`label` are note-only tokens (valid per the platform-convention pattern in design-md-spec.md); `rounded.DEFAULT` uses a theme variable — accepted under the inheritance decision per scope note.
- Visual reference inventory: `imports/` = 0 files; `mockups/`, `wireframes/` = absent. No spine links reference them.
- Both spines are `status: draft` — findings above assume a pre-final review pass; nothing blocks the mockup gate.
- Severity = downstream impact on architecture/story-dev consumption, per brief.

Finding counts: 0 critical, 1 high, 5 medium, 7 low.
