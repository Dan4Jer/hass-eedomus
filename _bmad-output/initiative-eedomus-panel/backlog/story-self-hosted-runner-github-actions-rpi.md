---
id: 101
type: story
title: "Installer le self-hosted runner GitHub Actions sur le RPi"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: true
risk: medium
---

# Installer le self-hosted runner GitHub Actions sur le RPi

## Description

Prépare et documente l'installation du runner GitHub Actions self-hosted sur le Raspberry Pi (192.168.1.5) pour exécuter les tests E2E en CI ; la registration effective (token GitHub, validation de l'enregistrement) requiert l'utilisateur.

## Acceptance Criteria

1. **Runner opérationnel en CI**
   **Given** le workflow CI appelle la suite E2E sur runner self-hosted
   **When** l'utilisateur a fourni le token d'enregistrement et validé `./svc.sh install` sur le Pi
   **Then** un push sur unstable déclenche les tests E2E sur le RPi et le statut remonte au commit

## Boundaries

- Must not change: la suite E2E elle-même (tests/), le déploiement git-only (AD-10) — le runner ne déploie rien, il teste.

## References

- skill — .vibe/skills/hass-eedomus-deploy/ (enveloppe opérationnelle RPi)
- tickets E2E — tests/e2e/test_e2e_integration.py (suite à exécuter en CI)
