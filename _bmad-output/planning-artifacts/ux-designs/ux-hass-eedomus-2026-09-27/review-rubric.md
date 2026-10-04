# Spine Pair Review — Eedomus Config

## Overall verdict

The pair is a coherent, near-complete contract: the 5-tab IA, the localized microcopy regime, and the Supervision extension are consistently integrated, with real behavioral rules in every component row and an inheritance discipline that holds across spines and all three source SPECs. One mechanical break remains (`{components.coherence-table}` has no frontmatter token entry) and the new Supervision surface ships without any Key Flow exercising its four backfill actions. Nothing found blocks downstream extraction; both gaps are cheap to close.

## 1. Flow coverage — adequate

Checked: every UJ / requirement surfaced by the `sources` frontmatter (spec-eedomus-mapping-panel CAP-1..8, spec-eedomus-history CAP-1..4, spec-eedomus-i18n CAP-1..4) and every flow decision in `.memlog.md` against EXPERIENCE.md Key Flows. Flows 1–3 each carry a named protagonist, numbered steps, an explicit climax beat, and a failure path; panel-side coverage of the mapping-panel SPEC is complete (CAP-1..5 via Flows 1–2 and state patterns, CAP-6/7/8 via Flow 3). The i18n SPEC is a backend contract, not a UJ source — correctly absent from Key Flows.

### Findings

- **medium** The Supervision tab — a full new interaction surface (four backfill actions, queue statuses, metric charts, tab link) — is covered by component rows, state rows, and an interaction primitive, but no Key Flow exercises it end-to-end (EXPERIENCE.md §Key Flows). The closest journey a consumer can extract is the component table; nothing demonstrates the actions in sequence (e.g. stuck peripheral → « Réessayer maintenant » → feedback → queue re-render) nor the error → retry path within Supervision. *Fix:* add Flow 4 (« Surveiller la box et débloquer un backfill », same protagonist register), numbered, with climax and failure path.
- **medium** Rule deletion is claimed in the IA (Règles : « création, modification, suppression ») and in CAP-3 of the source SPEC, but no component row, interaction primitive, or state pattern specifies how a rule is deleted — and deletion is destructive, so the spine's own two-gesture discipline (restore, « Ignorer ») has no counterpart here (EXPERIENCE.md §Information Architecture, §Component Patterns `rule-form-field`, §Interaction Primitives). *Fix:* either add a delete primitive with its confirmation microcopy, or state explicitly that deletion lives outside this surface.

## 2. Token completeness — adequate

Checked: every frontmatter token and every `{path.to.token}` reference in DESIGN.md prose (all `{colors.*}`, `{typography.*}`, `{rounded.*}`, `{spacing.*}`, `{components.*}`), against the type rules of `design-md-spec.md`. Colors as HA CSS variables with `color-mix` is the platform-convention form the spec allows (UI-system inheritance, tokens referenced by name) — not a miss. Load-bearing contrast targets are stated and testable: diff text ≥ 4.5:1 and chip text ≥ 4.5:1 on their 12 % tinted backgrounds, verified on both default HA themes; semantic colors held at the 3:1 graphics threshold. Typography uses the `note` convention correctly; `spacing` and `rounded` carry stated `[ASSUMPTION]` provenance.

### Findings

- **high** `{components.coherence-table}` is referenced in the Components body section (DESIGN.md §Components, « Tableau de cohérence ») but has no entry in the frontmatter `components` object — the reference is unresolvable by a machine extractor, and the visual spec never reaches the flattened token stream downstream code mirrors (DESIGN.md frontmatter `components:` vs §Components). *Fix:* add a `coherence-table` entry (`background: '{colors.card-background}'`, `border-color: '{colors.divider}'`) or change the body reference to plain prose.

## 3. Component coverage — strong

Checked: every component name used anywhere in either spine (`periph-row`, `badge-modified`, `rule-form-field`, `yaml-editor`, `diff-line-added/removed/modified`, `version-card`, `coherence-table`, `coherence-chip-*`, `periph-popover`, `sort-header`, `entity-link`, `metric-chart-card`, `backfill-queue`) for a DESIGN.md §Components visual row and an EXPERIENCE.md §Component Patterns behavioral row. All 13 names have real specs on both sides — multi-clause rules, not one-word descriptions; the two Supervision components are fully specified visually and behaviorally despite the spine-only mock status, and every claim they make (standard HA buttons, text-carried statuses, four actions with named feedback) is supported by the spine tables alone. The only asymmetry is the frontmatter gap recorded in category 2, not a missing spec.

### Findings

(none)

## 4. State coverage — adequate

Checked: every IA surface (5 tabs, plus the popover and the two mobile surfaces) against the applicable states: empty, cold-load, focus, error, offline, permission-denied. Loading (skeletons) and websocket error are declared « Tous » and enumerated per shape; Supervision correctly reuses the positive-empty discipline (« Vide — rien à vérifier » → « Vide — rien à récupérer ») and adds a no-half-loaded-queue rule; Historique config covers the single-version edge; Règles covers validation, saving, reload, and save error with content preservation.

### Findings

