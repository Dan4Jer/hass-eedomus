---
id: 8
type: story
title: "Rework AD-13 — le HA storage devient le canon du mapping custom"
parent: epic-mapping-panel-editor
covers: [CAP-4]
after: [4]
risk: medium
---

# Rework AD-13 — le HA storage devient le canon du mapping custom

## Description

Implémente AD-13 du spine (update run 2026-09-28) : Store eedomus.mapping (current + file_fingerprint) lu par tout le runtime ; ingestion au chargement (texte brut vs fingerprint, différent+valide → nouvelle version archivée, invalide → canon conservé + miroir régénéré, absent → miroir régénéré, bootstrap fichier si storage vide) ; save UI écrit current + miroir + fingerprint + archive. L'API ws (get_mapping/save_mapping) ne change pas.

## Acceptance Criteria

Verify: Une édition manuelle du fichier sur le Pi est ingérée comme nouvelle version au rechargement (badge/Historique la montrent) ; un save UI réécrit miroir+fingerprint sans double version au reload suivant ; un fichier invalide n'écrase pas le canon (warning) ; tests unitaires verts.

## References

- parent — _bmad-output/initiative-eedomus-panel/epic-mapping-panel-editor/epic-mapping-panel-editor.md
- ../../planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md#ad-13
