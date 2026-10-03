---
id: 103
type: story
title: "Unifier la lecture du canon du mapping sur config_manager"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: low
---

# Unifier la lecture du canon du mapping sur config_manager

## Description

Deux chemins résolvent aujourd'hui « le canon du mapping custom » : le badge « modifié » de l'onglet Périphériques passe par `device_mapping.async_get_canonical_custom_mapping` (`ui_service.py::_load_custom_mapping`, posé en P.1.3) tandis que `get_mapping`/`save_mapping` passent par `config_manager.async_get_custom_mapping`. Convergents à ce jour (même Store `eedomus.mapping`, même repli fichier), mais une divergence future (plafond de repli, pré-cache) passerait inaperçue car aucun test ne relie les deux chemins. Unifier sur `config_manager.async_get_custom_mapping` (la lecture device_mapping reste disponible pour le bootstrap interne du loader). Source : rétrospective epic-mapping-panel-editor (2026-10-03), vue invariants de données.

## Acceptance Criteria

Le badge lit via config_manager ; un test unitaire relie les deux chemins (assertion : les deux lectures d'un même storage renvoient le même dict) ; aucun double repli fichier divergent.

## References

- _bmad-output/initiative-eedomus-panel/epic-mapping-panel-editor/epic-mapping-panel-editor-retrospective.md (finding double chemin)
- _bmad-output/planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md AD-13
