---
id: 2
type: story
title: "Enregistrer le panel via l'API supportée"
parent: epic-mapping-panel-editor
covers: [CAP-1]
after: [1]
risk: medium
---

# Enregistrer le panel via l'API supportée

## Description

Réécrit panel.py sur async_register_built_in_panel(component_name=custom, _panel_custom.module_url) + StaticPathConfig servant www/ ; appel au setup, async_remove_panel à l'unload ; supprime frontend.yaml et le vieux code à API inventée.

## Acceptance Criteria

Verify: Le panneau Eedomus Config apparaît dans la sidebar (admin only) après le setup, disparaît à l'unload, aucun frontend.yaml, aucune erreur dans les logs.

## References

- parent — _bmad-output/initiative-eedomus-panel/epic-mapping-panel-editor/epic-mapping-panel-editor.md
- ../../specs/spec-eedomus-mapping-panel/SPEC.md
- ../../planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md#foundation
