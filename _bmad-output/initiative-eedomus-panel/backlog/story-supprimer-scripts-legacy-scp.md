---
id: 100
type: story
title: "Supprimer les scripts legacy de déploiement scp"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: low
---

# Supprimer les scripts legacy de déploiement scp

## Description

Supprime `scripts/deploy_history_fix.sh` et `scripts/deploy_and_analyze.py`, qui déploient par sshpass+scp en violation de l'invariant AD-10 du spine (déploiement git-only) ; vérifie qu'aucune référence ne subsiste.

## Acceptance Criteria

1. **Scripts supprimés**
   **Given** le repo contient les deux scripts scp
   **When** la suppression est commitée
   **Then** `grep -rn "sshpass\|scp " scripts/` ne retourne rien et la suite de tests passe

## Boundaries

- Must not change: le script de déploiement officiel du skill (deploy_hass_eedomus.sh), les scripts d'analyse qui ne déploient pas.

## References

- architecture — _bmad-output/planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md (AD-10)
