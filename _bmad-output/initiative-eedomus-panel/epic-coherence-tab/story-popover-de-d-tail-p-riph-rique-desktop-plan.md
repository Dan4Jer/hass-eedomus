---
title: 'Popover de détail périphérique (desktop)'
type: 'feature'
ticket: 4
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
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/DESIGN.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Les données riches de la réponse `get_coherence` (état vivant, identité de mapping + justification, raw API, détails d'erreur) ne sont visibles nulle part — la table n'en montre qu'une fraction (ticket 2.4 de epic-coherence-tab, covers CAP-7).

**Approach:** Au survol et au focus clavier de la cellule `periph_id` d'une ligne du tableau de cohérence, ouvrir un **popover riche** : (1) état vivant — valeur courante (`state`), `usage_id`, parent (`parent_periph_id`), dernière mise à jour (`last_update`) ; (2) identité de mapping — `ha_entity`/`ha_subtype`, `justification` ; (3) actions correctif inline — « Créer une règle » qui bascule sur l'onglet Règles avec le `usage_id` pré-rempli (chemin existant du panneau) ; (4) les champs bruts de l'API (`raw`) en section secondaire **repliable** (repliée par défaut). Contrat clavier complet : déclencheur focusable avec `aria-expanded`, focus **piégé** pendant l'ouverture, `Échap` referme, focus **rendu au déclencheur**, **une seule** instance ouverte à la fois. Contrat visuel (DESIGN.md §Elevation & Depth, `periph-popover`) : surface flottante unique du panneau — fond `--card-background-color`, filet `--divider-color`, rayon `--ha-card-border-radius`, ombre carte du thème ; positionnement ancré à la cellule, jamais hors viewport.

## Boundaries & Constraints

**Always:** le popover ne fait **aucun** appel réseau — tout vient de la ligne déjà chargée ; parité de contenu préparée pour la ligne étendue mobile (2.5 lira la même structure — factoriser le contenu du popover en une méthode de rendu réutilisable) ; HA CSS vars uniquement ; une seule surface flottante (pas de tooltip séparé) ; le déclencheur reste la cellule `periph_id` (code font), le reste de la ligne n'ouvre rien ; fermeture au clic extérieur et au changement de tri/filtre/vue (la ligne peut disparaître sous le popover).

**Never:** pas de lien « Config HA » actif (2.6 livre la navigation — le popover réserve la place de l'action sans navigation morte : soit l'action absente, soit présente et désactivée avec un libellé explicite) ; pas de ligne étendue mobile (2.5) ; pas de modification du backend ni des autres onglets ; pas de lib d'UI externe.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | survol/focus du periph_id | popover ancré : état vivant, identité, action règle, raw replié | — |
| Clavier | Tab jusqu'à la cellule, Entrée | Ouverture, focus piégé, Échap referme + focus rendu | — |
| Une seule | ouvrir un 2e periph_id | le premier se referme proprement | — |
| Ligne sans entité | entity_id null | état vivant montre « aucune entité », pas de valeur | — |
| En erreur active | error_message présent | détails d'erreur visibles dans la section état vivant | — |
| Tri/filtre pendant ouverture | la ligne filtrée disparaît | le popover se referme (jamais un popover orphelin) | — |

## Code Map

- `custom_components/eedomus/www/eedomus-panel.js` — bloc Cohérence (2.2/2.3 livrés) : `COHERENCE_COLUMNS`, `_renderCoherenceRow` (cellule periph_id en code font), `_renderCoherenceTable` (corps re-rendu séparé — le popover doit survivre au re-rendu du tbody ou se refermer), pure helpers (`coherenceType`, `coherenceToVerify`), toolbar/états. Pattern existant de bascule d'onglet avec pré-remplissage : l'action « Créer une règle pour ce périphérique » de l'onglet Périphériques (`data-prefill-usage` ou équivalent — réutiliser le mécanisme exact).
- Réponse `get_coherence` par ligne : `state`, `last_update`, `usage_id`, `parent_periph_id`, `ha_entity`, `ha_subtype`, `justification`, `raw` (dict JSON-safe), `error_message`, `attempts`, `retry_after`, `entity_id`, `name`.
- EXPERIENCE.md §Component Patterns (`periph-popover` : contenu, parité mobile, focus piégé/Échap/focus rendu/aria-expanded, une seule ouverte) ; DESIGN.md §Elevation & Depth + §Components (`periph-popover` : surface flottante fonctionnelle, ombre thème + filet).

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/www/eedomus-panel.js` — popover de détail : déclencheur, rendu de contenu factorisé (réutilisable par 2.5), gestion clavier/focus, positionnement/fermeture, styles — cœur du ticket

**Acceptance Criteria:**
- Given une ligne chargée, when le `periph_id` reçoit le survol ou le focus clavier + Entrée, then le popover s'ouvre ancré à la cellule avec état vivant, identité de mapping + justification, l'action « Créer une règle » et la section raw repliée — sans aucun appel réseau.
- Given le popover ouvert, when `Échap` est pressé ou le focus tente d'en sortir, then il se referme avec le focus rendu au déclencheur (focus piégé pendant l'ouverture).
- Given un popover ouvert sur une ligne, when le tri/filtre/bascule fait disparaître la ligne, then le popover se referme — jamais un popover orphelin.
- Given l'action « Créer une règle » activée, then le panneau bascule sur l'onglet Règles avec le `usage_id` du périphérique pré-rempli, via le chemin existant.

## Implementation Notes

Full route : ~250 lignes de JS (popover = le composant le plus riche du panneau). Factoriser le contenu (`_renderCoherenceDetail(row)`) pour que 2.5 (ligne étendue mobile) le ré utilise tel quel — la parité de contenu est un contrat de la spine UX. Le positionnement : ancrage à la cellule avec clamp au viewport (le panneau vit dans la zone de contenu HA ; pas de lib). L'ouverture au survol doit avoir un petit délai/annulation (hover intent ~150-300 ms) pour ne pas mitrailler les popovers au passage de la souris ; le focus clavier ouvre sans délai. La fermeture au clic extérieur : un seul écouteur global actif seulement pendant l'ouverture.

## Verification

**Commands:**
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: syntaxe OK
- `node tests/js/test-coherence.js` -- expected: exit 0 (les helpers purs restent verts ; étendre le fichier si des helpers purs du popover s'y prêtent)
- `python3 -m pytest tests/unit/ -q` -- expected: 186 passed

**Manual checks (if no CLI):**
- Vérification live (survol, clavier, focus) différée à 2.8.
</intent-contract>

## Review Triage Log

### 2026-10-04 — Review pass (thorough: blind-hunter, edge-case-hunter, verification-gap, intent-alignment)
- verdicts: 21 findings — high 0, medium 9, low 8, false 2, maybe-false 2
- findings (routes: patch ×7 groups, defer ×3, reject ×2):
  - `[medium]` `[patch]` Hover-opened popover never closed on mouse-out nor on Tab-escape (stray popovers, broken trap). Patched: hover-open flag + 200 ms leave grace + focusout close.
  - `[medium]` `[patch]` Hover stole focus from a keyboard-opened popover. Patched: hover ignored while focus-opened; focusin hands over to the keyboard contract.
  - `[medium]` `[patch]` Esc regressed the search fields' Escape handling (popover branch returned early). Patched: fall-through when the popover did not hold focus.
  - `[medium]` `[patch]` No resize/orientation handling (stale fixed coordinates). Patched: dismiss on resize/orientationchange.
  - `[medium]` `[patch]` Hover path active on touch devices. Patched: gated on matchMedia (hover: hover) and (pointer: fine).
  - `[medium]` `[patch]` (verification-gap, pre-verified) Trigger/detail markup builders untested — injection surface fed by eedomus API strings. Patched: extracted as top-level pure functions + hostile-value tests (quotes, angle brackets, &, no entity, NaN attempts). Also: trigger aria-label, dead .detail-value dropped, uniform [disabled] trap exclusion, shared normalizer.
  - `[low]` `[patch]` NaN plural guard (Number.isFinite) — folded into the extraction patch.
  - `[medium]` `[defer]` « Pièce » absent from the popover (room not in the get_coherence contract — only buried in raw) — spec-level data-contract gap; candidate for a small backend addition or raw extraction at 2.5/2.7.
  - `[medium]` `[defer]` Popover lifecycle (open/trap/Escape/close-on-reshuffle) has no executable verification — needs jsdom, out of proportion; live check at 2.8.
  - `[low]` `[defer]` tests/js/test-coherence.js not run in CI (no Node step) — pre-existing CI hygiene, consistent with earlier defers; sweep candidate.
  - `[false]` `[reject]` « Config HA » not navigating (2.6 delivers it — plan-specified sequencing, disabled placeholder as planned); focus drop after « Créer une règle » (pattern parity with the existing Périphériques shortcut).

## Auto Run Result

Status: built

- Summary: popover de détail au survol/focus du periph_id — contenu factorisé (état vivant + détails d'erreur, identité de mapping + justification, action « Créer une règle » via le chemin existant, raw repliable, « Config HA » désactivée en attendant 2.6), focus piégé/Échap/focus rendu, une seule instance, fermeture (clic extérieur, scroll, resize, tri/filtre/vue, changement d'onglet), hover gated desktop-only, positionnement clampé au viewport.
- Files: custom_components/eedomus/www/eedomus-panel.js (+~480 net), tests/js/test-coherence.js (49 assertions, +25).
- Review: 21 findings — 7 patch groups applied (0 high), 3 deferred (pièce/data contract, lifecycle DOM verification → 2.8, CI Node step), 2 rejected.
- Follow-up review: not required (0 high; the mediums were interaction guards and the extraction patch, verified by the node harness).
- Verification: node --check OK ; node tests/js/test-coherence.js exit 0 (49 assertions) ; pytest tests/unit/ -q → 186 passed.
- Residual risks: interaction contract live-unverified until 2.8; room/pièce still absent from the data contract (deferred).

## Verification
