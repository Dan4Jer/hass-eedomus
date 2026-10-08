---
title: 'H.1.2 Import statistics direct via async_import_statistics'
type: 'feature'
ticket: 2
created: '2026-10-03'
status: done
route: 'full'
route_source: 'auto'
baseline_revision: '8f256621b5ebd080eb923854fd2a4dd1ecb690e5'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/_bmad-output/planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md']
warnings: []
deferred:
  - summary: >-
      L'ancre AD-11 (premiere statistique native) peut deriver vers nos propres
      heures backfillees si les chunks n'arrivent pas strictement dans l'ordre
      decroissant.
    evidence: >-
      Comportement attendu de periph.history (pages decroissantes) mais non
      confirme ; si vrai ordre decroissant, aucun drop illegitime. Settle :
      confirmer l'ordre des pages de l'API cloud eedomus sur un periph reel.
      Fix defensif possible : cache d'ancre par entite.
    location: >-
      custom_components/eedomus/coordinator.py:1560
    severity: medium (unverified)
  - summary: >-
      unit_class absent du metadata : HA le derive aujourd'hui depuis
      unit_of_measurement, mais le fallback sera retire en HA 2026.11.
    evidence: >-
      Source HA 2026.9.4 statistics.py (report_usage) : derive explicite avec
      avertissement de deprecation. Revoir a la montee vers HA 2026.10.
    location: >-
      custom_components/eedomus/coordinator.py:1585
    severity: low
  - summary: >-
      Le contrat reel de l'API HA n'est pas verifie par les tests : les stubs
      conftest sont construits d'apres le meme plan et le meme source lu.
    evidence: >-
      Les cles critiques (signature sync @callback, StatisticMeanType IntEnum,
      has_sum requis) ont ete validees contre le source HA 2026.9.4 telecharge,
      mais aucun test n'execute le vrai recorder. Se regle par le smoke test
      post-deploy (sqlite min(start) < installation) puis H.1.6.
    location: >-
      tests/unit/conftest.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** L'import d'historique passe par le service Spook `recorder.import_statistics` (payload limité 32 Ko, dépendance externe interdite par AD-1) et vise parfois une entité fantôme `sensor.eedomus_<periph_id>` ; l'horizon AD-11 (heures strictement antérieures à la première statistique native) n'est pas appliqué.

**Approach:** Remplacer l'appel de service par l'API Python `homeassistant.components.recorder.statistics.async_import_statistics` sur le statistic_id de l'entité réelle (résolution exacte registry, AD-8bis), avec clip AD-11 des heures avant la première statistique native du capteur, réutilisant l'agrégation horaire existante.

## Boundaries & Constraints

**Always:** tz-aware top-of-hour (l'agrégation existante le garantit) ; `source: "recorder"` (exigé par l'API, vérifié source 2026.9.4) ; metadata porte `mean_type` + `unit_of_measurement` (l'API dérive `unit_class` ; requis explicites à partir de HA 2026.11) ; upsert par (statistic_id, start) — le re-import est sûr ; une seule warning utilisateur par chunk (l'appelant `async_import_history_chunk` la possède) ; l'unité vient de l'état live de l'entité (`hass.states.get(entity_id).attributes["unit_of_measurement"]`).

