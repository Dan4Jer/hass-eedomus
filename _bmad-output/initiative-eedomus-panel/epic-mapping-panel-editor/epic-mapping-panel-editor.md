---
type: epic
title: "Éditeur de mapping eedomus (side panel complet)"
parent: initiative-eedomus-panel
covers: [CAP-1, CAP-2, CAP-3, CAP-4, CAP-5]
after: []
assignee: ""
risk: medium
---

# Éditeur de mapping eedomus (side panel complet)

## Description

Le panneau Eedomus Config s'affiche dans la sidebar (API supportée), liste les périphériques avec leur mapping, permet l'édition des règles custom (formulaire + YAML, autocomplete, validation temps réel), sauvegarde avec auto-apply, et gère l'historique des 3 dernières versions avec diff coloré et restauration confirmée.

## Outcome

Le success signal du spec : un utilisateur comme celui de la discussion #28 corrige type et unité d'un capteur depuis la sidebar, sans YAML, et voit le changement appliqué immédiatement.

## Requirements

- CAP-1: Panneau sidebar via l'API supportée HA 2026.9.3 (async_register_built_in_panel + StaticPathConfig), require_admin, retrait propre à l'unload. (spec, Capabilities)
- CAP-2: Liste des périphériques avec usage_id, nom, mapping courant, recherche/filtre. (spec, Capabilities)
- CAP-3: Édition des règles en double mode (formulaire + YAML), autocomplete, validation temps réel via le websocket existant. (spec, Capabilities)
- CAP-4: Sauvegarde dans custom_mapping.yaml via config_manager + auto-apply (reload). (spec, Capabilities)
- CAP-5: Historique des 3 dernières versions (.storage, horodatées), diff type git, restauration confirmée. (spec, Capabilities)

## Done when

1. Le panneau s'affiche/supprime proprement (CAP-1) — aucune API inventée, frontend.yaml supprimé.
2. Le parcours #28 (mock-01 → mock-02 → save → entité corrigée) fonctionne bout en bout sur l'instance.
3. Le diff respecte le traitement C1 : texte --primary-text-color, sémantique par fond teinté + préfixes +/-/~ + barre, ≥4.5:1 clair et sombre (bascule des mocks).
4. Le mode YAML vendorisé passe le critère M9 (clavier, AT, erreurs aria-live) et la bascule formulaire↔YAML est sans perte.
5. Restauration en un clic avec confirmation « le mapping actuel sera archivé » ; 4e save purge la plus ancienne.
6. Suite E2E étendue panel + validation production passées.

## Boundaries

Le panneau et son socle (ui_service, panel.py, www/, config_manager). Pas le backfill (initiative-eedomus-history), pas l'entity registry, aucune écriture box. Non-goals du spec.

## References

- parent — _bmad-output/initiative-eedomus-panel/initiative-eedomus-panel.md
- spec — _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md (5 CAPs, contraintes, non-goals)
- ux — _bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/DESIGN.md et EXPERIENCE.md (tokens, composants, états, flux) + mockups/ (3 écrans, bascule clair/sombre)
- architecture — _bmad-output/planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md (AD-7, AD-9, AD-10)

## Notes

- Decision: ticket 1 avant tout — le backend websocket existe déjà, il n'est juste jamais appelé ; brancher avant de construire.
- Tracer bullet: le ticket 3 livre la liste visible dans le panel réel — premier écran tangible.
- Unknown: lib YAML (ticket 5) — sélection selon le critère M9, repli textarea si aucune ne passe.
- Decision: build en bmad-build interactif (pattern du ticket 1.1 history), un downtime seulement au ticket 7 (déploiement).
