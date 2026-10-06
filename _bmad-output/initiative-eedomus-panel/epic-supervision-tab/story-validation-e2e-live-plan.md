---
title: 'Validation E2E + live'
type: 'feature'
ticket: 5
created: '2026-10-06'
status: 'in-progress'
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
