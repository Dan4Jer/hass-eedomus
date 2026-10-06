---
type: epic
title: "Simulateur eedomus — strate E2E multi-box et destructive"
parent: initiative-eedomus-panel
covers: [CAP-1, CAP-2, CAP-3, CAP-4, CAP-5]
after: []   # l'épique Supervision (4) est done ; aucune dépendance dure
assignee: ""
risk: medium
---

# Simulateur eedomus — strate E2E multi-box et destructive

## Description

Le multi-box et les actions destructives du backfill sont architecturalement intestables : la strate E2E live (le Pi, jamais mockée — AGENTS.md) est mono-box et interdit l'exercice des actions destructives sur la box réelle. Le salvage ciblé de la PR #119 (fmo01 — simulateur Flask d'API eedomus + outillage d'extraction/anonymisation, base pré-BMAD donc non mergeable) apporte la pièce manquante : une 2e strate E2E fondée sur un simulateur d'API local, validée AD-16 (revue architecture 2026-10-06). Le spec `spec-eedomus-simulator` (5 CAPs) possède les capacités et les contraintes — dont la passe de vie privée obligatoire avant tout commit de dump.

## Outcome

Un E2E-sim ajoute une 2e box simulée sur l'instance via la config flow réelle, en voit les 69 entités, exécute les 4 actions backfill destructives dessus — et la suite live-Pi reste verte et inchangée (success signal du spec).

## Requirements

- CAP-1: Simulateur d'API eedomus local — serve les endpoints de la config flow et des entités depuis un dump JSON, auth, ports multiples, injection de changement. (spec-eedomus-simulator, Capabilities)
- CAP-2: Historique synthétique — `periph.history` déterministe, chunking conforme client. (spec-eedomus-simulator, Capabilities)
- CAP-3: Ajout d'une box simulée dans HA — 2e config entry via la config flow réelle, cycle de vie propre. (spec-eedomus-simulator, Capabilities)
- CAP-4: Strate E2E simulateur — multi-box + actions destructives, distincte de la strate live-Pi. (spec-eedomus-simulator, Capabilities)
- CAP-5: Outils d'extraction/anonymisation — enrichissement des jeux de données, vie privée obligatoire. (spec-eedomus-simulator, Capabilities)

## Done when

1. La config flow de HA crée une 2e entry pointant vers le simulateur et les entités du dump apparaissent — sans code d'intégration modifié.
2. Le backfill d'une box simulée importe des statistics horaires via le chemin production (CAP-2 vérifié en E2E-sim).
3. Les 4 actions backfill s'exercent de bout en bout sur la box simulée ; l'entry disparaît proprement après le test.
4. La strate live-Pi reste verte et inchangée ; AGENTS.md porte la règle deux strates (AD-16).
5. Le dump commité a passé la passe de vie privée complète.

## Boundaries

L'infrastructure de test. Pas de merge de la PR #119 au-delà du salvage, pas de HA conteneurisé en CI (backlog 101), pas de simulation du temps réel push ni du fallback PHP, pas de simulation du webhook proxy — voir les non-goals du spec.

## References

- spec — _bmad-output/specs/spec-eedomus-simulator/SPEC.md (CAP-1..CAP-5 ; companion: spec-eedomus-history)
- architecture — décision AD-16 (revue architecture 2026-10-06, validée utilisateur) : deux strates E2E, live-Pi = vérité de régression
- pr — PR #119 (fmo01) : source du salvage — scripts/simulateur/ (simulator.py, 00/01/02, README, dump 69 periphs anonymisé)

## Notes

- Decision: placement tout dans scripts/simulateur/ comme la PR ; runtime Flask (requirements-test uniquement) ; dump fmo01 adopté après passe de vie privée complète (décisions utilisateur 2026-10-06, dans le memlog du spec).
- Decision: plan_checkpoint sur l'entrée 3 (harnais box simulée — cycle de vie d'une config entry sur l'instance live, risque high).
- Unknown: mécanisme de suppression propre de l'entry simulée (API config entries vs nettoyage manuel) — tranché à l'entrée 3 (open question du spec).
- Unknown: profondeur N (années) et densité de l'historique synthétique — fixées au premier E2E backfill mesuré (entrée 5, open question du spec).
- Waits on nothing: l'épique est indépendant des épiques done ; l'instance live doit simplement être joignable depuis la machine tenant le simulateur.
