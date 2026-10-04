---
title: 'Navigation vers les réglages d’entité HA'
type: 'feature'
ticket: 6
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
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** L'entité HA de la table de cohérence et du détail périphérique est un texte inerte : impossible d'atteindre la surface standard HA de l'entité (ticket 2.6 de epic-coherence-tab, covers CAP-8).

**Approach:** Activer la navigation vers la **surface standard HA de l'entité** sur les deux surfaces du panneau : (1) dans la table, la colonne « Entité HA » devient un lien texte inline (accent, souligné — pas un bouton) ; (2) dans le détail (popover desktop et ligne étendue mobile — le même `coherenceDetailHtml`), l'action « Config HA » (actuellement désactivée « bientôt disponible ») devient active. Le mécanisme, vérifié contre le bundle frontend de l'instance live : émettre l'événement **`hass-more-info`** avec `{entityId}` (CustomEvent `bubbles: true, composed: true`, document-level) — le mécanisme standard des éléments custom HA, présent dans le bundle live ; la boîte more-info ouvre la surface standard de l'entité (état, commandes, et l'accès aux réglages via son engrenage) en web et mobile. Aucune écriture, aucune édition du registry — une navigation, pas un contrôle d'édition. Lignes sans entité (`entity_id` null, signal `sans_entite`) : aucun lien, le texte reste inerte avec son libellé « aucune entité ».

**Décision d'implémentation soumise au checkpoint** : l'investigation du bundle live (`/frontend_latest/app.*.js`, 564 Ko) confirme `hass-more-info` et l'événement `navigate` (`navigation_path`), mais **aucune route deep-link** `/config/entity/<id>` ni `?edit=` n'existe dans le bundle — la page de réglages d'une entité s'atteint depuis la boîte more-info. Le plan retient donc `hass-more-info` comme mécanisme (il satisfait « fonctionnement standard de HA, web et mobile ») ; le libellé de l'action devient « Voir dans HA » / le lien ouvre la surface standard, l'engrenage des réglages est à un geste. Si tu exiges le deep-link vers la page de réglages elle-même, c'est un autre mécanisme non vérifié — à trancher au checkpoint.

## Boundaries & Constraints

