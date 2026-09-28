---
id: 6
type: story
title: "Historique, diff coloré et restauration"
parent: epic-mapping-panel-editor
covers: [CAP-5]
after: [9]
risk: medium
---

# Historique, diff coloré et restauration

## Description

Onglet Historique conforme au mock-03 : archivage .storage à chaque save (version horodatée, retention 3, purge à la 4e), cartes de version, diff type git avec le traitement C1 (texte --primary-text-color, fond teinté + préfixes +/-/~ + barre gauche), restauration avec confirmation 'Le mapping actuel sera archivé', passage par le chemin auto-apply de CAP-4.

## Acceptance Criteria

Verify: Après 3 saves, 3 versions horodatées visibles ; restaurer la précédente remet son contenu et l'applique ; le 4e save purge la plus ancienne ; contraste du diff ≥4.5:1 en thème clair ET sombre (vérifié sur les variables).

## References

- parent — _bmad-output/initiative-eedomus-panel/epic-mapping-panel-editor/epic-mapping-panel-editor.md
- ../../planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/mockups/mock-03-historique.html
- ../../planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/DESIGN.md#colors
