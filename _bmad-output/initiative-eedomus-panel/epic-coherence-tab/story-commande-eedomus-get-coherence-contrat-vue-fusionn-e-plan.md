---
title: 'Commande eedomus/get_coherence (contrat + vue fusionnée)'
type: 'feature'
ticket: 1
created: '2026-10-04'
status: 'built'
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: true
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Le panneau n'expose aucune des données dont l'onglet Cohérence a besoin : le mapping registry (ha_subtype, parent_periph_id, justification), l'état vivant, les champs bruts de l'API et les signaux de cohérence n'existent nulle part côté websocket (ticket 2.1 de l'épique epic-coherence-tab, covers CAP-6).

**Approach:** Nouvelle commande websocket `eedomus/get_coherence` (require_admin, dispatcher `ui_service` existant) qui étend la projection `_project_coordinator` : chaque ligne périphérique gagne les champs du registry (join par periph_id), l'état vivant (valeur courante, dernière mise à jour), une section raw (le dict periph de coordinator.data, JSON-safe), et `signals` — la liste dérivée des 4 signaux : `sans_entite` (entity_id null), `douteux` (entité sans état vivant, ou capteur sans unité), `regle_active` (modified_by_rule), `en_erreur` (periph dans coordinator._retry_queue). Une ligne par périphérique de chaque coordinator (multi-box), jamais une ligne perdue ; `eedomus/get_peripherals` reste inchangé (AD-7 : lecture uniquement).

## Boundaries & Constraints

