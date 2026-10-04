---
type: epic
title: "i18n — audit et migration vers les mécanismes natifs Home Assistant"
parent: initiative-eedomus-panel
covers: [CAP-1, CAP-2, CAP-3, CAP-4]
after: []
assignee: ""
risk: medium
---

# i18n — audit et migration vers les mécanismes natifs Home Assistant

## Description

L'intégration viole sa propre règle (`AGENTS.md`) : ~42 chaînes utilisateur en français codé en dur dans le panneau, `en.json` sans la section `ui`, services non localisés, logs et docstrings massivement en français. L'épique livre l'inventaire, le catalogue de chaînes servi par websocket, les traductions backend complètes et la passe complète des logs/docstrings — anglais partout en dur, le français uniquement comme traduction.

## Outcome

Le signal du spec : un utilisateur sous HA en anglais ne voit zéro texte français sur aucune surface (panneau, flows, services, entités, logs) ; sous HA en français, tout est complet — la FR livrée complète avant release.

## Requirements

- CAP-1: Inventaire i18n — chaque chaîne cataloguée avec surface, mécanisme cible et clé. (spec-eedomus-i18n, Capabilities)
- CAP-2: Traductions backend complètes et structurellement identiques — en.json source de vérité, fr.json arbre identique (section ui), services via strings.json, replis d'entités localisés. (spec-eedomus-i18n, Capabilities)
- CAP-3: Chaînes du panneau via websocket — catalogue servi par le backend selon hass.locale, zéro chaîne en dur dans le JS, repli anglais. (spec-eedomus-i18n, Capabilities)
- CAP-4: Source anglais partout — logs, docstrings, commentaires en anglais, en une passe complète. (spec-eedomus-i18n, Capabilities)

## Done when

1. L'inventaire couvre toutes les chaînes user-facing du repo (grep croisé sans chaîne oubliée).
2. `en.json` et `fr.json` partagent le même arbre de clés (test automatisé), y compris la section `ui`.
3. Aucune chaîne user-facing en dur dans `www/eedomus-panel.js` (garde grep en CI).
4. Aucun message de log ni docstring en français dans `custom_components/eedomus` ; les logs de l'instance live s'affichent en anglais.
5. Déployé et validé sur le Pi : le panneau s'affiche en anglais sous HA anglais et en français sous HA français (suite E2E + contrôle visuel).

## Boundaries

Les chaînes d'affichage uniquement. Pas de nouvelle fonctionnalité, pas de changement des contrats gelés (get_peripherals, get_coherence), pas de traduction des données (noms cloud), pas d'infrastructure au-delà de en/fr. Non-goals du spec.

## References

- spec — _bmad-output/specs/spec-eedomus-i18n/SPEC.md (4 CAPs, contraintes, signal)
- regle — AGENTS.md (politique tout-anglais, mécanismes natifs, repli EN)
- ux — _bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md §Voice and Tone (régime de localisation)

## Notes

- Decision: passe complète des logs/docstrings FR existants (user, 2026-10-04) — pas de migration au toucher.
- Decision: repli anglais, FR complète avant livraison ; mécanisme panneau = catalogue servi par websocket (user, 2026-10-04).
- Decision: build non assisté (bmad-build-auto), plan_checkpoint sur 3.3 (migration des ~42 chaînes du panneau) et 3.5 (passe complète des logs) (user, 2026-10-04).
- Decision: cet épique se construit AVANT epic-supervision-tab — les nouveaux onglets naîtront directement localisés (user, 2026-10-04).
- Unknown: disponibilité réelle des composants graphiques HA dans le contexte du panneau (n/a ici — porte par epic-supervision-tab).
