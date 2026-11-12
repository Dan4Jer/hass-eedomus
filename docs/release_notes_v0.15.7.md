# Release Notes - Version 0.15.7 / Notes de version - Version 0.15.7

## English

### Bug Fixes

- **Panel module graph cache-busting (ticket 118)** — 0.15.5 shipped a live
  `SyntaxError`: only the entry URL carried `?v=`, so a new import in a panel
  module broke against the browser-cached entry (a URL's query does not reach
  a module's own imports, RFC 3986 drops the base query). Every served JS file
  (the entry and each panel module) now goes through a `PanelEntryView`
  registered before the static path, with its relative import specifiers
  rewritten to carry `?v=<manifest version>`. A new import in any module is
  safe on reload.
- **YAML editor scroll zone (ticket 122, issue #138)** — the flex wrap had no
  fixed height, so the line-number gutter stretched it and the highlight
  overlay showed more lines than the editable textarea. The wrap now owns a
  fixed 420px box (user-resizable); gutter, highlight and textarea all fill
  that one box and only the textarea scrolls. Contract pinned by
  `tests/js/test-regles-styles.js`, wired into CI.
- **`cleanup_unused_entities` safety guard (ticket 123, issue #136 follow-up)** —
  registry entries with `disabled_by: user` are never removed: deleting them
  erased the disable flag, so at the next setup the peripheral recreated its
  entity ENABLED (on the reporter's install ~576 deliberately-disabled
  peripherals would have resurrected at once). They are counted separately in
  the service response as `skipped_user_disabled: N`. Entries disabled by the
  integration itself (`disabled_by: integration`) remain cleanable. New
  `dry_run: true` field (boolean selector in the service UI, EN/FR labels)
  lists what would be removed without removing anything. The service response
  is now actually returned to the caller (`supports_response=OPTIONAL`), and
  the mass-deletion guard (0.15.5) counts only real removals. Verified live on
  the reference Pi: dry run → 0 removed, `changed_states: []`.

### Dependencies / CI

- Dependabot bumps (PR #139–143, dev/test requirements only, no runtime
  impact): pytest-asyncio 1.4.1.post1, mypy 2.4.1, mkdocs-material 9.8.0,
  flake8 7.5.0, websockets >=17.4.
- CI: workflow Python bumped 3.9 → 3.11 (Ubuntu 26.04 runners dropped 3.9);
  test dependencies installed from `requirements-test.txt` instead of a
  hardcoded list.

### Documentation

- Branching model formalized in `docs/CHANGELOG.md`: `unstable` is the trunk,
  `main` is the release mirror (fast-forwarded at every release cut, so
  Dependabot alerts on the default branch scan fixed code).
- `AGENTS.md` audits (exact panel module graph, ticket-118 pitfall, Pi drift
  pitfall) and the simulator epic retrospective.

### Technical

- 481 unit tests, 3 strict JS harnesses, pre-push format gate
  (black 26.10.1 + isort 9.0.2) — all green; fixes deployed and live-validated
  on the reference Pi.
- Release pipeline: `main` fast-forwarded to the 0.15.7 tagged state.

---

## Français

### Corrections

- **Cache-busting du graphe de modules du panneau (ticket 118)** — la 0.15.5
  embarquait un `SyntaxError` en live : seule l'URL d'entrée portait `?v=`,
  donc un nouvel import dans un module du panneau cassait contre l'entrée
  mise en cache par le navigateur (la query d'une URL n'atteint pas les
  imports propres d'un module, la RFC 3986 supprime la query de base). Chaque
  fichier JS servi (l'entrée et chaque module du panneau) passe désormais par
  une `PanelEntryView` enregistrée avant le chemin statique, avec ses
  spécificateurs d'import relatifs réécrits pour porter `?v=<version du
  manifest>`. Un nouvel import dans n'importe quel module est sans danger au
  rechargement.
- **Zone de défilement de l'éditeur YAML (ticket 122, issue #138)** — le wrap
  flex n'avait pas de hauteur fixe : la gouttière de numéros de ligne
  l'étirait et la surcouche de coloration affichait plus de lignes que la
  zone réellement éditable. Le wrap possède désormais une boîte fixe de 420px
  (redimensionnable par l'utilisateur) ; gouttière, surcouche et textarea
  remplissent cette seule boîte et seul le textarea défile. Contrat épinglé
  par `tests/js/test-regles-styles.js`, intégré à la CI.
- **Garde-fou de `cleanup_unused_entities` (ticket 123, suite de l'issue #136)**
  — les entrées du registre avec `disabled_by: user` ne sont jamais supprimées
  : les supprimer effaçait le drapeau de désactivation, et au setup suivant le
  périphérique recréait son entité ACTIVÉE (chez le rapporteur, ~576
  périphériques désactivés volontairement seraient ressuscités d'un coup).
  Elles sont comptées à part dans la réponse du service :
  `skipped_user_disabled: N`. Les entités désactivées par l'intégration
  elle-même (`disabled_by: integration`) restent nettoyables. Nouveau champ
  `dry_run: true` (sélecteur booléen dans l'UI du service, libellés EN/FR) :
  liste ce qui serait supprimé sans rien supprimer. La réponse du service est
  désormais réellement renvoyée à l'appelant (`supports_response=OPTIONAL`),
  et le garde-fou de suppression de masse (0.15.5) ne compte que les vraies
  suppressions. Vérifié en live sur le Pi de référence : dry run → 0
  suppression, `changed_states: []`.

### Dépendances / CI

- Bumps Dependabot (PR #139–143, exigences dev/test uniquement, aucun impact
  runtime) : pytest-asyncio 1.4.1.post1, mypy 2.4.1, mkdocs-material 9.8.0,
  flake8 7.5.0, websockets >=17.4.
- CI : Python du workflow passé de 3.9 à 3.11 (les runners Ubuntu 26.04 ont
  supprimé 3.9) ; dépendances de test installées depuis
  `requirements-test.txt` au lieu d'une liste codée en dur.

### Documentation

- Modèle de branches formalisé dans `docs/CHANGELOG.md` : `unstable` est le
  trunk, `main` est le miroir de release (fast-forwardé à chaque coupe de
  release, pour que les alertes Dependabot de la branche par défaut scannent
  du code corrigé).
- Audits `AGENTS.md` (graphe exact des modules du panneau, piège du ticket
  118, piège de dérive du Pi) et rétrospective de l'épique simulateur.

### Technique

- 481 tests unitaires, 3 harnais JS stricts, porte de formatage pre-push
  (black 26.10.1 + isort 9.0.2) — tout est vert ; correctifs déployés et
  validés en live sur le Pi de référence.
- Pipeline de release : `main` fast-forwardé vers l'état taggé 0.15.7.
