---
title: 'Passe complète : logs, docstrings et commentaires en anglais'
type: 'refactor'
ticket: 5
created: '2026-10-04'
status: done
route: 'full'
route_source: 'auto'
baseline_revision: '017a18b6590f4279db1a5617ab4e9a6bbf46c455'
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
      ConfigEntryNotReady first-refresh failure path: the translated setup-error
      message is untested (no coordinator harness drives the failure branch),
      and the message could use HA's native error-translation grammar
      (strings.json) instead of plain-EN for all locales.
    evidence: >-
      No test constructs the first-refresh failure; conftest only stubs the
      exception class. A live setup failure would show the new English message
      unverified. Fold into the next change that touches coordinator setup
      tests; observe once live during the E2E pass.
    location: custom_components/eedomus/coordinator.py:117-128
    severity: medium
  - summary: >-
      Translated log messages have no automated observer — the heuristic grep
      is the gate for a mechanical pass; caplog-pinning every site would be
      brittle.
    evidence: >-
      Repo pins log text with caplog where behavior matters (PARTIAL REFRESH),
      but no migrated log string (old or new) appears in any test; humans are
      the only consumer.
    severity: low
  - summary: >-
      tests/js/test-coherence.js still carries French comments and assertion
      labels (l.185/192/337/350/353) mirroring the pre-3.5 panel commentary —
      out of this ticket's scope (custom_components/eedomus only), now
      divergent from the migrated panel comments.
    evidence: >-
      Panel comments now say "ascending -> descending -> neutral" while the
      test still says "croissant -> décroissant -> neutre"; French also leaks
      into test output labels.
    location: tests/js/test-coherence.js
    severity: low
  - summary: >-
      The acceptance grep needs a documented exemption list to be falsifiable
      (frozen trees, panel_translations, user-data matchers) — that CI guard is
      ticket 3.7's deliverable.
    evidence: >-
      The pass correctly leaves runtime data matching in French
      (binary_sensor "porte"/"fenêtre"/"fumée"/"présence", climate
      "arrêt"/"désactiver") — any naive accent grep reports them; this pass's
      exact command and exclusions are recorded in the Auto Run Result.
    severity: low
---

<intent-contract>

## Intent

**Problem:** CAP-4 : les logs, docstrings et commentaires en français de `custom_components/eedomus` (17 fichiers Python + ~54 lignes du panneau JS) brisent le régime d'anglais-source ; trois familles de chaînes backend servies à l'appelant ou au panneau restent françaises (inventaire §6) — un utilisateur anglais verrait du français après la migration complète.

**Approach:** Passe mécanique complète, fichier par fichier, sous l'inventaire comme source (§5 : 7 appels de log FR — coordinator.py ×5 l.115/1196/1199/1250/1289, __init__.py ×2 l.221/262 ; 26 blocs de docstring FR sur 8 fichiers — coordinator ×9, ui_service ×4, light ×3, mapping_registry ×3, mapping_rules ×3, eedomus_client ×2, sensor ×1, config_flow ×1 ; commentaires FR dans 17 fichiers py + www/eedomus-panel.js ~54 lignes ; §6 : les ValueError FR du coordinator l.1816/1822/1825, les préfixes servis `f"mapping personnalisé {key}"`/`f"règle {key}"` d'ui_service l.849/858, les fallbacks d'erreur ws l.355/780/999/1011). Anglais naturel, sémantique des messages préservée, aucune logique touchée.

## Boundaries & Constraints

**Always:** un fichier à la fois, suite unitaire verte à chaque étape ; anglais naturel (pas des calques littéraux) ; les logs gardent niveau, placeholders et contexte à l'identique — seule la langue change ; les tests qui épinglent une chaîne migrée sont mis à jour vers le texte anglais (et uniquement ceux-là — le compte de tests ne change pas) ; les noms de règles sont des données utilisateur — seul le préfixe `règle {key}`/`mapping personnalisé {key}` migre ; ligne ≤ 88 ; commentaires JS du panneau migrés sans aucun changement de code.

