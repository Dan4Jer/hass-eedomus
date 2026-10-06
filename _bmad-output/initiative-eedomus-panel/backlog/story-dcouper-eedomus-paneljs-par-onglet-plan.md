---
title: 'Découper eedomus-panel.js par onglet'
type: 'refactor'
ticket: 'story-dcouper-eedomus-paneljs-par-onglet'
created: '2026-10-05'
status: done
route: 'full'
route_source: 'auto'
baseline_revision: '6cc6c39c38ace7e66321d57228b4d7058ca112d4'
review: 'thorough'
review_source: 'auto'
review_source: ''
lenses_ran: [blind-hunter, edge-case-hunter, verification-gap, intent-alignment]
review_loop_iteration: 0
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/initiative-eedomus-panel/epic-coherence-tab/epic-coherence-tab-retrospective.md
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** `www/eedomus-panel.js` est un god-file de ~4 300 lignes : quatre onglets, l'éditeur YAML, le moteur diff, tous les helpers et le composant unique. La rétro cohérence l'a mesuré (1 852 → 3 668 sur son épique) et la décision utilisateur du 2026-10-05 impose le découpage AVANT l'épique 4 — le 5e onglet Supervision ne doit pas grossir le monolithe.

**Approach:** Découpage en vrais modules ES — `panel.py` charge déjà le panneau via `module_url` (le frontend HA l'importe comme module), donc l'entrée `eedomus-panel.js` (URL inchangée) importe des modules de `www/panel/` : `shared.js` (escapeHtml, constantes transverses, helpers d'annonce), `coherence.js`, `peripheriques.js`, `regles.js`, `historique.js` — chacun portant ses fonctions libres ET son mixin de prototype (`Object.assign(EedomusConfigPanel.prototype, {...})`) pour les méthodes de classe de son onglet. L'entrée garde le cœur (constructeur, t()/catalogue, set hass, shell _render + styles, délégation d'événements) et le `customElements.define`. Extraction pure : le code DEMÉNAGE sans réécriture (aucun changement de comportement), chaque test existant garde ses assertions intactes.

## Boundaries & Constraints

**Always:** l'URL du module enregistré reste `eedomus-panel.js` (panel.py inchangé) ; les imports sont relatifs (`./panel/x.js`) servis par le même StaticPathConfig (sous-dossier servi comme le reste de www/) ; extraction sans réécriture — seuls import/export et les liens de symboles sont ajoutés ; le harnais node (test-coherence.js) gagne un mini-chargeur de modules (charge les fichiers dans l'ordre de dépendance, strip import, collecte export) — ses assertions ne changent pas ; la garde i18n scanne TOUS les fichiers JS de www/ (définition de la surface du panneau = ensemble des fichiers) ; les tests de contrat qui regexaient le fichier unique (COHERENCE_SIGNALS dans test_ui_service, substrings de test_panel) lisent les fichiers modules correspondants ; chaque module reste ≤ 88 colonnes ; l'entrée descend sous ~900 lignes, chaque module d'onglet est cohérent et nommé.

**Never:** aucun changement de comportement du panneau (le DOM rendu doit être identique) ; pas de toolchain/build (modules ES natifs servis tels quels) ; pas de réécriture de la logique pendant le déménagement ; pas de toucher aux arbres de traduction ni au backend ; pas de renommage des symboles publics que les tests hookent ; les 262 tests unitaires et les assertions du harnais JS restent vertes sans modification de leurs assertions (seuls les chemins/chargeurs changent).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Chargement panneau | navigateur, module_url | l'entrée importe les 5 modules, le composant se définit | 404 module = console error (comme tout module) |
| Cache | déploiement des nouveaux fichiers | le module_url de l'entrée est rechargé ; les modules relatifs partagent son origine | — |
| Harnais node | test-coherence.js | mini-chargeur évalue les modules dans l'ordre, tous les tests existants passent | échec loud si un module manque |
| Garde i18n | n'importe quel fichier www/*.js | chaîne en dur → échec du scan (surface = ensemble) | — |
| Contrat signaux | test_ui_service | COHERENCE_SIGNALS lu depuis coherence.js | échec loud si absent |
| E2E live | panneau déployé | le panneau charge et rend à l'identique (validation visuelle + test_panel_asset_served) | — |
| Taille | wc -l | entrée < ~900, chaque module d'onglet nommé et cohérent | — |

</intent-contract>

## Code Map

Carte du fichier actuel (4 187 lignes) :
- **l.14-725** — constantes + fonctions libres : transverses (`TABS`:14, délais d'annonce 55-73, `escapeHtml`:360) et cohérence (COHERENCE_SIGNALS:19, helpers purs 80-663, popover 343+, chips 653+, `coherenceRowHtml`:697).
- **l.727-1040** — classe : constructeur (728), `t()` (843), `setConfig` (923), `connectedCallback` (930), catalogue/`set hass` (~797-836), tab/hash (973-1020), `_filteredPeriphs` (1021).
- **l.1040-1673** — `_render` : shell + STYLES inline + rendu de tous les onglets (~630 lignes — le plus gros bloc ; les styles et le squelette restent à l'entrée, les sections par onglet se délèguent aux mixins si le déménagement reste pur, sinon le shell reste entier à l'entrée).
- **l.1675-1980** — délégation : `_onClick` (1675), `_onAuxClick` (1780), copie JSON (1848), `_onInput` (1876), `_onKeyDown` (1904), `_createRuleFor` (1975).
- **l.1982-2399** — historique : `_renderTabContent` (1982), `_formatTimestamp` (2062), `_reasonLabel` (2074), `_renderHistoryTab` (2084), `_wireHistoryTab` (2177), `_historyStatusText` (2187), `_renderDiff` (2198), `_diffLines` (2229).
- **l.2400-3118** — cohérence : toolbar/table/sort/filter/popover/breakpoint/skeleton/row (2400-3118) + `_openEntityMoreInfo` (2734).
- **l.3119-3397** — périphériques : toolbar (3119), liste (3148), announce (3278), `_renderRow` (3306), escape helpers (3361).
- **l.3398-3670** — règles (form) : `_usageIdRules` (3398), `_openRuleForm` (3405), validation programmée (3427), états (3475), statuts (3506), cache invalidation (3546 — transverse, à l'entrée ou shared), `_renderRulesList` (3671).
- **l.3716-4280** — règles (tab + YAML) : `_renderRulesTab` (3716), highlighter YAML (4089-4213), `_onRulesEvent` (4214), `_onRulesInput` (4273).

Dépendances de test au fichier unique (à adapter) :
- `tests/js/test-coherence.js` — `vm.runInContext(readFileSync(PANEL_PATH) + hook)` (l.119) : remplace par le mini-chargeur multi-modules ; le hook exporte les mêmes symboles (certains viendront des modules — le chargeur les expose dans le scope du sandbox).
- `tests/js/test-i18n-guard.js` — `PANEL_PATH` (l.55) : scan de `www/**/*.js` (l'entrée + les modules) ; la définition de « chaîne du panneau » devient l'ensemble.
- `tests/unit/test_panel.py` — substring checks (l.87) sur l'entrée + `is_file()` : étendre l'existence aux modules.
- `tests/unit/test_ui_service.py:1586` — regex COHERENCE_SIGNALS sur le fichier panel : lire `www/panel/coherence.js` (ou l'ensemble).
- `tests/e2e/test_e2e_panel.py` — `test_panel_asset_served` : vérifie l'entrée servie ; ajouter la vérification qu'un module est servi (fetch `./panel/coherence.js` via l'URL statique) — optionnel, à la discrétion de l'impl avec preuve.

## Tasks & Acceptance

**Execution:**
- [ ] Découpage : `www/panel/{shared,coherence,peripheriques,regles,historique}.js` + entrée allégée — déménagement pur, imports/exports ajoutés
- [ ] Harnais : mini-chargeur de modules dans test-coherence.js (ordre de dépendance, exports exposés) — assertions inchangées
- [ ] Garde : scan de tous les fichiers JS de www/ (surface = ensemble)
- [ ] Contrats : test_ui_service (COHERENCE_SIGNALS → coherence.js), test_panel (modules existants)
- [ ] Vérification taille : entrée < ~900 lignes, modules nommés

**Acceptance Criteria:**
- Given le panneau déployé, when il charge, then il rend à l'identique (aucun changement de DOM/behavior) — validé par le harnais existant (toutes ses assertions vertes sans modification) + E2E + validation visuelle live.
- Given la garde i18n, when une chaîne en dur apparaît dans N'IMPORTE QUEL module, then elle échoue.
- Given le harnais, when il charge les modules, then tous les tests existants passent avec leurs assertions d'origine.
- Given wc -l, when le découpage est fait, then l'entrée est < ~900 lignes et chaque onglet vit dans son module.

## Implementation Notes

Full route — le plus gros refactor de la chaîne (déménagement de ~3 400 lignes), mais pur : aucune réécriture, le DOM doit rester identique. Le mini-chargeur du harnais est la seule pièce nouvelle (charge les modules dans l'ordre, strip `import`, transforme `export const/function/class` en déclarations + collecte dans un registre que le hook expose). Prudence sur l'ordre : shared → coherence → tabs (les mixins s'applicant à la classe, l'entrée importe tout et assemble). Les styles restent dans le _render de l'entrée. Le déploiement + validation live suit le build (décision utilisateur 2026-10-05 : découpage avant épique 4 ; déploiement mode précédent 2.8).

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 262 verts (contrats adaptés aux chemins modules)
- `node tests/js/test-coherence.js && node tests/js/test-i18n-guard.js` -- expected: verts (harnais multi-modules, garde multi-fichiers)
- `node --check` sur CHAQUE fichier JS de www/ -- expected: OK (l'entrée avec ses imports check)
- `wc -l custom_components/eedomus/www/eedomus-panel.js custom_components/eedomus/www/panel/*.js` -- expected: entrée < ~900, modules nommés
- `python3 -m pytest tests/e2e/ --collect-only -q` -- expected: 27 collectés
- Post-déploiement (orchestrateur) : `pytest tests/e2e/ -v` vert sur le Pi + validation visuelle du panneau (les 4 onglets rendent)
</intent-contract>

## Review Triage Log

### 2026-10-05 — Review pass (thorough: blind-hunter, edge-case-hunter, verification-gap, intent-alignment)
- verdicts: 18 findings — high 0, medium 8, low 8, false 2, maybe-false 0
- findings:
  - `[medium]` `[reject]` (blind) Commande `node --check` du plan inexécutable sur fichiers ESM (node 12 parse .js en CommonJS) — le fix édite le plan ; vérification syntaxe RÉELLEMENT exécutée via `vm.SourceTextModule` (--experimental-vm-modules), 6/6 OK, consignée dans Auto Run Result.
  - `[medium]` `[patch]` (blind) E2E ne vérifiait que coherence.js servi (1/5 modules) — un 404 sur shared.js tuait le panneau test vert ; P1 : boucle HTTP 200 + marqueur sur les 5 modules.
  - `[low]` `[patch]` (blind) En-tête d'entrée obsolète (« P.1.3 … Rules and History placeholders ») — P2 : réécrit (architecture réelle, 5 modules + mixins + *_STYLES).
  - `[low]` `[reject]` (blind) 48 lignes > 88 colonnes — ensemble identique pré/post split (CSS dans template literals, hérité) ; reformater casserait la parité byte-identique du déménagement pur ; contrainte pure-move prioritaire.
  - `[low]` `[reject]` (blind) Figures de taille incohérentes dans le plan (~4 300 / 4 187 / 4 322) — le fix édite le plan ; refs Code Map inertes post-split.
  - `[medium]` `[reject]` (blind) Implementation Notes « les styles restent à l'entrée » contredit le livré (styles par module interpolés) — déviation RATIFIÉE : « styles à l'entrée » + « entrée < 900 » étaient incompatibles ; composition DOM byte-identique, toutes les lignes Never tenues ; fix = éditer le plan.
  - `[false]` (blind) Métadonnées datées du futur (created 2026-10-05 vs « review 2026-10-03 ») — la date système est 2026-10-05 ; created est correct ; le lens a comparé à une mauvaise date de référence.
  - `[low]` `[patch]` (blind) Mini-chargeur silencieux sur formes d'import exotiques (double quotes, side-effect, namespace, re-export) — P3 : rejet loud AVANT évaluation, message nommant la cause ; sondé (exit 1 ×2), revert byte-clean.
  - `[medium]` `[patch]` (blind) Garde i18n : PANEL_FILES codé dur (entrée + readdir plat) vs contrat « tous les www/*.js » — P4a : parcours récursif de www/, dir manquant → message clair.
  - `[low]` `[patch]` (blind, verif) Exemption `^\./` trop large (toute chaîne commençant par ./) — P4b : exemption supprimée, imports strippés avant extraction ; sondé par littéral planté `./Périphériques…` → FAIL nommé, revert byte-clean.
  - `[medium]` `[defer]` (blind) coherence.js 1 670 lignes = futur god-file — concentration préexistante d'un onglet entier, pas causée par ce changement ; candidate scission (helpers purs / mixin / styles) avant ou avec l'épique 4, à proposer au board.
  - `[low]` `[defer]` (blind) AGENTS.md décrit encore le panel monofichier — fix édite un fichier de contexte agent ; différé.
  - `[medium]` `[patch]` (edge) FAIL de la garde imprime `undefined` comme fichier — vérifié réel par le patch P4 lui-même : `checkLiterals` retourne des enregistrements frais, donc `literalFiles.get(v)` → undefined ; corrigé en taggant les violations à la source (pipeline par fichier). (Verdict initial « false » corrigé après preuve de l'impl.)
  - `[false]` (edge) Clash de méthodes prototype entre modules silencieux — parité des noms vérifiée mécaniquement (89 méthodes, aucune collision) ; composition fixe de l'entrée.
  - `[low]` `[reject]` (edge) Dépendance croisée historique→règles (`_yamlDumpFull`, `_persistMapping`) sans garde au chargement — état injoignable : l'entrée importe les 5 modules en dur, le harnais échoue loud sur module manquant ; garde = complexité défensive.
  - `[medium]` `[patch]` (verif, pré-vérifié) Interpolations `${*_STYLES}` sans témoin de test — suppression du lien RULES_STYLES laissait TOUTE la suite verte (démontré par expérience) ; P5 : un sélecteur représentatif par constante (`.periph-list {`, `.rule-form {`, `.version-card {`, `.coherence-table-wrap {`).
  - `[medium]` `[reject]` (verif) Étape `node --check` du plan inatteignable — doublon du finding blind ; fix édite le plan ; la variante exécutable est consignée dans Auto Run Result.
  - `[low]` `[patch]` (verif) Exemption `^\./` non ciblée — groupé avec B10, P4b.
- intent-alignment (descriptif) : lecture retenue — noyau commun = `shared.js` (126 lignes, ≤ 400 tenu sous R1), l'entrée < 900 est la baseline du plan validée ; surface runtime (AC1) couverte par E2E live + validation visuelle post-déploiement, planifiées en clôture du ticket.

Patches appliqués par impl-102-split (tour 2), tous re-vérifiés indépendamment (voir Auto Run Result). Pas d'intent_gap, pas de bad_plan. Deferred : scission coherence.js (candidate backlog), ligne frontend AGENTS.md.

## Auto Run Result

**Route:** full — impl par subagent, review thorough 4 lens, triage, patches, re-vérif.

**Vérifications exécutées (orchestrateur, session du 2026-10-05) :**
- `python3 -m pytest tests/unit/ -q` — 262 passed
- `node tests/js/test-coherence.js` — exit 0, 148 PASS (post-patch)
- `node tests/js/test-i18n-guard.js` — self-test 5/5 ; 731 littéraux / 6 fichiers, 26 exemptés, aucun texte en dur (post-patch)
- Syntaxe ESM : `vm.SourceTextModule` sous `node --experimental-vm-modules` — 6/6 OK (remplace le `node --check` du plan, inexécutable sur modules ES)
- `python3 -m pytest tests/e2e/ --collect-only -q` — 27 collectés
- `wc -l` — entrée 865 (< 900), panel/ : shared 126, peripheriques 337, historique 383, regles 1054, coherence 1670
- git : HEAD = 6cc6c39 (baseline), 4 stashes préexistants intacts, index propre avant commit

**Déviations ratifiées :** (1) styles par onglet dans les modules (contraintes « styles à l'entrée » + « entrée < 900 » incompatibles — composition byte-identique) ; (2) mixins via apply functions (TDZ ES) ; (3) placement helpers selon Code Map ; (4) exemption garde `^\./` supprimée (imports strippés en amont).

**Post-déploiement :** à consigner après validation live (E2E sur le Pi + validation visuelle 4 onglets + logs).

**Post-déploiement (2026-10-05, 21:36-21:41 CEST) :**
- Déployé via `deploy_hass_eedomus.sh` (git-only, unstable @ 1cd0b16), restart HA, ~2 min d'attente
- Fichiers servis (HTTP 200) : entrée + les 5 modules `panel/*.js`
- `python3 -m pytest tests/e2e/ -v` sur le Pi : **27 passed in 62.67s** (dont `test_panel_asset_served` avec la boucle 5 modules)
- Logs post-restart : `Eedomus configuration panel registered`, `websocket commands registered`, `Eedomus integration initialized successfully` ; aucune ERROR/traceback liée au panel — seules erreurs : motif préexistant de retry historique (periph 1235258, retry in 24 h)
- Validation visuelle des 4 onglets : faite par l'utilisateur (2026-10-05) — « tout est identique » ; ticket marqué done

**Sweep 4.4 (2026-10-06) :** findings différés traités — scission coherence.js livrée (helpers purs → `coherence-helpers.js`, byte-identiques, S1) et ligne frontend AGENTS.md mise à jour (entrée + 7 modules, S2).
