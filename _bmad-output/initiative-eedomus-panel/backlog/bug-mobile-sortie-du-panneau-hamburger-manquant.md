---
id: 116
type: bug
title: "Mobile : impossible de sortir du panneau eedomus (pas de hamburger, sidebar masquée)"
parent: none
covers: []
after: []
assignee: ""
refined: true
hitl: false
risk: medium
severity: P2
---

# Mobile : impossible de sortir du panneau eedomus (pas de hamburger, sidebar masquée)

## Description

Sur mobile ou tablette, l'utilisateur qui ouvre le panneau « Eedomus Config » n'a plus aucun moyen d'en sortir : HA ne rend aucun app-header pour les panels custom et masque la sidebar permanente sur viewport étroit. Les pages natives de HA montrent un hamburger (ou une flèche back) en haut à gauche ; le panneau n'en montre aucun. Rapporté avec captures à l'appui par Ecirbaf69 (issue #125).

## Reproduction

1. Sur un appareil à viewport étroit (mobile/tablette, ou fenêtre de navigateur < 900 px), ouvrir le panneau « Eedomus Config » depuis le menu de HA.
2. Actual : la page se rend, mais aucun hamburger ni flèche n'apparaît — la sidebar est masquée et il n'y a pas de sortie (sauf geste navigateur/app).
3. Expected : un hamburger en haut à gauche ouvre le drawer de HA, comme sur les autres pages.

## Cause Hypothesis

La route `panel_custom` de HA ne rend pas d'app-header : sur viewport large la sidebar permanente masque le problème ; sur viewport étroit HA délègue la sortie au hamburger de chaque page, et le panneau n'en a pas. Précédent : HACS issue #1187.

## Acceptance Criteria

1. **Le hamburger ouvre le drawer sur viewport étroit**
   **Given** le panneau ouvert sur un viewport étroit (< 900 px)
   **When** la page se rend puis l'utilisateur active le bouton menu
   **Then** un bouton hamburger est visible en tête du panneau et son activation dispatche l'événement standard `hass-toggle-menu` (bubbles + composed) — le drawer de HA s'ouvre
2. **Viewport large : pas de bouton redondant**
   **Given** le panneau ouvert sur un viewport large (sidebar permanente visible)
   **When** la page se rend
   **Then** le bouton menu est masqué (media query sur la même constante étroite que la cohérence, aucun nouveau breakpoint)
3. **Étiquette et cibles accessibles**
   **Given** le bouton rendu
   **Then** son `aria-label` vient du catalogue i18n (`panel.menu.aria`, EN source + FR traduit) et sa cible est ≥ 44 px
4. **Tests couvrent la condition corrigée**
   **Given** la suite node des helpers purs
   **When** elle tourne
   **Then** des tests couvrent le markup du bouton (aria-label, data-action) et la règle media CSS — ils échouent avant le correctif et passent après
5. **Ou : pas de changement nécessaire, preuve à l'appui**
   **Given** la reproduction
   **When** jouée sur le code actuel
   **Then** le comportement attendu tient déjà, ou le rapport était erroné, preuve en Notes — prime sur 1-4

## References

- issue — https://github.com/Dan4Jer/hass-eedomus/issues/125 (captures : page native avec hamburger vs page panneau sans sortie)
- experience — _bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md (Foundation, Interaction Primitives « Menu », Responsive « Sortie mobile »)
- code — custom_components/eedomus/www/eedomus-panel.js (render shell, `.tabs`), custom_components/eedomus/www/panel/coherence-helpers.js (`COHERENCE_NARROW_PX`), custom_components/eedomus/panel_translations.py (catalogues EN/FR)
- precedent — https://github.com/hacs/integration/issues/1187

## Notes

- Decision: option A retenue (hamburger propre au panneau dispatchant `hass-toggle-menu`), périmètre 0.15.4 (utilisateur, 2026-10-10).
- Open question: `hass-toggle-menu` est une interface interne de HA — vérifier le nom contre le source HA 2026.9 au moment du fix ; le E2E live sur le Pi confirme l'ouverture réelle du drawer.
