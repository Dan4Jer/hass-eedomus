---
id: 4
type: story
title: "Éditeur Règles — formulaire + validation + save auto-apply"
parent: epic-mapping-panel-editor
covers: [CAP-3, CAP-4]
after: [3]
risk: high
---

# Éditeur Règles — formulaire + validation + save auto-apply

## Description

Onglet Règles mode Formulaire conforme au mock-02 : formulaire structuré (nom, priorité, conditions usage_id avec autocomplete, mapping ha_entity/device_class/unit/state_class), validation temps réel via websocket, save → config_manager → auto-apply (reload de l'intégration) avec feedback nominatif sur l'entité.

## Acceptance Criteria

Verify: La règle 'capteur de température' de la discussion #28 se crée par l'UI, une erreur de schema est signalée avant save (save désactivé), et après save l'entité change effectivement (unité corrigée visible).

## References

- parent — _bmad-output/initiative-eedomus-panel/epic-mapping-panel-editor/epic-mapping-panel-editor.md
- ../../planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/mockups/mock-02-regles.html
- ../../planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md#component-patterns
