---
title: 'Commandes websocket de la file de backfill (état + 4 actions)'
type: 'feature'
ticket: 1
created: '2026-10-05'
status: done
route: 'full'
route_source: 'auto'
baseline_revision: '7357145be31456987cbe3d27a8762620ac97f26d'
review: 'thorough'
review_source: 'auto'
lenses_ran: [blind-hunter, edge-case-hunter, verification-gap, intent-alignment]
review_loop_iteration: 0
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/specs/spec-eedomus-history/SPEC.md
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/initiative-eedomus-panel/epic-supervision-tab/epic-supervision-tab.md
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Le moteur de récupération d'historique (backfill, découpé dans le cycle de refresh partiel) n'est ni exposé ni pilotable : le panneau ne peut ni rendre l'état de la file (position, erreurs, retry) ni déclencher les quatre actions CAP-5 (réessayer, prioriser, pause/reprise, ignorer).

**Approach:** Ajouter au coordinator les structures de pilotage dérivées de l'existant (file ordonnée, ensembles pause/ignore/priorité, interrupteur global, verrou mono-importer, persistance `.storage` par config entry) et exposer 5 commandes websocket via le dispatcher ui_service (`require_admin`) : `eedomus/get_backfill_state` + 4 verbes d'action. Le panneau (4.3) affichera ; le moteur reste dans le coordinator.

## Boundaries & Constraints

