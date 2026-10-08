---
id: 110
type: story
title: "Indicateur de progression backfill (barre + texte) : file Supervision et détail Cohérence"
parent: none
covers: ["CAP-9"]
after: []
assignee: ""
refined: false
hitl: false
risk: medium
---

# Indicateur de progression backfill (barre + texte) : file Supervision et détail Cohérence

## Description

Une fois les champs de progression servis par le backend (epic-history-backfill 1.4 : `retrieved_points`, `total_points` ESTIMÉ, plus ancien timestamp récupéré, début de rétention — dans `eedomus/get_backfill_state` ET `eedomus/get_coherence`), le panneau rend l'indicateur aux deux surfaces spécifiées (spine UX update run 4) : une ligne par périphérique dans la file de l'onglet Supervision, et le détail périphérique de la Cohérence. L'indicateur mesure les deux : couverture temporelle et % de points (retrieved/total), le total marqué « estimé » dans l'UI. Aucune logique moteur dans le JS — le panneau affiche ce que le backend sert (CAP-9 : « le panneau affiche, il ne réimplémente pas le moteur »). Microcopie nouvelle via le catalogue websocket + inventaire i18n, jamais codée en dur dans le JS.

Prérequis : epic-history-backfill 1.4 livré (champs de progression exposés par les deux commandes websocket).

## Acceptance Criteria

1. **File Supervision**
   Given la file de récupération ouverte dans l'onglet Supervision
   When une ligne de périphérique est rendue
   Then la barre reflète retrieved/total avec le texte « X / Y points (estimé) », le total portant le marqueur d'estimation

2. **Détail Cohérence**
   Given le détail d'un périphérique ouvert dans l'onglet Cohérence
   When le periph a une progression de backfill
   Then le même indicateur (même markup, même convention) s'affiche, alimenté par `eedomus/get_coherence`

3. **i18n**
   Given une locale non anglaise
   When l'indicateur s'affiche
   Then tous ses libellés viennent du catalogue websocket, l'inventaire i18n passe vert

## References

- spec — _bmad-output/specs/spec-eedomus-history/SPEC.md (CAP-5 : champs de progression servis par get_backfill_state et get_coherence)
- spec — _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md (CAP-9 : le panneau affiche, il ne réimplémente pas le moteur)
- ux — EXPERIENCE.md update run 4 (indicateur barre + texte, file Supervision et détail périphérique)
- ticket — _bmad-output/initiative-eedomus-history/epic-history-backfill (story 1.4, prérequis backend)

## Notes

- Créée le 2026-10-08 après vérification live : aucun champ de progression servi par get_backfill_state (lignes sans retrieved_points/total_points), capteur History Progress Sonoff `unavailable` (bug 109), aucun rendu dans www/panel/supervision.js ni coherence.js — la validation utilisateur de l'indicateur était impossible.
