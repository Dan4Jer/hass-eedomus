---
title: "Fix 122 — éditeur YAML Règles : zone affichée = zone modifiable"
type: 'bugfix'
ticket: 122
created: 2026-11-01
status: done
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['lens-122-quick']
review_loop_iteration: 0
context: []
baseline_revision: '8a14a25'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Issue #138 — dans le panneau Règles/YAML, 30 lignes sont affichées mais seules les ~21 premières sont modifiables : la scrollbar du textarea s'arrête à la ligne 21. Cause racine (investiguée) : `.yaml-editor-wrap` (flex, `overflow: hidden`) n'a pas de hauteur fixe — elle vient du textarea en flux (`min-height: 420px` ≈ 21 lignes à line-height 1.5 + padding). La `.yaml-gutter` en flux contient 30 numéros de ligne (`white-space: pre`), ce qui étire le wrap ; le `pre.yaml-highlight` en `absolute inset:0` épouse alors toute la hauteur du wrap et affiche les 30 lignes, tandis que le textarea reste sur sa propre boîte de 420px. Affiché ≠ modifiable.

**Approach:** donner au wrap une hauteur fixe (`height: 420px`, `resize: vertical` déplacé sur le wrap) et faire remplir cette hauteur identique aux trois enfants — gutter, code-area (donc le pre absolu), et textarea (`height: 100%`, `min-height: 0`, `resize: none`) — avec scroll unique sur le textarea, le pre/gutter restant synchronisés par `_syncYamlScroll` (déjà en place). Les fichiers repo gardent des specifiers simples (AD-17).

</frozen-after-approval>

## Implementation Notes

Oneshot rationale : ~15 lignes de CSS dans `RULES_STYLES` (`custom_components/eedomus/www/panel/regles.js`) + un test de contrat JS ; aucun changement de logique métier, un seul fichier produit + un harness de test.

Key decisions:
- `.yaml-editor-wrap` : remplacer la hauteur implicite par `height: 420px; resize: vertical; overflow: hidden;` (le redimensionnement utilisateur reste possible, sur le wrap, et reste cohérent).
- `.yaml-gutter` : `overflow: hidden` (son scrollTop est déjà synchronisé).
- `.yaml-highlight` : inchangé (`absolute inset: 0`), son `overflow: auto` devient `hidden` (sync manuel).
- `.yaml-editor` : `height: 100%; min-height: 0; resize: none;` — le textarea remplit exactement la boîte partagée, sa scrollbar couvre toutes les lignes.
- Test de contrat : nouveau harness `tests/js/test-regles-styles.js` qui lit `regles.js` et épingle le contrat (wrap a une hauteur fixe, textarea `height: 100%` + `resize: none`, pre/gutter sans hauteur propre) ; câblé dans `.github/workflows/tests.yml` à côté des deux harness existants.
- Ne pas toucher : `_syncYamlScroll` (déjà correct), la logique de save/validation YAML, les traductions.

## Review Triage Log

Quick lens (lens-122-quick, 2026-11-01), 3 findings :
- **fixed** — docstring du harness contenait « Règles » (policy English-only, AGENTS.md) → remplacé par « Rules » ; grep repo = 0 occurrence restante.
- **fixed** — le contrat promis (pre/gutter sans hauteur propre) n'était pas épinglé → 2 assertions ajoutées ; faux positif initial `line-height:` contourné par un regex borné `(^|[;\s])height:`.
- **accepted-as-is (deferred)** — aucune couverture automatisée de la géométrie rendue : impossible sans mocker le Pi (AD-16 interdit), le repo n'a pas de strate de test layout. Le critère utilisateur reste couvert par le contrôle manuel post-déploiement (30 lignes, toutes modifiables).

## Verification

**Commands:**
- `node tests/js/test-regles-styles.js` — passe (contrat CSS épinglé).
- `node tests/js/test-coherence.js` et `node tests/js/test-i18n-guard.js` — verts (fichiers panel non modifiés hors styles).
- `python3 -m pytest tests/unit/ -q` — 478+ verts (aucun changement Python).
- `bash scripts/hooks/pre-push` — exit 0.
- Manuel (post-déploiement Pi) : éditeur YAML avec 30 lignes — toutes les lignes affichées sont modifiables, la scrollbar couvre les 30 lignes.
