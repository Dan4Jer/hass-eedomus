---
title: 'Validation E2E + live'
type: 'feature'
ticket: 5
created: '2026-10-06'
status: 'built'
route: 'oneshot'
route_source: 'auto'
baseline_revision: '3fe01eb29299cc7c116154dc586d4579faa89c9d'
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

**Problem:** La suite E2E live ne couvre pas encore les surfaces livrées par l'épique Supervision (4.1-4.3) : l'état de la file de backfill et les métriques box ne sont vérifiés ni par websocket ni sur l'instance déployée.

**Approach:** Étendre `tests/e2e/test_e2e_panel.py` de deux tests live NON destructifs (lectures websocket uniquement, aucune des quatre actions n'est exercée sur l'instance réelle) : `eedomus/get_backfill_state` (forme de la file + des ignorés + état global, file réelle non vide — 157 periphs en attente mesurés) et `eedomus/get_box_metrics` (une section par box, tampon de cycles rempli après les refreshs). Puis déployer sur le Pi et valider : suite E2E complète verte sur l'instance déployée (la boucle dynamique des modules servis s'exerce alors réellement), contrôle visuel des graphiques et de la file par l'utilisateur.

## Boundaries & Constraints

**Always:** lectures websocket uniquement (`get_backfill_state`, `get_box_metrics`) — JAMAIS d'action (retry_now, prioritize, set_paused, set_ignored) sur l'instance réelle (non destructif, les actions sont vérifiées visuellement par l'utilisateur) ; les asserts vérifient la FORME (clés de lignes : periph_id, name, status, position, entry_id ; cycles : ts, refresh_time, api_time, api_calls, periphs_total, periphs_dynamic) et les invariants réels (file non vide, cycles non vides) ; la suite tourne ensuite intégralement sur le Pi déployé (29 attendus) ; validation visuelle consignée.

**Never:** aucune mutation de l'instance réelle (pas d'action backfill, pas de save_mapping supplémentaire au-delà de l'existant) ; aucun changement au backend ni au panneau (l'épique est livré) ; pas de nouveau test unitaire (la couverture unitaire est faite).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| État de la file live | ws get_backfill_state | queue non vide (≈157), chaque ligne porte ses clés, statut dans les 5 tokens, ignored liste, global_paused bool | échec loud si vide ou clé manquante |
| Métriques live | ws get_box_metrics | boxes ≥ 1, chaque box : entry_id, name, cycles non vide après les refreshs, clés de cycle complètes | échec loud si tampon vide |

</intent-contract>

## Implementation Notes

Oneshot — la surface livrée par 4.1-4.3 est testée unitairement et par harnais ; ce ticket ajoute les deux lectures live manquantes et porte la validation de fin d'épique (déploiement + suite verte + contrôle visuel utilisateur). La boucle E2E des modules servis est déjà dynamique (4.4) : elle s'exerce pour de vrai sur le Pi. Le contrôle visuel porte sur les graphiques (cartes métriques) et la file (157 lignes attendues, interrupteur global, 4 actions, Ignorer deux gestes — sans nécessairement tout exécuter).

## Verification

**Commands:**
- `python3 -m pytest tests/e2e/ --collect-only -q` -- expected: 29 collectés (27 + 2)
- `python3 -m pytest tests/unit/ -q` -- expected: 324 verts inchangés
- Post-déploiement : `python3 -m pytest tests/e2e/ -v` sur le Pi -- expected: 29 verts, dont la boucle dynamique des 7 modules servis
</intent-contract>

## Review Triage Log

### 2026-10-06 — Review pass (quick, inline — route oneshot)
- verdicts: 3 findings — high 0, medium 2, low 1, false 0
- findings:
  - `[medium]` `[patch]` (live) course reload → tampon vide : le test métriques échouait quand il tombait juste après le reload d'entrée (restart-cycle des tests OptionsFlow) — le tampon ne se remplit qu'à la FIN du premier cycle (~10 s) — patch : retry borné (6 × 5 s) sur le remplissage du tampon.
  - `[medium]` `[patch]` (live) course reload → AUCUN coordinator : pendant la fenêtre de reload, la commande rend service_unavailable et ws_call lève immédiatement au lieu de retenter — patch : try/except AssertionError dans les deux boucles de retry (fenêtre plus courte qu'un cycle).
  - `[low]` `[ratifié]` la file dérive de _history_progress rechargé au first refresh : même fenêtre → même blinding appliqué au test file (cohérence, la course n'a pas été observée sur ce test).

Patches appliqués en direct par l'orchestrateur (impl oneshot), re-vérifiés : suite E2E complète **29 passed × 2 passes consécutives** sur le Pi.

## Auto Run Result

**Route:** oneshot — impl directe (orchestrateur), review quick inline, 2 courses de rechargement traitées.

**Vérifications exécutées (2026-10-06, 04:05-04:24 CEST) :**
- `python3 -m pytest tests/e2e/ --collect-only -q` — 29 collectés (27 + 2)
- `python3 -m pytest tests/unit/ -q` — 324 verts inchangés
- Déployé via `deploy_hass_eedomus.sh` (git-only, unstable @ f96a9f7), restart HA
- `python3 -m pytest tests/e2e/ -q` sur le Pi : **29 passed in 62.53s** puis **29 passed in 59.43s** (2 passes complètes consécutives, courses de reload couvertes)
- La boucle dynamique des modules servis s'est exercée réellement contre le Pi (7 modules + marqueurs, incl. coherence-helpers.js nouveau et supervision.js)
- État live vérifié : file non vide (157 periphs en attente), tampon métriques rempli (cycles de FULL et PARTIAL REFRESH), aucune action exercée sur l'instance réelle (non destructif)
- Logs : intégration initialisée proprement, aucun échec de capture métriques

**Post-déploiement :** le contrôle visuel des graphiques et de la file par l'utilisateur (Done when #5) est demandé au HALT built — l'onglet Supervision est déployé (attention cache navigateur : rechargement forcé nécessaire après déploiement).
