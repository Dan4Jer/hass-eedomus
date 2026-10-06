---
id: SPEC-eedomus-docs
companions: []
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Documentation hass-eedomus — restructuration bilingue

## Why

**Douleur à résoudre.** `docs/` contient 86 fichiers historiques (~18 216 lignes — résumés de fix, analyses de debug, notes de release par version, wireframes) accumulés session après session sans structure ; le README bilingue (160 l.) est la seule vraie documentation utilisateur. Un nouvel utilisateur ne peut pas trouver comment installer, configurer ou écrire une règle de mapping — et l'onglet Règles (CAP-10, story 107) a besoin d'une page canonique de format à lier.

## Capabilities

- **CAP-1 — Jeu canonique bilingue**
  - **intent:** Six pages canoniques EN+FR — Installation, Configuration (options flow), Format du mapping (`docs/mapping-format.md`, cible du lien de l'onglet Règles), Guide du panneau (les 5 onglets), Historique/backfill (activation, reprise, statistics vs timeline brute), Dépannage — chacune distillant l'as-built v0.15.0 et absorbant le contenu pertinent des fichiers historiques.
  - **success:** Un nouvel utilisateur part du README et atteint l'installation complète et le format du mapping en deux clics, dans les deux langues.

- **CAP-2 — Fonds historique archivé**
  - **intent:** Les 86 fichiers historiques déménagent dans `docs/archive/` (arborescence conservée telle quelle), jamais réécrits ; l'index les nomme comme archive sans les lier page par page.
  - **success:** `docs/` ne montre plus que le jeu canonique + l'index + `CHANGELOG.md` + `archive/` ; le git diff montre des déplacements sans réécriture (renames détectés).

- **CAP-3 — Index et navigation**
  - **intent:** `docs/README.md` (EN+FR) indexe le jeu canonique et l'archive ; le README racine lie les pages canoniques ; l'onglet Règles (story 107, CAP-10) pointe `docs/mapping-format.md`.
  - **success:** Aucun lien mort ; l'index rend chaque page trouvable depuis le repo et GitHub.

## Constraints

- Bilingue obligatoire : chaque page canonique existe en EN (source de vérité) et FR (traduction complète) — double maintenance acceptée (décision utilisateur 2026-10-06).
- Les pages reflètent l'as-built v0.15.0 (specs, instance, options flow) — pas les promesses.
- L'archive est déplacée, jamais réécrite ; `CHANGELOG.md` reste en place.
- Markdown servi par GitHub — aucun générateur statique, aucun build.

## Non-goals

- Pas de traduction de l'archive historique.
- Pas de documentation des internals (AGENTS.md et le spine d'architecture les possèdent).
- Pas de restructuration du README au-delà des liens vers le jeu canonique.
- Pas de générateur de site statique (mkdocs/docusaurus) — markdown GitHub seul.

## Success signal

Un nouvel utilisateur part du README, atteint l'installation complète et le format du mapping en deux clics, dans les deux langues — et `docs/` ne montre plus que le jeu canonique, l'index et l'archive.

## Open Questions

- Convention de nommage bilingue : suffixe `.fr.md` à la README (`installation.md` / `installation.fr.md`, recommandé — précédent, liens relatifs simples) ou sous-dossiers `docs/en/` + `docs/fr/` — à trancher au début du build.
