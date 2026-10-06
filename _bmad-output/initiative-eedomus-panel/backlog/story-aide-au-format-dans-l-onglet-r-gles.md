---
id: 107
type: story
title: "Aide au format dans l'onglet Règles + page docs/mapping-format.md"
parent: none
covers: ["CAP-10"]
after: []
assignee: ""
refined: false
hitl: false
risk: low
---

# Aide au format dans l'onglet Règles + page docs/mapping-format.md

## Description

L'utilisateur qui écrit une règle de mapping ne connaît pas la grammaire sans ouvrir la discussion #28. Une section d'aide repliable dans l'onglet Règles présente la grammaire (conditions `usage_id`/regex, champs `ha_entity`/`device_class`/`unit`/`state_class`/`priority`) avec de courts exemples, accessible dans les deux modes (formulaire structuré et YAML brut) ; un lien pointe vers `docs/mapping-format.md` qui documente le format complet — page écrite dans le même livrable (décisions utilisateur 2026-10-06 : les deux formes ; lien interne au repo). Toutes les chaînes via le catalogue i18n (EN+FR+fixtures).

## Acceptance Criteria

Un utilisateur qui ne connaît pas le format écrit une règle valide dans chaque mode après avoir lu l'aide ; le lien ouvre la page de doc du repo ; l'aide repliée n'encombre pas l'éditeur ; la garde i18n reste verte.

## References

- spec — _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md (CAP-10)
- ux — _bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md (onglet Règles, régimes de localisation)
- code — custom_components/eedomus/www/panel/regles.js (module de l'onglet), panel_translations.py + fixtures (catalogue)

## Notes

- Decision: les deux formes (aide repliable + lien) ; cible du lien = page docs/ du repo, pas la discussion #28 (décisions utilisateur 2026-10-06, memlog du spec).
- Attention : si la restructuration de la doc (spéc en cours) aboutit, docs/mapping-format.md est une page du jeu canonique restructuré — à coordonner.
