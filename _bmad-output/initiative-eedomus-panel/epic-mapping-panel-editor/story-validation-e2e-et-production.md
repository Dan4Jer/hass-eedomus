---
id: 7
type: story
title: "Validation E2E et production"
parent: epic-mapping-panel-editor
covers: [CAP-1, CAP-2, CAP-3, CAP-4, CAP-5]
after: [10]
risk: low
---

# Validation E2E et production

## Description

Étend la suite E2E (panel présent, websocket répond, parcours save+auto-apply, historique/diff/restauration), déploie sur le RPi (git-only), déroule le parcours #28 bout en bout en production, vérifie le contraste clair/sombre réel.

## Acceptance Criteria

Verify: Suite E2E étendue verte sur l'instance live ; parcours #28 démontré ; aucun avertissement d'accessibilité majeur ; aucun fantôme.

## References

- parent — _bmad-output/initiative-eedomus-panel/epic-mapping-panel-editor/epic-mapping-panel-editor.md
