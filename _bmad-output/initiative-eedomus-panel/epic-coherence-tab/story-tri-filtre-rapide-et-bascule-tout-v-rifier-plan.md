---
title: 'Tri, filtre rapide et bascule Tout / À vérifier'
type: 'feature'
ticket: 3
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

**Problem:** L'onglet Cohérence (livré en 2.2) affiche une table plate sans tri, sans filtre et sans bascule : impossible de retrouver un périphérique ni de se concentrer sur ceux à vérifier (ticket 2.3 de epic-coherence-tab, covers CAP-6).

**Approach:** Ajouter au-dessus de la table : (1) le tri par colonne — chaque en-tête devient un bouton focusable, cycles croissant → décroissant → neutre, état exposé par `aria-sort`, indicateur de direction (flèche) en `--secondary-text-color`, réordonnancement **local** des données déjà chargées sans nouvel appel websocket ; (2) un filtre rapide texte (insensible à la casse, sur nom et `periph_id`, résultat compté « N périphériques ») ; (3) la bascule « Tout afficher » / « À vérifier » — « À vérifier » n'affiche que les lignes avec au moins un signal (tous les signaux, y compris la puce inconnue) ; l'activation et le compte de résultats annoncés en `aria-live` ; (4) les états : « filtre sans résultat » (« Aucun périphérique ne correspond à “{requête}”. » — aucune ligne, état explicite, effacer le filtre ou basculer restitue la table) et le vide positif « Tout est cohérent. Aucun périphérique à vérifier. » + bascule « Tout afficher » pour parcourir la table complète (le vide est une bonne nouvelle, pas une erreur).

## Boundaries & Constraints

**Always:** tri/filtre/bascule réordonnent et filtrent les données déjà chargées en mémoire — aucun nouvel appel `eedomus/get_coherence` ; l'état des trois interactions survit au re-rendu de l'onglet (tri actif, filtre, vue) et se reflète dans l'affichage ; microcopie française conforme à EXPERIENCE.md (§Interaction Primitives, §State Patterns) ; cibles ≥ 44 px sur mobile, en-tête collant conservé ; le tri et le filtre se composent (filtre s'applique d'abord, tri réordonne le résultat).

**Never:** pas de popover ni de ligne étendue (2.4/2.5) ; pas de lien entité cliquable (2.6) ; pas de changement du backend ni de la réponse ; pas de persistance de l'état entre sessions (l'état est volatil par onglet, comme le reste du panel).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | ~165 lignes chargées, tri croissant sur nom | Table réordonnée localement, aria-sort="ascending" | — |
| Filtre sans résultat | requête ne matchant rien | Message explicite + aucune ligne, aria-live | Effacer/basculer restitue |
| À vérifier vide | aucun signal sur aucune ligne | « Tout est cohérent. » + action « Tout afficher » | Bonne nouvelle, pas une erreur |
| Bascule + filtre composés | filtre actif + vue À vérifier | Les deux s'appliquent, compte annoncé | — |
| Tri neutre | 3e clic sur le même en-tête | Retour à l'ordre de réponse | — |

## Code Map

