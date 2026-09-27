---
type: epic
title: "Backfill d'historique eedomus en statistics horaires"
parent: initiative-eedomus-history
covers: [CAP-1, CAP-2, CAP-3, CAP-4]
after: []
assignee: ""
risk: high
---

# Backfill d'historique eedomus en statistics horaires

## Description

L'historique cloud eedomus des capteurs numériques est importé dans les statistics horaires HA via les APIs officielles, en tâche de fond, avec reprise et idempotence — sans écrire un seul état passé dans la state machine. Le temps réel redevient et reste ~1 s en toutes circonstances.

## Outcome

L'utilisateur voit dans les graphs long-terme HA l'historique de ses capteurs eedomus antérieur à l'installation — le success signal du spec.

## Requirements

- CAP-1: Importer tout l'historique cloud des capteurs numériques en statistics horaires, sans toucher la state machine. (spec-eedomus-history, Capabilities)
- CAP-2: Le backfill ne ralentit jamais le rafraîchissement temps réel. (spec-eedomus-history, Capabilities)
- CAP-3: Interruption, redémarrage, re-import sans perte ni doublon. (spec-eedomus-history, Capabilities)
- CAP-4: L'activation de l'option est documentée, première activation incluse. (spec-eedomus-history, Capabilities)

## Done when

1. L'import passe exclusivement par `async_import_statistics` en Python (aucun service, aucun `async_set`), horizon AD-11 respecté.
2. Le backfill intégral d'un capteur numérique est visible en graph long-terme au-delà de l'installation HA.
3. Après un redémarrage HA en cours de backfill, la reprise repart de la progression persistée — pas depuis zéro.
4. Un partial refresh reste ~1 s pendant un backfill complet (log décomposée `API / History / Processing`).
5. La doc d'activation décrit comportement, durée, reprise et visibilité.
6. La suite E2E couvre le history et la validation production est passée.

## Boundaries

Le sous-système history (fetch, import, progression), le options flow et la documentation. Pas le panel (#28), pas les états discrets, pas les états bruts — non-goals du spec.

## References

- parent — _bmad-output/initiative-eedomus-history/initiative-eedomus-history.md
- spec — _bmad-output/specs/spec-eedomus-history/SPEC.md, sections Capabilities, Constraints et Non-goals
- architecture — _bmad-output/planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md (AD-1..6, 8, 11)

## Notes

- Decision: réparation recorder = option 1, maintenance WAL à froid (décision utilisateur, 2026-09-27) ; exécutée au ticket 1.
- Unknown: durée réelle de la première activation ; mesurée au ticket 6 pour la doc (boucle avec le ticket 5 si l'estimation diverge).
- Decision: build en bmad-build interactif — raffinement des critères pendant le build, pas de checkpoints unattended requis (décision utilisateur, 2026-09-27).
- Tracer bullet: le ticket 2 livre un capteur de température visible en graph long-terme, bout en bout.
