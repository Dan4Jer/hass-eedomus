---
type: initiative
title: "Historique eedomus vivant dans Home Assistant"
parent: none
covers: [CAP-1, CAP-2, CAP-3, CAP-4]
after: []
assignee: ""
risk: high
status: done
---

# Historique eedomus vivant dans Home Assistant

## Description

L'historique cloud eedomus — des années de mesures — existe dans Home Assistant sous forme de statistics horaires, sans jamais pénaliser le temps réel ni polluer le recorder. Le spec `spec-eedomus-history` possède les capacités, contraintes et non-goals ; le spine d'architecture (companion du spec) possède les décisions techniques. Cette initiative les livre.

## Outcome

L'utilisateur consulte dans HA l'historique long-terme de ses capteurs eedomus au-delà de la date d'installation — le success signal du spec est la mesure.

## Done when

1. Les graphs long-terme des capteurs eedomus remontent au-delà de la date d'installation HA.
2. Un cycle de partial refresh reste ~1 s pendant un backfill complet (log décomposée).
3. Aucune entité ni statistic fantôme `sensor.eedomus_*` ne subsiste dans HA.
4. Le recorder HA persiste à nouveau states, events et statistics (verrou réparé).

## Boundaries

Le sous-système history de l'intégration (fetch, import, progression), le options flow et la documentation. Pas le panel de configuration (discussion #28), pas de nouveau frontend — voir les non-goals du spec.

- Touch point: scripts legacy scp (`deploy_history_fix.sh`, `deploy_and_analyze.py`) — à supprimer hors de tout epic ; owner: epic-history-backfill

## References

- spec — _bmad-output/specs/spec-eedomus-history/SPEC.md
- constraint — le même spec, section Constraints (AD-1..4, 6, 8, 11 cités)
- architecture — _bmad-output/planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md

## Notes

- Decision: réparation recorder via option 1 — maintenance WAL à froid, pas de base neuve (décision utilisateur, 2026-09-27).
- Unknown: durée réelle de la première activation (volume par périph inconnu) ; mesurée au dernier ticket de l'epic.
