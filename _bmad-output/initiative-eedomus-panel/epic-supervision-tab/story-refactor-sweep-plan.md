---
title: 'Refactor sweep'
type: 'refactor'
ticket: 4
created: '2026-10-06'
status: done
route: 'full'
route_source: 'auto'
baseline_revision: '1f9a6b8e12285ae1b7d1e0e42b55e75ea04bc096'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/AGENTS.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Fin d'épique Supervision : des findings différés s'accumulent dans les build records — `coherence.js` (1 660 lignes) reste un god-file en puissance (finding différé de la story 102), `AGENTS.md` décrit encore le panel monofichier (finding différé de 102), et la file de brouillon `uv.lock` traîne non suivi à chaque session.

**Approach:** Sweep de cleanup uniquement, périmètre fixé au démarrage : (S1) scission pure de `coherence.js` — les helpers purs et constantes (COHERENCE_SIGNALS, fonctions libres) déménagent byte-identiques dans `www/panel/coherence-helpers.js`, le mixin et COHERENCE_STYLES restent dans `coherence.js` qui importe ce qu'il consomme ; (S2) la ligne frontend d'AGENTS.md décrit l'architecture réelle (entrée + 7 modules panel/) ; (S3) le finding différé « canal push » est TRAITÉ par décision consignée (le plan_checkpoint 4.3 a ratifié le polling — un callWS par visite, pas d'abonnement) ; (S4) `uv.lock` rejoint `.gitignore` (artefact d'outillage uv, jamais stagé).

## Boundaries & Constraints

**Always:** S1 = déménagement pur (méthode 102 : corps byte-identiques, seuls import/export ajoutés, aucune réécriture, aucun changement de comportement) ; chaque symbole consommé par `coherence.js` est importé explicitement (le harnais concatène en un scope unique et ne détecterait pas un import manquant — le navigateur, lui, le ferait) ; le contrat COHERENCE_SIGNALS de `test_ui_service.py` lit le fichier où vit la constante après la scission ; le harnais charge le nouveau module via le DFS récursif du mini-chargeur ; AGENTS.md mis à jour pour décrire l'entrée + les 7 modules ; les suites restent vertes SANS modification de leurs assertions (seuls les chemins de contrat changent).

**Never:** aucune nouvelle fonctionnalité (pas de canal push — décision S3 consignée, pas d'implémentation) ; pas de réécriture/réformatage du code déplacé (parité byte-identique) ; pas de renommage de symboles publics hookés par le harnais ; pas de touche au backend, aux contrats gelés des rows, ni au catalogue i18n ; le module d'entrée `eedomus-panel.js` ne change pas d'imports (c'est `coherence.js` qui importe `coherence-helpers.js`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Scission | chargeur DFS | coherence-helpers.js chargé avant coherence.js (post-ordre), tout le scope inchangé | module manquant = échec loud du chargeur |
| Imports réels | navigateur | coherence.js importe chaque symbole consommé depuis coherence-helpers.js (liaison ESM valide) | symbole manquant = erreur module au chargement |
| Contrat signaux | test_ui_service | regex COHERENCE_SIGNALS sur le fichier hébergeant la constante | échec loud si absent |
| AGENTS.md | lecture agent | la carte frontend décrit l'entrée + panel/{shared,coherence,coherence-helpers,peripheriques,regles,historique,supervision}.js | — |
| uv.lock | session uv | non listé par git status (ignoré) | — |

</intent-contract>

## Code Map

- `custom_components/eedomus/www/panel/coherence.js` (1 660 l.) — header l.1-9, `import { escapeHtml, coherenceStatusText, truncateDetailText } from './shared.js'` l.9, `COHERENCE_SIGNALS` l.~15, helpers purs jusqu'à `coherenceNarrowMedia` l.499, `coherenceNarrowView` l.511, `coherenceExpandedRowId` l.542 (les 3 seuls exports de la zone helpers), `COHERENCE_STYLES` l.655-916, `applyCoherenceMixin` l.917-1660. Point de scission : ~l.655 (tout ce qui précède COHERENCE_STYLES déménage).
- `tests/js/test-coherence.js` — `loadPanelSource()` (mini-chargeur) : DFS récursif sur les imports (`deps.forEach(walk)`), strip 2 formes, échec loud sinon ; le hook expose les exports des modules chargés.
- `tests/unit/test_ui_service.py` — contrat COHERENCE_SIGNALS : regex sur `www/panel/coherence.js` (chemin à mettre à jour vers le nouveau fichier).
- `tests/unit/test_panel.py` — existence des fichiers modules (étendre la liste à coherence-helpers.js).
- `AGENTS.md` — l.~15 : décrit `www/eedomus-panel.js` sans mention de `www/panel/`.
- `.gitignore` — ajouter `uv.lock`.
- Précédent méthode : plan 102 (story-dcouper-eedomus-paneljs-par-onglet-plan.md) — déménagement byte-identique, TDZ mixins, styles composés.

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/www/panel/coherence-helpers.js` + `coherence.js` -- scission pure : COHERENCE_SIGNALS + helpers purs (jusqu'aux 3 exports inclus) déménagent byte-identiques dans coherence-helpers.js avec leurs imports de shared.js et les export des symboles consommés ; coherence.js garde COHERENCE_STYLES + applyCoherenceMixin et importe explicitement chaque symbole utilisé (signaux, helpers, escapeHtml… si consommés) -- le god-file cesse de croître
- [ ] `tests/unit/test_ui_service.py` + `tests/unit/test_panel.py` -- le contrat COHERENCE_SIGNALS lit coherence-helpers.js ; la liste des modules existants gagne coherence-helpers.js -- churn de chemins de contrat prévu
- [ ] `AGENTS.md` -- la ligne/courte section frontend décrit l'entrée (URL servie, core/shell/délégation) + les 7 modules de panel/ (un par onglet + shared + coherence-helpers) -- la carte des agents est exacte
- [ ] `.gitignore` -- ajouter uv.lock (artefact uv, jamais stagé) -- hygiène repo
- [ ] Plans de 102 et 4.1/4.3 -- consigner S3 : le finding différé « canal push » est traité par la décision du plan_checkpoint 4.3 (polling ratifié : un callWS par visite + Réessayer, pas d'abonnement) ; note one-line dans les Auto Run Result concernés -- aucun différé non traité

**Acceptance Criteria:**
- Given le harnais node, when il charge l'entrée, then coherence-helpers.js est évalué avant coherence.js, toutes les assertions existantes passent inchangées (210 PASS).
- Given la suite unitaire, when elle tourne, then le contrat COHERENCE_SIGNALS lit la constante dans son nouveau fichier, la liste des modules inclut coherence-helpers.js, 324 tests verts.
- Given AGENTS.md, when un agent le lit, then la description frontend correspond à l'arborescence réelle (entrée + 7 modules).
- Given git status, when une session uv tourne, then uv.lock n'apparaît plus comme non suivi.
- Given les build records de l'épique, when le sweep se termine, then chaque finding différé est traité (patché ou décision consignée) — aucun non-traité.

## Implementation Notes

Full route — sweep figé au démarrage : S1 scission (le finding différé 102, la pièce substantive), S2 AGENTS.md (différé 102), S3 décision push-canal consignée (différé 4.1, tranché au checkpoint 4.3 : polling), S4 .gitignore uv.lock (hygiène récurrente). Pas de cache-busting dans ce sweep (candidat backlog à proposer au board, pas un cleanup). Méthode 102 : déménagement byte-identique, l'ordre DFS du mini-chargeur couvre l'import imbriqué, l'entrée ne change pas.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 324 verts (chemins de contrat mis à jour)
- `node tests/js/test-coherence.js && node tests/js/test-i18n-guard.js` -- expected: verts (210 PASS inchangés, garde sur 8 fichiers)
- `python3 -m pytest tests/e2e/ --collect-only -q` -- expected: 27 collectés
</intent-contract>

## Review Triage Log

### 2026-10-06 — Review pass (thorough, 4 lens inline par l'orchestrateur — limite de noms de subagents ; le déménagement a été vérifié byte-identique indépendamment : 501/501 lignes de l'ancienne zone helpers trouvées verbatim dans coherence-helpers.js)
- verdicts: 5 findings — high 0, medium 2, low 1, false 0, ratifiées 2
- findings:
  - `[medium]` `[patch]` (blind+verif) boucle E2E des modules servis : TROIS défauts — (a) marqueur coherence.js = "COHERENCE_SIGNALS" mais la constante a déménagé (0 occurrence dans coherence.js — le test live aurait échoué au 4.5), (b) supervision.js absent depuis 4.2 (404 = panneau mort, test vert — la forme exacte du finding 102), (c) coherence-helpers.js absent — P1 : marqueurs corrigés, 7 modules, liste DÉRIVÉE dynamiquement de www/panel/*.js avec map de marqueurs (un module non marqué échoue loud — la dérive ne peut plus récuser).
  - `[low]` `[patch]` (blind) commentaire du mini-chargeur auto-contradictoire (« re-export … REJECTED » dans le commentaire qui documente la forme gérée) — P2 : libellé corrigé.
  - `[ratifié]` (edge) parité byte-identique du déménagement vérifiée indépendamment (501/501 verbatim, 0 manquante) + liaison ESM native 8 modules (SourceTextModule) — le cas navigateur invisible au harnais.
  - `[ratifié]` (intent) périmètre du sweep livré tel que fixé : S1 scission (finding différé 102 TRAITÉ), S2 AGENTS.md (différé 102 TRAITÉ), S3 décision push-canal consignée dans les trois plans concernés (différé 4.1 TRAITÉ par décision checkpoint 4.3), S4 .gitignore uv.lock — aucun finding différé non traité (verify du ticket).
  - `[low]` `[reject]` (verif, other) coherence.js reste à 1 041 lignes (mixin + styles du plus gros onglet) — acceptable après scission des helpers ; la limite god-file du finding 102 était la zone helpers.

Patches P1-P2 appliqués par impl-42-supervision (tour 5), re-vérifiés indépendamment. Pas d'intent_gap, pas de bad_plan.

## Auto Run Result

**Route:** full — sweep au périmètre fixé, impl par subagent (impl-42-supervision), review 4 lens inline (limite de noms), triage, 2 patchs, re-vérif.

**Vérifications exécutées (orchestrateur, 2026-10-06) :**
- `python3 -m pytest tests/unit/ -q` — 324 passed (chemins de contrat mis à jour, zéro assertion changée)
- `node tests/js/test-coherence.js` — exit 0, 210 PASS inchangés
- `node tests/js/test-i18n-guard.js` — 919 littéraux / 8 fichiers, aucun texte en dur
- `python3 -m pytest tests/e2e/ --collect-only -q` — 27 collectés
- Parité byte-identique : 501/501 lignes de la zone helpers déménagées verbatim (vérification indépendante orchestrateur) ; liaison ESM native des 8 modules (vm.SourceTextModule)

**Findings différés traités :** scission coherence.js (102) — fait ; AGENTS.md frontend (102) — fait ; canal push (4.1) — décision consignée (polling ratifié au checkpoint 4.3). + hygiene : uv.lock ignoré.

**Post-déploiement :** couvert par la 4.5 (validation live de fin d'épique, la boucle E2E dynamique s'exerce alors contre le Pi).
