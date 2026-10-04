---
title: 'Refactor sweep'
type: 'chore'
ticket: 7
created: '2026-10-04'
status: done
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Fermeture d'épique : les build records 2.1–2.6 ont laissé des findings différés explicitement routés vers le sweep (ticket 2.7 de epic-coherence-tab, cleanup uniquement).

**Approach:** Périmètre dérivé des `## Review Triage Log` des six plans (`defer` marqués « sweep »), nettoyage seulement — aucune nouvelle portée :

1. **CI — étape Node** : ajouter `node tests/js/test-coherence.js` comme étape au workflow CI (`.github/workflows/tests.yml` ou le fichier pertinent) — les 63 assertions JS ne tournent aujourd'hui que manuellement ; une ligne les rend load-bearing au push.
2. **CHANGELOG** : ajouter les fonctionnalités de l'épique (onglet Cohérence : get_coherence, tableau + chips, tri/filtre/bascule, popover/ligne étendue, navigation entité) à la section « 0.15.0 (unstable - in development) » de `docs/CHANGELOG.md` — style des entrées existantes.
3. **`_collect_coherence` (ui_service.py)** : la re-parcours de `coordinator.data` avec un index `raw_by_id` recalé sur `_project_coordinator` est documenté comme fragile (« so the raw section cannot miss ») — factoriser la projection (raw passé par la projection partagée ou un générateur commun) pour supprimer le couplage documenté au lieu de le maintenir.
4. **Annonce par frappe** : le compte de résultats (`role="status"`) est annoncé à chaque caractère dans les DEUX onglets (Périphériques + Cohérence) — décision cross-tab différée au sweep : débouncer l'annonce (~300 ms après la dernière frappe) sur les deux champs de recherche, la valeur filtrée restant temps réel.
5. **Skeleton/head** : le squelette rend un thead en markup simple pendant que la table rend `_renderCoherenceHead()` (boutons) — faire rendre le squelette par le même générateur de tête (labels partagés déjà faits, markup à unifier).

Hors périmètre (routés ailleurs, confirmés non-sweep) : UX spine wording (bmad-ux), lien entité cross-tab (backlog, nouvelle portée), fraîcheur du cache cohérence (décision produit), pièce/room (contrat de données).

## Boundaries & Constraints

**Always:** cleanup uniquement — chaque item ci-dessus est la reprise d'un finding différé, pas une amélioration nouvelle ; les suites existantes (186 pytest unit, 63 node, e2e collect) restent vertes à l'identique ; style du fichier respecté (88 chars, HA vars, patterns existants).

**Never:** pas de nouvelle fonctionnalité ; pas de changement de contrat (get_coherence, get_peripherals, événements, microcopie) ; pas de refactor au-delà des items listés ; pas de toucher aux tickets déjà built au-delà du nettoyage nommé.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CI | push | L'étape node tourne, exit 0 | Étape absente si node indisponible dans le runner — utiliser la syntaxe du workflow existant |
| Debounce | frappe rapide dans la recherche | Annonce unique après ~300 ms d'inactivité | Le filtrage visuel reste instantané |
| Projection | appel get_coherence | Payload identique (contrat gelé par test) | Le test de contrat doit rester vert sans modification |

## Code Map

- `.github/workflows/tests.yml` (et `lint.yml` si pertinent) — workflow existant ; y ajouter l'étape node avec la syntaxe du runner déjà utilisée.
- `docs/CHANGELOG.md` — section « 0.15.0 (unstable - in development) » ; style des entrées existantes ; lister les 6 tickets de l'épique en user-facing terms.
- `custom_components/eedomus/ui_service.py` — `_collect_coherence` (re-parcours + raw_by_id), `_project_coordinator` (projection partagée) ; le test de contrat `get_coherence` (row lock) doit rester vert SANS être modifié.
- `custom_components/eedomus/www/eedomus-panel.js` — les deux recherches (`#periph-search`, `#coherence-search`) : annonce debounce (timer annulé à la frappe) ; `_renderCoherenceSkeleton` vs `_renderCoherenceHead` : unifier le générateur de tête.
- `tests/js/test-coherence.js` — doit rester vert ; étendre si un helper pur change (la tête partagée peut devenir un helper testé).

## Tasks & Acceptance

**Execution:**
- [ ] `.github/workflows/tests.yml` — étape node tests/js — rendre les 63 assertions load-bearing
- [ ] `docs/CHANGELOG.md` — entrées 0.15.0 de l'épique
- [ ] `ui_service.py` — factoriser la projection raw (supprimer le couplage documenté)
- [ ] `eedomus-panel.js` — debounce annonce (2 onglets) + tête de squelette unifiée

