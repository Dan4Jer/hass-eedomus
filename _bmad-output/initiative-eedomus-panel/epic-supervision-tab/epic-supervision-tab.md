---
type: epic
title: "Onglet Supervision — métriques box et pilotage du backfill"
parent: initiative-eedomus-panel
covers: [CAP-9, CAP-5]
after: []   # the wait on epic-i18n lives in the initiative's tickets.toml
assignee: ""
risk: medium
---

# Onglet Supervision — métriques box et pilotage du backfill

## Description

Un 5e onglet du panneau Eedomus Config présente en une vue les informations de la box (temps de refresh, nombre de périphériques, sollicitations de l'API proxy) en graphiques natifs HA, un lien vers le tableau de cohérence, et la visualisation de la file de récupération d'historique en cours avec ses quatre actions (réessayer, prioriser, pause/reprise, ignorer). La vue relève de CAP-9 (spec-eedomus-mapping-panel) ; les données et actions de la file relèvent de CAP-5 (spec-eedomus-history) — le panneau affiche, il ne réimplémente pas le moteur.

## Outcome

Le signal du spec history : l'utilisateur pilote la récupération d'historique depuis le panneau — chaque action produit un retour nominatif, le temps réel n'est jamais bloqué, l'ignorage survit à un redémarrage — et lit l'état de la box en un coup d'œil.

## Requirements

- CAP-9: Onglet Supervision — métriques box en graphiques (composants frontend HA, repli SVG inline thémé), lien Cohérence, vue de la file ; le panneau affiche, le moteur reste dans le coordinator. (spec-eedomus-mapping-panel, Capabilities)
- CAP-5: File de backfill exposée et pilotable — état par périphérique (position, en cours, erreur, ignoré, en pause) + état global ; quatre actions (réessayer maintenant, prioriser, pause/reprise par périph ET interrupteur global, ignorer persisté) via eedomus/<verb>, AD-7. (spec-eedomus-history, Capabilities)

## Done when

1. `eedomus/get_backfill_state` (ou équivalent) rend l'état complet de la file sur l'instance live ; chaque action produit un retour nominatif et la file se re-rend.
2. L'onglet Supervision affiche les métriques en chart cards thémées avec équivalents textuels ; le lien Cohérence bascule d'onglet.
3. L'ignorage survit à un redémarrage HA ; la pause globale stoppe le drain sans casser la reprise (CAP-3 history) ; le temps réel (CAP-2 history) n'est jamais bloqué par une action.
4. Tout l'onglet est localisé via le catalogue (aucune chaîne en dur) — l'épique i18n a livré avant.
5. Déployé et validé sur le Pi : suite E2E verte, actions vérifiées non destructivement, contrôle visuel des graphiques.

## Boundaries

L'affichage et les commandes websocket ; pas de réimplémentation du moteur de backfill (coordinator), pas d'appel direct à l'API eedomus depuis le panneau, pas de nouveau mécanisme de traduction (l'épique i18n a livré le catalogue). Les contrats gelés ne changent pas.

## References

- spec — _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md (CAP-9)
- spec — _bmad-output/specs/spec-eedomus-history/SPEC.md (CAP-5, contraintes AD-2/AD-7)
- ux — _bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md (onglet Supervision, backfill-queue, metric-chart-card, Flow 4)
- regle — AGENTS.md (mécanismes natifs, chaînes via le catalogue)

## Notes

- Decision: pause/reprise par périphérique ET interrupteur global (user, 2026-10-04).
- Decision: ignorage persistant en .storage, destructeur, confirmé, réactivable (user, 2026-10-04).
- Decision: les deux épiques vivent sous initiative-eedomus-panel ; les actions référencent le spec history (user, 2026-10-04).
- Decision: build non assisté (bmad-build-auto), plan_checkpoint sur 4.1 (les 4 actions touchent le moteur) et 4.3 (l'UI de contrôle) (user, 2026-10-04).
- Decision: après epic-i18n — l'onglet naît directement localisé (user, 2026-10-04).
- Unknown: disponibilité des composants graphiques HA dans le contexte du panneau — repli SVG inline thémé prévu par la spine UX ; à trancher au plan_checkpoint de 4.2.
