---
epic: epic-eedomus-simulator
date: 2026-11-01
verdict: accepted-with-open-items
criteria: declared
headless: true
---

# Rétrospective — epic-eedomus-simulator

## Epic summary

Epic clôturé le 2026-10-10 (dernières земли ed1039e/6dff34f) : salvage du simulateur Eedomus
(PR #119) en outil de test, endpoint synthétique `periph.history`, harnais 2e config entry via
config flow réelle, refactor sweep, suite E2E-sim multi-box + destructive.

Tickets — build order, tous `done` (`pending_tickets` vide) :

| Ref | Titre | Statut | Range de build |
|---|---|---|---|
| 5.1 | Salvage du simulateur (PR #119) | done | cf8b642..f3df73a (25 commits, 5 merges mesurés) |
| 5.2 | Endpoint periph.history synthétique | done | f3df73a..a32bb8e |
| 5.3 | Harnais box simulée (config flow réelle) | done | a32bb8e..4a8e8fa |
| 5.4 | Refactor sweep | done | 4a8e8fa..ed1039e (groupé avec 5.5) |
| 5.5 | Suite E2E-sim multi-box + destructive | done | idem (pas de `baseline_revision` — gap consigné) |

Inventaire des preuves : fichier epic lu intégralement, initiative Requirements (CAP-1..5),
plans ×5 avec triage/change-log, `git_evidence.py` tourné une fois par range distinct.
Manques : `story_file` null partout (tickets non raffinés — le build lisait l'entry + l'epic) ;
5.5 sans `baseline_revision` (range déduit par regroupement avec 5.4, cut = ed1039e) ;
pas de session logs (expirés) ; l'attribution du range 5.1 repose sur le matching de sujets
(l'epic s'intercale avec du travail parallèle 1.x/panel/deps) ; revue de 5.2 inline seulement
(limite de noms de subagents à l'époque de l'epic, prompts supprimés par le sweep de2dd45,
récupérables dans git).

## Findings

### Vues agrégées

- **Architecture delta — checked and clean** : modules neufs dans `scripts/simulateur/` +
  `tests/e2e/` conformes aux Notes de l'epic ; aucun import de Flask hors test
  (grep custom_components/ = 0 hits ; flask cantonné à requirements-test.txt:15 +
  requirements_dev.txt:13). Marqueur `e2e_sim` enregistré (pyproject.toml:46-51).
- **Duplication map (low)** : pattern fixture sim-entry (garde stale-run + create/remove)
  dupliqué entre test_e2e_sim_config_flow.py:41-59 et test_e2e_sim_multi_box.py:44-59.
  Aussi : les deux listes de requirements test dupliquent le pin Flask.
- **God-class — checked, pas de god-class** : simulator.py = 364 lignes, module plat sans
  classe ; churn top = data dump (+5277) et script 02_apply_renom.py (+728, salvage verbatim).
- **Pattern divergence (low)** : simulator.py parse argv à l'import (le plan 5.2 le note —
  les tests patchent sys.argv) ; sinon conftest étendu (delete(), 4a8e8fa) dans le style existant
  — clean.
- **Spec-to-implementation (med)** : Done-when #1 « 2e entry **sans code d'intégration
  modifié** » contredit par 6c26543 (config_flow.py, const.py, eedomus_client.py, strings +
  translations : champ `history_api_host`) — frôle aussi CAP-2 « sans modification du client ».
  Écart consigné dans le memlog (L13-14) mais jamais réconcilié avec le spec de l'epic.

### Lentilles code (diff cf8b642..ed1039e)

- **[réel]** tests/e2e/test_e2e_sim_multi_box.py:55-59 — le teardown rétablit sans condition
  `backfill_set_paused {global: True, paused: False}`, fan-out vers TOUS les coordinateurs,
  box réelle comprise ; l'état pause global d'avant-suite n'est pas enregistré/restauré.
  Variant : interrompre pytest brutalement laisse la pause globale sur la box réelle.
- **[réel]** scripts/simulateur/simulator.py — POST `simulate_change` sans auth (contrairement
  à /api/get et /api/set), bind `0.0.0.0`, et `request.get_json()` renvoie None sur body
  non-JSON → AttributeError → 500. Outillage test-only, mais exposé au LAN pendant une suite.
- **[réel]** .github/workflows/tests.yml (job e2e posé par la story 101) — `pytest tests/e2e/ -q`
  sans filtre `-m`, en violation de la règle AD-16, et sans flask/env `E2E_SIM_*` ; le job était
  dormant. Rendu caduc par la décision utilisateur de clore la 101 (E2E = phase ad-hoc locale,
  job dormant documenté réversible) — enregistré comme closed-by-decision, avec ce caveat.
- **[réel]** Story 5.1 promettait des tests de contrat unitaires (periph.list/caract/value_list/
  value, auth, thermostat) ; aucun n'a atterri (drop consigné au plan 5.1 sans renégociation du
  ticket). Exemple concret : `periph.value_list` sur id inconnu renvoie silencieusement `[]`,
  une divergence d'API réelle passerait inaperçue.