**Always:** suivre le pattern exact des commandes existantes (constante WS_TYPE, @require_admin @websocket_command @async_response, dispatch vers EedomusUIService, inscription dans la liste d'enregistrement) ; réutiliser `_project_coordinator`/`_resolve_entity_id` et `_matching_rule_name` (ne pas dupliquer la résolution) ; signals = liste de chaînes cumulables ; JSON-safe partout (le dict raw peut contenir des datetime — sérialiser) ; tests unitaires dans le style de tests/unit/test_ui_service.py.

**Never:** ne pas modifier le contrat de `eedomus/get_peripherals` (sa response shape doit rester identique — un test le verrouille) ; pas d'appel direct à l'API eedomus (AD-7) ; pas d'écriture ; pas de tri ni de filtrage côté backend (le frontend trie localement).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | ~165 periphs, registry rempli | `{peripherals: [...165 lignes], total: 165}`, chaque ligne avec registry + état + raw + signals | No error expected |
| Periph sans entité HA | entity_id null (résolution échoue) | Ligne présente, `signals` contient `sans_entite`, champs entité null | Ligne jamais perdue |
| Periph hors registry | periph non mappé (absent du registry) | Ligne présente avec registry fields null, join ne plante pas | Pas d'exception |
| Periph en erreur | periph dans coordinator._retry_queue | `signals` contient `en_erreur` (+ error_message exposé dans la ligne) | — |
| Capteur sans unité | sensor vivant sans unit_of_measurement | `signals` contient `douteux` | — |
| get_peripherals inchangé | appel des deux commandes | response shape de get_peripherals identique (test de contrat) | — |

## Code Map

- `custom_components/eedomus/ui_service.py` — dispatcher : pattern `_ws_get_peripherals` (l.115-128), liste d'inscription (l.~185 `WS_TYPE_EEDOMUS_GET_PERIPHERS` etc.), `EedomusUIService._project_coordinator` (l.456-494, à étendre ou factoriser), `_resolve_entity_id` (l.496-504, réutiliser), `_matching_rule_name` (badge modifié). Multi-box : `_collect_peripherals` (l.436) itère `hass.data[DOMAIN]` par coordinator.
- `custom_components/eedomus/mapping_registry.py` — `get_mapping_registry()` (l.41) retourne une liste de dicts {periph_id, periph_name, parent_periph_id, ha_entity, ha_subtype, justification}.
- `custom_components/eedomus/coordinator.py` — `coordinator.data[periph_id]` : dict periph brut (name, usage_id, value, room/parent fields) ; `coordinator._retry_queue[periph_id]` : {error_time, retry_after, error_message, attempts}.
- `custom_components/eedomus/const.py` — ajouter la constante du type de commande près des existantes.
- `tests/unit/test_ui_service.py` — style existant des tests du dispatcher ; la conftest stubbe les modules HA.

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/ui_service.py` + `const.py` — commande `eedomus/get_coherence` : constante, dispatch, inscription, `_handle_get_coherence` + collecte/join/signals — cœur du ticket
- [ ] `tests/unit/test_ui_service.py` — tests : join complet (periph sans entité présent, periph hors registry présent), dérivation des 4 signaux, contrat get_peripherals inchangé, JSON-safety (datetime sérialisé)
- [ ] `tests/unit/test_history_import_statistics.py`-adjacents — aucun changement attendu, juste vérifier que la suite passe

**Acceptance Criteria:**
- Given l'instance live avec ~165 périphériques, when un appel `eedomus/get_coherence`, then la réponse contient une ligne par périphérique (aucune perdue, y compris sans entité HA) avec registry, état vivant, raw et signals.
- Given un périphérique en file d'erreur du coordinator, when la réponse est collectée, then sa ligne porte le signal `en_erreur` et son error_message.
- Given un appel `eedomus/get_peripherals` avant et après ce changement, then la forme de sa réponse est identique.

## Implementation Notes

Full route : ~250 lignes (handler + join + registration + tests), 3 fichiers. Le raw periph dict peut contenir des datetime — sérialiser en ISO pour rester JSON-safe (pattern à vérifier dans _project_coordinator qui n'expose pas le dict brut aujourd'hui). Unknown du ticket : champs exacts de coordinator.data — le dict brut sérialisé les expose tous ; le popover frontend (2.4) choisira quoi afficher.

## Review Triage Log

### 2026-10-04 — Review pass (thorough: blind-hunter, edge-case-hunter, verification-gap, intent-alignment)
- verdicts: 28 findings — high 1, medium 8, low 12, false 4, maybe-false 3
- findings (routes: patch ×7 groups, defer ×3, reject ×6):
  - `[high]` `[patch]` Stale registry join after reload — `clear_mapping_registry` is never called, devices re-register at every reload, first-wins kept the pre-change entry: the view showed the mapping as it was BEFORE the user's save, defeating the tool's primary use. Patched: last-wins join + test.
  - `[medium]` `[patch]` douteux missed dead states and over-flagged enum sensors — unavailable/unknown are not living states (spec: "pas d'état vivant"); unit check now only for device_class set and != enum. Patched with tests.
  - `[medium]` `[patch]` Module dispatcher never executed by any test (pre-verified by verification-gap) — a wrong-handler copy-paste would pass the suite. Patched: dispatcher tests (service awaited / service_unavailable).
  - `[medium]` `[patch]` Non-finite floats break JSON-safety of the whole payload — NaN/Infinity passed through _json_safe. Patched: isfinite guard → str, with test.
  - `[low]` `[patch]` Group: "11 keys" comment (10 keys), lazy logging + exc_info, attempts/retry_after exposure, signal literals → module constants, realistic exception test, multi-box box-1 intactness assertion.
  - `[maybe-false]` `[defer]` Multi-box periph_id collision in the global registry join (medium if true) — settles with a multi-box instance or per-entry registry index; not demonstrable on this single-box deployment.
  - `[low]` `[defer]` raw_by_id re-walk coupling — refactor candidate for the epic's sweep (2.7).
  - `[medium]` `[defer]` Live-instance check (~165 lignes) requires deploy — covered by the epic's closing E2E story (2.8) on the Pi.
  - `[false]` `[reject]` "No frontend consumer" — sequenced by design (2.2+ wires the tab). "en_erreur under-reports polling errors" — spec fixes the operational definition (retry queue). "Non-dict retry entry" — unreachable (coordinator always writes dicts). "Semantics trace to plan, not ticket" — the plan legitimately instantiates the ticket. "Constant placement vs plan code map" — fix would edit this plan; the existing-pattern constraint wins. "Unbounded raw payload" — low, fix beyond intent (no truncation designed).

## Auto Run Result

Status: built

- Summary: `eedomus/get_coherence` implemented per plan: dispatcher (require_admin, ui_service pattern), coordinator-driven join (never a lost row), registry fields + living state + JSON-safe raw + 4 signals + error details, get_peripherals frozen by contract test.
- Files: custom_components/eedomus/ui_service.py (+~190), tests/unit/test_ui_service.py (+~450, 17 new tests incl. dispatcher, last-wins join, dead-state douteux, enum exclusion, NaN guard, multi-box intactness).
- Review: 28 findings — 7 patch groups applied (1 high: stale registry join), 3 deferred (multi-box collision unverified; raw re-walk → sweep 2.7; live check → 2.8), 6 rejected with reasons.
- Follow-up review: recommended — the last-wins join and the douteux refinement are new code verified by unit tests only; the live surface (~165 rows) is untouched until 2.8.
- Verification: pytest tests/unit/ -q → 185 passed (was 168 before the ticket). Lines ≤ 88 (black unavailable locally).
- Residual risks: multi-box collision (deferred), raw payload size on large installs (rejected as low).

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: tous verts, y compris les nouveaux tests get_coherence
- `git status --short` -- expected: seuls les fichiers visés modifiés

**Manual checks (if no CLI):**
- Sur l'instance déployée (après les tickets suivants ou via un appel websocket manuel) : `eedomus/get_coherence` renvoie ~165 lignes avec signals.
</intent-contract>
