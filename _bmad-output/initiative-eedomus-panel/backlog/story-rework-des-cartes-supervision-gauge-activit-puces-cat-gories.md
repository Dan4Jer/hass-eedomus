---
id: 111
type: story
title: "Rework des cartes Supervision : gauge d'activité, puces catégories, métrique système"
parent: none
covers: ["CAP-9"]
after: []
assignee: ""
refined: false
hitl: false
risk: medium
---

# Rework des cartes Supervision : gauge d'activité, puces catégories, métrique système

## Description

Applique la refonte des métriques de l'onglet Supervision (spine UX update run 2026-10-08, spec CAP-9 synchronisée) : la carte « API calls » disparaît (diagnostic développeur, nominal 1-3, illisible pour l'utilisateur), remplacée par une métrique système de la box : les periphs système de la box (usage 23 — CPU Box 1061603, Espace libre Box 1061604) sont la source ; le coordinator échantillonne l'état CPU à chaque cycle de refresh dans le buffer get_box_metrics (série, même discipline que refresh_time), l'espace libre voyage en valeur associée ; carte masquée si le periph CPU est absent. Le compte de périphériques devient un nombre statique + puces par catégorie (sensor/light/switch/cover/climate/…), sans graphique temporel. Une gauge d'activité fait son entrée : X périphériques actifs dans la dernière heure, calculée côté backend depuis les `last_value_change` déjà en cache — pas de nouvelle série de cycle, pas d'abonnement (instantané de visite, discipline de la spine). Le temps de refresh (série ligne) est inchangé. Microcopie nouvelle via le catalogue websocket + inventaire i18n.

## Acceptance Criteria

1. **Gauge d'activité**
   Given l'onglet Supervision ouvert
   When la vue métriques se charge
   Then la gauge affiche « X périphs actifs dans la dernière heure » avec son équivalent textuel, valeur issue des `last_value_change` en cache

2. **Compte par catégories**
   Given la vue métriques chargée
   Then le compte de périphériques s'affiche en nombre statique avec une puce par catégorie, sans graphique temporel

3. **Métrique système (chart échantillonné)**
   Given un periph système CPU Box présent (usage 23)
   When chaque cycle de refresh se termine
   Then le coordinator ajoute l'état CPU échantillonné au buffer get_box_metrics et la carte rend la série avec équivalent textuel + l'espace libre en valeur associée ; sans le periph, la carte est absente de la grille — jamais de carte vide présentée comme complète

4. **API calls retiré + i18n**
   Then plus aucune carte « API calls », les clés i18n orphelines sont nettoyées, tout nouveau libellé passe par le catalogue websocket (inventaire vert)

## References

- ux — _bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md (update run 2026-10-08 : IA Supervision, `metric-chart-card`, Key Flow)
- spec — _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md (CAP-9, métriques redéfinies)
- code — custom_components/eedomus/www/panel/supervision.js (cartes actuelles : refresh_time / periphs_total / api_calls)

## Notes

- Décisions utilisateur 2026-10-08 : remplacer API calls par une métrique système (CPU en vue) ; compte périphs = nombre + catégories, pas de graphique ; activité = gauge instantané (pas de série par cycle).
- Faisabilité CPU tranchée (2026-10-08) : la box expose ses periphs système via l'API normale (usage 23) — CPU Box et Espace libre Box, déjà en cache coordinator. Décisions utilisateur : chart échantillonné par cycle + CPU et espace libre sur la carte.
