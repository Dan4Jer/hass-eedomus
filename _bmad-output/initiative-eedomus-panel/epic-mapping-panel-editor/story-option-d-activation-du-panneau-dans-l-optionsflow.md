---
id: 10
type: story
title: "Option d'activation du panneau dans l'OptionsFlow"
parent: epic-mapping-panel-editor
covers: [CAP-1]
after: [9]
risk: low
---

# Option d'activation du panneau dans l'OptionsFlow

## Description

Ajoute l'option enable_panel dans l'OptionsFlow (AD-9 : options > data > défaut, False explicite honoré, défaut activé) : active/désactive l'enregistrement du panneau Eedomus Config au chargement de l'entry ; désactivée, le panneau enregistré est retiré.

## Acceptance Criteria

Verify: L'option apparaît dans l'OptionsFlow ; activée par défaut le panneau reste en place ; désactivée le panneau disparaît de la sidebar (et réapparaît à la réactivation), sans erreur au reload.

## References

- parent — _bmad-output/initiative-eedomus-panel/epic-mapping-panel-editor/epic-mapping-panel-editor.md
- ../../specs/spec-eedomus-mapping-panel/SPEC.md
