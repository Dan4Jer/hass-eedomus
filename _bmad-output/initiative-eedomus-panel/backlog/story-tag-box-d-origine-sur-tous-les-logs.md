---
id: 113
type: story
title: "Tag box d'origine sur toutes les lignes de log de l'intégration"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: medium
---

# Tag box d'origine sur toutes les lignes de log de l'intégration

## Description

Sur une installation multi-box, aucune ligne de log n'identifie la box émettrice : chaque plateforme (28 modules Python avec `_LOGGER`) logge sans origine, et les bugs multi-box passés (#102, #103) ont été diagnostiqués à l'aveugle. Un helper/logger unique balise chaque ligne de log de l'intégration avec l'identifiant de la box émettrice — toutes plateformes, pas seulement coordinator et mapping_registry comme le proposait la PR #119.

## Acceptance Criteria

Sur une install multi-box, toute ligne de log de l'intégration (toutes plateformes) identifie la box émettrice avec un tag stable et uniforme ; la convention de tag est tranchée et documentée ; les suites (unit, node, e2e) restent vertes. Vérifié par un test unitaire du logger partagé (le tag de la box est injecté dans chaque ligne) et une passe sur `custom_components/eedomus` garantissant qu'aucun module ne logge hors du logger balisé.

## References

- forge — _bmad-output/forge/community-idea-mining/forged-idea.md (décision 1)
- pr — PR #119 fmo01 (proposition d'origine — coordinator + mapping_registry seulement — non retenue au salvage)
- issues — #102 (bug multi-box corrigé, attesté dans services.py:43) et #103 (bug multi-box corrigé — source : issues GitHub du repo)
- code — custom_components/eedomus/coordinator.py:1424 (le titre du config entry = nom utilisateur de la box, convention déjà documentée)

## Notes

- Decision: périmètre élargi à toute l'intégration, pas seulement coordinator + mapping_registry (forge 2026-10-10).
- Open question: convention du tag — titre du config entry (nom utilisateur, déjà la convention du coordinator) vs identifiant court ; à trancher au raffinage.
