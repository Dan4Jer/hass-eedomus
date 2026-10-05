---
title: 'Refactor sweep (i18n + rétro cohérence)'
type: 'refactor'
ticket: 6
created: '2026-10-05'
status: 'built'
route: 'full'
route_source: 'auto'
baseline_revision: 'de628ddb747754624ae4205085c9e54b524a707b'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 0
followup_review_recommended: true
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/initiative-eedomus-panel/epic-coherence-tab/epic-coherence-tab-retrospective.md
warnings: ['oversized']
deferred:
  - summary: >-
      lint.yml black/isort pins still diverge from requirements.txt (23.12.1 /
      5.13.2 vs 26.5.1 / 9.0.1) — aligning them changes whole-codebase
      formatting expectations, beyond a cleanup sweep.
    evidence: >-
      flake8 and mypy were aligned (volet F scope); black/isort alignment would
      reformat or re-flag large parts of the tree — a tooling pass of its own,
      candidate for release preparation.
    location: .github/workflows/lint.yml
    severity: low
---

<intent-contract>

## Intent

**Problem:** Le sweep de clôture de l'épique i18n : les findings différés des revues 3.2-3.5 et les action items de la rétrospective de l'épique cohérence restent ouverts — défauts user-visibles laissés par les seams inter-tickets (cache jamais invalidé, « 1 périphériques », focus perdu, courses hover/breakpoint, registre ressuscitant les mappings supprimés), trous de vérification frontend, garde i18n durcissable, tests couplés aux artefacts `_bmad-output`.

