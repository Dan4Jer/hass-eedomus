---
id: SPEC-eedomus-history
companions: [../../planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md]
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Historique eedomus dans Home Assistant — backfill statistics horaires

## Why

**Douleur à résoudre + opportunité à saisir.** Le cloud eedomus détient des années d'historique des périphériques, et l'intégration crée bien les entités HA correspondantes — mais HA n'affiche l'historique que depuis l'installation de l'intégration. Le SDK Home Assistant n'offre toujours pas (y compris en 2026.9) d'API pour écrire l'historique *brut* des entités ; l'implémentation actuelle contourne ce manque en hackant la state machine (`async_set` avec timestamps passés, entités fantômes, double-import), ce qui pollue le recorder et bloque le refresh temps réel (mesuré : 195 s d'history sur un cycle de 196 s — les lumières mettaient des minutes à réagir). HA 2026 offre enfin une voie officielle durable — les statistics horaires, non purgées — qui rend le backfill à la fois possible et propre. Les AD cités sont ceux du companion `ARCHITECTURE-SPINE.md`.

## Capabilities

- **CAP-1 — Backfill statistics horaires**
  - **intent:** Importer tout l'historique cloud eedomus des capteurs numériques en statistics horaires HA (mean/min/max par heure), sans jamais toucher à la state machine.
  - **success:** Les graphs long-terme des capteurs eedomus (températures, consommations…) affichent l'historique antérieur à l'installation de HA ; aucune entité fantôme `sensor.eedomus_*` n'est créée.

- **CAP-2 — Temps réel jamais bloqué**
  - **intent:** Le backfill s'exécute sans jamais ralentir le rafraîchissement temps réel des entités.
  - **success:** Un partial refresh reste ~1 s pendant un backfill complet en cours (vérifiable par la log décomposée `API / History / Processing`).

- **CAP-3 — Reprise et idempotence**
  - **intent:** Interrompre, redémarrer, recharger ou re-importer sans perte ni doublon.
  - **success:** Après un redémarrage HA, le backfill reprend à la progression persistée (pas de reprise depuis zéro) ; un re-import produit un upsert horaire, zéro doublon.

- **CAP-4 — Activation documentée**
  - **intent:** L'utilisateur sait ce qui se passe à l'activation de l'option history, y compris la toute première fois.
  - **success:** La documentation de l'option décrit le comportement à l'activation, la durée attendue de la première activation, la reprise après redémarrage, et ce qui est visible dans HA (statistics/graphes long terme) vs ce qui ne l'est pas (panel History).

- **CAP-5 — File de backfill exposée et pilotable**
  - **intent:** L'état de la récupération est exposé — par périphérique : en attente (position dans la file), en cours, en erreur (message et `retry_after`), ignoré, en pause, **plus la progression de la récupération (points récupérés `retrieved_points` / total `total_points`, plus ancien timestamp récupéré, début de rétention)** ; plus un état global du moteur (actif / en pause globale) — et quatre actions : Réessayer maintenant (relance immédiate hors cadence), Prioriser (remonte en tête de file, pris au prochain drain), Pause/Reprise par périphérique et un interrupteur global, Ignorer (persisté en `.storage`, destructeur, confirmé, réactivable). Les champs de progression sont servis par `eedomus/get_backfill_state` **et** par la vue `eedomus/get_coherence` (le détail périphérique de la Cohérence affiche le même indicateur que la file). Les commandes websocket suivent le pattern `eedomus/<verb>` (`require_admin`) ; toutes les actions passent par le coordinator (AD-7).
  - **success:** La vue de Supervision (spec-eedomus-mapping-panel, CAP-9) rend l'état complet de la file, dont l'indicateur de progression par périphérique (barre + texte, file de Supervision et détail périphérique de la Cohérence — spine UX update run 4, instantané de visite) ; chaque action produit un retour nominatif et la file se re-rend ; l'ignorage survit à un redémarrage HA ; la pause globale stoppe le drain sans casser la reprise (CAP-3) ; le temps réel (CAP-2) n'est jamais bloqué par une action.

## Constraints

- Import **exclusivement** via les APIs Python `recorder.statistics` (`async_import_statistics`) sur le `statistic_id` de l'entité réelle — jamais d'écriture d'états passés dans la state machine, aucune dépendance au service Spook (AD-1).
- Périmètre : uniquement les périphériques mappés en entité `sensor` avec valeur numérique résoluble — `float()` puis `value_list` (AD-3, AD-6). Résolution exacte via l'entity registry requise avant tout import (AD-8).
- Backfill **intégral** de l'historique cloud disponible — pas d'option de fenêtre (AD-4, décision explicite).
- Horizon : uniquement les heures **strictement antérieures à la première statistique native** du capteur — le recorder reste propriétaire des heures récentes (AD-11).
- Exécution en tâche de fond dédiée, progression persistée en `.storage` sous la clé `<config_entry_id>_<periph_id>`, au plus un importer actif par config entry, unload = `await` + flush (AD-2).
- Environnement : HA 2026.9.3, recorder SQLite (`purge_keep_days: 30` sur les states ; les statistics ne sont pas purgées), API cloud `periph.history` limitée à 10 000 points/appel, rate-limit cloud.

## Non-goals

- Pas de backfill des états bruts (panel History) — non supporté par le SDK HA, et la purge à 30 jours effacerait le résultat.
- Pas de statistics pour les états discrets (light/switch/climate) — le besoin « temps d'allumage » se sert via `history_stats` en temps réel.
- Pas de fenêtre de backfill configurable.
- Aucune dépendance à Spook ou à un service tiers.
- Le panel de configuration (discussion #28) est hors périmètre.

## Success signal

Après la première activation complète : les graphs long-terme des capteurs eedomus remontent au-delà de la date d'installation HA, un cycle de refresh reste ~1 s pendant le backfill, et la base ne contient aucune entité fantôme `sensor.eedomus_*`.

## Assumptions

- L'instance restera sous HA 2026.9.3+ avec le recorder SQLite par défaut.
- Les credentials API existants autorisent `periph.history` (déjà utilisé en production aujourd'hui).

## Open Questions

- Durée à annoncer dans la doc d'activation (CAP-4) : à mesurer sur la première exécution réelle — le volume exact par périph est inconnu (ticket 1.6 de l'épique backfill).
