---
id: 106
type: story
title: "Cache-busting du module panneau"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: low
---

# Cache-busting du module panneau

## Description

L'URL du module du panneau (`eedomus-panel.js`, servie par `panel.py` via `StaticPathConfig`) ne change pas entre les déploiements : les navigateurs servent l'ancien JS après chaque release, et l'utilisateur doit forcer un rechargement (vécu deux fois le 2026-10-05/06 — consigné dans les plans 4.3 et 4.5). Ajouter un suffixe de version (`?v=<version du manifest>`) au `module_url` servi, avec un test de contrat épinglant que l'URL portée change avec la version — chaque déploiement invalide le cache nativement.

## Acceptance Criteria

Le `module_url` servi porte la version du manifest ; un changement de version produit une URL différente (test de contrat) ; la suite E2E (fetch de l'entrée + des 7 modules) reste verte.

## References

- retro — _bmad-output/initiative-eedomus-panel/epic-supervision-tab/epic-supervision-tab-retrospective.md (action item 1)
- architecture — décision AD-17 (revue architecture 2026-10-06, validée utilisateur : backlog story séparée)
- code — custom_components/eedomus/panel.py (enregistrement du panneau, module_url)

## Notes

- Decision: backlog story séparée, pas fusionnée avec CAP-10 (Winston, 2026-10-06).
