---
id: 122
type: bug
title: "138 — Panneau Règles/YAML : la zone affichée dépasse la zone modifiable (ascenseur incomplet)"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: low
severity: P3
---

# 138 — Panneau Règles/YAML : la zone affichée dépasse la zone modifiable (ascenseur incomplet)

## Description

Dans Eedomus Config → Règles → mode YAML, il y a un décalage entre la partie affichée et la partie modifiable : 30 lignes sont affichées mais seules les 21 premières sont modifiables directement — l'ascenseur s'arrête à la ligne 21. En dessous, seule la poignée « prendre et agrandir la taille » est disponible. Les deux zones devraient être cohérentes.

## Reproduction

1. Instance réelle, panneau Eedomus Config → onglet Règles → bascule YAML.
2. Un contenu d'environ 30 lignes est présent.
3. Actual : 30 lignes visibles, mais seules les ~21 premières sont éditables ; la scrollbar s'arrête à la ligne 21. Expected : toute la zone affichée est modifiable, ou la zone affichée est limitée à ce qui est modifiable.

## Cause Hypothesis

La hauteur du textarea éditable et la hauteur du rendu affiché divergent dans `regles.js` (styles YAML / conteneur scrollable) — probablement une hauteur max posée sur le mauvais élément.

## Acceptance Criteria

1. **The expected behavior holds**
   **Given** un contenu YAML de 30 lignes dans l'éditeur Règles
   **When** l'utilisateur fait défiler
   **Then** toutes les lignes affichées sont modifiables et l'ascenseur couvre toute la zone affichée
2. **Tests cover the condition found and fixed**
   **Given** the panel JS harness
   **When** it runs
   **Then** a test pins la cohérence hauteur affichée / hauteur éditable (ou le contrat visuel retenu)

## References

- github — issue #138 (fmo01, 2026-11-04) : https://github.com/Dan4Jer/hass-eedomus/issues/138
- code — custom_components/eedomus/www/panel/regles.js (éditeur YAML + styles)

## Notes

- Open question: réduire la zone affichée à la zone modifiable, ou étendre la zone modifiable à tout l'affiché — à trancher au raffinage (choix UX).
