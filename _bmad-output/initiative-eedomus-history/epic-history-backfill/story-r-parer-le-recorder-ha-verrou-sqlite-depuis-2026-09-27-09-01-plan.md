---
title: "1.1 Réparer le recorder HA (verrou SQLite) — maintenance WAL + suppression de la tempête d'écritures"
type: 'bugfix'
ticket: 1
created: '2026-09-27'
status: 'built'
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: ''
lenses_ran: ['blind-hunter', 'edge-case', 'verification-gap', 'intent-alignment']
review_loop_iteration: 0
baseline_revision: '3d9d232'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Le recorder HA ne persiste plus rien depuis le 27/09 09:01 (states, events, statistics gelés) : le WAL de la base SQLite ne contient plus que le spill d'une transaction jamais commise, et toute écriture externe échoue avec `database is locked`. La cause racine est la tempête d'écritures fantômes du backfill eedomus (214 311 `async_set` avec timestamps anciens à chaque boot) qui étouffe le recorder sans qu'il commette jamais.

**Approach:** Supprimer les deux boucles d'écriture d'états passés (`async_set`) du sous-système history — l'inline du fetch et le fallback d'import — puis exécuter la maintenance WAL à froid (arrêt complet HA, `wal_checkpoint(TRUNCATE)`, redémarrage laissé finir sans interruption) et valider que le recorder écrit à nouveau. Un échec d'import statistics se solde par un warning et un skip, jamais par une écriture d'état.

</frozen-after-approval>

## Implementation Notes

Exécution de l'option 1 (2026-09-27 ~15:45) et découverte majeure :

