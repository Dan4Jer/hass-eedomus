---
id: 1
type: bug
title: "Deep-link #historique : l'onglet Historique ne charge jamais si hass est assigné après l'ouverture du panneau"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: low
severity: P3
---

# Deep-link #historique : l'onglet Historique ne charge jamais si hass est assigné après l'ouverture du panneau

## Description

Un utilisateur ouvre le panneau Eedomus Config directement sur l'onglet Historique (URL `#historique`, favori ou lien partagé). Si le panneau s'affiche avant que Home Assistant ait assigné `hass` à l'élément, `_loadVersions` sort immédiatement (`if (!this._hass) return;`) et rien ne le relance : l'onglet reste sur ses squelettes à vie. Le même bug a été corrigé pour l'onglet Cohérence (le `set hass` rejoue le loader de l'onglet actif) — pas pour Historique ni pour Périphériques dans le même cas de figure.

## Reproduction

1. Déployer le panneau, recharger HA, ouvrir `/#eedomus-config-panel` (ou l'équivalent local) directement avec le hash `#historique` avant la fin du démarrage du panneau.
2. L'onglet Historique s'affiche avec ses squelettes.
3. Actual : les squelettes ne cèdent jamais la place ; aucun appel `eedomus/get_mapping_versions`. Expected : au moment où `hass` est assigné, le loader de l'onglet actif se rejoue et les versions s'affichent.

## Cause Hypothesis

`_loadVersions` (et par symétrie `_loadPeripherals` dans le même scénario) ne se réarment pas à l'arrivée de `hass` ; le fix de l'onglet Cohérence (`set hass` rejoue le loader si l'onglet actif n'est pas chargé) est un correctif ponctuel qui n'a pas été généralisé aux autres onglets à chargement différé.

## Acceptance Criteria

1. **The expected behavior holds**
   **Given** le panneau ouvert sur `#historique` avant l'assignation de `hass`
   **When** `hass` est assigné
   **Then** l'onglet Historique charge ses versions (et par généralisation, chaque onglet à chargement différé rejoue son loader à l'arrivée de `hass`)
2. **Tests cover the condition found and fixed**
   **Given** la suite de tests du panneau
   **When** elle tourne
   **Then** un test couvre le deep-link avant `hass` pour chaque onglet paresseux (au minimum Historique, vérifié par harnais node ou assertion DOM)
3. **Or: no change is needed, with proof**
   **Given** la reproduction
   **When** elle est jouée sur le code actuel
   **Then** le chargement se fait déjà correctement, ou le rapport était erroné, avec l'évidence consignée dans Notes — ceci prime 1 et 2

## References

- code — custom_components/eedomus/www/eedomus-panel.js (`set hass`, `_loadVersions`, correctif ponctuel Cohérence)
- review — revue bmad-review des commits 2.1/2.2 (2026-10-04), constat adversarial n°4

## Notes

- Decision: créé depuis le routage de la revue 2.1/2.2 (utilisateur, 2026-10-04) — bug préexistant, hors épique cohérence, ne bloque pas la chaîne.
