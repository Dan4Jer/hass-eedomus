---
id: 115
type: story
title: "Garantie de format : hook pre-push + porte dans le script de deploy"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: true
risk: medium
---

# Garantie de format : hook pre-push + porte dans le script de deploy

## Description

Le formatage black/isort n'est garanti nulle part dans la chaîne de livraison actuelle : la règle ≤ 88 caractères est tenue à la main, et les jobs GitHub tournent après le push et le déploiement (git-only, local d'abord). Deux verrous locaux, sans installation permanente (uvx éphémère) : un hook git pre-push qui refuse tout push mal formaté vers n'importe quel remote du repo (origin unstable comme main), et la même porte dans la section pre-deployment checks de `deploy_hass_eedomus.sh` comme filet — elle attrape aussi ce qui a été poussé depuis une autre machine. Étape personne : l'installation du hook est par machine (script d'installation + documentation).

## Acceptance Criteria

Un push vers n'importe quel remote du repo avec du code mal formaté est refusé par le hook ; le script de deploy s'arrête avant tout déploiement si le format ne suit pas ; aucun outil de formatage n'est installé en permanence ; la suite E2E reste verte.

## References

- forge — _bmad-output/forge/community-idea-mining/forged-idea.md (décision 3)
- deploy — .vibe/skills/hass-eedomus-deploy/deploy_hass_eedomus.sh (section pre-deployment checks, où s'insère la porte)
- policy — AGENTS.md (black/isort non installés localement, ≤ 88 à la main — la porte rend la règle vérifiable)
- source — pratique du fork fmo01 (auto-fix CI GitHub Actions, rejetée car tardive dans cette chaîne)

## Notes

- Decision: pas d'auto-fix en CI — les jobs GitHub arrivent après le déploiement local git-only (forge 2026-10-10).
- Decision: le hook contrôle tout push vers n'importe quel remote du repo, pas seulement origin/unstable (utilisateur, ticketing 2026-10-10).
- Decision: hook + porte en redondance volontaire — le hook est le verrou du quotidien, la porte de deploy le vrai filet (forge 2026-10-10).
- hitl: l'installation du hook git est une étape personne, par machine qui pousse.
- Open question: où vit le hook dans le repo (répertoire dédié + core.hooksPath vs installation documentée) — à trancher au raffinage.
