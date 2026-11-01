---
id: 119
type: story
title: "Revue de la PR #137 : règles value_type/unit, text sensors par description (0.15.6)"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: medium
---

# Revue de la PR #137 : règles value_type/unit, text sensors par description (0.15.6)

## Description

PR #137 d'Ecirbaf69 (ouverte le 2026-10-31, non incluse dans la 0.15.5) : le moteur de règles ignore le `value_type` et l'unité d'un périphérique — usage_id 35 couvre compteurs numériques ET texte libre sans moyen de les mapper différemment, un texte non numérique devient `None`, une règle `text_sensor` ne crée aucune entité, et `last_value_text` vide masque le texte de `last_value`. La PR ajoute les conditions `value_type`/`unit`, un `value_resolver.py` unifié, et sert les `text_sensor` depuis la plateforme sensor. Pas de changement de mapping par défaut : installs existantes inchangées sauf règle utilisant les nouvelles conditions. 458 tests unitaires côté PR (14 nouveaux, construits sur des payloads réels).

## Acceptance Criteria

La revue applique le processus complet (diff lu, suites complètes 452+ du repo + les 14 tests de la PR, format gate, deploy live + E2E live avant tout release), vérifie l'interaction avec le fix du cache coordinator (#135 : les conditions se lisent-elles depuis le canon HA storage ?), et tranche les known limitations que la PR assume (text flag, `-9999` error entry, sensor platform servant les text_sensor). Livrée en 0.15.6 si verte.

## References

- pr — https://github.com/Dan4Jer/hass-eedomus/pull/137 (Ecirbaf69, feat(mapping))
- related — PR #135 mergée en 0.15.5 (même auteur, le canon mapping est désormais le cache coordinator)
- related — issue #126 fermée (les « Unknown device » usage_id 49 : cette PR est l'outil propre pour les mapper différemment)

## Notes

- Decision: hors 0.15.5 — une feature ne se glisse pas dans une release de bugfixs déjà validée en live (utilisateur, 2026-11-01).
- Open question: la PR date d'avant le merge #135 — rebasée nécessairement sur le nouveau canon mapping.
