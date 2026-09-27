---
id: 3
type: story
title: "Écran Périphériques (liste, recherche, badge, raccourci)"
parent: epic-mapping-panel-editor
covers: [CAP-2]
after: [2]
risk: medium
---

# Écran Périphériques (liste, recherche, badge, raccourci)

## Description

Onglet Périphériques conforme au mock-01 et à EXPERIENCE.md : liste des périphs (nom, usage_id, entité HA, mapping courant) depuis coordinator.data, recherche nom/usage_id, filtre 'Périphériques touchés' (aria-live), badge modifié accessible (aria-label nominatif), action 'Créer une règle pour ce périphérique' basculant sur Règles avec usage_id pré-rempli.

## Acceptance Criteria

Verify: Les ~165 périphs s'affichent avec recherche fonctionnelle ; le badge annonce la règle au lecteur d'écran ; le raccourci pré-remplit l'usage_id ; thémé HA (variables), reflow mobile 360px.

## References

- parent — _bmad-output/initiative-eedomus-panel/epic-mapping-panel-editor/epic-mapping-panel-editor.md
- ../../planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/mockups/mock-01-peripheriques.html
