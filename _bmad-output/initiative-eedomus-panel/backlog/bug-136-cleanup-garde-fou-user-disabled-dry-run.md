---
id: 123
type: bug
title: "136 — cleanup_unused_entities : ne pas supprimer les entités disabled_by:user, les compter à part, et ajouter un mode dry_run"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: medium
severity: P2
---

# 136 — cleanup_unused_entities : protéger les entités disabled_by:user + dry_run

## Description

Le service `eodomus.cleanup_unused_entities` (corrigé en v0.15.5 pour les 3 défauts de l'issue #136) retire aujourd'hui toutes les entités désactivées sans distinguer leur origine. Or `disabled_by: user` signifie une désactivation volontaire de l'utilisateur : supprimer l'entrée de registre efface le drapeau, et au setup suivant les périphs recréent leurs entités **activées** — chez le rapporteur, ~576 entités indésirables ressusciteraient d'un coup (périphs renommés « [Invisible] », capteurs History Progress désactivés à la main, entités miroir de renvois HA→eedomus dont la réactivation recréerait une boucle de rétroaction).

## Reproduction

1. Instance v0.15.6, 2 boxes, ~800 périphs, ~576 entités eedomus désactivées dont une large majorité `disabled_by: user`.
2. Lancer l'action `eedomus.cleanup_unused_entities`.
3. Actual : les entrées `disabled_by: user` sont supprimées comme les autres. Expected : elles sont laissées en paix (ou comptées à part dans la réponse), et un mode simulation liste sans supprimer.

## Cause Hypothesis

Le handler de nettoyage (services.py, boucle de suppression ~:367-383) ne filtre pas sur `disabled_by` de l'entrée de registre avant suppression.

## Acceptance Criteria

1. **The expected behavior holds**
   **Given** des entités eedomus dont l'entrée de registre a `disabled_by: user`
   **When** `eodomus.cleanup_unused_entities` s'exécute
   **Then** ces entrées ne sont pas supprimées, et la réponse du service les compte séparément (ex. `skipped_user_disabled: N`)
2. **Dry run**
   **Given** l'appel du service avec `dry_run: true`
   **When** il s'exécute
   **Then** il liste ce qui serait supprimé sans rien supprimer, et la réponse le dit explicitement
3. **Tests cover the condition found and fixed**
   **Given** the unit suite
   **When** it runs
   **Then** a test pins la protection `disabled_by: user`, le comptage séparé, et le mode dry_run

## References

- github — issue #136, commentaire du 2026-11-12 (Ecirbaf69) : https://github.com/Dan4Jer/hass-eedomus/issues/136#issuecomment-6817231619
- code — custom_components/eedomus/services.py (handler cleanup, boucle ~:367-383)
- precedent — fix v0.15.5 des 3 défauts originels de #136 (garde-fou de suppression de masse déjà en place)

## Notes

- Decision: le rapporteur demande « laisser en paix » les `disabled_by: user`, a minima un comptage séparé ; le mode dry_run est « idéalement » — à confirmer au raffinage si les deux landent ensemble ou séparément.