- `custom_components/eedomus/www/eedomus-panel.js` — le bloc Cohérence livré en 2.2 : `COHERENCE_TABLE_HEAD` (thead partagé), `_renderCoherenceTab`, `_renderCoherenceRow`, `_renderCoherenceChips` (les signaux + puce inconnue neutre), `_loadCoherence` (single-flight, `_coherenceLoading`), squelettes, `.state-message` + retry. Patterns à réutiliser : la toolbar de recherche de l'onglet Périphériques (recherche temps réel nom/usage_id + compte « N périphériques » + filtre « Périphériques touchés » annoncé aria-live) est le modèle direct de la toolbar Cohérence. Variables CSS HA uniquement ; mobile `@media (max-width: 900px)`.
- Réponse `eedomus/get_coherence` : lignes avec `periph_id`, `name`, `entity_id`, `ha_entity`/`ha_subtype`, `signals` (liste, vide = cohérent). Colonnes du thead : Périphérique / Nom / Entité HA / Type-sous-type / Statut.
- EXPERIENCE.md §Interaction Primitives (Tri de colonnes : bouton focusable, aria-sort, cycle asc/desc/neutre, réordonnancement local) et §State Patterns (Filtre sans résultat ; Vide — rien à vérifier).

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/www/eedomus-panel.js` — toolbar Cohérence (recherche + bascule) + tri par colonne + états (filtre sans résultat, vide positif) — cœur du ticket

**Acceptance Criteria:**
- Given la table chargée, when l'utilisateur clique un en-tête, then le tri cycle localement (croissant, décroissant, neutre), `aria-sort` porte l'état et aucun appel réseau n'est émis.
- Given un filtre ne matchant rien, when la requête est saisie, then « Aucun périphérique ne correspond à “{requête}”. » s'affiche (aucune ligne), annoncé en aria-live, et effacer le filtre restitue la table.
- Given la vue « À vérifier » sans aucun signal, when elle est activée, then l'état vide positif « Tout est cohérent. » s'affiche avec l'action « Tout afficher ».
- Given le filtre et la bascule actifs, when les résultats changent, then le compte (« N périphériques ») est annoncé en aria-live et les deux interactions se composent.

## Implementation Notes

Full route : ~150-200 lignes de JS dans le bloc Cohérence existant. Le tri doit rester stable entre les cycles neutres (retour à l'ordre de réponse — conserver l'ordre original du payload). La composition : filtre (texte + vue) d'abord, puis tri du résultat filtré. Suivre le pattern toolbar/recherche de l'onglet Périphériques à l'identique (même structure DOM, mêmes annonces).

## Verification

**Commands:**
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: syntaxe OK
- `python3 -m pytest tests/unit/ -q` -- expected: 186 passed (aucun changement Python ; le pin du contrat de signaux doit rester vert)

**Manual checks (if no CLI):**
- Vérification live différée à 2.8 (déploiement).
</intent-contract>

## Review Triage Log

### 2026-10-04 — Review pass (thorough: blind-hunter, edge-case-hunter, verification-gap, intent-alignment)
- verdicts: 22 findings — high 1, medium 6, low 9, false 2, maybe-false 4
- findings (routes: patch ×7 groups, defer ×3, reject ×2):
  - `[high]` `[patch]` JS-style // comments inside the @media CSS block — CSS error recovery discarded the ENTIRE mobile thead rule (sticky sort bar never applied). Patched: /* */ comments, style block swept clean.
  - `[medium]` `[patch]` Keyboard focus destroyed on every sort (innerHTML replace of the focused button). Patched: focus restored to the active sort button after re-render.
  - `[medium]` `[patch]` No-result copy referenced a « Tout afficher » button absent from that state. Patched: « Effacez le filtre pour restituer la table. »
  - `[medium]` `[patch]` Positive-empty fired for an empty payload in the all view (false good news + no-op button). Patched: scoped to to_verify.
  - `[medium]` `[patch]` Sort robustness/semantics: String() coercion for name/entity_id/periph_id; Statut ties broken by signal severity (en_erreur > douteux > sans_entite > regle_active, unknown last). Patched.
  - `[medium]` `[patch]` (verification-gap, pre-verified) Filter/sort logic had no executable verification anywhere. Patched: pure top-level helpers extracted + tests/js/test-coherence.js (plain Node asserts, 26 assertions: cycle, composition, search, predicate, tie-break, coercion).
  - `[low]` `[patch]` Refactors: shared _coherenceType, single to-verify predicate, dead null branch dropped, Escape reads state, state-aware aria-labels.
  - `[medium]` `[defer]` DOM-level/browser verification of the rendered tab — no headless infra in the repo; live check at 2.8.
  - `[low]` `[defer]` Result-count announced per keystroke — pattern parity with the Périphériques toolbar (plan constraint); a cross-tab debounce decision belongs to the sweep.
  - `[low]` `[defer]` Skeleton/live head markup sharing (labels shared, markup differs) — cosmetic, sweep candidate.
  - `[false]` `[reject]` Per-keystroke announcement as a defect (pattern parity is the plan's constraint); toggle-label reading R1 (single aria-pressed button is the sibling-tab pattern the plan requires).

## Auto Run Result

Status: built

- Summary: toolbar Cohérence (recherche + bascule « À vérifier » avec compte), tri par colonne (cycle asc/desc/neutre, aria-sort, focus restauré), états (filtre sans résultat, vide positif cadré à la vue À vérifier), composition filtre→tri, zéro appel réseau.
- Files: custom_components/eedomus/www/eedomus-panel.js (+~280 net), tests/js/test-coherence.js (nouveau, 26 assertions Node).
- Review: 22 findings — 7 patch groups applied (1 high: CSS // comments killing the mobile rule), 3 deferred (browser/DOM checks → 2.8, per-keystroke announcements → sweep, skeleton head markup → sweep), 2 rejected.
- Follow-up review: not required (1 high patched but it was a two-character comment fix verified by sweep + node tests; mediums were guards/copy/scoping verified by the harness).
- Verification: node --check OK ; node tests/js/test-coherence.js exit 0 (26 assertions) ; pytest tests/unit/ -q → 186 passed.
- Residual risks: browser/live rendering unobserved until 2.8; mobile sticky bar worth a visual pass on a phone (thead restyled from display:none to a sort bar).

## Verification