**Never:** Aucun `async_set` d'états passés (AD-1) ; aucune entité fantôme `sensor.eedomus_*` comme cible (le fallback legacy `f"sensor.eedomus_{periph_id}"` de `async_import_history_chunk` est supprimé) ; pas de repli suffixé pour la cible statistics (AD-8bis — le `_resolve_main_entity_id` actuel renvoie un repli suffixé : interdit ici) ; ne pas toucher à la progression/`_load_history_progress` (H.1.4) ; ne pas retirer les écritures inline de `async_fetch_history_chunk` (H.1.3) ; pas d'appel bloquant direct : `statistics_during_period` passe par `hass.async_add_executor_job`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Chunk nominal | Entité exacte résolue, heures antérieures au premier stat natif | `async_import_statistics` appelé avec metadata + stats horaires | Pas d'erreur |
| Aucune entité exacte | Registry sans match exact `<prefixe>_<periph_id>` | Import sauté + log debug (pas de warning user : rien d'anormal) | — |
| Toutes les heures ≥ premier stat natif | Clip AD-11 vide la liste | Aucun appel d'import, log info « nothing to import (AD-11) » | — |
| Entité sans état live | `hass.states.get` → None | Import sauté + warning (unité inconnue → metadata invalide) | Warning nommé |
| Unité non supportée | `unit_of_measurement` hors converters HA | HomeAssistantError de l'API → chunk sauté | Warning de l'appelant |
| Recorder indisponible | DB verrouillée | L'API lève → chunk sauté, reprise au cycle suivant | Warning de l'appelant |

</intent-contract>

## Code Map

- `custom_components/eedomus/coordinator.py` — tout le travail backend :
  - `async_import_history_chunk` (~l.1343) : résolution de l'entité à rendre exacte ; supprimer le fallback fantôme ; le docstring « legacy target » part avec.
  - `_resolve_main_entity_id` (~l.1385) : expose un mode strict (paramètre `allow_suffixed: bool = True` ; le chemin panel P.1.3 garde le comportement actuel, l'import passe `allow_suffixed=False`).
  - `_import_via_statistics` (~l.1440-1538) : l'agrégation horaire (l.1457-1500, issue de a263d65) est conservée telle quelle ; remplacer le bloc service (l.1502-1524) par l'appel API + le clip AD-11 ; le try/except diagnostic reste.
  - `get_entry_prefix` déjà importé ; `dt_util` (homeassistant.util.dt) déjà importé.
- API vérifiée dans le source HA 2026.9.4 (`homeassistant/components/recorder/statistics.py`) :
  - `async_import_statistics(hass, metadata, statistics)` : `metadata` = dict `statistic_id` (valid entity_id), `source` DOIT valoir `"recorder"`, `name` optionnel, `mean_type` ("arithmetic" quand mean présent), `unit_of_measurement` (l'API en déduit `unit_class`, lève si unité non supportée) ; chaque stat : `start` tz-aware top-of-hour (convertie en UTC), `mean/min/max/state` ; upsert par (statistic_id, start) — idempotent.
  - `statistics_during_period(hass, start_time, end_time, statistic_ids: set, period: "hour", units: None, types: {"state"})` → `dict[stat_id, list[rows]]` triées par start ; appel bloquant → executor job ; `start_time=datetime(1970,1,1,tzinfo=utc)`, première ligne = premier stat natif.
- `tests/unit/conftest.py` — ajouter les stubs `homeassistant.components.recorder` + `...recorder.statistics` (`async_import_statistics` MagicMock, `statistics_during_period` MagicMock ; suivi des appels pour les assertions).
- `tests/unit/test_history_value_resolution.py` — pattern existant des tests history (style à suivre).
- Ne pas toucher : `_resolve_history_value`, `_validate_history_data`, `async_fetch_history_chunk` (H.1.3), progression `.storage` (H.1.4).

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/coordinator.py` — résolution exacte (paramètre strict sur `_resolve_main_entity_id`, suppression du fallback fantôme dans `async_import_history_chunk`) + réécriture de `_import_via_statistics` (metadata API, clip AD-11 via premier stat natif, appel `async_import_statistics` en lieu et place du service Spook) — c'est le cœur du ticket.
- [ ] `tests/unit/conftest.py` — stubs du module recorder.statistics.
- [ ] `tests/unit/test_history_import_statistics.py` — nouveaux tests couvrant la matrice I/O.

**Acceptance Criteria:**
- Given un chunk d'heures antérieures, when l'import s'exécute, then `async_import_statistics` reçoit metadata (source "recorder", mean_type, unit_of_measurement) et les stats horaires, jamais le service Spook.
- Given des heures ≥ à la première statistique native, when le clip AD-11 s'applique, then seules les heures strictement antérieures sont importées (aucune si toutes native-or-later).
- Given aucune entité exacte au registry, when l'import tente la résolution, then l'import est sauté sans création de cible fantôme et sans repli suffixé.
- Given `python3 -m pytest tests/unit -q`, when la suite tourne, then 154+X verts, aucun test existant cassé.

## Implementation Notes

Run auto : invocation nue — le ticket résolu est H.1.2 (unique ticket prêt de l'épic history, désigné par la conversation précédant l'invocation).

## Plan Change Log

## Review Triage Log

## Design Notes

L'API `async_import_statistics` écrit dans la table long-terme pour le vrai `statistic_id` — les heures backfillées fusionnent avec le graphe natif du capteur. Le clip AD-11 évite d'écraser (l'upsert UPDATE les heures existantes) des heures calculées par le recorder. Exemple metadata :

```python
metadata = {
    "statistic_id": entity_id,          # entité réelle, ex. sensor.temperature_salon_2
    "source": "recorder",              # exigé par async_import_statistics
    "name": periph_name,
    "mean_type": "arithmetic",          # requis explicite à partir de HA 2026.11
    "unit_of_measurement": unit,        # l'API en dérive unit_class ; lève si non supportée
}
```

## Verification

**Commands:**
- `python3 -m pytest tests/unit -q` -- expected: tous verts (154 existants + nouveaux)
- `uv run --with flake8 --no-project flake8 custom_components/eedomus/coordinator.py` -- expected: aucun nouveau finding (le fichier porte du legacy — ne pas reformatter au-delà des lignes touchées)
- `uv run --with black --no-project black --check custom_components/eedomus/coordinator.py` -- expected: pas de régression du formatage (fichier legacy : vérifier que le diff black n'est pas préexistant avant d'en conclure quoi que ce soit)

**Manual checks (déploiement, hors run auto) :**
- Après deploy : `sudo sqlite3 /config/home-assistant_v2.db "select min(start) from statistics where statistic_id='sensor.<capteur temp>'"` affiche des heures antérieures à l'installation HA, sans doublon sur les heures natives (validation complète en H.1.6).

### 2026-10-03 — Review pass
- verdicts: 25 findings — high 1, medium 5, low 10, false 4, maybe-false 1 (+4 intent-audit observations, descriptive, no defect rows)
- findings:
  - `[high]` `[patch]` (blind-hunter, edge-hunter ×2, edge claim) `await` sur `async_import_statistics` — l'API est un `@callback` SYNCHRONE (source HA 2026.9.4 statistics.py:2830, vérifié) : chaque import lèverait TypeError — fix : retirer le `await` ; le stub conftest passe en MagicMock (sync), il masquait le bug (E6 partagé la même cause racine).
  - `[false]` `[reject]` (blind-hunter) forme d'API dict-keyed — réfutée par le source : signature plate `metadata: StatisticMetaData, statistics: Iterable[StatisticData]` (2026.9.4).
  - `[medium]` `[patch]` (edge-hunter) `mean_type: "arithmetic"` en chaîne — `StatisticMeanType` est un IntEnum (models/statistics.py : NONE=0, ARITHMETIC=1) : la chaîne n'est pas la valeur attendue du TypedDict — fix : passer `StatisticMeanType.ARITHMETIC`.
  - `[medium]` `[patch]` (edge-hunter) metadata sans `has_sum` — clé REQUISE du TypedDict `StatisticMetaData`, KeyError possible dans `update_or_add` — fix : `"has_sum": False`.
  - `[medium]` `[patch]` (blind-hunter + vgap) log de succès trompeur + surcomptage métriques — les chemins de saut (pas d'état, clip vide, pas de données valides) loggent « Successfully imported len(chunk) » et comptent `history_states` à tort — fix : `_import_via_statistics` retourne le nombre importé, l'appelant loggue et compte le réel.
  - `[medium]` `[patch]` (blind-hunter) skip sans entité exacte silencieux — perte définitive de backfill sans aucun signal utilisateur (progression consommée) — fix : debug → warning (l'annotation « rien d'anormal » de la ligne matrice était le propre commentaire du plan, pas l'intention du ticket).
  - `[low]` `[patch]` (blind-hunter) `native_rows[0]` suppose le tri ascendant — fix direct : `min()` sur les start (garde aussi le KeyError résiduel).
  - `[low]` `[patch]` (vgap, pré-vérifié) état live sans `unit_of_measurement` non testé — fix : test épinglant le comportement (import avec unit None, valide per TypedDict `str | None`).
  - `[low]` `[patch]` (blind-hunter + vgap) branche `main_entity_id` non testée (side door sans validation registry, aucun appelant production) — fix : test documentant le contrat explicite.
  - `[low]` `[patch]` (vgap) docstring `test_api_error_skips_chunk` invoque une file de retry qui n'existe pas pour les imports (seuls les fetch errors y entrent, coordinator.py:1169) — fix : corriger la docstring.
  - `[low]` `[patch]` (blind-hunter) cibles fantômes des tests d'agrégation sans explication — fix : commentaire d'en-tête (bypass délibéré pour tester l'agrégation ; H.1.3 purgera).
  - `[maybe-false]` `[defer]` (blind-hunter) l'ancre AD-11 dérive vers nos propres heures backfillées — si les chunks arrivent strictement décroissants (comportement attendu de periph.history), aucun drop illégitime ; à régler : confirmer l'ordre des pages de l'API cloud ; fix défensif possible (cache d'ancre par entité).
  - `[low]` `[defer]` (edge-hunter ×2) `unit_class` absent de metadata — le fallback HA le dérive aujourd'hui mais sera retiré en HA 2026.11 (report_usage) — revoir à la montée HA 2026.10.
  - `[low]` `[defer]` (vgap) aucune vérification du contrat réel HA (stubs authored from the same plan) — se règle par le smoke test post-deploy (sqlite min(start) < install) puis H.1.6.
  - `[low]` `[reject]` (blind-hunter ×2) stub singleton muté + harness dupliqué — hygiène test, fix = refactor au-delà d'une correction directe.
  - `[false]` `[reject]` (blind-hunter) plan-record désynchronisé — le workflow met à jour statut/vérification à ses étapes.
  - `[low]` `[reject]` (blind-hunter) appelant panel non testé — la valeur par défaut est trivialement correcte, les tests panel couvrent leur surface.
  - `[false]` `[reject]` (edge claim) metadata « incomplete » pour 2026.9.4 — le fallback dérive unit_class aujourd'hui ; le risque 2026.11 est le defer ci-dessus.

## Auto Run Result

### 2026-10-03 — Finalize

**Summary.** L'import d'historique utilise l'API Python officielle `recorder.statistics.async_import_statistics` (fin de la dépendance Spook, AD-1) sur l'entité réelle résolue en correspondance exacte registry (AD-8bis, fallback fantôme `sensor.eedomus_<periph_id>` supprimé), avec clip AD-11 : seules les heures strictement antérieures à la première statistique native du capteur sont importées. `_import_via_statistics` retourne le compte réel importé ; le cycle de refresh partiel et les logs comptent sur ce réel.

**Files changed.**
- `custom_components/eedomus/coordinator.py` — résolution exacte (`allow_suffixed=False` pour la cible statistics), suppression du fallback fantôme, réécriture de `_import_via_statistics` (metadata API + clip AD-11 + appel sync), comptes réels, warning sur skip définitif.
- `tests/unit/conftest.py` — stubs `recorder.statistics` (`async_import_statistics` MagicMock sync, `statistics_during_period` MagicMock), vrai IntEnum `StatisticMeanType` sous `recorder.models`.
- `tests/unit/test_history_import_statistics.py` — nouveau : 13 tests couvrant la matrice I/O (nominal, clip AD-11, sans état live, unité manquante, erreur API, `main_entity_id` explicite, lignes non triées, comptes de retour).
- `tests/unit/test_history_value_resolution.py` — assertions migrées vers le contrat sync + metadata (enum, `has_sum`) ; commentaire d'en-tête sur les cibles fantômes (bypass délibéré, purge H.1.3).
- `tests/unit/test_coordinator_partial_refresh.py` — mocks du chemin d'import retournent le compte (`AsyncMock(return_value=len(chunk))`).

**Review breakdown (first pass, 25 findings + 4 observations intent-audit).**
- Patches appliqués : 9 — verdicts à l'entrée : 1 high, 5 medium, 3 low (le high `await` sur `@callback` sync était masqué par le stub AsyncMock ; les 5 medium : `mean_type` IntEnum, `has_sum` requis, comptes réels/logs trompeurs, warning sur skip définitif, + regroupement des lignes de saut).
- Defer : 3 — dérive éventuelle de l'ancre AD-11 (medium, unverified), `unit_class` fallback retiré en HA 2026.11 (low), contrat réel HA couvert par stubs (low). Voir frontmatter `deferred`.
- Rejects avec raison : 4 false (forme d'API dict-keyed réfutée par le source 2026.9.4 ; metadata « incomplete » — le fallback dérive `unit_class` aujourd'hui ; plan-record désynchronisé — mise à jour par le workflow ; duplication de la cause racine E6) + 3 low rejetés (refactor stub/harness au-delà d'une correction directe, appelant panel trivialement correct, commentaires du plan mis à jour par les étapes du workflow).

**Follow-up review recommendation: true.** Pass counts (à l'entrée) : high 1, medium 5, low 3 patchés. Risque non vérifié nommé : le contrat réel de l'API HA (`async_import_statistics` sync, `StatisticMeanType`, `has_sum`, clip `statistics_during_period`) n'est couvert que par des stubs construits d'après le même plan et le même source HA 2026.9.4 lu — jamais exécuté contre un vrai recorder. Le smoke test post-deploy (sqlite `min(start)` antérieur à l'installation, pas de doublon sur les heures natives) est l'étape de vérification suivante, complétée en H.1.6.

**Verification performed.**
- `python3 -m pytest tests/unit -q` : 167 passed (154 existants à la baseline + 13 nouveaux), 0 failure.
- `flake8 custom_components/eedomus/coordinator.py` : aucun finding dans la zone touchée (l.1340-1620) ; le legacy hors zone (E501) est préexistant.
- `black --check` : 5 fichiers touchés inchangés.
- Diff complet relu hunk par hunk après retour du builder (`/tmp/h12_diff_full.patch`, régénéré sur 8f25662).

**Residual risks.**
1. Contrat HA réel non éprouvé hors stubs (cf. follow-up ci-dessus) — smoke test post-deploy obligatoire avant de marquer le parcours backfill validé.
2. Ordre décroissant des pages `periph.history` supposé (ancre AD-11) — à confirmer sur un périph réel, sinon cache d'ancre défensif.
3. `unit_class` dérivé par fallback HA — cassure programmée HA 2026.11, revoir à la montée 2026.10.