**Acceptance Criteria:**
- Given un push, when CI tourne, then l'étape node exécute `node tests/js/test-coherence.js` et échoue le workflow si elle sort non-zéro.
- Given la section 0.15.0 du CHANGELOG, when on la lit, then les fonctionnalités de l'épique y figurent dans le style existant.
- Given un appel `eedomus/get_coherence`, when la réponse arrive, then le payload est identique octet pour octet au contrat gelé (le test de row lock inchangé reste vert).
- Given une frappe rapide dans l'une des deux recherches, when 300 ms s'écoulent sans frappe, then UNE SEULE annonce du compte est émise (le filtrage visuel reste temps réel).

## Implementation Notes

Full route : ~100-150 lignes sur 4 fichiers hétérogènes (CI yaml, docs, py, js). Le point délicat est le 3 : `_project_coordinator` construit les lignes de base ; `_collect_coherence` y ajoute raw + signaux. Passer le dict raw par la projection (paramètre optionnel ou retour enrichi en interne) sans changer la forme de sortie publique de get_peripherals (contract testgelé). Pour le 4, un timer partagé (clé par champ) annulé à chaque input — pattern simple, pas de lib.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 186 passed (contrats inchangés)
- `node tests/js/test-coherence.js` -- expected: exit 0
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: syntaxe OK
- `git status --short` -- expected: seuls les 4 fichiers visés modifiés

**Manual checks (if no CLI):**
- Le workflow CI n'est pas exécutable localement — relire la syntaxe yaml contre le fichier existant.
</intent-contract>

## Review Triage Log

### 2026-10-04 — Review pass (thorough: blind-hunter, edge-case-hunter, verification-gap, intent-alignment)
- verdicts: 16 findings — high 0, medium 7, low 6, false 2, maybe-false 1
- findings (routes: patch ×7 groups, defer ×2, reject ×2):
  - `[medium]` `[patch]` Visible result count lagged 300 ms with the debounced announce (dual-role element). Patched: visible count updated immediately on every render; debounced announcement moved to a sr-only role=status twin per tab.
  - `[medium]` `[patch]` (verification-gap, pre-verified) Debounce wiring and skeleton inert had no executing test. Patched: setTimeout/clearTimeout stubs + panel-driven assertions (one announce per burst, immediate announce cancels the pending timer); skeleton assertions (inert, neutral head, derived colspan).
  - `[medium]` `[patch]` with_raw contract pinned in Python (pre-verified): _raw only in the with_raw path, never in frozen get_peripherals rows, equals the coordinator entry, non-dict values yield no row (the dropped isinstance guard was proven redundant — skip happens before attachment).
  - `[low]` `[patch]` Group: debounce timers cleared on disconnect, explicit tab guards on the announce callbacks, empty-_periphs guard (no "0 périphériques" over the blank empty state), skeleton colspan derived from COHERENCE_COLUMNS, dead _renderCoherenceHead wrapper removed, setup-node@v7 step verified to exist (latest release) + strict-on-purpose comment, CHANGELOG stale figures updated (186 unit / 20 e2e / JS suite in CI).
  - `[medium]` `[defer]` Pytest step's || echo swallow + tests/unit not run in CI — pre-existing CI infra rework (self-hosted runner story in backlog); noted, untouched.
  - `[medium]` `[defer]` Panel-runtime behavior (debounce timing in a real browser, 4-tab session) — live check at 2.8.
  - `[false]` `[reject]` JS announce callbacks re-deriving rows at fire time (the announcement reflects reality when it fires — the pure helpers guarantee message consistency); non-dict raw regression (proven unreachable: the skip precedes the attachment, now pinned by test).

## Auto Run Result

Status: built

- Summary: sweep de fermeture — étape Node en CI (setup-node@v7, stricte), CHANGELOG 0.15.0 complété (épique + figures à jour), projection raw unifiée dans un seul parcours (couplage fragile supprimé, contrat gelé vert à l'identique), annonces de recherche débouncées avec compte visible immédiat + jumelles sr-only, tête de squelette unifiée (inert, colspan dérivé).
- Files: .github/workflows/tests.yml, docs/CHANGELOG.md, custom_components/eedomus/ui_service.py, custom_components/eedomus/www/eedomus-panel.js, tests/js/test-coherence.js (74 assertions), tests/unit/test_ui_service.py (+4 tests with_raw).
- Review: 16 findings — 7 patch groups applied (0 high), 2 deferred, 2 rejected.
- Follow-up review: not required (0 high; contract tests frozen and green unchanged).
- Verification: pytest tests/unit/ -q → 190 passed (+4) ; node tests/js/test-coherence.js exit 0 (74 assertions) ; node --check OK ; YAML du workflow valide.
- Residual risks: workflow proves out on the next push; debounce timing in a real browser checked at 2.8.

## Verification
