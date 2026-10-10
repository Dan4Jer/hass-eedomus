---
id: 114
type: story
title: "Catalogue des types matériels manquants dans le dump du simulateur"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: true
risk: medium
---

# Catalogue des types matériels manquants dans le dump du simulateur

## Description

Le dump anonymisé du simulateur (`eedomus_dump.json`, 69 périphériques, usage_id dominants 7 température, 1 lampe, 0 électrique, 52, 35, 26 conso) ne couvre pas tous les types matériels que l'intégration traite — le cataloguer : types de périphériques eedomus manquants au regard des plateformes de l'intégration (climate/thermostat, lumière couleur, etc.), priorisés par gain de couverture de code ; chaque nouveau dump passe la passe de vie privée complète avant commit (règle CAP-5). Étape personne : l'extraction d'un nouveau dump (00_extract.py) tourne contre une box réelle avec ses credentials — fmo01 a proposé d'enrichir le sien.

## Acceptance Criteria

Le catalogue liste chaque type manquant avec la plateforme concernée et sa priorité de couverture ; tout dump ajouté a passé la passe de vie privée complète avant commit ; la suite e2e_sim reste verte avec les dumps enrichis.

## References

- spec — _bmad-output/specs/spec-eedomus-simulator/SPEC.md (CAP-5 : outils d'extraction/anonymisation, vie privée obligatoire)
- forge — _bmad-output/forge/community-idea-mining/forged-idea.md (décision 2)
- sim — scripts/simulateur/ (00/01/02 extraction/anonymisation, eedomus_dump.json 69 periphs)
- pr — PR #119 fmo01 (proposition : « intéressant d'y ajouter d'autres cas de matériel géré par eedomus »)

## Notes

- Decision: backlog story séparée — l'epic-eedomus-simulator est done (état de l'arbre au 2026-10-10, `tickets.py status` : 35/35 tickets de l'initiative done), précédent AD-17 (revue architecture 2026-10-06 — backlog story séparée pour le cache-busting) ; la décision initiale du forge plaçait la story dans l'epic alors cru en cours, amendée à la création du ticket.
- hitl: l'extraction d'un nouveau dump exige une box eedomus réelle (credentials, passe de vie privée) — étape personne.
- Open question: qui fournit les dumps des types manquants (fmo01 candidat naturel ; l'utilisateur peut extraire le sien).
- Open question: où vit le catalogue (document dans scripts/simulateur/, README, ou artefact de test) — à trancher au raffinage, les critères complets l'exigent.
