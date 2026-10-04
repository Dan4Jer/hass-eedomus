---
type: epic
title: "Onglet Cohérence (vérification du mapping eedomus ↔ HA)"
parent: initiative-eedomus-panel
covers: [CAP-6, CAP-7, CAP-8]
after: []
assignee: ""
risk: medium
---

# Onglet Cohérence (vérification du mapping eedomus ↔ HA)

## Description

Un 4e onglet du panneau Eedomus Config présente le tableau de cohérence du mapping : tous les ~165 périphériques eedomus, triés et filtrables, avec leurs signaux de statut (sans entité HA, mapping douteux, règle active, en erreur), un détail riche par périphérique (popover desktop / ligne étendue mobile) et un lien vers les réglages standard de l'entité HA. Vue strictement en lecture : elle signale et relie vers où corriger, l'édition reste dans l'onglet Règles. Le spec `spec-eedomus-mapping-panel` porte les CAP-6/7/8 ; les spines UX (DESIGN.md / EXPERIENCE.md, mises à jour 2026-10-04) portent les composants, états et flux.

## Outcome

Le signal du spec : un utilisateur comme celui de la discussion #28 sait, d'un coup d'œil sur l'onglet Cohérence, quels périphériques demandent une vérification de mapping — et corrige depuis les liens que la vue lui donne.

## Requirements

- CAP-6: Vue de cohérence — tableau triable des ~165 périphériques (periph_id, nom, entité HA cliquable, type/sous-type, puces de statut), en-tête collant, filtre rapide, bascule « Tout afficher » / « À vérifier » ; 4 signaux cumulables dérivés côté backend ; lecture seule, point d'entrée. (spec, Capabilities)
- CAP-7: Détail périphérique — popover desktop / ligne étendue mobile en parité de contenu stricte : état vivant, identité de mapping (ha_entity, ha_subtype, justification), actions correctif inline, raw API repliable ; opérable au clavier. (spec, Capabilities)
- CAP-8: Navigation vers les réglages d'entité HA — lien texte inline vers la page de réglages standard de l'entité (fonctionnement standard HA, web et mobile), aucune édition du registry. (spec, Capabilities)

## Done when

1. `eedomus/get_coherence` répond sur l'instance live avec une ligne par périphérique (~165, aucune perdue) et des signaux corrects sur des cas réels (periph sans entité, en retry, règle active).
2. L'onglet Cohérence affiche le tableau complet — tri par colonne (aria-sort), filtre rapide, bascule avec compte — opérable au clavier, états squelette/erreur/vide positif conformes à EXPERIENCE.md.
3. Parité de contenu stricte popover desktop / ligne étendue mobile (≥ 900px / < 900px), popover focusable (Échap, focus rendu, aria-expanded, une seule ouverte).
4. Le clic sur une entité ouvre les réglages standard HA (web et mobile) ; les chips portent leur sens par glyphe + libellé, jamais la couleur seule, clair et sombre.
5. Suite E2E panel étendue (cohérence incluse) verte sur l'instance déployée ; déploiement validé par les logs (chargement différé, pas d'erreur websocket).

## Boundaries

Le panneau (ui_service, www/eedomus-panel.js, mapping_registry en lecture) et une nouvelle commande websocket de lecture. Pas de backfill (initiative-eedomus-history), pas d'édition du mapping ni du registry depuis cette vue (onglet Règles uniquement), aucune écriture box, `get_peripherals` inchangé. Non-goals du spec.

## References

- parent — _bmad-output/initiative-eedomus-panel/initiative-eedomus-panel.md
- spec — _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md (CAP-6, CAP-7, CAP-8, contrainte get_coherence)
- ux — _bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/DESIGN.md et EXPERIENCE.md (onglet Cohérence : coherence-table, coherence-chip-*, periph-popover, entity-link, sort-header, Responsive, Flow 3)
- architecture — _bmad-output/planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md (AD-7, AD-8, AD-9)

## Notes

- Decision: tracer bullet = entrée 1 (commande get_coherence) — elle prouve la jointure registry × périphériques et la dérivation des signaux, et tout le frontend en dépend (user, 2026-10-04).
- Decision: lane JS séquentielle (3 → 4 → 5 → 6 chaînées) — un seul fichier eedomus-panel.js, aucun risque de collision (user, 2026-10-04).
- Decision: build non assisté (bmad-build-auto), un run par ticket ; plan_checkpoint sur les entrées 1, 4 et 6 (risque élevé : jointure backend, accessibilité popover, navigation HA) (user, 2026-10-04).
- Decision: suite E2E de clôture (entrée 8) après le sweep — pattern de l'épique 1, validation post-déploiement du projet (user, 2026-10-04).
- Unknown: la navigation vers la page de réglages standard d'une entité depuis un panneau custom (CAP-8) — mécanisme HA exact à confirmer à l'entrée 6 (route navigate/more-info vs lien direct) ; le plan_checkpoint de l'entrée 6 couvre ce risque.
- Unknown: glyphes des chips — laissés à l'implémentation (assumption du spec : un glyphe distinct par signal, redondant avec le libellé).
