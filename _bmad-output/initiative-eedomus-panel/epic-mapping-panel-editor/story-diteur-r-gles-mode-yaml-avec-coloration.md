---
id: 5
type: story
title: "Éditeur Règles — mode YAML avec coloration"
parent: epic-mapping-panel-editor
covers: [CAP-3]
after: [8]
risk: medium
---

# Éditeur Règles — mode YAML avec coloration

## Description

Mode YAML brut conforme à EXPERIENCE.md : lib vendorisée légère sélectionnée selon le critère M9 (clavier complet, texte exposé à l'AT, erreurs aria-live avec numéro de ligne ; repli textarea sinon), coloration syntaxique, validation temps réel, bascule Formulaire↔YAML sans perte.

## Acceptance Criteria

Verify: Un bloc YAML collé avec une erreur est signalé ligne par ligne en aria-live ; la bascule formulaire→YAML→formulaire préserve le contenu ; le focus est conservé à la bascule.

## References

- parent — _bmad-output/initiative-eedomus-panel/epic-mapping-panel-editor/epic-mapping-panel-editor.md

## Notes

- Open question: Lib YAML exacte à sélectionner (critère M9) - repli textarea si aucune candidate légère ne passe.
