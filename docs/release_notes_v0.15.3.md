# Release Notes - Version 0.15.3 / Notes de version - Version 0.15.3

## English

### New Features

**Supervision tab: first position and default landing**
- The Supervision tab is now the first tab (leftmost) and the panel's
  default tab on open (spec CAP-9 updated).

**History-recovery indicators (Supervision tab)**
- A conditional indicator row (rendered when the `history` option is
  enabled): global completion gauge (X/Y eligible peripherals),
  aggregated points (retrieved / estimated total), oldest retrieved
  data, and queue health with ETA.
- Backfill progress bar + text on every Supervision queue row and in
  the Coherence peripheral detail (popover and mobile extended row -
  strict parity, shared keys).

**E2E simulator strate (second test strate)**
- A local eedomus API simulator (`scripts/simulateur/`, salvaged from
  PR #119) serves the API from a JSON dump, including a deterministic
  synthetic `periph.history` endpoint.
- The E2E-sim suite boots the simulator on the Raspberry Pi over SSH,
  creates a second simulated box through the real config flow, and
  exercises the untestable: multi-box aggregation, box metrics
  sections, global-pause fan-out, and the four destructive backfill
  actions end to end.
- New optional `history_api_host` config field: points a box's
  history retrieval at a local simulator (default empty = eedomus
  cloud; the real box is untouched - it does not serve
  `periph.history` locally).
- AGENTS.md now carries the two-strates rule (live-Pi = regression
  truth, never mocked; simulator = multi-box and destructive).

**Seam probe: the backfill keeps watching completed peripherals**
- When the drain queue is empty, the worker probes one completed
  peripheral per pass: cloud points that arrived after the one-shot
  walk (entity disabled for a while, cloud lag) are re-imported
  through the production path (AD-11 clip preserved, idempotent
  upsert). Deep-history re-walks are a documented non-goal.

### Bug Fixes

- **Dead-window fetch loop**: peripherals whose walk reached the
  present re-fetched the same 10,000-point window forever (the cloud
  returns the newest page whatever the window). A frozen max
  timestamp now completes the walk - the drain quota is no longer
  burned by 5-6 looping peripherals.
- **Silent chunk loss without a registry match**: an eligible sensor
  whose entity never resolves is removed from the queue after 3
  consecutive misses (fix the mapping, then reset its progress)
  instead of silently burning every fetched chunk.
- **TypeError in history progress sensors**: `total_points` can be
  `None` when the estimate is unavailable - the History Progress and
  History Stats sensors tolerate it (previously a listener error on
  every refresh).
- **unit_class for statistics imports** (0.15.2): derived through the
  recorder's own unit map (`STATISTIC_UNIT_TO_UNIT_CONVERTER`) - the
  HA 2026.11 deprecation no longer fires and live imports no longer
  abort.

### Documentation

- Architecture, connection-modes and mapping-granularity diagrams
  restored (ASCII + mermaid doublettes, English, verified against the
  current code), exhaustive mapping diagram in `docs/mapping-format.md`.
- Measured first-activation numbers in `docs/history_backfill.md`.
- README test counters corrected (396 unit, 29 + 9 + 1 E2E, JS strict).

### Technical

- Dependency bumps: black 26.10.0, isort 9.0.2, yarl 1.25.1,
  async-timeout 5.0.1, voluptuous 0.16.0.
- Test suite: 396 unit, 39 E2E (29 live-Pi + 9 simulator + 1 history
  statistics), strict JS harness - all green on the target Pi.

---

## Français

### Nouveautés

**Onglet Supervision : première position et onglet par défaut**
- L'onglet Supervision devient le premier onglet (le plus à gauche)
  et l'onglet par défaut à l'ouverture du panneau (spec CAP-9).

**Indicateurs de récupération d'historique (onglet Supervision)**
- Une rangée d'indicateurs conditionnelle (rendue si l'option
  `history` est active) : gauge de complétion globale (X/Y
  périphériques éligibles), points agrégés (récupérés / total
  estimé), données les plus anciennes récupérées, santé de la file
  avec ETA.
- Barre + texte de progression du backfill sur chaque ligne de la
  file Supervision et dans le détail périphérique de la Cohérence
  (popover et ligne étendue mobile - parité stricte, clés partagées).

**Strate E2E simulateur (seconde strate de tests)**
- Un simulateur local d'API eedomus (`scripts/simulateur/`, salvage de
  la PR #119) sert l'API depuis un dump JSON, y compris un endpoint
  `periph.history` synthétique déterministe.
- La suite E2E-sim démarre le simulateur sur le Raspberry Pi via
  SSH, crée une seconde box simulée à travers la config flow réelle,
  et exerce l'intestable : agrégation multi-box, sections de métriques
  par box, fan-out de la pause globale, et les quatre actions
  destructives du backfill de bout en bout.
- Nouveau champ optionnel `history_api_host` : pointe la récupération
  d'historique d'une box vers un simulateur local (vide par défaut =
  cloud eedomus ; la box réelle est inchangée - elle ne sert pas
  `periph.history` en local).
- AGENTS.md porte la règle des deux strates (live-Pi = vérité de
  régression, jamais mockée ; simulateur = multi-box et destructif).

**Sondage du joint : le backfill surveille les périphériques complétés**
- Quand la file de drain est vide, le worker sonde un périphérique
  complété par passe : les points cloud apparus après le walk
  (entité désactivée un temps, retard du cloud) sont ré-importés via
  le chemin production (clip AD-11 préservé, upsert idempotent). Les
  re-parcours de l'historique profond sont un non-goal documenté.

### Corrections

- **Boucle de fetch infinie** : les périphériques arrivés au présent
  re-fetchaient indéfiniment la même fenêtre de 10 000 points (le
  cloud renvoie la page la plus récente quelle que soit la fenêtre).
  Un timestamp max figé complète désormais le walk - le quota du
  drain n'est plus brûlé par 5-6 périphériques en boucle.
- **Chunks perdus sans correspondance registry** : un capteur éligible
  sans entité résolue quitte la file après 3 échecs consécutifs
  (corrigez le mapping, puis réinitialisez sa progression) au lieu de
  brûler silencieusement chaque chunk.
- **TypeError des capteurs History Progress** : `total_points` peut
  valoir `None` quand l'estimation est indisponible - les capteurs
  History Progress et History Stats le tolèrent (auparavant une
  erreur de listener à chaque refresh).
- **unit_class des imports de statistics** (0.15.2) : dérivé via la
  table d'unités du recorder (`STATISTIC_UNIT_TO_UNIT_CONVERTER`) -
  la dépréciation HA 2026.11 ne se déclenche plus et les imports
  live n'échouent plus.

### Documentation

- Diagrammes d'architecture, de modes de connexion et de granularité
  du mapping réintégrés (doublettes ASCII + mermaid, anglais, vérifiés
  contre le code actuel), diagramme de mapping exhaustif dans
  `docs/mapping-format.md`.
- Mesures réelles de la première activation dans
  `docs/history_backfill.md`.
- Compteurs de tests du README corrigés (396 unitaires, 29 + 9 + 1
  E2E, harnais JS strict).

### Technique

- Montées de versions : black 26.10.0, isort 9.0.2, yarl 1.25.1,
  async-timeout 5.0.1, voluptuous 0.16.0.
- Suite de tests : 396 unitaires, 39 E2E (29 live-Pi + 9 simulateur +
  1 statistics historiques), harnais JS strict - tout vert sur le Pi
  cible.