**Always:** zéro appel réseau, aucune écriture ; l'entité du lien = `entity_id` de la ligne déjà chargée ; le lien reste opérable au clavier (focus visible, Entrée) et se distingue du déclencheur popover/ligne étendue ; aria-label porté par le libellé de l'entité (destination = l'entité nommée) ; le lien absent quand `entity_id` est null ; cohérence des deux surfaces (même comportement table et détail).

**Never:** pas d'édition du registry ni d'API d'écriture ; pas de page propriétaire ; pas de nouvelle commande websocket ; pas de modification du popover au-delà de l'activation de l'action ; pas de lib externe.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | clic/Entrée sur l'entité (table ou détail) | Événement `hass-more-info` émis avec l'entity_id — la surface standard HA s'ouvre | — |
| Sans entité | entity_id null | Aucun lien (texte inerte, « aucune entité ») | — |
| Popover ouvert | clic sur « Config HA » | more-info s'ouvre ; le popover se referme proprement (focus rendu) | — |
| Ligne étendue mobile | tap sur le lien | more-info s'ouvre ; l'extension reste cohérente (se referme comme tout reshuffle) | — |

## Code Map

- `custom_components/eedomus/www/eedomus-panel.js` — bloc Cohérence : `coherenceDetailHtml` (le bouton « Config HA — bientôt disponible » désactivé livré en 2.4/2.5 — l'activer), `_renderCoherenceRow` (colonne Entité HA en texte — la transformer en lien), le déclencheur popover (le lien entité doit NE PAS ouvrir le popover — stopPropagation si besoin), `_onClick` (nouvelle branche de dispatch), la gestion d'état du popover/ligne étendue (fermeture propre à l'ouverture de more-info).
- Mécanisme vérifié (bundle live /frontend_latest/app.14aa97223db841e4.js) : `hass-more-info` (CustomEvent document-level, detail {entityId}) ×2 occurrences ; `navigate` + `navigation_path` présents ; aucune route `/config/entity/<id>` ni `?edit=` dans le bundle.
- SPEC.md CAP-8 (lien texte inline, fonctionnement standard HA, aucune édition) ; EXPERIENCE.md §Component Patterns `entity-link` (« lien, pas un contrôle d'édition », opérable au clavier, destination portée par le libellé).

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/www/eedomus-panel.js` — lien entité dans la table + activation de « Config HA » dans le détail partagé + émission `hass-more-info` + fermetures propres — cœur du ticket

**Acceptance Criteria:**
- Given une ligne avec entité, when l'utilisateur clique/active le lien de la colonne Entité HA (ou « Config HA » dans le détail), then l'événement `hass-more-info` est émis avec l'entity_id et la surface standard HA s'ouvre — sans appel réseau ni écriture.
- Given une ligne sans entité, when la table est rendue, then aucun lien n'est émis (texte inerte).
- Given le popover/ligne étendue ouverts, when le lien est activé, then ils se referment proprement (focus rendu, pas de surface flottante orpheline).
- Given le lien et le déclencheur periph_id voisins, when l'utilisateur interagit, then le lien n'ouvre jamais le popover/l'extension et réciproquement.

## Implementation Notes

Full route : ~100-150 lignes. Le lien est un vrai `<a href="#">` interceptré ou un `<button>` stylé lien — au choix de l'implémentation, mais le contrat EXPERIENCE dit « lien texte inline, pas un chrome de bouton ». L'événement `hass-more-info` se dispatche depuis le shadow root avec `composed: true, bubbles: true` pour franchir la frontière shadow → document (le listener HA est au niveau document). stopPropagation sur le clic du lien pour ne pas déclencher le déclencheur parent.

## Verification

**Commands:**
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: syntaxe OK
- `node tests/js/test-coherence.js` -- expected: exit 0 (étendre : un helper pur pour le markup du lien entité avec cas hostile/null)
- `python3 -m pytest tests/unit/ -q` -- expected: 186 passed

**Manual checks (if no CLI):**
- Vérification live (ouverture réelle de more-info) différée à 2.8.
</intent-contract>

## Review Triage Log

### 2026-10-04 — Review pass (thorough: blind-hunter, edge-case-hunter, verification-gap, intent-alignment)
- verdicts: 19 findings — high 0, medium 7, low 7, false 3, maybe-false 2
- findings (routes: patch ×5 groups, defer ×4, reject ×3):
  - `[medium]` `[patch]` Focus dropped when the entity link itself was the activation target during an expansion re-render. Patched: focus restored to the re-rendered link (mutually exclusive with the expansion path).
  - `[medium]` `[patch]` hass-more-info dispatch contract and the row's entity cell had no executing test (pre-verified by verification-gap). Patched: panel class exposed in the vm hook, dispatch test through the real _onClick branch (event type, detail.entityId, bubbles/composed, preventDefault/stopPropagation), row composition extracted to pure coherenceRowHtml with entity-cell assertions.
  - `[medium]` `[patch]` Inconsistent no-entity predicates between table link and detail button (whitespace id: link without button). Patched: shared coherenceHasEntity predicate.
  - `[low]` `[patch]` Group: auxclick neutralized (no hash touch on middle-click), action-bearing aria-label on the table link matching the detail button, hostile-escaping test for the detail button path.
  - `[low]` `[patch]` Judgment call kept: dispatched id not trimmed (only the inert predicate trims) — real HA ids contain no spaces.
  - `[medium]` `[defer]` UX spine wording drift (« Config HA » → réglages standard vs shipped more-info surface) — spine update is bmad-ux territory; the plan/memlog carry the checkpoint decision.
  - `[medium]` `[defer]` docs/CHANGELOG.md 0.15.0 in-dev section lacks the whole epic's features — sweep (2.7) scope.
  - `[low]` `[defer]` Cross-tab dead entity text (Périphériques renders entity_id inert) — backlog story candidate for consistency.
  - `[medium]` `[defer]` Live more-info opening (web + mobile) unverified until 2.8.
  - `[false]` `[reject]` Stale entity_id dispatch (HA's more-info handles unavailable entities — standard surface); popover button vs inline-link clause (the UX spine's popover component specifies actions as buttons; the entity-link contract governs the table cell); R1 deep-link reading (superseded by the user's checkpoint decision).

## Auto Run Result

Status: built

- Summary: navigation vers la surface standard HA de l'entité : lien texte inline dans la colonne Entité HA + bouton « Voir dans HA » actif dans le détail partagé (popover et ligne étendue), dispatch hass-more-info (bubbles/composed) vérifié contre le bundle live, prédicat sans-entité unifié, fermetures propres des surfaces, focus restauré, auxclick neutralisé.
- Files: custom_components/eedomus/www/eedomus-panel.js (+~140 net), tests/js/test-coherence.js (63 assertions, +4 executing dispatch/row tests).
- Review: 19 findings — 5 patch groups applied (0 high), 4 deferred, 3 rejected.
- Follow-up review: not required (0 high; the dispatch contract now has an executing test).
- Verification: node --check OK ; node tests/js/test-coherence.js exit 0 (63 assertions, panel class executed) ; pytest tests/unit/ -q → 186 passed.
- Residual risks: more-info opening live-unverified until 2.8; UX spine wording drift (deferred).

## Verification