- Arrêt HA OK (l'arrêt propre a mis ~3 min, le `ha core stop` a hangé mais le stop a abouti).
- Checkpoint à froid OK : le WAL de **97 Mo ne contenait ZÉRO frame commise** — tout était le spill d'une transaction jamais validée. Base propre au redémarrage.
- Au boot : le recorder écrit sa ligne de run (première écriture depuis 09:01 !) puis se re-gèle — **même avec une base propre**. Le WAL est repassé de 8 Ko à 47 Mo en ~9 min (+17 Ko/s de spill infini, silencieux).
- Cause racine confirmée par corrélation totale : **la tempête d'écritures fantômes du backfill eedomus** (214 311 `async_set` avec timestamps anciens à chaque boot, car la progression vit dans la state machine et ne survit pas aux redémarrages). Le thread recorder reste vivant (il émet des warnings en retraitant le lot) mais ne commet jamais. Aucune erreur loggée ; le debug logger ne produit rien côté recorder.
- Consequence : la maintenance seule (option 1) est nécessaire mais **insuffisante** — le storm se rejoue à chaque boot. La suppression des écritures fantômes (prévu au ticket 1.3, AD-1 du spine) est un prérequis du repair.
- HA est actuellement UP mais son recorder est de nouveau gelé (WAL 47 Mo en croissance). Une nouvelle maintenance à froid sera nécessaire après le changement de code.

## Code Map

- `custom_components/eedomus/coordinator.py` (~ligne 1245, `async_fetch_history_chunk`) — la boucle inline `states.async_set(...)` qui écrit chaque point d'historique vers `sensor.eedomus_<periph_id>` : **première moitié de la tempête**, à supprimer.
- `custom_components/eedomus/coordinator.py` (~ligne 1415, `_fallback_import_history_chunk`) — la boucle fallback `states.async_set(..., timestamp)` : **seconde moitié de la tempête**, à supprimer (l'import statistics raté se solde par un skip loggé, pas par une écriture d'état).
- `tests/unit/test_history_value_resolution.py` — tests du chemin statistics existants (à adapter si le fallback async_set disparaît : `test_async_set_fallback_resolves_labels`, `test_async_set_fallback_targets_real_entity`).
- Ne pas toucher : la résolution de valeur (`_resolve_history_value`), le résolveur d'entité (`_resolve_main_entity_id`), le fetch cloud — tous validés ce jour.

## Open Questions

*(Résolues le 2026-09-27 par décision utilisateur.)*

1. ~~Re-scopage du ticket~~ — **Décision : option (a)**, la suppression des écritures fantômes est incluse dans ce ticket ; le ticket 1.3 conserve le nettoyage des fantômes existantes et la vérification finale. Note d'implémentation associée : la progression state-machine marquera les périphs « completed » au boot malgré les imports statistiques désormais skippés — sans conséquence pour ce ticket ; les tickets 1.2/1.4 géreront la réinitialisation de progression (nouvelles clés `.storage` en 1.4).

## Review Triage Log

Review thorough, 4 lenses (blind-hunter, edge-case, verification-gap, intent-alignment), itération 1 :

- [low, patch] `if chunk:` mort dans `async_fetch_history_chunk` (1248) — le `return []` antérieur sur `not chunk` garantit toujours vrai ; suppression du garde + dédent. (blind-hunter)
- [low, patch] Double log du même échec — `_import_via_statistics` logue warning/error puis re-raise, le handler externe re-logue ; démotiver le log interne en debug. (blind-hunter, verification-gap)
- [low, patch] Test filtre sur `record.message` (template brut) au lieu de `record.getMessage()` (sortie formatée) — l'assertion pourrait passer sur de mauvais arguments. (blind-hunter)
- [low, patch] Aucune assertion « jamais d'état écrit » sur le chemin de SUCCÈS — un ajout d'une ligne dans `test_import_targets_real_entity_when_registered`. (blind-hunter)
- [medium, defer→1.4] Perte silencieuse permanente du chunk en cas d'échec d'import (last_timestamp avancé avant l'import, pas de retry) — conséquence consignée dans la décision de re-scopage ; la sémantique retry/progression (AD-2) est le cœur du ticket 1.4. (3 lenses)
- [medium, defer→1.2/1.6] Spook devient dépendance dure silencieuse du chemin statistics (le service n'existe pas en HA core) — le remplacement par l'API Python direct est l'intitulé du ticket 1.2 ; le test E2E (existence du service + statistics réelles) est le scope du ticket 1.6. (blind-hunter, verification-gap)
- [medium, defer→1.2] Log « Successfully imported N points » alors que `_import_via_statistics` peut retourner tôt avec zéro point importé (tous points non résolubles, ex. periph 1269566) — préexistant au diff ; 1.2 réécrit la fonction (retour du compte importé).
- [low, defer→1.2] Métrique « states » du PARTIAL REFRESH désormais mal nommée (points fetchés ≠ états écrits, chunks skippés comptés) — 1.2 redéfinit les métriques du chemin import.
- [low, defer→1.5] Conséquence utilisateur non documentée (history = statistics horaires, rien dans le panel History avant import) — le doc d'activation est l'intitulé du ticket 1.5.
- [low, defer→1.4] Timezone naïf du fetch (host-local) vs `dt_util.as_local` de l'import — préexistant ; l'unification appartient à la refonte progression de 1.4.
- [low, defer→1.2/1.4] Contrat d'erreur changé sans retour exploitable (plus de raise, retour None silencieux) — le retour deviendra significatif quand 1.2/1.4 restructureront l'appel.
- [false] « Clause B absente du diff » (maintenance/validations live) — lecture R1 correcte : la clause opérationnelle vit dans la section Verification du plan et s'exécute avec l'utilisateur ; aucune trace dans le repo attendue. (intent-alignment)
- [false] « Progress/error sensors toujours en async_set » — écritures à l'heure courante d'entités enregistrées (history_sensor.py), hors lecture étroite de l'intention (« timestamps anciens ») ; charge normale. (intent-alignment)

## Verification

**Commands:**

- `ssh 192.168.1.5 'sudo -i ha core stop'` -- expected: HA s'arrête (state stopped, vérifier avec `sudo -i ha core info` → plus de processus core)
- `ssh 192.168.1.5 'sudo python3 -c "import sqlite3; c=sqlite3.connect(\"/homeassistant/home-assistant_v2.db\"); print(c.execute(\"PRAGMA wal_checkpoint(TRUNCATE)\").fetchone())"'` -- expected: `(0, N, N)` avec le fichier `-wal` tronqué à 0 octet
- `ssh 192.168.1.5 'sudo -i ha core start'` -- expected: HA démarre et le boot est laissé terminer SANS interruption (aucun restart/déploiement pendant ~5 min)
- Compteurs croissants -- expected: `SELECT COUNT(*) FROM states` et `FROM events` augmentent sur deux mesures espacées de 60 s après le boot
- Import de test statistics -- expected: un appel `recorder.import_statistics` (entité de test, top-of-hour) atterrit dans `statistics_meta` sous 60 s

**Manual checks:**

- Le fichier `-wal` reste petit (< quelques Mo) et croît normalement après le boot (plus de spill infini)
- Aucune erreur `database is locked` lors d'un `INSERT` de test externe post-boot
