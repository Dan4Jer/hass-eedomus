---
title: 'Suite E2E cohérence'
type: 'chore'
ticket: 8
created: '2026-10-04'
status: 'built'
route: 'oneshot'
route_source: 'auto'
baseline_revision: '9d05f0f'
review: 'none'
review_source: 'pinned'
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

# Suite E2E cohérence — Auto Run Result

Status: built

- Summary: validation live de l'épique sur l'instance déployée (7 commits, bf15686..9d05f0f) : déploiement git-only, redémarrage HA, vérification des logs, suite E2E complète.
- Logs : panneau enregistré à 13:56:34 (admin only), intégration initialisée en ~10 s (cadence AD-2 en vigueur : 4 periphs/cycle, plus de blocage de 180 s), aucune erreur eedomus.
- E2E : `python3 -m pytest tests/e2e/ -v` → **20 passed in 67.50 s** — dont `test_get_coherence_lists_every_peripheral` (appel live de `eedomus/get_coherence` : total > 0, clés de ligne, et **ensembles de periph_id identiques** entre get_coherence et get_peripherals — CAP-6 « jamais une ligne perdue » prouvé sur les ~165 périphériques réels), et `test_identical_save_applies_and_changes_nothing` (le save_mapping autrefois bloquant, toujours vert).
- Review: none (pinned — run opérationnel, aucun code modifié).
- Residual risks (vérification manuelle navigateur, non automatisable sans harnais DOM) : survol/focus du popover desktop, ligne étendue au tactile, ouverture réelle de more-info, chips en thème clair et sombre, barre de tri collante mobile — à l'œil par l'utilisateur dans le panneau.
- État de l'épique : 2.1–2.8 built. Le passage en `done` appartient à l'utilisateur (validation visuelle ci-dessus faite ou non).
