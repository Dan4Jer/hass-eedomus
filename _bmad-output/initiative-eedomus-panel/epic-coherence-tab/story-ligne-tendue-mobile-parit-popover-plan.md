---
title: 'Ligne étendue mobile (parité popover)'
type: 'feature'
ticket: 5
created: '2026-10-04'
status: 'built'
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Le survol n'existe pas au tactile : le détail périphérique (livré en 2.4 pour le desktop) doit avoir son équivalent mobile avec exactement le même contenu (ticket 2.5 de epic-coherence-tab, covers CAP-7).

**Approach:** Sous 900 px, la ligne de périphérique s'étend à la demande (tap sur la cellule `periph_id` — le même déclencheur, `aria-expanded`) et montre **exactement** le contenu du popover desktop : réutiliser `coherenceDetailHtml(row)` (la fonction pure livrée en 2.4, prévue pour la parité) — état vivant + détails d'erreur, identité de mapping + justification, action « Créer une règle » (chemin existant), « Config HA » désactivée (2.6), raw repliable. Une seule ligne étendue à la fois (ouvrir une autre referme la première) ; l'état survit au re-rendu du corps tant que la ligne reste visible, et se referme si la ligne disparaît (tri/filtre/vue) ; le tap sur le déclencheur d'une ligne déjà étendue la referme. Sur desktop (> 900 px), le comportement popover de 2.4 est inchangé — la ligne étendue n'existe que sous 900 px.

## Boundaries & Constraints

**Always:** parité de contenu stricte avec le popover (même fonction de rendu, aucun contenu dupliqué) ; tri/filtre/bascule restent opérables, cibles ≥ 44 px, en-tête collant conservé ; zéro appel réseau ; pas de scroll horizontal silencieux ; le déclencheur garde son aria-label et porte `aria-expanded` reflétant l'état étendu.

