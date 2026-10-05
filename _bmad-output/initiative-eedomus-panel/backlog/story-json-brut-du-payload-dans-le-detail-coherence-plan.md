---
title: 'Cohérence : JSON brut du payload sous « Champs bruts de l''API eedomus »'
type: 'feature'
ticket: 'story-json-brut-du-payload-dans-le-detail-coherence'
created: '2026-10-04'
status: done
route: 'full'
route_source: 'auto'
baseline_revision: 'd8392566dde5292a553e572e9f0f107a809c0747'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 0
followup_review_recommended: true
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/specs/spec-eedomus-i18n/i18n-inventory.md
warnings: []
deferred:
  - summary: >-
      E2E live validation of the raw-JSON block: the copy fallback on a real
      insecure context (HA served over plain http, where navigator.clipboard
      is absent and execCommand is the primary path) and the rendered JSON
      surface in an actual browser.
    evidence: >-
      The vm harness stubs navigator.clipboard and document.execCommand; the
      fallback's real-browser behavior (focus, permission prompts, hang) and
      the visual rendering are unverifiable there. Live check belongs to the
      E2E validation pass (precedent: 2.8/3.7 pattern, Pi deploy).
    severity: low
---

<intent-contract>

## Intent

**Problem:** Le détail d'un périphérique (popover Cohérence + ligne étendue mobile) rend la section « Champs bruts de l'API eedomus » comme une simple liste triée clé→valeur — l'utilisateur attendait le JSON brut de l'API eedomus (payload mis en cache par le coordinator), fidèle, diagnostique et copiable.