**Always:** toutes les commandes suivent le pattern exact du dispatcher (constante `eedomus/<verb>`, `@require_admin` + `@websocket_command` + `@async_response`, entrée `WS_COMMANDS` + `ENDPOINT_DESCRIPTIONS`, handler `_handle_<verb>` sur `EedomusUIService`) ; toutes les actions passent par le coordinator (AD-7) — jamais d'appel direct à l'API eedomus depuis ui_service ; au plus un importer actif — un `asyncio.Lock` côté coordinator couvre le segment historique du refresh partiel ET `retry_now` (acquission non bloquante : occupé = refus nominal, pas d'attente) ; l'ignorage et la pause persistent dans `.storage` (nouveau `Store` par config entry, calqué sur `EedomusConfigManager.mapping_store`) et survivent à une réinstanciation ; la pause globale stoppe le drain (section historique sautée) sans toucher aux états — la reprise est intacte ; le temps réel (refresh partiel hors historique) n'est jamais bloqué par une action ; les contrats gelés (rows `get_coherence` 10 clés / extra 11 clés, rows `get_peripherals`) ne gagnent aucun champ ; toute payload datetimes/NaN passe par `_json_safe`.

**Never:** pas de réimplémentation du moteur de backfill (pas de tâche de fond dédiée nouvelle — le drain reste le cycle de refresh existant) ; pas de migration de la progression existante (`hass.states` `eedomus.history_progress_*` reste telle quelle — l'extension `.storage` ne couvre QUE ignored/paused/global_paused) ; pas de destruction de données à l'ignorage (le périphérique quitte la file, sa progression n'est pas effacée, réactivation possible) ; pas d'attente bloquante dans un handler websocket ; pas de modification des tests gelés au-delà de l'extension des listes de contrats (commandes enregistrées, descriptions d'endpoints).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| État de la file | `get_backfill_state` | File par périphérique (periph_id, nom, statut, position 1-based, error_message, retry_after, attempts), état global (global_paused, engine_active) — multi-box agrégé comme `_collect_peripherals` | `service_unavailable` si aucun coordinator |
| Statuts dérivés | periph non complété | priorisé/en tête > in_progress (import actif) > error (retry_after futur) > paused > pending+position ; ignoré = absent de la file, listé à part | — |
| Réessayer maintenant | `backfill_retry_now {periph_id}` en erreur | relance hors cadence immédiate : entrée retry purgée, fetch+import exécutés, retour nominatif | verrou occupé → `error` "import déjà en cours" ; periph inconnu/complété → `invalid_format` |
| Prioriser | `backfill_prioritize {periph_id}` | tête de file au prochain drain (liste de priorité, consommée par le drain avant l'ordre naturel), retour nominatif | periph inconnu → `invalid_format` |
| Pause/reprise | `backfill_set_paused {periph_id?, global?, paused}` | periph en pause (set persisté) ou interrupteur global ; drain saute les periphs en pause et toute la section historique si global ; retour nominatif + état | payload vide/incohérente → `invalid_format` |
| Ignorer | `backfill_set_ignored {periph_id, ignored}` | ignored=true : quitte la file (persisté, réactivable par ignored=false) ; retour nominatif | periph inconnu → `invalid_format` |
| Persistance | restart HA | ignored/paused/global_paused rechargés du Store à l'init du coordinator ; l'ignorage survit à une réinstanciation | Store vide → ensembles vides, global False |
| Pause globale | global_paused pendant refresh partiel | aucun import historique ce cycle (quota non consommé — pas de chunk), refresh temps réel inchangé | — |

</intent-contract>

## Code Map

- `custom_components/eedomus/coordinator.py` — moteur. Classe `EedomusDataUpdateCoordinator` (l.32) ; `_history_progress` l.48, `_retry_queue` l.53, `_error_count` l.58 ; drain = `_async_partial_refresh` l.851 (quota `CONF_HISTORY_PERIPHERALS_PER_SCAN`, const.py:64, le slot vide se consomme — contrat AD-2, test test_coordinator_partial_refresh.py:127) ; `async_fetch_history_chunk` l.1213 (skip retry_after futur l.1216-1222) ; `async_import_history_chunk` l.1372 ; `_handle_fetch_error` l.1180 (retry_after = now + 24 h, const.py:63) ; `_load/_save_history_progress` l.1105/1134 (hass.states — NE PAS migrer). Attention : `request_full_refresh` l.1096-1104 est du code mort dans un littéral chaîne.
- `custom_components/eedomus/ui_service.py` — dispatcher. Constantes l.19-27 ; pattern décorés l.221-232 ; `WS_COMMANDS` l.255 ; `ENDPOINT_DESCRIPTIONS` l.296 (absence = test rouge) ; handlers `_handle_get_peripherals` l.525 (walk multi-box l.558), `_handle_save_mapping` l.820 (action + validation) ; `_get_ui_service` l.74 ; `_json_safe` l.79 ; fallback import l.43-69.
- `custom_components/eedomus/config_manager.py` — modèle Store : `Store(hass, 1, f"{DOMAIN}.mapping")` l.38 ; versioning `MAPPING_CONFIG_SCHEMA_VERSION` + migrations l.23-31.
- `tests/unit/test_ui_service.py` — contrats : `test_registers_all_four_commands_once` l.58 (liste exacte à étendre), endpoint descriptions l.133/146, rows gelés l.703/876/1151 ; fixture `make_service` l.47 (handlers invoqués directement, `connection.send_result.call_args`).
- `tests/unit/test_coordinator_partial_refresh.py` — `make_coordinator` l.22, contrat quota l.127.
- `tests/unit/conftest.py` — `_StubStore` l.230 (registre classe, patch global `ha_storage.Store`) : pattern « survit à la réinstanciation ».
- `_bmad-output/specs/spec-eedomus-history/SPEC.md` — CAP-5 (l.33-35) + contraintes AD-1/AD-2 (l.41-43), citées dans l'épique.

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/coordinator.py` -- ajouter l'API de pilotage : ensembles `_backfill_ignored`/`_backfill_paused`, flag `_backfill_global_paused`, liste `_backfill_priority`, verrou `_backfill_import_lock`, periph actif ; méthodes `get_backfill_state()` (dérivation file/statuts/positions), `async_backfill_retry_now`, `async_backfill_prioritize`, `async_backfill_set_paused`, `async_backfill_set_ignored`, + chargement/sauvegarde du Store par config entry à l'init et à chaque mutation -- le moteur pilotable, sans nouvelle tâche de fond
- [ ] `custom_components/eedomus/coordinator.py` -- intégrer au drain existant : section historique de `_async_partial_refresh` saute si global_paused, saute les periphs paused/ignored, consomme la liste de priorité avant l'ordre naturel, acquiert le verrou autour du segment import -- CAP-5 respecté dans le cycle AD-2 existant
- [ ] `custom_components/eedomus/ui_service.py` -- 5 commandes : `eedomus/get_backfill_state`, `eedomus/backfill_retry_now`, `eedomus/backfill_prioritize`, `eedomus/backfill_set_paused`, `eedomus/backfill_set_ignored` (constantes + dispatchers `@require_admin` + `WS_COMMANDS` + `ENDPOINT_DESCRIPTIONS` + handlers agrégeant multi-box, retours nomina via `_json_safe`) -- la surface CAP-5
- [ ] `tests/unit/test_backfill_commands.py` -- nouveau : état complet dérivé (statuts/positions/ignore listé à part), chaque action produit son effet sur la file, ignorage + pause survivent à une réinstanciation (via `_StubStore`), retry_now occupé = refus nominal, pause globale stoppe le drain sans casser la reprise, priorité consommée au prochain drain -- couvre la matrice I/O
- [ ] `tests/unit/test_ui_service.py` -- étendre `test_registers_all_four_commands_once` et les contrats de descriptions d'endpoints aux 5 nouvelles commandes ; rows gelés intacts -- churn de contrats prévu
- [ ] `tests/unit/test_coordinator_partial_refresh.py` -- test pause globale : refresh partiel avec global_paused n'exécute aucun import (quota non consommé) ; test priorité : le periph priorisé est pris au prochain drain -- le drain modifié reste sous contrat AD-2

**Acceptance Criteria:**
- Given un coordinator avec periphs non complétés (dont un en erreur), when `get_backfill_state`, then la file rend chaque periph avec son statut exact (pending+position, in_progress, error+message+retry_after, paused), les ignorés listés à part, et l'état global (global_paused, engine_active).
- Given un periph en erreur (retry_after futur), when `backfill_retry_now`, then le fetch repart immédiatement hors cadence et le verrou interdit tout import concurrent (occupé = refus, jamais d'attente).
- Given `backfill_prioritize`, when le prochain drain tourne, then le periph priorisé est traité en tête, avant l'ordre naturel, puis la priorité est consommée.
- Given `backfill_set_paused {global: true}`, when un refresh partiel s'exécute, then aucun import historique ne part, le quota n'est pas consommé, et la reprise (`paused: false`) restaure le drain intact.
- Given `backfill_set_ignored {ignored: true}` puis une réinstanciation du coordinator (restart), then le periph reste ignoré (persistance `.storage`) et `ignored: false` le réactive.
- Given les suites existantes, when les tests tournent, then les contrats gelés (rows coherence/peripherals, quota AD-2) restent verts sans modification de leurs assertions.

## Implementation Notes

Full route — recon faite (voir Code Map) : pas de file réelle à exposer, la file est DÉRIVÉE (`_history_progress` non complétés × ordre de drain) ; l'invariant mono-importer est aujourd'hui implicite (event loop unique) — le verrou le rend explicite sans changer le comportement. Le Store backfill est le PREMIER `.storage` du backfill (la progression est en `hass.states` et y reste) : clé `f"{DOMAIN}.backfill_{entry_id}"`, version de schéma + migrations calquées sur config_manager. La décision « interrupteur global = par config entry » (une box = un coordinator) couvre le mono-box actuel ; l'agrégation multi-box suit `_collect_peripherals`.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: tous verts (nouvelles commandes + contrats étendus + drain inchangé sinon)
- `node tests/js/test-coherence.js && node tests/js/test-i18n-guard.js` -- expected: verts (aucune incidence attendue, la surface frontend n'est pas touchée)
- `python3 -m pytest tests/e2e/ --collect-only -q` -- expected: 27 collectés (aucune incidence)
</intent-contract>

## Review Triage Log

### 2026-10-05 — Review pass (thorough: blind-hunter, edge-case-hunter, verification-gap, intent-alignment)
- verdicts: 35 findings — high 0, medium 14, low 15, false 6, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) retry_now renvoyait success sur un retry échoué (fetch avale ses erreurs, retour []) — P1 : statut frais dans le résultat (status error + error_message + retry_after si re-échec, completed si clôturé).
  - `[medium]` `[patch]` (blind) prioritize sans les gardes de retry_now (complété/ignorable priorisable, entrée jamais consommée) — P2 : refus invalid_format, paused reste priorisable.
  - `[medium]` `[patch]` (blind) agrégat multi-box sans identité de box (positions en doublon, routing premier-match) — P3 : entry_id sur chaque ligne queue/ignored ; routing inchangé (mono-box, latent comme get_peripherals).
  - `[medium]` `[patch]` (blind) forme de réponse incohérente (seul set_paused rendait l'état) — P3 : les 4 actions rendent {…, state}.
  - `[medium]` `[patch]` (blind) drain-skip du verrou mono-importer non testé — P10b : test verrou tenu → segment sauté, quota intact.
  - `[low]` `[patch]` (blind) datetimes naïfs dans get_backfill_state — P4 : dt_util (utcnow/as_local/utc_from_timestamp), retry_after tz-aware.
  - `[low]` `[patch]` (blind) branche globale non gardée (AttributeError → erreur générique après application partielle) — P5a : garde getattr comme le chemin de lecture.
  - `[low]` `[patch]` (blind) XOR : {global: false} passait puis « Unknown peripheral None » — P5b : cible par véracité, global:false sans periph = invalid_format.
  - `[medium]` `[patch]` (blind) fenêtre retry écoulée effaçait error_message/attempts — P6 : historique d'échec conservé tant qu'une entrée retry existe, statut dégradé seul.
  - `[low]` `[patch]` (blind) _send_backfill_error fuyait str(error) vers le client — P7 : message générique client, détail en log serveur.
  - `[low]` `[reject]` (blind) course persistance pendant le setup (action websocket pendant first refresh écrasée par le load) — fenêtre étroite avant tout panneau, ensembles frais à cet instant ; le côté test est couvert par P10a.
  - `[low]` `[reject]` (blind) code busy partagé avec « error » générique — le plan épingle délibérément `error` (matrice validée) ; le message reste branchable ; à revisiter en 4.3 si le panneau a besoin de distinguer.
  - `[low]` `[reject]` (blind) validation de schéma voluptuous non exercée — pattern constant du repo (les 9 commandes existantes testées handler-direct) ; changer de philosophie de test sort du périmètre.
  - `[low]` `[patch]` (blind) nom de test obsolète — P10c : renommé test_registers_all_commands_once.
  - `[medium]` `[defer]` (blind) aucun canal push pour les changements de file (polling seul) — décision de conception pour 4.3 : à trancher délibérément au plan_checkpoint de la vue, pas une lacune de ce backend.
  - `[low]` `[patch]` (edge) marqueur actif placé après le fetch dans le drain (état « pending » pendant un fetch long) — P8 : posé avant le fetch.
  - `[low]` `[patch]` (edge) version de schéma stockée supérieure à la courante chargée sans garde — P9 : warning + état vide.
  - `[low]` `[reject]` (edge) ignored/paused persistés en chaîne → set() poubelle — état injoignable : notre écrivain écrit toujours des listes ; tampon manuel de .storage hors programme.
  - `[medium]` `[patch]` (edge, dup blind-2) prioritize sur complété — groupé, P2.
  - `[medium]` `[patch]` (edge) retry_now contournait la pause (import immédiat d'un periph en pause) — P1 : refus invalid_format « paused ».
  - `[false]` (edge) hang API = verrou tenu pour toujours — réfuté : eedomus_client.py:92,134 (http_request_timeout + async_timeout) → TimeoutError → _handle_fetch_error ; le finally libère le marqueur et le verrou.
  - `[low]` `[patch]` (edge, dup blind-8) payload global:false — groupé, P5b.
  - `[low]` `[patch]` (edge, dup blind-7) branche globale non gardée — groupé, P5a.
  - `[medium]` `[patch]` (edge, dup blind-3) collisions periph_id multi-box routées vers la première box — lignes portent entry_id (P3) ; routing premier-match documenté latent (mono-box confirmé).
  - `[false]` (edge) porte « periph_id in peripherals_for_history » supprimée — réfuté : la file dérivée est construite depuis _dynamic_peripherals, repeuplé du body du cycle courant (coordinator l.870-890) AVANT le segment drain (l.1047) ; peripherals_for_history était construit de la même source.
  - `[medium]` `[patch]` (verif, pré-vérifié) câblage first_refresh → _load_backfill_persistence jamais testé par le chemin réel — P10a : test async_config_entry_first_refresh avec Store semé, internals stubés, ensembles repeuplés.
  - `[medium]` `[patch]` (verif, pré-vérifié) skip drain du verrou busy non testé — P10b (groupé avec blind-5).
  - `[medium]` `[patch]` (verif, other) routing premier-match multi-box — groupé avec edge-9/blind-3 (entry_id sur les lignes).
  - `[medium]` `[patch]` (verif, other) positions 1-based par box sans discriminant — groupé, P3.
  - `[false]` (intent) drain réécrit, ordre/membres changés — réfuté comme edge-10 : même source (_dynamic_peripherals ← body du cycle), même ordre d'insertion.
  - `[low]` `[reject]` (intent) interrupteur global hybride (stockage par entry, fan-out commande) — per-box ratifié au checkpoint ; fan-out documenté ; mono-box indistinguable, multi-box latent.
  - `[false]` (intent) payload E2 vs liste de statuts littérale de l'entrée — la matrice du plan (validée au checkpoint) épingle « ignoré absent de la file, listé à part » et la priorité en tête.
  - `[low]` `[reject]` (intent) retry_now permissif (pending éligible, pas seulement error) — sur-ensemble testé ; le panneau 4.3 contrôle l'exposition du bouton ; refus des ignorés cohérent.
  - `[false]` (intent) positions multi-box non épinglées — traité : entry_id sur les lignes (P3).
  - `[false]` (intent) plan commis dans le diff — pratique repo (plans archivés à côté des tickets).

Patches P1-P10 appliqués par impl-41-backfill (tour 2), re-vérifiés indépendamment (307 unitaires). Pas d'intent_gap, pas de bad_plan. Deferred : canal push (décision 4.3). Judgment call ratifié : retry_after aussi conservé après fenêtre écoulée (cohérent avec l'historique d'échec visible).

## Auto Run Result

**Route:** full — recon par subagent, plan validé au plan_checkpoint utilisateur (ask_user, 2026-10-05 : plan approuvé ; pause globale par box ; unignore via la même commande), impl par subagent, review thorough 4 lens, triage, 10 groupes de patchs, re-vérif.

**Vérifications exécutées (orchestrateur, 2026-10-05) :**
- `python3 -m pytest tests/unit/ -q` — 307 passed (298 pré-patch, +9 nouveaux de la passe de patchs)
- `node tests/js/test-coherence.js` — exit 0 (aucune incidence frontend)
- `node tests/js/test-i18n-guard.js` — 731 littéraux / 6 fichiers, aucun texte en dur
- `python3 -m pytest tests/e2e/ --collect-only -q` — 27 collectés
- Audit de matrice : les 8 lignes de la matrice I/O ont chacune leurs tests, tous passés (état, statuts, retry, priorité, pause periph/globale, ignoration, persistance, drain).

**Contrats gelés :** rows get_coherence (10 clés) et get_peripherals intacts ; quota AD-2 inchangé (le slot vide se consomme) ; contrats d'enregistrement étendus 9→14 commandes + descriptions d'endpoints (churn prévu au plan).

**Post-déploiement :** à consigner après validation live.

**Post-déploiement (2026-10-05, 22:55-23:05 CEST) :**
- Déployé via `deploy_hass_eedomus.sh` (git-only, unstable @ 2125461), restart HA, ~2 min d'attente
- `python3 -m pytest tests/e2e/ -q` sur le Pi : **27 passed in 62.23s**
- Logs post-restart : « Eedomus integration initialized successfully » ; le nouveau segment drain fonctionne (PARTIAL REFRESH avec History 5 periphs ce cycle, import statistics AD-11 normal) ; aucune erreur liée aux commandes CAP-5 ; motif préexistant de retry historique inchangé
- Les commandes ne sont pas encore consommées (le panneau les rend en 4.3) ; les actions ne sont pas exercées sur l'instance réelle (non destructif, conforme au plan de la 4.5)

**Sweep 4.4 (2026-10-06) :** finding différé « canal push » traité par décision consignée (S3) — le plan_checkpoint de la 4.3 a ratifié le polling : un callWS par visite + Réessayer, pas d'abonnement.
