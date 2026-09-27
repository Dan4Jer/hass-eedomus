---
type: initiative
title: "Panel de configuration eedomus dans Home Assistant"
parent: none
covers: [CAP-1, CAP-2, CAP-3, CAP-4, CAP-5]
after: []
assignee: ""
risk: medium
---

# Panel de configuration eedomus dans Home Assistant

## Description

L'utilisateur HACS configure ses périphériques eedomus (types, unités, mappings) depuis la barre latérale de Home Assistant, avec aide à la saisie et historique visible en couleurs — sans jamais ouvrir un fichier YAML. Le spec `spec-eedomus-mapping-panel` (5 CAPs) possède les capacités et non-goals ; les companions DESIGN.md/EXPERIENCE.md (UX finalisés, validés) possèdent l'apparence et le comportement ; le spine d'architecture possède les invariants techniques.

## Outcome

Un utilisateur comme celui de la discussion #28 corrige le type et l'unité d'un capteur depuis la barre latérale, sans YAML — le success signal du spec est la mesure.

## Done when

1. Le panneau apparaît dans la sidebar après le setup (API supportée HA 2026.9.3) et disparaît à l'unload.
2. Le parcours #28 complet fonctionne par l'UI : recherche → mapping courant → règle créée → auto-apply → entité corrigée.
3. L'historique montre les 3 dernières versions en diff coloré lisible (≥4.5:1) en thème clair ET sombre, restauration confirmée en un clic.
4. Le mode YAML brut avec coloration et le formulaire coexistent, bascule sans perte.
5. Aucune entité fantôme ni écriture box eedomus ; websocket existant branché, pas réinventé.

## Boundaries

Le panneau de configuration (enregistrement, liste périphériques, éditeur mapping, historique versions). Pas le backfill history (initiative-eedomus-history), pas l'entity registry, pas d'écriture vers la box — voir les non-goals du spec.

## References

- spec — _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md (companions: ARCHITECTURE-SPINE.md, DESIGN.md, EXPERIENCE.md)
- architecture — _bmad-output/planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md (AD-7, AD-9, AD-10)
- ux — _bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/ (DESIGN.md, EXPERIENCE.md, mockups/)

## Notes

- Decision: auto-appliquer au save, formulaire + YAML double mode, historique+restauration, stockage .storage (décisions utilisateur 2026-09-27, dans le memlog du spec).
- Unknown: lib YAML vendorisée à sélectionner selon le critère d'accessibilité M9 (clavier complet, texte AT, erreurs aria-live) — ticket 5.
