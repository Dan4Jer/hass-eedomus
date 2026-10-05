---
title: 'Onglet Supervision : vue métriques + lien Cohérence'
type: 'feature'
ticket: 2
created: '2026-10-05'
status: done
route: 'full'
route_source: 'auto'
baseline_revision: '3b5745c3ea46cdd3cba048fc9497913dd6e15ae5'
review: 'thorough'
review_source: 'auto'
lenses_ran: [blind-hunter, edge-case-hunter, verification-gap, intent-alignment]
review_loop_iteration: 0
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/initiative-eedomus-panel/epic-supervision-tab/epic-supervision-tab.md
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Le panneau n'a pas de 5e onglet Supervision : les métriques de la box (temps de refresh, nombre de périphériques, sollicitations de l'API) ne sont visibles que dans les logs, et rien ne relie la vue aux tableaux de cohérence.

**Approach:** Un 5e onglet `supervision` branché sur l'architecture par onglet (TABS/nav/hash/mixin/STYLES), rendant des chart cards des métriques box alimentées par une commande websocket dédiée `eedomus/get_box_metrics` servie d'un tampon circulaire de cycles de refresh dans le coordinator ; graphiques en SVG inline thémé (variables CSS HA), chaque valeur doublée d'un équivalent textuel ; lien « Voir le tableau de cohérence » via `_setTab('coherence')`.

## Boundaries & Constraints

**Always:** l'onglet se branche exactement comme les autres (`TABS` shared.js:12, bouton nav `t('panel.tabs.supervision')`, branche `_renderTabContent`, branche lazy `set hass`, garde in-flight/génération, styles composés à l'entrée) ; la commande suit la recette 5 pièces (constante, dispatcher `@require_admin`/`@websocket_command`/`@async_response`, `WS_COMMANDS`, `ENDPOINT_DESCRIPTIONS`, handler `_json_safe`) ; les graphiques sont du SVG inline thémé par variables CSS uniquement — l'unknown est TRANCHÉ : aucun composant graphique du frontend HA n'est exposé dans le contexte du panneau (chunks esbuild internes, URLs hachées par version), la condition de repli de la spine UX est déjà remplie, pas de sonde runtime `customElements.get()` (rendu non déterministe interdit) ; chaque valeur métrique porte un équivalent textuel (texte lisible, jamais le graphique unique porteur) ; squelette au format du contenu attendu (cartes) puis état error + bouton Réessayer (`role="alert"`), jamais de carte à moitié chargée présentée comme complète ; tampon circulaire dans le coordinator (dernier N cycles : durée totale, api time, appels API eedomus du cycle — delta des compteurs cumulés, nombre de périphériques total/dynamique), alimenté à chaque `_async_update_data` ; multi-box agrégé comme `_collect_peripherals` (une section par box, entry_id porté) ; toutes les chaînes du catalogue `panel.supervision.*` + `panel.tabs.supervision` (EN source, FR, fixture `tests/fixtures/panel-catalog.json` synchronisée — drift = suite rouge) ; cibles ≥ 44 px, une colonne mobile / plusieurs desktop.