**Never:** aucun changement de comportement ou de logique ; pas de toucher aux arbres gelés (catalogue `panel_translations.py` hors ses clés existantes, `strings.json`/`translations/*` de 3.4) ; pas de nouvelles clés de catalogue (les chaînes §6 sont plain-EN par décision d'inventaire, pas ws-catalog) ; pas de lib de traduction ; pas de migration des textes user-facing du panneau (déjà en catalogue depuis 3.3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Log FR | coordinator/__init__, 7 sites | même niveau/params, texte EN naturel | la suite reste verte |
| Docstring/commentaire FR | 8 fichiers docstrings, 17 fichiers commentaires, panel JS | anglais naturel, même sens | grep heuristique vide après passe |
| ValueError FR servie | coordinator l.1816/1822/1825 | message EN ; l'appelant (service/websocket) voit l'anglais | tests épinglants mis à jour |
| Préfixe servi au panneau | ui_service l.849/858 | « custom mapping {key} » / « rule {key} » — les noms de règles restent des données | badge Cohérence/Périphériques rend le préfixe EN comme donnée (déviation plain-EN assumée par l'inventaire) |
| Fallback ws l.355/780/999/1011 | erreurs servies au panneau | texte EN | idem |
| Tests épinglant du FR | assertions sur les chaînes migrées | mises à jour vers l'EN, même compte de tests | suite verte |

</intent-contract>

## Code Map

- Source unique des sites : inventaire §5 (logs/docstrings/commentaires, comptes vérifiés ligne par ligne en 3.1) et §6 (chaînes servies). Fichiers commentaires py : coordinator (~43 lignes), light (17), entity (10), __init__, switch, cover, const, binary_sensor, climate, webhook, scene, select, api_proxy, + mapping_registry, mapping_rules, eedomus_client, sensor, config_flow (docstrings).
- `custom_components/eedomus/coordinator.py` — 5 logs FR + 9 docstrings + ~43 lignes de commentaires + 3 ValueError servies (l.1816/1822/1825).
- `custom_components/eedomus/__init__.py` — 2 logs FR (l.221/262) + commentaires.
- `custom_components/eedomus/ui_service.py` — 4 docstrings + commentaires + l.849/858 (préfixes servis) + l.355/780/999/1011 (fallbacks ws).
- `custom_components/eedomus/www/eedomus-panel.js` — ~54 lignes de commentaires FR ; la garde i18n ignore déjà les commentaires (machine à états) — la migration est neutre pour elle.
- `tests/unit/` — les tests épinglant les chaînes §6 migrées (rechercher les textes FR dans tests/ avant d'éditer chaque site).

## Tasks & Acceptance

**Execution:**
- [ ] Passe py fichier par fichier (logs, docstrings, commentaires — l'inventaire fait foi pour les sites)
- [ ] Chaînes §6 : coordinator ValueErrors + ui_service préfixes/fallbacks → EN
- [ ] `www/eedomus-panel.js` — commentaires FR → EN, aucun code touché
- [ ] Tests épinglants mis à jour (mêmes comptes)

**Acceptance Criteria:**
- Given le grep heuristique (accents/guillemets/lexique FR dans commentaires, docstrings et messages de log), when il tourne sur `custom_components/eedomus`, then il ne retourne plus de sites français (les valeurs user-data et les arbres de traduction exclus).
- Given la suite unitaire, when elle tourne, then elle est verte avec le même compte de tests (226) — seules les assertions des chaînes migrées ont changé de texte.
- Given un appelant de service ou le panneau, when coordinator/ui_service servent les chaînes §6, then il reçoit de l'anglais ; les noms de règles restent inchangés.

## Implementation Notes

Full route — subagent d'implémentation, l'inventaire en source unique. Décision d'inventaire assumée : les préfixes §6 sont plain-EN (données), pas ws-catalog — un utilisateur FR verra « Modifié par rule 7 » comme nom de règle ; c'est le comportement décidé en 3.1 et confirmé par l'inventaire. Le checkpoint validera ce point.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 226 verts (assertions migrées, compte identique)
- `node tests/js/test-coherence.js && node tests/js/test-i18n-guard.js` -- expected: verts (JS commentaires = neutre)
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: OK
- Grep heuristique FR sur custom_components/eedomus (hors arbres translations/, panel_translations, données user) -- expected: zéro site
</intent-contract>

## Review Triage Log

### 2026-10-05 — Review pass
- verdicts: 24 findings — high 0, medium 3, low 19, false 1, maybe-false 1 (graded low, unverified)
- findings:
  - `[low]` `[patch]` panel.js l.244/3836 : guillemets FR restants dans des commentaires citant le catalogue/l'historique — reformulés en anglais sans le texte français.
  - `[low]` `[patch]` sensor.py:200 : FR non accentué (« Espace libre ») dans un commentaire — reformulé en anglais, sens des données conservé.
  - `[low]` `[patch]` inventaire §5 : numéros de ligne dérivés par rapport à la baseline — ligne de statut ajoutée (« migrated in 3.5, enregistrement pré-migration »), comptes inchangés.
  - `[low]` `[patch — groupé]` inventaire §6 : sites fantômes (fallbacks ws déjà anglais à la baseline, seul l.613 était FR) — ligne de statut ajoutée.
  - `[low]` `[patch — groupé]` config_flow listé sans rien à migrer / options_flow édité non listé — couvert par la note d'état (l'inventaire devient l'enregistrement historique).
  - `[low]` `[reject]` extraction `host` = changement structurel dans une passe « sans logique » — préservé au comportement (garde hasattr maintenue, deletion check propre), exigé par la règle ≤88 ; documenté ici et dans le résultat.
  - `[medium]` `[defer]` ConfigEntryNotReady : message UI-facing HA pour toutes les locales, mécanisme natif de traduction existant (strings.json) non utilisé — path first-refresh non testé de surcroît ; reporté (voir deferred), candidat grammaire native.
  - `[low]` `[reject]` décision badge bilingue non enregistrée dans warnings/deferred — enregistrée au checkpoint (validée utilisateur), dans Implementation Notes, ce journal et le résultat ; deferred: est réservé aux findings de revue.
  - `[false]` `[reject]` date du plan « future » — l'horloge du relecteur était obsolète (date réelle : 2026-10-05) ; dates du plan correctes ; l'état du plan dans le diff précède la Finalize qui écrit les champs finaux.
  - `[medium]` `[patch]` branche `rule {key}` jamais exécutée par un test — règle sans nom ajoutée au fixture + épingle `modified_by_rule == "rule 42"`.
  - `[medium]` `[patch]` ValueErrors next_best_value sans couverture — TestNextBestValue ×3 messages anglais (226 → 229).
  - `[low]` `[defer]` grep d'acceptation sans liste d'exemptions documentée — la garde CI falsifiable est le livrable de 3.7 ; commande exacte + exclusions consignées dans le résultat.
  - `[low]` `[defer]` commentaires/labels FR dans tests/js/test-coherence.js — hors périmètre du ticket (custom_components/eedomus), divergence notée ; candidat 3.6.
  - `[false-as-claim]` `[patch via ligne de statut]` claim inventaire « docstring FR dans config_flow » — aucun français à la baseline ; note historique.
  - `[false-as-claim]` `[patch via ligne de statut]` claim inventaire « fallbacks ws FR l.355/780/999/1011 » — déjà anglais ; seul l.613 migré.
  - `[medium]` `[patch]` message d'erreur cohérence jamais observé par le test — épingle exacte ajoutée (11, "internal_error", "Failed to build the coherence view").
  - `[medium]` `[defer]` path first-refresh non testé (V4) — fusionné avec l'entrée deferred ConfigEntryNotReady.
  - `[low]` `[defer]` textes de log sans observateur automatisé (V5) — grep = gate proportionnée ; le pinning caplog serait brittle.
  - `[low]` `[reject]` §6 = « scope creep » sous lecture littérale (intent) — sanctionné par le checkpoint (validé utilisateur).
  - `[low]` `[reject]` asymétrie du poids de vérification (§6 épinglé, logs statiques) — converge avec le defer V5 ; le grep documenté est la gate.
  - `[low]` `[patch — même correctif]` citations résiduelles de valeurs catalogue dans les commentaires (intent) — couvert par le premier patch.
  - `[low]` `[patch — groupé]` références de plan périmées résolues en effet (intent) — note d'état inventaire.
  - `[low]` `[reject]` fichier de plan = artefact workflow hors produit (intent) — attendu, pas du produit.
  - `[low]` `[reject]` extraction host (intent, doublon) — voir ligne 6.
  - `[maybe-false→low]` `[reject]` « Created » incohérent — vérifié faux (horloge) ; gradé low car cosmétique au pire.

## Auto Run Result

Status: built

- Summary: passe EN complète livrée — 19 fichiers Python + panneau JS : 7 logs FR, 26 docstrings, tous les commentaires FR migrés en anglais naturel ; chaînes §6 servies migrées (3 ValueErrors coordinator, préfixes « custom mapping {key} »/« rule {key} » — décision plain-EN validée au checkpoint, noms de règles = données, message d'erreur cohérence) ; ConfigEntryNotReady migré (déviations déclarées, extraction host préservée au comportement).
- Files: coordinator.py, __init__.py, ui_service.py, light.py, entity.py, switch.py, cover.py, const.py, binary_sensor.py, climate.py, webhook.py, scene.py, select.py, api_proxy.py, mapping_registry.py, mapping_rules.py, eedomus_client.py, sensor.py, options_flow.py, www/eedomus-panel.js (commentaires), tests/unit/test_ui_service.py (+épingles rule 42 + message cohérence), tests/unit/test_history_value_resolution.py (+TestNextBestValue), i18n-inventory.md (notes de statut §5/§6).
- Review: 24 findings sur 4 lenses — 6 patchs appliqués (2 commentaires JS + 1 commentaire sensor.py résiduels FR, notes d'état inventaire, épingle règle sans nom, TestNextBestValue ×3, épingle message cohérence), 4 déférés (ConfigEntryNotReady grammaire native + path first-refresh, pinning de logs, labels FR tests/js, garde grep falsifiable → 3.7), 8 rejets motivés (1 réfutation d'horloge, décisions déjà enregistrées, artefacts workflow, doublons regroupés).
- Follow-up review: recommandé (3 mediums patchés, prouvés par mutation). Risque non vérifié nommé : le message ConfigEntryNotReady traduit et son path first-refresh ne sont observés par aucun test — une panne de setup live montrerait le nouvel anglais non vérifié ; à observer une fois en E2E ou dans le prochain changement coordinator-setup.
- Verification: pytest tests/unit/ -q → 229 passed (226 + 3 nouveaux) ; node test-coherence.js + test-i18n-guard.js verts (garde : 720 littéraux, 0 FR) ; node --check OK ; grep Unicode FR sur custom_components/eedomus (exclusions : translations/, panel_translations.py) → 4 lignes restantes = matchers de données d'exécution uniquement (binary_sensor « porte »/« fenêtre »/« fumée »/« présence », climate « arrêt »/« désactiver »), exclus par design.
- Residual: badge FR bilingue assumé (décision checkpoint) ; inventaire §5/§6 désormais enregistrement historique ; garde grep CI falsifiable = 3.7.
