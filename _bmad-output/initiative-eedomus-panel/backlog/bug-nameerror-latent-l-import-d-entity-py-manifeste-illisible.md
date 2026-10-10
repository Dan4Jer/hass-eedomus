---
id: 117
type: bug
title: "NameError latent à l'import d'entity.py quand manifest.json est illisible"
parent: none
covers: []
after: []
assignee: ""
refined: true
hitl: false
risk: low
severity: P3
---

# NameError latent à l'import d'entity.py quand manifest.json est illisible

## Description

Si la lecture de `manifest.json` échoue à l'import d'`entity.py` (fichier absent, JSON invalide, permissions), le bloc `except` journalise via `_LOGGER` **avant** que la variable ne soit assignée quelques lignes plus bas : l'avertissement crée un `NameError` qui fait planter l'import du module — précisément au moment où il devrait journaliser. Différé en review du ticket 113 (préexistant, pas causé par ce build).

## Reproduction

1. Rendre `custom_components/eedomus/manifest.json` illisible (le renommer, corrompre le JSON, ou retirer les droits).
2. Importer `custom_components.eedomus.entity`.
3. Actual : `NameError: name '_LOGGER' is not defined`, l'import échoue. Expected : `VERSION = "unknown"`, un warning journalisé, l'import réussit.

## Cause Hypothesis

Ordre des déclarations au niveau module : le `try`/`except` de lecture du manifest (lignes 23-30) précède `_LOGGER = get_logger(__name__)` (ligne 32) ; le `except` référence `_LOGGER`.

## Acceptance Criteria

1. **L'import survit à un manifeste illisible**
   **Given** `manifest.json` illisible
   **When** `entity` est importé (ou rechargé)
   **Then** `VERSION == "unknown"`, l'import réussit, et le warning est journalisé via le logger balisé
2. **Tests couvrent la condition corrigée**
   **Given** la suite unitaire
   **When** elle tourne
   **Then** un test simule l'échec de lecture du manifeste au chargement d'`entity` et échoue avant le correctif (NameError) et passe après
3. **Ou : pas de changement nécessaire, preuve à l'appui**
   **Given** la reproduction
   **When** jouée sur le code actuel
   **Then** le comportement attendu tient déjà, ou le rapport était erroné, preuve en Notes — prime sur 1-2

## References

- code — custom_components/eedomus/entity.py:23-32 (try/except avant l'assignation de `_LOGGER`)
- deferred — plan du ticket 113 (`_bmad-output/initiative-eedomus-panel/backlog/story-tag-box-d-origine-sur-tous-les-logs-plan.md`, Review Triage Log, item defer)

## Notes

- Decision: embarqué dans la 0.15.4 avec l'accord explicite de l'utilisateur (2026-10-10).