**Never:** pas d'import de chunk interne du frontend HA ni de lib de chart (toolchain interdit, vanilla) ; pas d'abonnement websocket ni de polling (un `callWS` par visite d'onglet + Réessayer, comme les autres onglets) ; pas de compteurs clés mortes servies comme données (`set_periph_value`, `partial_refresh` dans `_endpoint_timings`/`_endpoint_call_counts` ne sont jamais incrémentées) ; pas d'UI de la file de backfill (story 4.3) ; pas de touche aux contrats gelés au-delà du churn prévu (enregistrements 14→15 commandes) ; `translations/en.json`/`fr.json` intacts (pas de clés `panel.*` dedans) ; le tampon et la commande ne changent aucun comportement du refresh (capture passive).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Visite de l'onglet | tab supervision, hass présent | squelette (cartes), puis `callWS eedomus/get_box_metrics`, rendu des chart cards + équivalents textuels | erreur → message d'état + Réessayer |
| Tampon court | < N cycles collectés | cartes rendues avec les cycles disponibles, équivalent textuel exact ; N=0 → état vide positif nominatif | — |
| Lien Cohérence | clic « Voir le tableau de cohérence » | `_setTab('coherence')` → hash `#coherence`, onglet Cohérence chargé, retour/arrière fonctionnel | — |
| Deep link | URL `#supervision` avant `hass` | tab actif dès `_tabFromLocation`, chargement différé à l'arrivée de `hass` (branche `set hass`) | — |
| Multi-box | 2 coordinateurs | une section par box (entry_id + nom de box si disponible), métriques par box | aucune box → `service_unavailable` |
| Garde i18n | nouvelle clé user-facing hors catalogue | échec du scan | — |
| Cycle de refresh | chaque `_async_update_data` | le tampon capte le cycle (durées, delta d'appels, comptes) sans toucher au flux | exception captée → log warning, le refresh continue |

</intent-contract>

## Code Map

- `custom_components/eedomus/www/panel/shared.js` — `TABS` l.12 (source de vérité, hash = id d'onglet).
- `custom_components/eedomus/www/eedomus-panel.js` — entrée : imports l.23-38, mixins l.857-861, styles composés l.418/467-469, nav l.478-488, hash l.286-309, dispatch `_renderTabContent` l.804-853, lazy `set hass` l.118-141, init état l.106-115 (garde/génération à calquer), `_setTab` l.303-309 (précédent de lien interne : `_createRuleFor` l.799-802).
- `custom_components/eedomus/www/panel/historique.js` — modèle de module : `HISTORY_STYLES` l.9, `applyHistoriqueMixin` l.63, `_loadVersions` l.67-98 (callWS + garde + erreur + retry).
- `custom_components/eedomus/coordinator.py` — scalars existants `_last_refresh_time` l.96, `_last_api_time` l.94, `_endpoint_call_counts` l.121 (cumulatif, jamais reset, incrémenté l.702/713/724/982), comptes `_all_peripherals` l.1170, `self.data`, `_dynamic_peripherals` l.84/256/870 ; `_async_update_data` ~l.410-475 (point de capture du cycle) ; AD-2 : capture passive, aucune attente.
- `custom_components/eedomus/ui_service.py` — recette 5 pièces : constantes l.20-33, dispatcher `_ws_get_translations` l.241-257, `WS_COMMANDS` l.354-368, `ENDPOINT_DESCRIPTIONS` l.399-455, handler `_handle_get_backfill_state` l.1128-1148, `_collect_coordinators`/agrégat multi-box (déjà livrés par 4.1), `_json_safe` l.85-96.
- `custom_components/eedomus/panel_translations.py` — EN l.13 (source de vérité), FR l.206, tab labels EN l.15-18 / FR l.210-213 ; `get_panel_translations` l.420-437.
- `tests/fixtures/panel-catalog.json` — drift-checké contre `PANEL_TRANSLATIONS` (test_ui_service.py:1841-1851).
- `tests/unit/test_ui_service.py` — `test_registers_all_commands_once` l.58 (14 → 15), fixture `make_service` l.47.
- `tests/js/test-coherence.js` — harnais : mini-chargeur DFS sur les imports de l'entrée (charge supervision.js automatiquement), `_render` witness ; i18n guard scanne `www/**` récursivement.
- `EXPERIENCE.md` — ligne 31 (contrat onglet), 69 (repli SVG), 83 (squelettes cartes), 91 (erreur + Réessayer), 104 (lien hash), 119 (responsive), 133 (équivalents textuels).

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/coordinator.py` -- tampon circulaire `_metrics_history` (deque N=30) : à chaque `_async_update_data`, capter {ts, refresh_time, api_time, api_calls (delta des `_endpoint_call_counts` cumulés), periphs_total, periphs_dynamic} ; méthode `get_box_metrics()` rendant les cycles + les scalars courants ; capture passive (try/except → warning, jamais d'interruption du refresh) -- la série temporelle qui n'existe nulle part ailleurs
- [ ] `custom_components/eedomus/ui_service.py` -- commande `eedomus/get_box_metrics` (recette 5 pièces, agrégation multi-box par `_collect_coordinators`, une section par box avec entry_id) -- la source de données de l'onglet
- [ ] `custom_components/eedomus/www/panel/supervision.js` -- nouveau module : `SUPERVISION_STYLES` + `applySupervisionMixin` ; état in-flight/génération ; `_loadMetrics` (callWS + erreur + retry) ; `_renderSupervisionTab` (squelette, cartes : SVG line/bar thémé variables CSS, équivalents textuels par valeur, état vide, lien Cohérence `_setTab('coherence')`) -- la vue CAP-9 (métriques + lien, sans la file 4.3)
- [ ] `custom_components/eedomus/www/panel/shared.js` + `www/eedomus-panel.js` -- brancher le 5e onglet : `TABS` + import/mixin + `${SUPERVISION_STYLES}` + bouton nav + branche `_renderTabContent` + branche `set hass` + init état -- l'onglet vit dans l'architecture existante
- [ ] `custom_components/eedomus/panel_translations.py` + `tests/fixtures/panel-catalog.json` -- clés `panel.tabs.supervision` + namespace `panel.supervision.*` (titre, cartes, labels de séries, équivalents textuels, vide, erreur, squelette aria, lien cohérence) en EN et FR, fixture synchronisée -- garde i18n verte
- [ ] `tests/unit/test_box_metrics.py` -- nouveau : capture de cycle alimente le tampon (N max respecté, delta d'appels correct), `get_box_metrics` rend la série + scalars, capture passive (exception → refresh non interrompu), handler websocket (payload par box, service_unavailable sans coordinator, _json_safe)
- [ ] `tests/unit/test_ui_service.py` -- étendre `test_registers_all_commands_once` 14→15 -- churn prévu
- [ ] `tests/js/test-coherence.js` -- assertions supervision : squelette au premier rendu de l'onglet, rendu des cartes avec des métriques factices (texte équivalent présent), lien Coherence déclenche `_setTab('coherence')` -- le harnais couvre le nouveau module

**Acceptance Criteria:**
- Given l'onglet supervision visité avec hass, when les métriques arrivent, then les chart cards se rendent (SVG thémé) et chaque valeur métrique est lisible en texte — le graphique n'est jamais l'unique porteur.
- Given la commande échoue, when l'onglet rend, then message d'état `role="alert"` + bouton Réessayer, aucune carte à moitié chargée.
- Given le clic sur « Voir le tableau de cohérence », when le lien s'exécute, then l'onglet Cohérence s'active, le hash devient `#coherence`, retour/arrière fonctionnels.
- Given N cycles de refresh écoulés, when `get_box_metrics` est appelé, then la série rend les cycles (N max tampon), le delta d'appels API par cycle est exact, et l'agrégation porte chaque box avec son entry_id.
- Given la garde i18n, when le scan tourne, then aucune chaîne user-facing en dur (catalogue EN+FR+fixture synchronisés).
- Given les suites, when les tests tournent, then unitaires verts (tampon, commande, contrats 15), harnais node vert (module chargé, onglet rendu), E2E collect inchangé.

## Implementation Notes

Full route — unknown tranché par recon : AUCUN composant graphique HA n'est exposé au contexte du panneau (chunks esbuild internes, URLs hachées par version) ; SVG inline thémé direct, sans sonde runtime (rendu déterministe). « Sollicitations de l'API proxy » = appels API eedomus par cycle (delta des compteurs cumulés `_endpoint_call_counts`) — le webhook `api_proxy.py` n'a aucun compteur et n'est pas « de la box ». Les clés mortes (`set_periph_value`, `partial_refresh`) ne sont pas servies. Le panneau ne s'abonne à rien : un callWS par visite + Réessayer (pattern des autres onglets).

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: tous verts (nouvelles commandes + tampon + contrats 15)
- `node tests/js/test-coherence.js && node tests/js/test-i18n-guard.js` -- expected: verts (module supervision chargé par le mini-chargeur, aucune chaîne en dur)
- `python3 -m pytest tests/e2e/ --collect-only -q` -- expected: 27 collectés
</intent-contract>

## Review Triage Log

### 2026-10-05 — Review pass (thorough: blind-hunter, edge-case-hunter, verification-gap, intent-alignment)
- verdicts: 29 findings — high 0, medium 13, low 13, false 1, maybe-false 0 (2 intent notes ratified)
- findings:
  - `[medium]` `[patch]` (blind) fallback `client.host` mort (le client stocke `api_host`, eedomus_client.py:75) — P1 : api_host d'abord, le test assert api_host.
  - `[medium]` `[patch]` (blind, verif) cycles timeout absents de la série — lecture RATIFIÉE : un cycle timeout n'est pas un cycle complété (retour de données dernier-connu, pas d'échec HA) ; P6 : test épinglant l'exclusion + commentaire au site de capture.
  - `[low]` `[patch]` (blind) carte Périphériques mélangeant les bases temporelles (box.periphs_dynamic vs last) — P4 : last.periphs_dynamic du cycle.
  - `[low]` `[patch]` (blind) scalars servis jamais rendus (last_refresh_time, api_calls_total…) — P2 : payload réduit à {entry_id, name, cycles}.
  - `[medium]` `[patch]` (blind) valeurs non finies forcées à 0 (creux faux sur le graphe) — P4 : supervisionCycleSeries filtre, série vide = pas de graphe.
  - `[medium]` `[patch]` (blind) erreur double-t() (message anglais brut passé dans t(), {tokens}) — P4 : _metricsErrorDetail rendu échappé sans t().
  - `[low]` `[patch]` (blind) getattr défensif mort _last_api_time — disparu avec la coupe P2.
  - `[medium]` `[patch]` (blind) nav 5 onglets sans wrap (débordement ~360px, contrat mobile rompu) — P5 : flex-wrap.
  - `[low]` `[patch]` (blind) preserveAspectRatio="none" déforme traits et barres — P4 : supprimé (meet par défaut).
  - `[low]` `[patch]` (blind) magic 30 dupliqué code/test — P1 : METRICS_BUFFER_SIZE constant partagé.
  - `[low]` `[reject]` (blind) artefact plan avec cases non cochées — le fix édite le plan ; le frontmatter est l'état vivant, les cases sont un artefact de planification.
  - `[low]` `[patch]` (blind) aucun test de rendu multi-box côté harnais — P6 : deux sections .supervision-section.
  - `[low]` `[patch]` (blind) supervisionMetricCardHtml interpole sans échapper (trou XSS latent) — P4 : escapeHtml à la frontière ; deux assertions existantes mises à jour (`l&#39;API` — conséquence honnête de l'échappement).
  - `[medium]` `[patch]` (blind) chemin err.message brut non testé — P6 : test du rendu échappé sans double traduction.
  - `[medium]` `[patch]` (edge) poison baseline : baseline None ou total cumulé inférieur → delta = total cumulé non borné — P1 : api_calls = 0 dans ces cas ; test poison ajouté.
  - `[medium]` `[patch]` (edge) un coordinator levant dans le walk → internal_error, toutes les box perdues — P3 : garde par box (skip + warning), internal_error seulement pour l'échec du walk lui-même.
  - `[low]` `[patch]` (edge) box sans nom ni entry_id → « Box  » vides indiscernables — P4 : « Box #N » par index via panel.supervision.box.fallback (EN/FR, fixtures).
  - `[medium]` `[patch]` (verif, pré-vérifié) branche full-refresh non testée (tous les tests forcent _full_refresh_needed=False) — P6 : test de capture full-refresh.
  - `[medium]` `[patch]` (verif, pré-vérifié) exclusion timeout non épinglée — groupé avec B2, P6.
  - `[medium]` `[patch]` (verif, pré-vérifié) branche internal_error du handler sans test — P6 (avec la garde P3, adapté au walk).
  - `[low]` `[patch]` (verif, pré-vérifié) branche no-service du dispatcher non testée — P6 : miroir du test _ws_get_translations.
  - `[medium]` `[patch]` (verif, pré-vérifié) reconnaissance deep-link #supervision sans test (retrait silencieux de TABS = suite verte) — P6 : _tabFromLocation rend supervision depuis le hash.
  - `[medium]` `[patch]` (verif, pré-vérifié) garde in-flight/génération de _loadMetrics sans test de concurrence — P6 : test de supersession (miroir du lifecycle cohérence).
  - `[low]` `[patch]` (verif, other) getattr incohérent — dup B7, disparu avec P2.
  - `[low]` `[reject]` (verif, other) fixture cycles de longueur 2 seulement — helpers purs couvrent les formes vides/plates ; résiduel marginal.
  - `[ratifié]` (intent) surface conditionnelle « composants HA quand disponibles » inexistante au runtime — settlement plan-time (A2) : rien n'est exposé au contexte du panneau, la spine UX impose le repli, la sonde runtime est interdite (non-déterminisme) ; consigné au plan.
  - `[ratifié]` (intent) « sollicitations de l'API proxy » = appels API eedomus par cycle (B2) — le webhook api_proxy.py n'a aucun compteur et n'est pas « de la box » ; nommé au plan.
  - `[low]` `[reject]` (intent) verify à distance (chaînes template vs DOM, _setTab stubbé) — philosophie de harnais constante du repo ; la surface navigateur est couverte par E2E live + validation visuelle au déploiement.
  - `[false]` (intent) churn mécanique (compteur 28→30, panel-keys.json) — conséquence directe des surfaces de comptage existantes, aucune divergence de comportement.

Patches P1-P6 appliqués par impl-42-supervision (tour 2), re-vérifiés indépendamment (324 unitaires). Pas d'intent_gap, pas de bad_plan.

## Auto Run Result

**Route:** full — recon par subagent (unknown tranché : SVG inline thémé, aucun composant graphique HA exposé au panneau), impl par subagent, review thorough 4 lens, triage, 6 groupes de patchs, re-vérif.

**Vérifications exécutées (orchestrateur, 2026-10-05) :**
- `python3 -m pytest tests/unit/ -q` — 324 passed (317 pré-patch, +7 de la passe de patchs)
- `node tests/js/test-coherence.js` — exit 0 (module supervision chargé par le mini-chargeur, multi-box, deep-link, supersession)
- `node tests/js/test-i18n-guard.js` — 795 littéraux / 7 fichiers, 158 clés catalogue, aucun texte en dur
- `python3 -m pytest tests/e2e/ --collect-only -q` — 27 collectés
- Audit de matrice : les 7 lignes de la matrice I/O ont chacune leurs tests, tous passés (visite onglet/squelette, tampon court/vide, lien cohérence, deep link, multi-box, garde i18n, capture passive de cycle).

**Contrats gelés :** rows coherence/peripherals intacts ; 15 commandes enregistrées (churn prévu 14→15 + compteur endpoints 28→30) ; translations/en.json+fr.json intacts ; catalogue EN+FR+fixtures synchronisés (158 clés).

**Post-déploiement :** à consigner après validation live.

**Post-déploiement (2026-10-06, 00:17-00:22 CEST) :**
- Déployé via `deploy_hass_eedomus.sh` (git-only, unstable @ 9b5e619), restart HA, ~2 min d'attente
- Fichiers servis (HTTP 200) : `panel/supervision.js` (nouveau), `panel/shared.js` mis à jour
- `python3 -m pytest tests/e2e/ -q` sur le Pi : **27 passed in 61.48s**
- Logs post-restart : « Eedomus integration initialized successfully », drain normal (PARTIAL REFRESH, 5 periphs importés ce cycle) ; aucune erreur liée à la capture métriques ni à la commande get_box_metrics
- Validation visuelle (utilisateur, 2026-10-06) : conforme — nav à 5 onglets, cartes et équivalents textuels, lien Cohérence ; ticket marqué done