- **low** Périphériques has no filter-no-result state pattern — the empty-search case exists only as a microcopy example (« Aucun périphérique ne correspond à "temp" » in Voice and Tone) while Cohérence has a full behavioral row for the same state, including `aria-live` (EXPERIENCE.md §State Patterns vs §Voice and Tone). *Fix:* mirror the Cohérence row for the Périphériques search (aria-live announcement + explicit empty-list state).
- **low** Permission-denied is undeclared: the panel is `require_admin` (Foundation) but no state pattern says what a non-admin sees — presumably HA's native gating, which is defensible, yet the spine never says so (EXPERIENCE.md §Foundation, §State Patterns). *Fix:* one sentence in Foundation (« non-admins never reach the panel; HA renders its own admin error ») closes it.

## 5. Visual reference coverage — strong

Checked: `mockups/` (mock-01-peripheriques.html, mock-02-regles.html, mock-03-historique.html), `imports/` (empty), `wireframes/` (none) against inline references. All three mocks are linked at the relevant section (DESIGN.md §Références visuelles) with per-file naming of what each illustrates, including the light/dark toggle rationale; spines-win-on-conflict is stated once with the inventory single-sourced in DESIGN.md and pointed to from EXPERIENCE.md; the Cohérence and Supervision spine-only status is explicitly recorded, which the review context confirms is deliberate. No orphans, no unspecific references.

### Findings

(none)

## 6. Bloat & overspecification — strong

Checked: pixel specs vs tokens, source restatement, prose-vs-table, unreadable sections, decorative narrative. EXPERIENCE.md is table-dominant with prose confined to Key Flows and editorial framing in Foundation — the right shape. DESIGN.md's editorial voice (Colors, Brand & Style) is permitted by the form and each passage lands on a rule. Numeric values that appear (44 px touch targets, 3 px diff bar, 12 % tint, ~760 px) are deltas the theme does not provide, not token restatements. The vendorised-lib selection criterion in `yaml-editor` is implementation-adjacent but load-bearing for the Accessibility Floor, so it earns its place. Only friction: the backfill scope note (« le domaine du backfill appartient à spec-eedomus-history ») appears twice (IA row and `backfill-queue` row) — harmless redundancy.

### Findings

- **low** Duplicate scope note for backfill ownership (EXPERIENCE.md §Information Architecture, Supervision row and §Component Patterns, `backfill-queue` row). *Fix:* keep it once, in the component row where the four actions live.

## 7. Inheritance discipline — adequate

Checked: `sources` frontmatter resolves (all three SPEC paths exist on disk); flow protagonists and scope decisions trace verbatim to `.memlog.md` decisions (witness journey #28, Flow 3 « dépannage express » climax, chip color semantics, graph component priority + SVG fallback, i18n regime matching spec-eedomus-i18n CAP-3 and the AGENTS.md rule it cites); glossary terms (`periph_id`, `usage_id`, `device_class`, `state_class`, `modified_by_rule`, `entity_id`, signal names, backfill statuses) are identical across both spines and the source SPECs; every `{...}` token reference in EXPERIENCE.md resolves to a DESIGN.md token by name. CAP/AD references (CAP-4, AD-13) are used for traceability, not restatement.

### Findings

- **medium** The `{components.coherence-table}` reference in DESIGN.md §Components does not resolve to any frontmatter token — an inheritance break in the token graph, recorded here because it is the same defect as category 2's high finding viewed from the cross-spine direction (DESIGN.md §Components vs frontmatter `components:`). *Fix:* same as category 2 — add the frontmatter entry or de-tokenize the body reference.

## 8. Shape fit — strong

Checked: section order and required defaults against the rubric. DESIGN.md body sections run Références visuelles (invented, earns its place as the single-sourced mock inventory) then Brand & Style → Colors → Typography → Layout & Spacing → Elevation & Depth → Shapes → Components → Do's and Don'ts — the canonical eight in canonical order. EXPERIENCE.md carries all eight required defaults (Foundation, IA, Voice and Tone, Component Patterns, State Patterns, Interaction Primitives, Accessibility Floor, Key Flows) plus Responsive & Platform, correctly triggered by the desktop+mobile parity commitment, plus the same invented Références visuelles pointer. Inspiration is not triggered: sources and memlog show no reference products or rejects. No dropped defaults.

### Findings

(none)

## Mechanical notes

- `{components.coherence-table}` (DESIGN.md §Components) is the only unresolvable token reference in either file.
- Wildcard references `{components.coherence-chip-*}` (DESIGN.md §Colors, §Shapes) and `{components.diff-line-*}` (EXPERIENCE.md §Information Architecture) are human-readable but not machine-resolvable; both families are fully enumerated in the frontmatter, so no information is lost.
- EXPERIENCE.md §Component Patterns names the chip family `coherence-chip` while DESIGN.md enumerates `coherence-chip-no-entity`…`-ok`; the two forms are consistent in intent but a strict name-matcher sees 6 names where 1 row exists on the EXPERIENCE side.
- `mockups/mock-03-historique.html` predates the « Historique config » rename; the spine label wins on conflict (stated), but a consumer rendering from the mock will see the old tab name.
- Mixed quote forms: the Cohérence filter row uses curly quotes (“{requête}”) while the same string elsewhere uses escaped straight quotes — cosmetic only.
- Frontmatter: DESIGN.md carries `name`, `description`, `status: final`, `updated`; EXPERIENCE.md carries `name`, `status: final`, `updated`, `sources` (all resolve). Mermaid: none used.

## Severity counts

Critical 0 · High 1 · Medium 2 · Low 3

(The category 7 medium is the same defect as category 2's high, viewed cross-spine — counted once at its highest severity.)
