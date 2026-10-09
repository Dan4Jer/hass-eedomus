---
id: 112
type: story
title: "Indicateurs de récupération d'historique dans l'onglet Supervision (si l'option est active)"
parent: none
covers: ["CAP-9"]
after: []
assignee: ""
refined: false
hitl: false
risk: low
---

# Indicateurs de récupération d'historique dans l'onglet Supervision (si l'option est active)

## Description

Une rangée de cartes dédiée au backfill s'ajoute à la zone métriques de l'onglet Supervision, rendue **uniquement si l'option history est active** (le payload porte un `history_enabled`). Quatre indicateurs agrégés, calculés côté backend depuis `_history_progress` + la file dérivée :

1. **Complétion globale** (gauge) : X/Y périphériques éligibles complétés (éligibles non ignorés ; Y = éligibles, X = complétés).
2. **Points agrégés** (valeur) : Σ retrieved_points / Σ total_points, le second marqué « estimé » (AD-6bis : l'estimation est fenêtre now−creation_date × 1/POLLING).
3. **Couverture temporelle** (valeur) : « données remontant jusqu'au JJ/MM/AAAA » — le plus ancien `oldest_timestamp` récupéré, tous périphs confondus.
4. **Santé de la file + ETA** (valeur) : en attente / en erreur, et ETA = pending × (intervalle worker / quota par passe).

Composants : les cartes existantes (`metric-value-card` pour la gauge et les valeurs, aucun nouveau composant visuel). Toute microcopie via le catalogue websocket (EN+FR+fixtures). Même discipline d'accessibilité : équivalent textuel obligatoire, jamais la couleur seule.

## Acceptance Criteria

1. **Rangée conditionnelle**
   Given l'option history désactivée, when l'onglet Supervision se rend, then la rangée n'apparaît pas
   Given l'option activée, then la rangée rend avec ses quatre cartes
2. **Complétion**
   Given 10 périphs éligibles dont 4 complétés, when la gauge se rend, then elle affiche 4/10 (40 %) avec son équivalent textuel
3. **Points agrégés**
   Given des periphs avec retrieved/total variés (dont total inconnu), when la valeur se rend, then elle affiche Σ retrieved / Σ total estimé, les periphs sans estimation exclus du dénominateur, le marqueur « estimé » présent
4. **Couverture temporelle**
   Given au moins un periph avec un oldest_timestamp, when la valeur se rend, then elle affiche la date la plus ancienne récupérée ; aucun oldest → l'état vide honnête, jamais une fausse date
5. **File + ETA**
   Given 12 pending et 2 en erreur avec quota 1/passe/60 s, when la valeur se rend, then elle affiche 12 en attente / 2 en erreur et un ETA (~12 h) ; file vide → « tout est récupéré » positif
6. **i18n**
   Toutes les nouvelles chaînes via le catalogue, la garde de parité reste verte

## References

- ux — _bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md (rangée de récupération, update run 2026-10-09)
- spec — _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md (CAP-9, rangée d'indicateurs conditionnelle)
- code — custom_components/eedomus/coordinator.py (_history_progress, get_backfill_state), custom_components/eedomus/www/panel/supervision.js (cartes)

## Notes

- Décisions utilisateur 2026-10-09 : les quatre indicateurs retenus (complétion, points, couverture, file+ETA), tickettage sans build immédiat.
- Source de données : tout existe déjà (l'agrégation est un pur calcul backend — pas de nouvelle collecte).
- L'ETA suppose la cadence worker constante (BACKFILL_WORKER_INTERVAL / quota) ; les periphs en pause sont exclus du calcul pending.
