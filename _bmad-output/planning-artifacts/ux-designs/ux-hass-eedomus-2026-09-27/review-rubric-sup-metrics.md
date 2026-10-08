# Spine Pair Review — Eedomus Config (delta: Supervision metrics, 2026-10-08)

## Overall verdict

The Supervision metrics redesign lands cleanly in EXPERIENCE.md (IA row, Component Patterns, Key Flow beat) and in the synchronized mapping-panel SPEC (CAP-9): the behavioral contract is source-extractable, the no-subscription stance holds, and the system-metric card carries an explicit out-of-scope fallback. The gap is on the visual side: the two new non-chart cards (activity gauge, static count + category chips) have no contract in DESIGN.md, and the `metric-chart-card` name now covers cards that are not charts. Pre-existing findings from the 2026-10-06 full pass remain open and are restated for the record.

## 1. Flow coverage — adequate

Checked: the Supervision journey (Dan, evening beat) against the redesigned metric cards. The beat now names the gauge, the category-complete count and the system metric; climax and failure paths intact.

### Findings

- **medium** (pre-existing, 2026-10-06): no Key Flow exercises the four backfill actions end-to-end (EXPERIENCE.md §Key Flows). *Fix:* add Flow 4 (« Surveiller la box et débloquer un backfill ») with the backfill-indicator work (story 110 territory).
- **medium** (pre-existing, 2026-10-06): rule deletion is claimed in the IA but has no component, primitive, or state row. *Fix:* decide scope explicitly.

## 2. Token completeness — strong

Checked: the delta introduces no new token references. Correction of the 2026-10-06 pass: `{components.coherence-table}` DOES have a frontmatter entry (DESIGN.md line 121) — that finding was stale. The newly added `metric-value-card` token is defined and referenced consistently.

### Findings

(none)

## 3. Component coverage — thin (delta)

Checked: every Supervision element against DESIGN.md §Components (visual) and EXPERIENCE.md §Component Patterns (behavioral).

### Findings

- **high** The activity gauge has a behavioral spec (X periphs active in the last hour, snapshot) but no visual contract: DESIGN.md only defines `metric-chart-card` (chart surface, series palette rule). A gauge needs its own visual rule (surface, HA gauge component priority vs SVG fallback, semantic color, never color alone). *Fix:* add a `metric-value-card` component with a gauge variant to DESIGN.md, or extend the metric-chart-card section.
- **medium** The static count card + category chips have no visual spec. The chips should inherit the coherence-chip discipline (12 % tint on card background, chip text ≥ 4.5:1, never color alone) but the spine does not say so. *Fix:* state the inheritance in DESIGN.md.
- **medium** `metric-chart-card` now covers non-chart cards (gauge, static value) — the name-to-visual mapping a downstream extractor relies on is muddy. *Fix:* split naming: charts stay `metric-chart-card`; non-chart metric cards become `metric-value-card`.

## 4. State coverage — strong

Checked: the redesigned cards against the existing Supervision states. The absent-source fallback for the system metric is specified on both sides (card stays out of scope; never a half-empty grid presented as complete); empty and error states already cover the metric zone.

## 5. Visual reference coverage — strong

Unchanged: Supervision remains spine-only (no mock), consistent with DESIGN.md §Références visuelles.

## 6-8. Judgment — adequate

Bloat: the delta stays lean; no pixel specs, no source restatement. Inheritance: EXPERIENCE references resolve; spec CAP-9 and the spine now carry identical metric enumerations. Shape fit: canonical order intact.

## Mechanical notes

- The `updated:` field of EXPERIENCE.md now reads 2026-10-08; DESIGN.md carries no delta and keeps 2026-10-06 — intentional (visual file untouched until the findings above resolve).