**Approach:** La section repliable existante gagne un second niveau sous la liste : le JSON du payload (`row.raw`) affiché formaté (`JSON.stringify(raw, null, 2)`, ordre des clés d'origine — decision UX run 3), plus un bouton « Copier le JSON » avec retour annoncé via une région aria-live dédiée. La liste triée actuelle reste le premier niveau. Le payload est déjà servi par `eedomus/get_coherence` (`row._raw` gelé) — aucun changement backend. Microcopie nouvelle : 3 clés `panel.*` dans l'inventaire + le catalogue (EN source, FR), validées par l'utilisateur.

## Boundaries & Constraints

**Always:** ordre des clés du JSON = ordre d'origine du payload (aucun tri, aucune transformation des valeurs) ; prettifying côté panneau (`JSON.stringify(raw, null, 2)`) ; bouton et feedback localisés via `this.t()` ; échec de copie annoncé (jamais silencieux) ; parité mobile automatique (la ligne étendue réutilise `coherenceDetailHtml` — un seul site de rendu) ; échappement : le JSON est rendu dans `<pre><code>` échappé par `escapeHtml`, échappé une seule fois ; nouvelle microcopie inventoriée (le test de parité inventaire/catalogue doit rester vert) ; ligne ≤ 88 (littéraux insécables exemptés) ; garde i18n verte.

**Never:** pas de changement backend (ui_service/panel_translations hors nouvelles clés de catalogue, contrats `get_coherence`/`get_peripherals` gelés) ; pas de re-fetch spécifique (le JSON affiché est celui du cache au moment du rendu) ; pas de lib externe ; pas de modification de la liste triée existante ni des autres sections du détail ; pas de commentaire/log en français (règle 3.5 pour le nouveau code).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | payload coordinator non vide, section dépliée | liste triée, puis `<pre>` avec le JSON indent 2, clés en ordre d'origine | — |
| Copie | clic « Copier le JSON » | JSON dans le presse-papiers + annonce « JSON copié. » | — |
| Échec copie | clipboard refusé (contexte non sécurisé, permission) | annonce « Copie impossible. » | fallback execCommand avant l'échec |
| Payload imbriqué | valeurs objets/tableaux | rendues telles quelles dans le JSON (structure préservée) | — |
| Locale EN/FR | catalogue selon hass.locale | bouton/feedback localisés | — |

</intent-contract>

## Code Map

- `custom_components/eedomus/www/eedomus-panel.js` — seul fichier de production. `coherenceDetailHtml(row, t)` (~l.402) : le bloc `<details class="popover-raw">` (~l.449-452) porte summary + `coherenceDetailPairsHtml(coherenceRawPairs(row.raw))` — y ajouter le bloc JSON + bouton ; `coherenceRawPairs` l.301 (liste triée, ne pas toucher) ; `escapeHtml` l.324 ; régions live : `_announceStatusNow(live, text)` l.2259, enregistrements l.1684-1690 (pattern pour une région dédiée `copy-status-live`) ; styles `.popover-raw` l.1454+ (réutiliser les tokens existants, aucune couleur en dur) ; la ligne étendue mobile réutilise `coherenceDetailHtml` (l.568) — parité gratuite.
- `custom_components/eedomus/panel_translations.py` — +3 clés ×2 arbres : `panel.coherence.detail.copy_json` ("Copy JSON" / « Copier le JSON »), `panel.coherence.detail.copy_feedback` ("JSON copied." / « JSON copié. »), `panel.coherence.detail.copy_failed` ("Copy failed." / « Copie impossible. ») ; docstring count 137 → 140.
- `_bmad-output/specs/spec-eedomus-i18n/i18n-inventory.md` — ligne du popover raw section : ajouter les 3 clés (le test de parité inventaire/catalogue en tests/unit échoue sinon).
- `tests/js/test-coherence.js` — harnais : tests de rendu (JSON présent sous la liste, clés en ordre d'origine vs triées, bouton présent), test de copie avec stub clipboard (succès → feedback annoncé, échec → copy_failed annoncé).
- `tests/unit/test_ui_service.py` — la parité inventaire/catalogue s'adapte via l'inventaire ; docstring 137→140 sans autre changement attendu.

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/panel_translations.py` + `i18n-inventory.md` — 3 clés ×2 langues + ligne inventaire + docstring — la parité inventaire/catalogue reste verte
- [ ] `custom_components/eedomus/www/eedomus-panel.js` — bloc JSON indent 2 sous la liste + bouton copier + région live dédiée + handler (clipboard API, fallback execCommand, feedback annoncé)
- [ ] `tests/js/test-coherence.js` — tests rendu/copie selon la matrice I/O

**Acceptance Criteria:**
- Given un payload non vide, when la section est dépliée, then le JSON s'affiche sous la liste triée avec les clés en ordre d'origine (test : ordre ≠ trié pour un payload dont l'ordre diffère).
- Given le clic copier, when clipboard résout, then le JSON complet est dans le presse-papiers et « JSON copié. » est annoncé.
- Given le clic copier, when clipboard échoue (y compris après fallback), then « Copie impossible. » est annoncé — jamais d'échec silencieux.
- Given la vue mobile, when la ligne est étendue, then le même contenu (liste + JSON + bouton) se rend.

## Implementation Notes

Full route : changements localisés mais multi-surfaces (rendu, i18n, tests) — subagent d'implémentation. Décisions validées par l'utilisateur (2026-10-04) : deux niveaux (liste conservée), ordre des clés d'origine, indentation 2, bouton « Copier le JSON » / "Copy JSON", feedback « JSON copié. » / "JSON copied." ; build enchaîné après le cycle 3.4.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 226 verts (parité inventaire/catalogue et arbres EN/FR à 140 clés)
- `node tests/js/test-coherence.js` -- expected: verts, nouveaux tests inclus
- `node tests/js/test-i18n-guard.js` -- expected: vert (les nouvelles clés panel.* passent la validation catalogue)
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: OK
</intent-contract>

## Review Triage Log

### 2026-10-04 — Review pass
- verdicts: 23 findings — high 0, medium 4, low 14, false 5, maybe-false 0
- findings:
  - `[false]` `[reject]` duplicate copy-status-live popover/expansion (blind) — réfuté : expansion unique par construction (`_coherenceExpandedId` = un seul id, `coherenceRowExpansionHtml` n'émet que pour l'id étendu, le côté large n'émet jamais, le toggle referme le popover) — une seconde région ne coexiste jamais.
  - `[low]` `[patch]` lookup manquant/texte vide → faux succès « JSON copié. » (blind + edge, groupés) — garde ajouté : announce copy_failed sans tentative de copie.
  - `[medium]` `[patch]` fallback copie jamais testé sur le texte copié + stub échoïsant le sélecteur du handler (blind) — test : `area.value` asseré == RAW_TEXT, sélecteur dérivé du markup réellement émis.
  - `[low]` `[patch]` pollution du sandbox (navigator/document laissés stubbés) (blind) — snapshot/restauration en finally (suppression vérifiée en vm probe).
  - `[false]` `[reject]` story/plan à la traîne dans le diff (status in-progress, cases non cochées) (blind) — le snapshot du diff précède la Finalize qui écrit les champs finaux ; les cases restent non cochées par convention des plans du repo.
  - `[low]` `[reject]` plan Approach dit `row._raw` alors que la clé servie est `raw` (blind) — le correctif édite le plan de ce build ; le Code Map et le code utilisent la bonne clé ; noté en résiduel.
  - `[low]` `[reject]` formes payload vide/scalaire non épinglées (blind) — payloads coordinator = dicts ; le rendu correct de ces formes est le comportement actuel, non des situations atteignables.
  - `[low]` `[defer]` chemin de copie en contexte non sécurisé stub-only (blind) — reporté : contrôle live E2E sur le Pi (voir deferred).
  - `[low]` `[patch]` writeText jamais résolu → aucun verdict (edge) — Promise.race timeout 2000 ms (COPY_WRITE_TIMEOUT_MS), échec annoncé.
  - `[low]` `[reject]` re-render pendant l'await perd le verdict (edge) — fenêtre de quelques ms ; pire cas un succès silencieux (la copie a eu lieu), correctif = complexité pour une fenêtre inobservable.
  - `[low]` `[patch]` (fusion blind/edge ci-dessus) garde texte vide.
  - `[low]` `[reject]` garde document.body manquant (edge) — body toujours présent dans le runtime du panneau HA ; situation inatteignable.
  - `[maybe-false→false]` `[reject]` claim « échec jamais silencieux » perdu si région live absente (edge) — avec une région unique et le helper announce, la fenêtre restante est la course du re-render (ligne ci-dessus) ; rien d'actionnable séparément.
  - `[medium]` `[patch]` branche de délégation _onClick non testée — bouton mort indétectable (verif, prouvé par mutation) — test _onClick stub-event ajouté (pattern entity-link).
  - `[medium]` `[patch]` le test fallback n'observe pas le texte copié (verif, prouvé par mutation) — asseré (regroupé avec la ligne blind ci-dessus).
  - `[low]` `[patch]` (verif, other) textarea jamais focus() avant select — execCommand exige le focus dans plusieurs navigateurs — area.focus() ajouté avant select.
  - `[low]` `[defer]` Acceptance(1) vérifiée sur chaînes HTML, pas en navigateur (intent) — portée inhérente au harnais vm ; observation live reportée à l'E2E (voir deferred).
  - `[medium]` `[patch]` câblage click→clipboard sous le handler (intent) — même correctif que la branche _onClick (regroupé).
  - `[false]` `[reject]` ambiguïté d'annonce multi-lignes étendues (intent) — réfuté par l'expansion unique (voir première ligne).
  - `[low]` `[reject]` parité testée par marqueurs, pas par égalité de contenu (intent) — le renderer partagé unique EST le mécanisme de parité (pattern du repo depuis 2.5) ; asserter l'égalité testerait le template contre lui-même.
  - `[false]` `[reject]` « la garde i18n n'est pas exécutée par le diff » (intent) — les suites ont tourné en session à la vérification step-03 (garde verte à 140 clés, 226 pytest) ; le diff est un artefact de patch, pas un journal d'exécution.
  - `[low]` `[reject]` ordre des clés entières (intent) — JSON.stringify hoiste les clés de type entier ; les clés du payload API sont des chaînes ; l'« ordre d'origine » tient pour toute forme atteignable.
  - `[low]` `[reject]` le fichier de plan 79 lignes hors du périmètre produit (intent) — artefact de processus de ce workflow, pas du produit.

## Auto Run Result

Status: built

- Summary: la section « Champs bruts de l'API eedomus » (popover + ligne étendue mobile, parité par renderer partagé) rend désormais deux niveaux : la liste triée clé→valeur conservée, puis le JSON brut du payload coordinator (JSON.stringify indent 2, ordre des clés d'origine, échappé une passe) avec un bouton « Copier le JSON » (API clipboard → fallback execCommand focusé → verdict toujours annoncé sur une région copy-status-live dédiée, timeout 2 s sur un writeText qui traîne). 3 clés panel.* (copy_json/copy_feedback/copy_failed) ×2 arbres, inventaire + docstring 140.
- Files: eedomus-panel.js (+128 : helper coherenceRawJson, bloc raw-json-bar/live/pre, styles tokens HA, _onClick + _copyCoherenceRawJson + fallback), panel_translations.py (+6), i18n-inventory.md (+1 ligne), tests/js/test-coherence.js (+248 : rendu ordre/échappement/null/parité, 9 assertions copie dont délégation _onClick et observation du texte fallback, sandbox restauré).
- Review: 23 findings sur 4 lenses — 8 patchs appliqués (garde faux-succès, timeout writeText, focus fallback, test délégation _onClick, observation texte fallback + sélecteur dérivé du markup, restauration sandbox), 1 différé (contrôle E2E live du fallback en contexte non sécurisé + rendu navigateur), 12 rejets avec raisons (5 réfutations, inatteignables, artefacts de processus, correctifs-éditant-le-plan).
- Follow-up review: recommandé (patcheds mediums = 2 : délégation et texte fallback, prouvés par mutation). Risque non vérifié nommé : le comportement réel du clipboard (permission, focus, hang) et le rendu visuel ne sont pas observables dans le harnais vm — un clic sur « Copier le JSON » en validation live (Pi) fermerait la boucle.
- Verification: pytest tests/unit/ -q → 226 passed ; node test-coherence.js (tous verts, +5 assertions copie post-patch) ; node test-i18n-guard.js vert (140 clés) ; node --check OK ; arbres catalogue ×2 à 140 clés épinglés par la parité inventaire/catalogue.
- Residual: plan Approach mentionne `row._raw` (la clé servie est `raw` — le Code Map et le code sont corrects) ; comportement navigateur réel reporté à l'E2E (deferred).
