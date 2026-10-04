---
title: 'Onglet Cohérence : tableau + puces de statut'
type: 'feature'
ticket: 2
created: '2026-10-04'
status: done
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/DESIGN.md
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Le backend `eedomus/get_coherence` (livré par le ticket 2.1) n'a aucune surface : le panneau a 3 onglets et aucun tableau de cohérence (ticket 2.2 de epic-coherence-tab, covers CAP-6).

**Approach:** Ajouter le 4e onglet « Cohérence » au panneau existant (TABS, TAB_LABELS, nav `data-tab`, `_renderTabContent` switch, routage hash) : chargement différé de `eedomus/get_coherence` via `this._hass.callWS` avec squelettes pendant l'appel et reprise « Réessayer » en cas d'échec (pattern existant), puis rendu d'une table (une ligne par périphérique) : colonnes `periph_id`, nom, entité HA (texte simple dans ce ticket — le lien arrive en 2.6), type/sous-type, puces de statut. Les puces : les 4 signaux de la réponse (`sans_entite`, `douteux`, `regle_active`, `en_erreur` — chaînes exactes de la réponse, les constantes côté backend) + « cohérent » quand `signals` est vide ; chaque puce = glyphe + libellé, jamais la couleur seule ; teintes de fond `color-mix` 12 % de la couleur sémantique (`--error-color`, `--warning-color`, `--primary-color`, `--success-color`), texte en `--primary-text-color` ; glyphes du jeu d'icônes déjà utilisé par le panneau (à défaut, caractères SVG inline thémés — choix laissé à l'implémentation, un glyphe distinct par signal, redondant avec le libellé, `aria-label` complet).

## Boundaries & Constraints

**Always:** variables CSS HA uniquement (aucun hex, aucun style codé en dur) ; conserver les 3 onglets existants à l'identique ; suivre les patterns existants du fichier (squelettes, `.state-message` + retry, `role="status"`/aria-live) ; responsive : sous 900 px la table reste lisible (reflow colonnes, pas de scroll horizontal silencieux) ; opérable au clavier (ordre de Tab = ordre de lecture) ; libellés en français conformes à EXPERIENCE.md.

**Never:** pas de tri, pas de filtre, pas de bascule (ticket 2.3) ; pas de popover ni de ligne étendue (2.4/2.5) ; pas de lien cliquable vers les réglages HA (2.6) ; pas de modification du backend ni des autres onglets ; pas de toolchain de build.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | get_coherence renvoie ~165 lignes | Table complète rendue, une ligne par périph, chips par signal | — |
| Chargement | appel en cours | Squelettes au format de la table (en-tête + lignes) | Résout à l'arrivée |
| Erreur commande | callWS échoue | `.state-message` avec bouton « Réessayer », jamais un spinner infini | Reprise |
| Aucun signal | signals vide | Puce « cohérent » (teinte success) | — |
| En erreur | signals contient en_erreur | Puce rouge avec libellé ; error_message accessible (title/aria) | — |
| Onglet via URL | #coherence au chargement | L'onglet s'ouvre directement (hash routing existant) | — |

## Code Map

- `custom_components/eedomus/www/eedomus-panel.js` — LE fichier : `TABS` const + `TAB_LABELS` en tête, nav `data-tab`, `_renderTabContent()` switch, `_tabFromLocation`/`hashchange` (URL), chargement différé par onglet via `this._hass.callWS(...)` (`null` = non chargé), squelettes pendant l'appel, `.state-message` + « Réessayer », `role="status"`. Réutiliser ces patterns à l'identique. Variables CSS disponibles : `--primary-text-color`, `--secondary-text-color`, `--primary-color`, `--divider-color`, `--card-background-color`, `--input-fill-color`, `--ha-card-border-radius`, `--accent-color`, `--error-color`, `--success-color`, `--warning-color`, `--code-font-family`. Mobile : `@media (max-width: 900px)` aplatit les lignes (flex-column).
- Réponse `eedomus/get_coherence` (livrée en 2.1, ui_service.py) : par périphérique — les 10 clés de get_peripherals (`periph_id`, `name`, `usage_id`, `entity_id`, `platform`, `device_class`, `unit`, `modified`, `modified_by_rule`, `modified_date`) + `ha_entity`, `ha_subtype`, `parent_periph_id`, `justification`, `state`, `last_update`, `raw` (dict JSON-safe), `signals` (liste de chaîmes : `sans_entite`/`douteux`/`regle_active`/`en_erreur`), `error_message`, `attempts`, `retry_after` ; enveloppe `{peripherals, total}`.
- DESIGN.md `Components` (tokens `coherence-chip-*`, `coherence-table` : filets `--divider-color`, pas de zébrage, en-tête fond carte, lignes ≥ 44 px) ; EXPERIENCE.md `State Patterns` (chargement Cohérence, erreur commande) et `Component Patterns` (`coherence-table`, `coherence-chip`).

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/www/eedomus-panel.js` — onglet Cohérence : TABS/labels/nav/switch/hash + lazy load + squelette/erreur/retry + rendu table + chips — cœur du ticket

**Acceptance Criteria:**
- Given le panneau ouvert, when l'utilisateur clique « Cohérence », then les squelettes cèdent la place à la table des ~165 périphériques alimentée par un seul appel `eedomus/get_coherence`.
- Given un périphérique portant des signaux, when la ligne est rendue, then chaque signal a sa puce glyphe + libellé avec teinte sémantique de fond et texte primaire, et le sens ne repose jamais sur la couleur seule (clair et sombre).
- Given l'appel qui échoue, when l'onglet est ouvert, then un message d'état avec « Réessayer » s'affiche — jamais un spinner infini ni une table à moitié chargée présentée comme complète.

## Implementation Notes

Full route : ~350 lignes de JS vanilla dans un fichier existant très structuré. Les glyphes : le panneau n'embarque pas de lib d'icônes — vérifier comment les onglets/nav actuels rendent leurs icônes (le cas échéant SVG inline thémé par currentColor, un glyphe distinct par signal). Le libellé exact des puces : EXPERIENCE.md (§Voice and Tone, sobriété) — « sans entité HA », « mapping douteux », « règle active », « en erreur », « cohérent ».

## Review Triage Log

### 2026-10-04 — Review pass (thorough: blind-hunter, edge-case-hunter, verification-gap, intent-alignment)
- verdicts: 29 findings — high 0, medium 6, low 13, false 6, maybe-false 4
- findings (routes: patch ×10 groups, defer ×5, reject ×6):
  - `[medium]` `[patch]` No in-flight guard in `_loadCoherence` (unlike `_loadPeripherals`) — concurrent calls on tab re-entry, stale error overwrites fresh success, repeated Réessayer queue loads. Patched: `_coherenceLoading` flag + skeleton re-render on retry.
  - `[medium]` `[patch]` `set hass` never triggers the coherence load — panel opened on #coherence before hass assignment shows skeletons forever. Patched: trigger with null/error guard.
  - `[medium]` `[patch]` Unknown signals render an empty Statut cell (contract drift surfaces as silence). Patched: neutral chip carrying the raw escaped string — never cohérent.
  - `[medium]` `[patch]` en erreur chip: message only in title/aria-label, accessible name ≠ visible text. Patched: truncated visible message in the chip, aria-label aligned, full message in title.
  - `[medium]` `[patch]` Type/sous-type column showed the HA classification (platform/device_class) with mapping identity as fallback — the plan's code map foregrounds the mapping identity. Patched: priority inverted (ha_entity/ha_subtype primary).
  - `[low]` `[patch]` Group: CSS var fallbacks matching the file convention (+ color-mix fallback), precise empty-state copy, thead deduplication (shared COHERENCE_TABLE_HEAD), French mobile data-labels, TAB_LABELS dead addition removed.
  - `[medium]` `[patch]` E2E per-tab pattern not applied to the 4th tab — added `test_get_coherence_lists_every_peripheral` + docstring update (runs at the epic's live validation).
  - `[medium]` `[defer]` Coherence data cached forever with no refresh path (stale after a mapping change until panel reload) — refresh-trigger design belongs to the sweep/live iteration.
  - `[medium]` `[defer]` No JS test infrastructure exists (frontend rendering unobserved by any executing test; node smoke harness used ad hoc) — out of proportion for this ticket; backend contract fully unit-verified.
  - `[medium]` `[defer]` All three Verify expectations live at the live/browser surface (tab renders ~165 rows, chips readable both themes, states per EXPERIENCE.md) — deferred to 2.8 by design.
  - `[low]` `[defer]` attempts/retry_after/state/last_update dropped by the table — consumed by the popover (2.4), not this ticket.
  - `[low]` `[defer]` CI workflow never runs tests/ and swallows pytest failures (pre-existing, noticed while tracing) — flagged to the user; sweep candidate.
  - `[false]` `[reject]` douteux chip conflates two backend causes — one chip per the UX spine. Filter/search/summary counts missing — ticket 2.3. attempts dropped — 2.4 scope. DESIGN token naming vs CSS class naming — cosmetic. Frontend payload-key typo risk with green suite — covered by the added E2E test at live validation.

## Auto Run Result

Status: built

- Summary: 4th tab « Cohérence » in eedomus-panel.js: tab plumbing (TABS/nav/switch/hash), lazy single-flight `get_coherence` load with skeleton + Réessayer, table (periph_id, nom, entité HA, mapping identity, statut), chips (4 signals + cohérent + neutral unknown), mobile reflow, HA CSS vars with fallbacks.
- Files: custom_components/eedomus/www/eedomus-panel.js (+~300), tests/e2e/test_e2e_panel.py (+1 live test, docstring).
- Review: 29 findings — 10 patch groups applied (0 high, 5 medium), 5 deferred (stale-cache refresh design, JS test infra, live/browser checks → 2.8, retry details → 2.4, CI hygiene), 6 rejected.
- Follow-up review: not required (0 high patched; mediums were single-fix guards and copy, verified by the node smoke harness). Residual: browser/live surface unobserved until 2.8.
- Verification: node --check OK ; pytest tests/unit/ -q → 185 passed ; e2e panel collects 8 tests (live run deferred) ; node smoke harness 15 checks.
- Residual risks: coherence tab untested in a real browser until deploy (2.8); stale-cache refresh absent by design for now.

## Verification

**Commands:**
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: syntaxe OK (si node indisponible, le vérifier par chargement du fichier dans un parseur JS disponible et le dire)
- `python3 -m pytest tests/unit/ -q` -- expected: 185 passed (aucun changement Python)

**Manual checks (if no CLI):**
- L'onglet Cohérence n'est visible que dans le panneau déployé (vérification live différée au ticket 2.8).
</intent-contract>

### 2026-10-04 — Follow-up pass (bmad-review of commits 2.1+2.2, user-routed)
- Independent review (adversarial, edge-case-hunter, verification-gap): 19 findings. Actionable fixes applied immediately per user decision: en_erreur now fires only inside its retry window (stale queue entries clear), retry_after serialized as UTC-aware (single time convention), client gets a stable internal_error code/message instead of str(e), E2E compares periph_id sets between get_peripherals and get_coherence, signal contract pinned by a JS-as-text unit test (backend constants == COHERENCE_SIGNALS keys). Pre-existing Historique deep-link bug filed as backlog bug. Deferred findings unchanged (payload size, JS test infra, multi-box collision, doubteux semantics refinements).
