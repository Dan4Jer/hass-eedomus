---
title: "P.1.10 Option d'activation du panneau dans l'OptionsFlow"
type: 'feature'
ticket: 10
created: '2026-09-28'
status: done
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
baseline_revision: '5440932'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Le panneau Eedomus Config est enregistré inconditionnellement — l'utilisateur ne peut pas le retirer de la sidebar sans désinstaller l'intégration.

**Approach:** Option `enable_panel` dans l'OptionsFlow (AD-9 : options > data > défaut, False explicite honoré, défaut activé). Au chargement de l'entry : activée → enregistrement idempotent ; désactivée → retrait d'un éventuel panneau déjà enregistré. Le changement d'option recharge l'entry via l'update listener existant, qui réévalue le gate.

</frozen-after-approval>

## Implementation Notes

- `const.py` : `CONF_ENABLE_PANEL = "enable_panel"`, `DEFAULT_ENABLE_PANEL = True`.
- `__init__.py` : gate en lieu et place de l'appel inconditionnel — `_get_config_value(entry, CONF_ENABLE_PANEL, DEFAULT_ENABLE_PANEL)` ; si activé → `async_setup_panel` (idempotent), sinon → `async_unload_panel` (retire un panneau d'un chargement précédent).
- `options_flow.py` : champ booléen dans le formulaire init + persistance dans les options sauvegardées (aux côtés de enable_api_proxy).
- L'update listener existant recharge l'entry à chaque soumission d'options → le gate rejoue : activé→désactivé retire le panneau, désactivé→activé le remet.
- Test : entry avec `options={"enable_panel": False}` → `async_setup_panel` jamais appelé, `async_unload_panel` appelé (le False explicite est honoré, AD-9).

## Review Triage Log

Review quick (self), itération 1 :

- [checked] `_get_config_value` honore un `False` explicite (test du `is not None`) — le bug du falsy check est couvert par le test AD-9 historique.
- [checked] Multi-box : le panneau est un état de domaine — la désactivation depuis n'importe quelle entry le retire (le gate unload est idempotent).
- [low, defer] Pas d'option par entrée distincte (le panneau est de niveau domaine) — documenté dans le gate.

## Verification

**Commands:**

- `python3 -m pytest tests/unit -q` -- expected: 152 verts (dont 1 nouveau gate)
- `python3 -m pytest tests/e2e -q` -- expected: 19 verts

**Manual checks (déploiement requis) :**

- L'option apparaît dans l'OptionsFlow ; désactivée puis soumise, le panneau disparaît de la sidebar après le reload ; réactivée, il revient
