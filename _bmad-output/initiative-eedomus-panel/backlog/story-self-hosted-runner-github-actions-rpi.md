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

## Runbook (préparé 2026-10-10, périmètre 0.15.4)

Étapes personne (hitl), sur le Pi (accès SSH du skill deploy) :

1. Sur GitHub : *Settings → Actions → Runners → New self-hosted runner* →
   noter le token d'enregistrement (jetable).
2. Sur le Pi :
   ```bash
   mkdir -p ~/actions-runner && cd ~/actions-runner
   curl -o actions-runner-linux-arm64-<version>.tar.gz -L <URL fournie par GitHub>
   tar xzf actions-runner-linux-arm64-<version>.tar.gz
   ./config.sh --url https://github.com/Dan4Jer/hass-eedomus --token <TOKEN> --labels self-hosted,pi
   sudo ./svc.sh install && sudo ./svc.sh start
   ```
3. Vérifier : GitHub → Settings → Actions → Runners — le runner apparaît
   *Idle* ; `sudo ./svc.sh status` sur le Pi.

Après enregistrement (revenir vers l'agent) : bascule du workflow E2E sur
`runs-on: [self-hosted, pi]` — la bascule n'est committée qu'après
l'enregistrement effectif, sinon les jobs CI font queue indéfiniment.

- Decision: embarqué dans la 0.15.4 avec hitl par l'utilisateur (2026-10-10) ; l'installation précède la bascule de workflow.
- Open question: le runner utilise-t-il le même utilisateur que HA sur le Pi (droits sur les dossiers de test) — à trancher à l'installation.
