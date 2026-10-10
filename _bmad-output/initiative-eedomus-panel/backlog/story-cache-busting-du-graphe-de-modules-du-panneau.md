---
id: 118
type: story
title: "Cache-busting du graphe de modules du panneau (pas seulement l'entry)"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: medium
---

# Cache-busting du graphe de modules du panneau (pas seulement l'entry)

## Description

Le cache-busting (AD-17, story 106) ne vise que l'URL de l'entry (`eedomus-panel.js?v=<version du manifest>`). Les modules importés (`./panel/shared.js`, `coherence.js`, etc.) sont servis sans paramètre : au premier déploiement qui ajoute ou retire un export consommé par l'entry, les navigateurs qui ont le module en cache servent l'ancienne copie face à l'entry neuve — SyntaxError en production. Vu en direct au déploiement 0.15.4 : `shared.js doesn't provide an export named: 'menuButtonHtml'`. Contournement 0.15.4 : les helpers du bouton menu vivent dans l'entry (commit 6ed6184). Le piège reste armé pour tout changement futur du graphe : chaque nouvelle surface doit vivre dans l'entry, ou le graphe doit être busté.

## Acceptance Criteria

Sur une install de production, when une nouvelle version change un module importé du panneau (ajout/retrait d'export), then les navigateurs qui avaient la version précédente en cache chargent la nouvelle copie de chaque module touché — aucun SyntaxError résiduel, aucun rechargement forcé demandé à l'utilisateur. La solution (paramètre de version sur les specifiers d'import, hash de contenu servi par le backend, ou toute autre) ne casse ni le harnais node (mini-loader), ni le chargement direct des modules.

## References

- code — custom_components/eedomus/panel.py (panel_module_url, cache-busting AD-17)
- code — custom_components/eedomus/www/eedomus-panel.js (imports du graphe, helpers menu en entry)
- live — SyntaxError du déploiement 0.15.4 (logs HA du 2026-10-10, `shared.js ... menuButtonHtml`)
- precedent — story 106 (cache-busting de l'entry), backlog id 106

## Notes

- Decision: contournement 0.15.4 = helpers dans l'entry (utilisateur informé) ; la solution générale est différée (2026-10-10).
- Open question: hash de contenu servi par le backend vs paramètre de version réécrit dans les specifiers d'import au chargement — à trancher au raffinage.