**Never:** pas de popover au tactile (le hover gating de 2.4 reste — sous 900 px le tap étend la ligne au lieu d'ouvrir le popover) ; pas de lien entité actif (2.6) ; pas de modification du backend ni des autres onglets.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | mobile, tap sur periph_id | La ligne s'étend : même contenu que le popover | — |
| Toggle | re-tap sur la même ligne | Se referme | — |
| Une seule | tap sur une 2e ligne | la 1re se referme, la 2e s'ouvre | — |
| Ligne filtrée | tri/filtre fait disparaître la ligne étendue | Elle se referme — jamais une ligne étendue orpheline | — |
| Desktop | > 900 px | Comportement popover 2.4 inchangé, aucune ligne étendue | — |

## Code Map

- `custom_components/eedomus/www/eedomus-panel.js` — bloc Cohérence 2.2-2.4 : `coherenceDetailHtml(row)` (fonction pure de contenu — LA réutiliser), `coherenceTriggerHtml` (déclencheur periph_id), `_openCoherencePopover`/`_closeCoherencePopover` (cycle popover desktop, gating hoverCapable), `_renderCoherenceTable` (re-rendu du corps, fermeture au reshuffle), `@media (max-width: 900px)` (reflow mobile, barre de tri collante). L'état d'extension : une clé `periph_id` sur l'instance, réappliquée au re-rendu du corps si la ligne est encore visible.
- EXPERIENCE.md §Responsive & Platform (règle Cohérence : parité de contenu, surface différente, cibles ≥ 44 px, en-tête collant) et §Component Patterns (periph-popover, contrat de parité).

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/www/eedomus-panel.js` — ligne étendue mobile : bascule au tap, rendu partagé, état une-seule-ligne, styles d'extension — cœur du ticket

**Acceptance Criteria:**
- Given un viewport < 900 px, when l'utilisateur tape le `periph_id` d'une ligne, then la ligne s'étend et montre exactement le contenu du popover desktop (même fonction de rendu), sans appel réseau.
- Given une ligne étendue, when l'utilisateur tape une autre ligne, then la première se referme et la seconde s'étend — une seule à la fois.
- Given une ligne étendue, when le tri/filtre/bascule fait disparaître la ligne, then l'extension se referme — jamais d'extension orpheline.
- Given un viewport desktop, when l'on interagit avec la table, then le comportement popover de 2.4 est inchangé.

## Implementation Notes

Full route : ~120-180 lignes de JS (le contenu est déjà factorisé — c'est la force du ticket). Attention à la détection viewport : baser la bascule tap-vs-popover sur la même media query que le reflow (900 px), de préférence via matchMedia plutôt que sur la largeur calculée au tap. L'état étendu doit être réappliqué après re-rendu du tbody (l'identité de la ligne = periph_id) tant qu'elle est dans le résultat filtré.

## Verification

**Commands:**
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: syntaxe OK
- `node tests/js/test-coherence.js` -- expected: exit 0 (étendre si un helper pur s'y prête, ex. la clé d'état)
- `python3 -m pytest tests/unit/ -q` -- expected: 186 passed

**Manual checks (if no CLI):**
- Vérification live au tactile différée à 2.8.
</intent-contract>

## Review Triage Log

### 2026-10-04 — Review pass (thorough: blind-hunter, edge-case-hunter, verification-gap, intent-alignment)
- verdicts: 21 findings — high 0, medium 8, low 9, false 2, maybe-false 2
- findings (routes: patch ×6 groups, defer ×3, reject ×2):
  - `[medium]` `[patch]` Hover popover coexisted with the expanded row under 900 px (hover ungated + toggle never closed the popover). Patched: hover gated on !narrow, toggle closes any popover first.
  - `[medium]` `[patch]` Escaped-vs-raw periph_id mismatch — hostile ids never expanded (same latent bug in the popover path). Patched: canonical id resolution from _coherence on both surfaces + shared predicate.
  - `[medium]` `[patch]` No Escape dismissal for the expanded row. Patched: Escape closes with focus restored, search fall-through preserved.
  - `[medium]` `[patch]` aria-haspopup="dialog" wrong for the row surface + no aria-controls link. Patched: static template aria-expanded only, popover sets/removes haspopup dynamically, expanded row id + aria-controls.
  - `[medium]` `[patch]` (verification-gap, pre-verified) Toggle semantics and expanded-row emission untested. Patched: pure helpers (nextCoherenceExpanded, coherenceIsExpanded, expanded-row composition) + 8 new assertions incl. hostile-id parity.
  - `[low]` `[patch]` Group: breakpoint focus restore, disconnect + hash-change state clears, CSS.escape guard (dataset fallback), legacy addListener fallback, colspan derived, COHERENCE_NARROW_PX named constant (JS+CSS cross-referenced), degenerate test call fixed.
  - `[medium]` `[defer]` Expanded-state cleanup behaviors (breakpoint/filter-orphan/tab) unverifiable without a DOM harness — live check at 2.8; render gate limits the residue to minor re-expansion.
  - `[low]` `[defer]` tests/js not in CI (no Node step) — consistent with earlier defers; sweep candidate.
  - `[false]` `[reject]` Whole-row-tap reading (the periph_id trigger is the contract); pointer-based breakpoint reading (the ticket says « Sous 900px » explicitly).

## Auto Run Result

Status: built

- Summary: ligne étendue mobile (< 900 px) au tap sur le periph_id : même contenu que le popover via coherenceDetailHtml (parité par construction), accordéon une-ligne-à-la-fois, Escape, aria-expanded/aria-controls, état nettoyé (breakpoint, filtre, onglet, disconnect), popover hover désactivé sous 900 px, cible ≥ 44 px.
- Files: custom_components/eedomus/www/eedomus-panel.js (+~160 net), tests/js/test-coherence.js (57 assertions, +8).
- Review: 21 findings — 6 patch groups applied (0 high), 3 deferred, 2 rejected.
- Follow-up review: not required (0 high; mediums were interaction gates/semantics verified by the node harness).
- Verification: node --check OK ; node tests/js/test-coherence.js exit 0 (57 assertions) ; pytest tests/unit/ -q → 186 passed.
- Residual risks: mobile rendering live-unverified until 2.8; CSS interpolates COHERENCE_NARROW_PX (template literal) — verify visually on a phone.

## Verification
