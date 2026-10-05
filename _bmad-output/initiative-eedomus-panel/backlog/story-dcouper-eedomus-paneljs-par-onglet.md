---
id: 102
type: story
title: "Découper eedomus-panel.js par onglet"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: low
---

# Découper eedomus-panel.js par onglet

## Description

Le panel frontend (`custom_components/eedomus/www/eedomus-panel.js`) a atteint 1852 lignes / 64,8 Ko en fin d'épic : les trois onglets, l'éditeur YAML (coloration + dumper), le moteur de diff LCS et la restauration vivent dans un seul custom element. Contrainte conservée : vanilla sans toolchain de build — le découpage se fait en fichiers ES modules servis depuis www/ (imports natifs), un module par onglet + un noyau commun (thème, websocket, états). Source : rétrospective epic-mapping-panel-editor (2026-10-03), vue taille/structure.

## Acceptance Criteria

Le panel fonctionne à l'identique (E2E 19 verts + validation visuelle) ; chaque onglet vit dans son module ; le noyau commun ne dépasse pas ~400 lignes ; aucun build step introduit.

## References

- _bmad-output/initiative-eedomus-panel/epic-mapping-panel-editor/epic-mapping-panel-editor-retrospective.md (finding taille/structure)
- _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md (Non-goals : pas de toolchain de build)

## Notes

- Decision: le découpage s'exécute AVANT l'épique 4 (Supervision) — le 5e onglet atterrit sur des fichiers sains, le god-file (4 187 lignes, mesuré en rétro cohérence) cesse de croître (user, 2026-10-05).
