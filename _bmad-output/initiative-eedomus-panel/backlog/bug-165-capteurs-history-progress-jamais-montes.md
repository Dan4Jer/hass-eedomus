---
id: 109
type: bug
title: "165 capteurs « History Progress » jamais montés + champs de progression fantômes"
parent: none
covers: ["CAP-5"]
after: []
assignee: ""
refined: false
hitl: false
risk: medium
severity: P2
---

# 165 capteurs « History Progress » jamais montés + champs de progression fantômes

## Description

Les 165 capteurs diagnostiques « History Progress » (`sensor.<entry>_eedomus_history_progress_*`) sont tous `unavailable` sans attribut sur l'instance live : ils n'ont jamais été montés, et même montés ils liraient des champs que le backfill n'écrit jamais. La progression réelle ne vit que dans les entités helper `eedomus.history_progress_*` (last_timestamp + completed). L'utilisateur attend de voir la progression de récupération d'historique dans les données des entités HA correspondantes (vérification live 2026-10-07).

## Reproduction

1. Ouvrir les états des entités `sensor.*history_progress*` de l'entrée eedomus.
2. Actual : les 165 sont `unavailable`, aucun attribut. Expected : chaque capteur affiche son pourcentage de progression et ses attributs (points récupérés, total estimé, dernier timestamp, completed).

## Given/When/Then

- Given l'option history activée, when l'intégration démarre, then `async_setup_history_sensors` retourne des capteurs qui sont réellement montés sur la plateforme (le retour n'est plus jeté — `async_add_entities` ou affectation de `coordinator._history_sensors` consommée par `sensor.py`).
- Given le backfill qui importe des points pour un périphérique, when un chunk est traité, then le coordinator écrit `retrieved_points` (cumul réel importé) et `total_points` (estimation marquée : fenêtre de rétention × densité) dans `_history_progress` — les clés lues par les capteurs existent.
- Given un capteur monté et vivant, when l'utilisateur l'ouvre, then le % reflète la progression réelle (0 → 100 en cours de backfill, 100 à completed) et les attributs portent les 4 champs.

## Cause Analysis

Triple défaut : (1) `async_setup_history_sensors` (`history_sensor.py:209`) retourne la liste des capteurs, mais les appelants (`__init__.py:425`, `:456`) jettent la valeur de retour — jamais montés ; (2) `sensor.py:167` ajouterait `coordinator._history_sensors` si l'attribut existait — personne ne l'assigne ; (3) `EedomusHistoryProgressSensor` lit `total_points`/`retrieved_points` que le coordinator n'écrit jamais (le % resterait à 0). Le résumé : la plateforme est du code mort depuis la restructuration backfill, et les 165 entités du registry restent `unavailable`.

## References

- code — custom_components/eedomus/history_sensor.py:209 (retour non consommé), :87-91 (lecture des clés fantômes)
- code — custom_components/eedomus/__init__.py:423-425, 453-456 (appelants qui jettent le retour)
- code — custom_components/eedomus/sensor.py:167-168 (la branche `_history_sensors` jamais vraie)
- spec — _bmad-output/specs/spec-eedomus-history/SPEC.md (CAP-5 étendu : champs de progression servis par get_backfill_state — décision 2026-10-07 : les deux mesures, total ESTIMÉ)
- ux — EXPERIENCE.md update run 4 (indicateur de progression barre + texte)

## Notes

- Décision utilisateur 2026-10-07 : RÉPARER les capteurs (pas supprimer la plateforme) ; l'indicateur du panneau mesure les DEUX — couverture temporelle ET % de points avec total estimé marqué comme estimation.
- À coordonner avec l'épique history-backfill 1.4 (« Tâche de fond et progression .storage scopée », planned) qui touche la même progression — la réparation doit précéder ou s'y fusionner.
- Décision utilisateur 2026-10-08 : FUSION dans epic-history-backfill 1.4 (écriture des champs retrieved_points/total_points ESTIMÉ, exposition get_backfill_state + get_coherence, remontée des capteurs) ; le rendu panneau (barre + texte, file Supervision et détail Cohérence) est la story 110 du backlog panel. Le bug sera fermé à la livraison de 1.4. Vérification live 2026-10-08 : aucun champ de progression servi, capteur Sonoff `unavailable`, aucun rendu dans www/panel/ — la validation de l'indicateur était impossible avant cette livraison.
