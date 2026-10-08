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

Applique la refonte des métriques de l'onglet Supervision (spine UX update run 2026-10-08, spec CAP-9 synchronisée) : la carte « API calls » disparaît (diagnostic développeur, nominal 1-3, illisible pour l'utilisateur), remplacée par une métrique système de la box (CPU en vue — source de données à vérifier à l'implémentation, aucune API eedomus connue ; sans source vérifiée, la carte reste hors périmètre). Le compte de périphériques devient un nombre statique + puces par catégorie (sensor/light/switch/cover/climate/…), sans graphique temporel. Une gauge d'activité fait son entrée : X périphériques actifs dans la dernière heure, calculée côté backend depuis les `last_value_change` déjà en cache — pas de nouvelle série de cycle, pas d'abonnement (instantané de visite, discipline de la spine). Le temps de refresh (série ligne) est inchangé. Microcopie nouvelle via le catalogue websocket + inventaire i18n.

## Acceptance Criteria

1. **Gauge d'activité**
   Given l'onglet Supervision ouvert
   When la vue métriques se charge
   Then la gauge affiche « X périphs actifs dans la dernière heure » avec son équivalent textuel, valeur issue des `last_value_change` en cache

2. **Compte par catégories**
   Given la vue métriques chargée
   Then le compte de périphériques s'affiche en nombre statique avec une puce par catégorie, sans graphique temporel

3. **Métrique système**
   Given une source de données système vérifiée pour la box
   Then la carte système (CPU) s'affiche avec équivalent textuel ; sinon la carte est absente de la grille — jamais de carte vide présentée comme complète

4. **API calls retiré + i18n**
   Then plus aucune carte « API calls », les clés i18n orphelines sont nettoyées, tout nouveau libellé passe par le catalogue websocket (inventaire vert)

## References

- ux — _bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md (update run 2026-10-08 : IA Supervision, `metric-chart-card`, Key Flow)
- spec — _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md (CAP-9, métriques redéfinies)
- code — custom_components/eedomus/www/panel/supervision.js (cartes actuelles : refresh_time / periphs_total / api_calls)

## Notes

- Décisions utilisateur 2026-10-08 : remplacer API calls par une métrique système (CPU en vue) ; compte périphs = nombre + catégories, pas de graphique ; activité = gauge instantané (pas de série par cycle).
- La faisabilité CPU est un préalable de la carte 3 : à vérifier avant d'implémenter (aucune API eedomus connue ; le scraping de la page locale de diagnostics est hors contrat API).
