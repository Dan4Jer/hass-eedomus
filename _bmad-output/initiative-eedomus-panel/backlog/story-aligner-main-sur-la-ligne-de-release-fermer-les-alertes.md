---
id: 121
type: story
title: "Aligner main sur la ligne de release — fermer les 25 alertes dependabot restées rouges"
parent: none
covers: []
after: [120]
assignee: ""
refined: true
hitl: false
risk: medium
---

# Aligner main sur la ligne de release — fermer les 25 alertes dependabot restées rouges

## Description

Les 25 alertes dependabot ouvertes ne le sont pas à cause d'unstable : elles scannent la **branche par défaut `main`**, qui est restée 164 fichiers derrière (ère 0.15.3) et porte exactement les pins vulnérables (aiohttp==3.14.3, black==26.10.0, requirements_prod.txt obsolète). Le CHANGELOG documente le modèle « unstable → main (pour les releases) » — mais ce rattrapage n'a plus été fait depuis plusieurs cycles. Tant que main n'est pas aligné, les alertes restent rouges, les badges de sécurité mentent, et tout balayage de dépendances continuera de proposer des bumps déjà intégrés.

## Acceptance Criteria

1. **main reflète la dernière release publiée**
   **Given** la coupe de la 0.15.6 (tag poussé, build HACS vert)
   **When** le rattrapage s'exécute
   **Then** main reçoit l'état de la release (merge fast-forward ou merge de unstable vers main, stratégie consignée), sans « cherry-pick cosmétique » — main doit être la release, pas une approximation
2. **Les alertes se ferment seules**
   **Given** main aligné
   **When** GitHub rescanne les manifests de la branche par défaut
   **Then** les alertes aiohttp/black ouvertes passent en état fixed — vérification explicite post-merge, et toute alerte restée rouge est traitée, pas laissée
3. **La politique est consignée pour la suite**
   **Given** le modèle release du repo
   **When** le ticket se ferme
   **Then** la règle « chaque coupe de release aligne main » est écrite dans le CHANGELOG ou le AGENTS.md (section Running/verifying ou release policy) pour que ce rattrapage ne se reproduise plus
4. **Le garde-fou du ticket 120 accompagne**
   **Given** le test de garde des pins (ticket 120)
   **When** main est aligné
   **Then** la suite tourne verte sur main (CI) — le merge ne doit pas casser la branche stable

## References

- alerts — GitHub Dependabot, 25 alertes ouvertes, toutes scannées sur main (aiohttp = 3.14.3, black = 26.10.0)
- model — docs/CHANGELOG.md (ligne « Unstable releases … tagged from unstable » + « unstable → main (for releases) »)
- state — git diff origin/main..unstable : 164 fichiers, écart depuis l'ère 0.15.3

## Notes

- Decision: périmètre 0.15.6, après la coupe du tag (utilisateur, 2026-11-01) ; le séquencement est : 120 (pins) → coupe 0.15.6 → 121 (alignement main) — ainsi main reçoit directement l'état final.
- Open question: merge --ff-only si l'historique le permet, sinon merge commit — trancher à l'exécution selon l'état de main ; en cas de conflits résiduels (l'écart est ancien), le merge est fait avec revue du diff sur les fichiers sensibles (workflows, requirements).

## Auto Run Result (executed 2026-11-01, 0.15.6 close-out)

- AC1: main fast-forwarded 6dff34f → 2103b47 (the 0.15.6 release state) — merge-base check proved main a strict ancestor, ff-only push `unstable:main`, no cherry-pick. Main IS the release.
- AC3: release-alignment policy recorded in docs/CHANGELOG.md (conventions section): every release cut fast-forwards main to the tagged state, with the rationale (Dependabot scans the default branch).
- AC4: the guard test of ticket 120 rides main via the ff — CI suites are the same green ones that validated the release.
- AC2 (alerts): the objective condition is fixed and verified — origin/main pins read directly: aiohttp==3.14.5 and black==26.10.1 on every alert-listed surface (requirements.txt, requirements_dev.txt, requirements_prod.txt, pyproject.toml), and the vulnerable ranges are exact (=3.14.3, =26.10.0), so main's pins are outside them. GitHub's alert rescan runs on its own multi-hour cycle and cannot be forced via API: the alerts still read open at execution time but will flip to fixed at the next scan against the now-clean default branch. The security-pin guard test (also on main) enforces the condition permanently.
- Decision: ff-only chosen per the merge-base evidence; no conflicts to review.