**Approach:** Cleanup uniquement, périmètre fixé (décisions utilisateur 2026-10-05 : sweep complet ; puce en_erreur = clarification du libellé uniquement, pas de nouveau signal). Six volets : (A) fixes de production panneau ; (B) fixes de production backend ; (C) catalogue/inventaire (pluriels + libellé en_erreur) ; (D) garde i18n + fixtures repo-owned ; (E) tests des trous de vérification ; (F) hygiène CI/lint. Le bug backlog 105 (deep-link #historique) est corrigé ici en même temps que #regles.

## Boundaries & Constraints

**Always:** les clés catalogues nouvelles/modifiées passent par l'inventaire puis le catalogue (parité épinglée par les tests 3.2/3.4) ; les contrats gelés `get_coherence`/`get_peripherals` (formes de payload) ne changent pas — les fixes backend touchent la dérivation interne, pas la forme servie ; ligne ≤ 88 ; nouveau code anglais (règle 3.5) ; la suite grandit sans test supprimé ; l'issue « 1 périphériques » se corrige dans les DEUX langues (EN aussi : « 1 peripherals » est fautif).

**Never:** pas de découpage du panel (story 102) ; pas de collisions multi-box (ticket dédié) ; pas de grammaire native pour ConfigEntryNotReady (reporté au prochain changement coordinator-setup) ; pas de gardes CI hassfest/grep (3.7) ; pas de pinning caplog des logs (brittle) ; pas de nouveau signal en_erreur ni changement du contrat CAP-6 ; pas d'E2E live (3.7) ; pas de refonte de scripts/tests (advisory-only, décision enregistrée).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Save mapping / création règle | retour à l'onglet Cohérence | signaux rechargés (cache invalidé) | — |
| Mapping supprimé | reload | le registre ne le ressuscite pas (clear/join lifecycle) | test du cas removed |
| Compte 1 | 1 périphérique | « 1 périphérique » / "1 peripheral" (one/other) | tests corrigés |
| Entrée directe #regles / #historique | hass assigné après premier rendu | lazy-load (re)partie | — |
| Focus clavier « Tout afficher » | re-render | focus restauré | — |
| Hover sous 900px (course 250ms) | viewport change pendant l'intent | popover ne s'ouvre pas en étroit | garde narrow dans le callback |
| Sweep entre triggers | leave-timer + nouvelle intention | le nouveau popover s'ouvre | _cancelCoherenceLeave en nouvelle intention |
| Entrée narrow popover ouvert | matchMedia sans resize | popover refermé | — |
| Sensor timestamp/date sans unité | dérivation douteux | pas de puce douteux | — |
| callWS catalogue jamais résolu | drop ws | slot libéré après timeout, retry au set hass suivant | timeout race |
| Gare : chaîne EN codée en dur | nouveau littéral EN | échec (référence = union EN+FR) | garde verte sur l'arbre actuel |
| Tests vs bmad-output | _bmad-output déplacé/archivé | tests lisent tests/fixtures/*.json (drift-check vs live) | fixture == catalogue épinglé |

</intent-contract>

## Code Map

- `custom_components/eedomus/www/eedomus-panel.js` — cache cohérence (`_renderTabContent` ~:1947, invalidation à faire après save/create-rule) ; deep-link (`set hass` ~:786-791 : généraliser à #regles `_loadMapping` ~:3260 et #historique `_loadVersions` ~:1962 — ferme le bug 105) ; focus « Tout afficher » (~:1642-1646) ; hover/breakpoint (~:2755-2794, :2572) ; pluriel one/other dans les status text (~:1017/1037/1049 côté tests, coherenceStatusText/periphStatusText) ; timeout ws dans `_loadStrings` (~:798-836).
- `custom_components/eedomus/ui_service.py` — registre : brancher le cycle de vie (`_registry_by_periph_id` ~:643, `clear_mapping_registry` mapping_registry.py:36 jamais appelé) ; douteux (~:692-698 : exemptions device-class sans unité + `not base["unit"]`) ; `get_available_endpoints` (~:1005) dérivé de `WS_COMMANDS`.
- `custom_components/eedomus/panel_translations.py` + `_bmad-output/specs/spec-eedomus-i18n/i18n-inventory.md` — splits one/other : `panel.coherence.status.total` → `.total_one`/`.total_other` (EN "(1 peripheral)" hmm — suivre la convention attempts : « {n} périphériques » → `({n} périphérique)`/`({n} périphériques)` ; EN "1 peripheral"/"{n} peripherals") + la famille periphs équivalente ; libellé `panel.coherence.chips.en_erreur` clarifié (proposition : « import en reprise » / "import retrying" — libellé final naturel, validé par la sémantique, pas de nouveau signal).
- `tests/js/test-i18n-guard.js` — union EN+FR comme référence (parser les deux arbres), seuil substring ≥ 8 + égalité exacte pour les textes courts, regex panel.* `[A-Za-z0-9_.]`, FRENCH_MARKER avant l'exit no-alnum, stopwords FR (le/la/les/dans/pour/avec…), regex-division après `)`/`]`, exemptions techniques saufées par côté.
- `tests/js/fr-catalog.js` + NOUVEAU `tests/fixtures/panel-keys.json` + `tests/fixtures/panel-catalog.json` — fixtures commitées, générées depuis l'inventaire/catalogue une fois ; `fr-catalog.js` lit le JSON (le parser python meurt ou ne sert plus) ; un test unit drift-check épingle fixture ≡ `PANEL_TRANSLATIONS` ; le test de parité inventaire/catalogue en tests/unit lit la fixture au lieu de `_bmad-output` (le fichier inventaire reste la source pour la GÉNÉRATION, plus pour le runtime des tests) ; throw explicite sur `\u` si le parser survit.
- `tests/js/test-coherence.js` — trous de vérification (rétro 2) : chips ×5 cas (per signal, coherent fallback, en_erreur detail+title, unknown neutral), dispatch narrow/wide stubé matchMedia, teardown popover + éviction d'expansion, lifecycle lazy #coherence + bouton Réessayer, debounce frappe Périphériques, renommage du test « never pluralize as NaN » (l'écart non-fini→pluriel est assumé en 3.3), labels/commentaires FR restants → EN (rétro 3.5, lines 185/192/337/350/353).
- `tests/unit/test_ui_service.py` — contrat de signaux bidirectionnel + regex resserrée à `COHERENCE_SIGNALS` ; statuts/bannières d'erreur : tests de rendu d'instance (double-résolution `t(stored)` clé-ou-message, `resolveApplied`, `_historyStatusText`) — findings 3.3 review reportés.
- `.github/workflows/lint.yml` — pin flake8 aligné sur requirements (7.4.1) ; mypy pin idem si listé.

## Tasks & Acceptance

**Execution:**
- [ ] Volet A — panel : cache, deep-link ×2 (+fermeture bug 105), focus, courses hover/breakpoint, pluriel JS, timeout ws
- [ ] Volet B — backend : registre (clear/join + test removed), douteux, endpoints WS_COMMANDS
- [ ] Volet C — catalogue/inventaire : splits one/other (cohérence + périphériques), libellé en_erreur
- [ ] Volet D — garde + fixtures : union EN+FR, seuils/regex/ordre, panel-keys.json + panel-catalog.json + drift-check, débranchement _bmad-output
- [ ] Volet E — tests des trous : chips, narrow/wide, teardown, lifecycle, debounce, bannières/statuts, renommage NaN, labels FR tests
- [ ] Volet F — lint.yml pins

**Acceptance Criteria:**
- Given une écriture (save/création règle), when l'utilisateur revient sur Cohérence, then les signaux sont rechargés (test harnais).
- Given un mapping supprimé puis rechargé, when la cohérence se dérive, then il n'alimente plus la ligne (test unit removed-mapping).
- Given un compte de 1, when les statuts se rendent, then le singulier s'affiche dans les deux langues (épingles corrigées).
- Given une entrée directe #regles/#historique avant hass, when hass arrive, then l'onglet charge.
- Given la garde, when une chaîne EN du catalogue est codée en dur, then elle échoue ; given _bmad-output archivé, when les tests tournent, then ils passent sur les fixtures.
- Given les trous de vérification, when le harnais tourne, then chips/dispatch/teardown/lifecycle/debounce sont exécutés.

## Implementation Notes

Full route — périmètre large mais chaque item est petit et tracé (sources : rétro cohérence action items 1-7/9-11, findings différés 3.2-3.5). Le subagent choisit les libellés exacts des valeurs de catalogue (naturels, fidèles) ; les clés suivent la convention one/other établie en 3.3 (attempts_one/attempts_other). Le bug 105 : son correctif atterrit ici — le passage en done du bug reste le geste de l'utilisateur. En ordre : C (catalogue) avant A (le JS consomme les clés), D avant E (les fixtures changent ce que les tests lisent).

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 229+ verts (fixture drift-check + removed-mapping + statuts/bannières + contrat bidirectionnel)
- `node tests/js/test-coherence.js && node tests/js/test-i18n-guard.js` -- expected: verts (chips/dispatch/teardown/lifecycle/debounce couverts, garde union EN+FR verte sur l'arbre)
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: OK
- `python3 -m json.tool tests/fixtures/panel-keys.json tests/fixtures/panel-catalog.json` -- expected: valides
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/lint.yml'))"` -- expected: OK
</intent-contract>

## Review Triage Log

### 2026-10-05 — Review pass
- verdicts: 40 findings — high 0, medium 8, low 29, false 1, accept-as-is 1, defer 1 ; convergences massives entre lens (le pluriel sibling, la course du cache, l'assertion supprimée et le guard-sans-self-test signalés par 3-4 lens chacun).
- production (patchée) : assertion `vol.Invalid validator(123)` supprimée par l'insertion TestGetAvailableEndpoints (le pin était vivant — rétabli) ; **pluriel sibling `filtered`** manqué (« 1 résultats » épinglé comme attendu par le propre test du diff — split filtered_one/filtered_other, catalogue 144 clés, fixtures régénérées, pin corrigée) ; **course du cache in-flight** (un _loadCoherence antérieur à l'écriture repeuple le cache périmé après invalidation — garde de génération) ; **ordre save→invalidation** (un échec de _loadPeripherals sautait l'invalidation — déplacée juste après le succès du write) ; rejet ws tardif non géré après le timeout (catch no-op) ; flags in-flight manquants des lazy #regles/#historique (duplications au set hass) ; newline final restauré ; warning sur enregistrement entry_id=None (imprenable rendu visible) ; dérivation entry_id dupliquée consolidée en `get_coordinator_entry_id` ; **ordre du prune** (le prune en tête de setup vidait la vague avant le refresh — un premier refresh en échec laissait la cohérence sans identité : la vague précédente est désormais retirée APRÈS le succès du first refresh, via prune_mapping_registry_objects) ; **imports morts `_register_device_mapping` supprimés** dans 8 plateformes (le nom n'existe pas dans entity.py — ImportError si la branche était atteinte) ; step « Run mypy » ajouté ; parité de fixture du garde étendue à l'union en∪fr.
- tests (patchés) : wiring du registre épinglé à ses sites d'appel (setup/unload/remove + tagging entity-level — mutation-proof par le lens) ; témoin focus « Tout afficher » ; témoin timeout ws (4 assertions) ; témoin invalidation _deleteRule ; **self-test de la garde** committé (5 sondes, une par règle, contrôle négatif vérifié) ; renommage du test de parité fixture (il ne lit plus l'inventaire).
- rejets avec raisons : commande de vérification du plan destructrice (json.tool à deux fichiers = outfile — le correctif édite le plan ; AVERTISSEMENT consigné : toujours l'exécuter fichier par fichier, le drift-check a déjà attrapé un clobber) ; témoins stub-level (accepté par la frontière E2E=3.7) ; réordonnancement des endpoints (aucun consommateur in-repo) ; date « future » (horloge obsolète du revoir — date réelle 2026-10-05, vérifiée deux fois en session).
- différé : pins black/isort du lint.yml (l'alignement re-formaterait l'arbre entier — passe d'outillage dédiée, préparation release).
- jugement assumé : les tests de setup épinglent le wiring réel post-correctif (retire de la vague après succès) et non l'appel prune par entry demandé à l'origine — le correctif d'ordre a changé le contrat, le pin est honnête.

## Auto Run Result

Status: built

- Summary: sweep complet de clôture livré en six volets : (A) panneau — invalidation du cache de cohérence après écritures avec garde de génération, deep-link généralisé aux 3 onglets lazy (ferme le bug 105 #historique + #regles), focus restauré sur « Tout afficher », courses hover/breakpoint, pluriels one/other (total + filtered), timeout ws 10 s avec catch du rejet tardif, flags in-flight des lazy tabs ; (B) backend — registre : tagging entry_id + retrait de la vague précédente APRÈS le succès du first refresh (mappings supprimés ne ressuscitent plus, refresh en échec préserve l'identité), warning sur les enregistrements imprenables, douteux (exemptions timestamp/date + chaîne vide), endpoints dérivés de WS_COMMANDS, accès partagé get_coordinator_entry_id, imports morts supprimés ; (C) catalogue 144 clés (splits one/other total+filtered, libellé en_erreur clarifié « import en reprise »/« import retrying ») ; (D) garde durcie (union EN+FR, seuils, ordres, regex, self-test committé) + fixtures repo-owned (panel-keys.json, panel-catalog.json, drift-check) débranchant les tests de _bmad-output ; (E) trous de vérification comblés (chips, dispatch narrow/wide, teardown, lifecycle ×3 + Réessayer + deleteRule, debounce Périphériques, statuts/bannières d'instance, wiring du registre, focus, timeout, NaN renommé, labels FR des tests) ; (F) pins lint.yml (flake8 7.4.1, mypy 2.3.1 + step Run mypy).
- Files: eedomus-panel.js, ui_service.py, entity.py, mapping_registry.py, __init__.py, 8 plateformes (imports morts), panel_translations.py (144), i18n-inventory.md, tests/fixtures/panel-{keys,catalog}.json, tests/js/{test-coherence,test-i18n-guard,fr-catalog}.js, tests/unit/{test_ui_service,test_init_domain_services}.py, .github/workflows/lint.yml.
- Review: 40 findings sur 4 lens — 15 items de patch appliqués par le subagent (2 medium critiques de correction du correctif : la course du cache in-flight et l'ordre du prune), 1 différé (pins black/isort), 4 rejets motivés (1 réfutation d'horloge, plan-edit, frontières, accept).
- Follow-up review: recommandé (8 mediums patchés). Risque non vérifié nommé : les corrections de prod (garde de génération du cache, retrait-de-vague après refresh réussi, timeout ws) ne sont observées qu'au niveau stub — l'E2E 3.7 doit ouvrir le panneau déployé et vérifier cohérence/sauvegarde/retour d'onglet.
- Verification: pytest tests/unit/ -q → 240 passed (229 + 11) ; node test-coherence.js → 141 PASS (97 + 44) ; garde i18n → verte avec self-test 5/5 (727 littéraux, 249 textes EN+FR, 144 clés) ; fixtures ≡ PANEL_TRANSLATIONS vérifié en session (144 clés en==fr) ; node --check OK ; lint.yml valide ; newline final restauré.
- Residual: pins black/isort (différé) ; AVERTISSEMENT permanent : ne jamais exécuter `python3 -m json.tool f1.json f2.json` (le second chemin est un outfile — le drift-check de fixture a déjà attrapé ce clobber une fois).
