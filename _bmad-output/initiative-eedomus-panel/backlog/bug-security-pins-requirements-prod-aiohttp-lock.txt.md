---
id: 120
type: bug
title: "Security pins : requirements_prod.txt (aiohttp 3.14.3 vulnérable, embarqué dans le paquet HACS) et requirements.lock périmé"
parent: none
covers: []
after: []
assignee: ""
refined: true
hitl: false
risk: medium
severity: P2
---

# Security pins : requirements_prod.txt (aiohttp 3.14.3 vulnérable, embarqué dans le paquet HACS) et requirements.lock périmé

## Description

Le lot de dépendances 0.15.5 (commit 13f8de6) a mis à jour requirements.txt, requirements_dev.txt, requirements-test.txt et pyproject.toml, mais a manqué deux fichiers : `requirements_prod.txt`, qui épingle encore `aiohttp==3.14.3` — pile dans la plage vulnérable des 8 alertes aiohttp ouvertes (CVE-2026-111064 serveur sans timeout initial, CVE-2026-111066 épuisement de FD multipart, GHSA-2g87-pp6c-29x5 mémoire non bornée, CVE-2026-111750 request smuggling, et les medium/low associées) — et `requirements.lock`, qui traîne un `aiohttp==3.9.3` pré-historique. Le point aggravant : `release.yml:48` copie `requirements_prod.txt` dans le paquet HACS — la release 0.15.5 embarque donc un fichier avec un pin vulnérable (inerte pour l'installation, qui passe par le manifest, mais livré tel quel aux utilisateurs).

## Reproduction

1. `grep aiohttp requirements_prod.txt requirements.lock` → `aiohttp==3.14.3` et `aiohttp==3.9.3`.
2. Comparer aux plages vulnérables des alertes dependabot ouvertes (`= 3.14.3` : 8 CVE aiohttp).
3. `git show v0.15.5:requirements_prod.txt` → le pin vulnérable est dans le paquet publié.

## Cause Hypothesis

La passe de bumps 0.15.5 n'a ciblé que les fichiers touchés par les PR dependabot visibles à l'époque ; requirements_prod.txt et requirements.lock ne l'ont jamais été par dependabot sur cette branche (alertes scannées sur main) et le lock n'est référencé par aucun workflow — trou de couverture du balayage manuel.

## Acceptance Criteria

1. **Aucun pin vulnérable sur la ligne de release**
   **Given** les fichiers d'exigences d'unstable (requirements.txt, requirements_dev.txt, requirements_prod.txt, requirements-test.txt, pyproject.toml, et requirements.lock s'il survit)
   **When** chaque pin est comparé aux plages vulnérables des alertes dependabot ouvertes (aiohttp = 3.14.3, black = 26.10.0, et toute nouvelle alerte du moment)
   **Then** aucun pin ne tombe dans une plage vulnérable — requirements_prod.txt passe à aiohttp==3.14.5 au minimum
2. **requirements.lock traité explicitement**
   **Given** le lock épingle aiohttp==3.9.3 et n'est consommé par aucun workflow ni script
   **When** le ticket est joué
   **Then** il est soit régénéré depuis les exigences courantes, soit supprimé comme artefact mort — la décision est consignée dans le plan, pas laissée en silence
3. **Le paquet HACS est propre**
   **Given** la coupe 0.15.6
   **When** release.yml construit le paquet
   **Then** le requirements_prod.txt embarqué ne porte plus aucun pin vulnérable
4. **Tests couvrent la condition corrigée**
   **Given** la suite unitaire
   **When** elle tourne
   **Then** un test de garde balaye les fichiers d'exigences suivis et échoue si un pin tombe dans une plage vulnérable connue du ticket (liste explicite des plages dans le test)

## References

- alerts — GitHub Dependabot, alerts #49-#74 (https://github.com/Dan4Jer/hass-eedomus/security/dependabot)
- code — .github/workflows/release.yml:48 (requirements_prod.txt copié dans le paquet)
- commit — 13f8de6 (lot 0.15.5 : les fichiers bumpés, pour contraste)

## Notes

- Decision: périmètre 0.15.6 (utilisateur, 2026-11-01).
- Open question: requirements.lock — régénérer (à quelle source ?) ou supprimer ? Trancher au raffinage ; défaut proposé par l'architecte : supprimer, c'est un artefact mort.
- Exposition réelle mesurée : le chemin d'attaque du CVE black (GitHub Action psf/black avec use_pyproject) n'est PAS utilisé par ce repo (lint.yml fait pip install + black --check en direct) ; les CVE aiohttp côté serveur concernent les vues webhook/api_proxy de l'intégration — en LAN derrière une allowlist IP, l'exposition réelle est faible mais réelle. Les deux se corrigent par le pin, à coût nul.