- **[réel, minor]** `get_device_history_count` du simulateur renvoie la constante 8760 alors
  qu'il émet 3 ans × 24 × densité points — pourcentage de progrès plafonné à 100 en run sim.
- **[réel]** `history_api_host` accepté par le flow sans aucune validation (format,
 joignabilité) ; le test de connexion du flow ne valide que `api_host` ;
  test_config_flow.py:89-127 ne couvre que le happy path de persistance.
- **[spéculatif-à-vérifier]** datetimes naïfs → epoch dépendants du TZ hôte
  (simulator.py / coordinator.py:1613,2318) — sûr uniquement tant que sim et HA partagent le
  TZ du Pi (décision harnais 2026-10-06) ; une HA conteneurisée casserait la reprise silencieusement.
- **[spéculatif-à-vérifier]** `evaluate_thermostat_rules` — `float(last_value)` sur valeur
  `None` (artefacts d'anonymisation du dump) → TypeError hors du tuple except
  (ValueError, KeyError) → 500 sur /api/set.
- **[spéculatif]** test_box_metrics_render_two_sections censure exactement 2 boxes — une 3e
  entry (ou une stale matchant SIM_TITLE_MARK) fait échouer la suite.
- **[clean]** reprise par chunks client-simulateur couverte par
  `test_client_resume_pagination_is_gapless` (invariant « strictly after start ») — frontière
  5.2↔client vérifiée.

## Behavior verification

Runtime de l'intégration inchangé par design (outillage test-only). Preuves courantes :
suite live-Pi post-déploiement du 2026-11-01 — 28 passed / 2 échecs attendus dépendants de
l'état (file backfill drainée). La strate e2e_sim n'a **pas** été rejouée lors de cette rétro
(scope rétréci : dernière exécution = story 5.5, commit ed1039e) ; validation visuelle du
panneau non rejouée (aucune surface UI touchée par l'epic).

## Previous-retro follow-through (rétro epic-supervision-tab)

1. « Cache-busting du module panneau » — **atterri** : ticket 106/AD-17 (suffixe `?v=` du
   `module_url`, panel.py) puis ticket 118 (graphe entier de modules, commits 0572863/41b6791,
   déployé et vérifié en live le 2026-11-01 : curl entry + modules portent `?v=0.15.7`).
2. « Cadence du drain backfill » (décision user) — **aucune preuve trouvée** : défaut toujours
   1/scan (const.py:71-72), aucun changement d'options repéré. Reste ouvert.
3. « Helper retry E2E — centraliser à la 4e occurrence » — **non atterri, par design** :
   toujours 3 occurrences (test_e2e_panel.py:53,152,185) ; le déclencheur n'est pas atteint.
4. « Limite de noms de subagents » (process) — leçon process, non vérifiable en commit ;
   les deux lens de cette rétro ont tourné en subagents sans blocage (donnée du jour).
5. « CI advisory→strict » (reporté de la rétro i18n) — **aucune preuve trouvée** ni dans un
   sens ni dans l'autre ; observation neuve ci-dessous (pins CI) à traiter à part.

## Action items (proposées, en attente de décision humaine — rien n'a été appliqué par cette rétro)

1. **[fix-now → story backlog]** Suite de contrat unitaire du simulateur — couvrir au minimum
   `periph.value_list` id inconnu, auth `/api/get`-`/api/set`, règles thermostat dont
   `last_value=None`, et rendre `get_device_history_count` honnête ou plafonner. Owner : dev.
2. **[fix-now → story backlog]** Fixture sim-entry : enregistrer l'état pause global avant
   suite et le restaurer au teardown (au lieu du resume inconditionnel) + garde pour
   l'interruption brute. Owner : dev.
3. **[fix-now → story backlog]** Valider `history_api_host` dans le flux (format/joignabilité)
   + tests non happy-path. Owner : dev.
4. **[defer]** Durcissement simulator.py (auth sur `simulate_change`, garde `get_json` None,
   bind 127.0.0.1 optionnel) — outillage test-only exposé au LAN. Owner : dev.
5. **[réconciliation spec]** Erreurs d'enregistrement autour du Done-when #1 : consacrer
   l'écart « code d'intégration modifié » (6c26543, knob `history_api_host`) comme déviation
   acceptée dans le spec/epic pour que les rétros futures ne le re-flag pas. Owner : user.
6. **[process/CI]** Aligner les pins de lint.yml (black==23.12.1, isort==5.13.2) sur les pins
   du ticket 115 (black==26.10.1, isort==9.0.2) — divergence observée le 2026-11-01,
   .github/workflows/lint.yml vs scripts/hooks/. Owner : dev.
7. **[reporté]** Décision cadence drain (item 2 de la rétro supervision) toujours ouverte.
   Owner : user.

## Acceptance verdict

**accepted-with-open-items** — critères **déclarés** (5 Done when), tickets 5/5 done
(pending_tickets vide, verdict machine non forcé) :

1. 2e entry via config flow réelle ✓ — **avec déviation consignée** : le knob
   `history_api_host` a modifié le code d'intégration (6c26543) ; déviation proposée à
   consacrer (action item 5), pas un défaut bloquant.
2. Statistiques horaires via chemin de production ✓ (test_e2e_sim_multi_box.py:116-129,
   reprise par chunks couverte).
3. 4 actions destructive + suppression d'entry propre ✓ (:157-184).
4. Live-Pi vert/inchangé + AD-16 dans AGENTS.md ✓ (ed1039e ; reconfirmé : E2E live
   2026-11-01, 28 verts / 2 échecs attendus dépendants de l'état).
5. Passe de confidentialité du dump ✓ **partiellement** : décision consignée (memlog L12),
   aucune passe documentée en artefact ; le README du dump lui-même prévient que le renaming
   n'est pas une anonymisation complète — écart mineur accepté.

Aucun critère manqué ; les items ouverts (findings réels ci-dessus) sont des propositions
d'amélioration sur l'outillage de test, pas des défauts de l'epic.

## Open questions

- La HA conteneurisée (TZ ≠ Pi) est-elle un horizon réaliste ? Si oui, les datetimes naïfs
  (coordinator/simulator) deviennent un vrai bug à plannifier ; sinon accepter tel quel.
- `last_value=None` est-il atteignable avec des dumps réels anonymisés ? Une capture
  suffirait à statuer (lens : spéculatif).
- Si le job e2e de la 101 est un jour ressuscité : il faut le filtre `-m` AD-16 + les deps
  Flask/env sim — prévu dans la doc de résurrection ?

## Assumptions (run headless — délégation utilisateur « applique les recommandations »)

- Epic choisi sans l'utilisateur : epic-eedomus-simulator, comme « dernier epic achevé sans
  rétro » (seul des 5 epics sans retrospective.md ; clôturé 2026-10-10, le plus récent).
- Aucune préoccupation d'entrée demandée (mode délégué) ; les phases 1-2 n'ont pas été
  orientées par des inputs humains.
- Verdict machine rendu sans décision humaine item par item ; les 7 action items sont des
  propositions en attente de décision.
- Behavior check rétréci : strate e2e_sim non rejouée (dernière exécution = story 5.5) ;
  la preuve live de non-régression est l'E2E live-Pi du 2026-11-01.
- Range de 5.5 déduit (pas de baseline_revision) par regroupement avec 5.4, cut = ed1039e.
