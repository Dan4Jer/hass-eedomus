---
id: 108
type: bug
title: "Identité de mapping « inconnu » : les mappings standard/par défaut ne s'enregistrent jamais dans le registry"
parent: none
covers: ["CAP-6", "CAP-7"]
after: []
assignee: ""
refined: false
hitl: false
risk: low
severity: P2
---

# Identité de mapping « inconnu » : les mappings standard/par défaut ne s'enregistrent jamais dans le registry

## Description

Dans le panneau de cohérence (popover / ligne étendue), la section « Identité de mapping » affiche `ha_entity`, `ha_subtype` et la justification à « inconnu » pour la majorité des périphériques qui ont pourtant un mapping défini et fonctionnel (entité vivante) — 138 des 165 sur l'instance live (vérifié via `eedomus/get_coherence`). Seuls les ~27 périphériques des chemins de mapping spéciaux (enfants RGBW, fumée, mouvement, boîte message) portent l'identité.

## Reproduction

1. Ouvrir l'onglet Cohérence du panneau Eedomus Config.
2. Ouvrir le détail d'un périphérique mappé par le chemin standard `usage_id` (ex. « Consommation Salon 5 ») ou par le fallback par défaut.
3. Actual : « Identité de mapping » rend `ha_entity`, `ha_subtype`, « Justification » à « inconnu ». Expected : les valeurs du mapping et la justification (« Usage ID mapping : usage_id=X » / la justification du `default_mapping` YAML).

## Given/When/Then

- Given un périphérique mappé par le chemin usage_id standard (entity.py:691), le chemin motifs de nom (l.708) ou le mapping par défaut (l.758), when l'intégration enregistre ses entités, then `register_device_mapping` est appelé et l'entrée apparaît dans le registry — la jointure `eedomus/get_coherence` sert `ha_entity`/`ha_subtype`/`justification`/`parent_periph_id` non nuls pour ces chemins.
- Given un test unitaire qui mappe un périphérique par chacun des trois chemins, when le registry est lu, then les trois entrées existent avec leur justification.
- Given l'onglet Cohérence déployé après le fix, when un périphérique standard ouvre son détail, then l'identité affiche les vraies valeurs — plus aucun « inconnu » sur les 138 périphériques concernés.

## Cause Analysis

`map_device_to_ha_entity` (entity.py) n'enregistre dans le registry que via `_create_mapping` (l.844 → `register_device_mapping`). Trois chemins retournent le dict de mapping **nu**, court-circuitant l'enregistrement : le mapping usage_id standard (l.691), les motifs de nom YAML (l.708) et le mapping par défaut (l.758). Les mappings standard/par défaut ne peuplent donc jamais le registry — la jointure de cohérence (last-wins, `ui_service.py:_registry_by_periph_id`) ne les trouve pas et sert des champs nuls que le panneau rend « inconnu ». Le mapping lui-même fonctionne (entités correctes) : seul le registry de diagnostic est troué.

## References

- code — custom_components/eedomus/entity.py:691,708,758 (les 3 return nus) et :844 (le seul point d'enregistrement)
- code — custom_components/eedomus/ui_service.py:_registry_by_periph_id + _coherence_row (la jointure last-wins)
- spec — _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md (CAP-7 : « justification du registry »)
- ux — EXPERIENCE.md (popover : identité de mapping — le rendu est correct, la donnée est absente)

## Notes

- Signalement utilisateur 2026-10-06 (via bmad-ux) : « parfois les mapping identity sont à unknown alors qu'ils ont un mapping défini avec une justification standard ou par défaut ».
- Point UX en attente : lisibilité des justifications une fois le registry alimenté (formulation, troncature éventuelle) — revue avec les vraies données après déploiement du fix (consigné au memlog UX).
