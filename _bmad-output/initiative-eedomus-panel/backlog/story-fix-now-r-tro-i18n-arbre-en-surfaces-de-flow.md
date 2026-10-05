---
id: 105
type: story
title: "Fix-now de la rétro i18n : valeur FR dans l'arbre EN, surfaces de flow, sondes de garde"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: low
---

# Fix-now de la rétro i18n : valeur FR dans l'arbre EN, surfaces de flow, sondes de garde

## Description

Les cinq fix-now de la rétrospective epic-i18n (action items 1-5) : (1) la valeur française « Connexion Eedomus » dans l'arbre EN (strings.json/en.json:15) devient une valeur anglaise, avec un test de structure qui épingne l'absence de valeurs marquées FR dans l'arbre EN ; (2) un TestConfigFlowSection épingle le contrat config-flow ↔ strings.json (champs de STEP_USER_DATA_SCHEMA ≡ config.step.user.data sur les trois arbres, clés d'erreur) et les `errors = {"base": str(err)}` bruts de config_flow.py (~:158) migrent en clés traduites ; (3) les labels du flow d'options passent dans la grammare native — section options.step.init.data pour les ~13 champs (trois arbres), réparation du label `php_fallback_script` keyé sur un champ inexistant (`php_fallback_script_name`), description du yaml_editor pointée sur une clé dédiée au lieu du blurb intégration — épinglé par test de structure ; (4) un test unitaire de la normalisation de région du flow d'options (fr-FR → fr) ; (5) la sonde canari du self-test de la garde JS (clé morte panel.coherence.status.total) est documentée/renommée et la course get_translations dupliquée post-timeout reçoit un token de génération.

## Acceptance Criteria

1. **Given** l'arbre EN, **when** un utilisateur anglais configure l'intégration, **then** le titre s'affiche en anglais (« Connexion Eedomus » migré en valeur EN, la FR reste la traduction) — et un test de structure échoue sur toute valeur marquée française introduite dans strings.json/en.json.
2. **Given** le schéma du config flow, **when** un champ est renommé ou ajouté sans label, **then** le TestConfigFlowSection échoue (égalité d'ensembles champs ↔ labels sur les trois arbres, clés d'erreur présentes) ; **and** les erreurs vol.Invalid brutes de validate_input migrent en clés `config.error.*` traduites (EN + FR).
3. **Given** le flow d'options, **when** il s'affiche, **then** chaque champ porte son label traduit (section options.step.init.data, trois arbres ; le label du champ php_fallback_script_name résout), et le yaml_editor rend une description dédiée (pas le blurb intégration) — épinglé par test de structure.
4. **Given** `hass.config.language = "fr-FR"`, **when** le yaml_editor se rend, **then** les placeholders viennent de l'arbre FR (test unitaire de la normalisation de région).
5. **Given** le self-test de la garde JS, **when** la sonde de clé inconnue échoue, **then** le message parle de la sonde, pas d'une régression ; **and** un timeout suivi d'un second appel de même locale ne duplique pas la commande ws (token de génération).

## Boundaries

- Must not change: les contrats ws gelés, le catalogue panel_translations (aucune clé panel.* touchée), la mécanique de traduction elle-même (grammaire native uniquement), la garde JS au-delà de la sonde documentée et du token.
- Les valeurs EN sont naturelles (pas des calques) ; la FR reste la traduction fidèle ; les trois arbres restent structurellement identiques (les tests de parité existants doivent rester verts).

## References

- rétro — _bmad-output/initiative-eedomus-panel/epic-i18n/epic-i18n-retrospective.md, action items 1-5 et findings « Défauts réels encore ouverts »
- spec — _bmad-output/specs/spec-eedomus-i18n/SPEC.md (CAP-1 : rien user-facing hors inventaire)

## Notes

- Decision: lot fix-now ordonné par la rétro i18n, décision utilisateur de les traiter immédiatement (2026-10-05).
- Les items 6-10 de la rétro (badge descripteur, noms dérivés, témoins live, CI préexistant, process) restent des propositions en attente de décision.
- Open question rétro liée : l'ajout des nouvelles clés config.error/options.step.init.data à l'inventaire i18n (l'inventaire est source de génération depuis 3.6 — mettre à jour la section §2 addendum par cohérence).
