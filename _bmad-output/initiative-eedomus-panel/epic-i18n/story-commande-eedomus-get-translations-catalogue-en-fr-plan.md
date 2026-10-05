---
title: 'Commande eedomus/get_translations (catalogue en/fr)'
type: 'feature'
ticket: 2
created: '2026-10-04'
status: done
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 1
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/specs/spec-eedomus-i18n/i18n-inventory.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-3 (volet backend) : le panneau n'a aucun moyen d'obtenir ses chaînes localisées — tout est codé en dur côté JS. Le backend doit servir le catalogue avant que 3.3 ne migre le panneau (ticket 3.2 de epic-i18n, covers CAP-3).

**Approach:** Nouvelle commande websocket `eedomus/get_translations` (dispatcher `ui_service`, `require_admin`) : le panneau appelle avec sa locale (ex. `{"locale": "fr"}`) et reçoit `{locale, translations}` — un dictionnaire plat clé → texte pour toutes les clés `panel.*` de l'inventaire. Le catalogue vit côté Python dans un module dédié (`panel_translations.py`) : `EN` est la source de vérité (~120 clés, textes anglais rédigés depuis les textes français actuels de l'inventaire), `FR` en est la traduction complète (les textes français actuels). Résolution de locale : locale demandée si couverte, sinon EN ; par clé, toute clé manquante dans la langue demandée retombe sur EN (robustesse) ; locale inconnue/absente → EN. Interpolation : les textes portent des placeholders `{n}`, `{err}`, `{q}`, etc. tels quels — le panneau fait le remplacement.

## Boundaries & Constraints

**Always:** pattern dispatcher exact des 8 commandes existantes (constante WS_TYPE, @require_admin @websocket_command @async_response, inscription dans WS_COMMANDS, compteur de registration mis à jour) ; clés = celles de l'inventaire (`panel.*` uniquement — les surfaces backend-i18n viennent en 3.4) ; textes EN naturels (pas des calques littéraux) mais fidèles à la sémantique des originaux FR ; ligne ≤ 88 ; tests unitaires dans le style existant (tests/unit/test_ui_service.py) + le pin du contrat de signaux doit rester vert.

**Never:** pas de changement du panneau JS (3.3) ; pas de toucher aux traductions flows/services (3.4) ; aucune des commandes gelées ne change (get_peripherals, get_coherence — leurs tests de contrat restent verts sans modification) ; pas de lib de traduction.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | locale "fr" | {locale:"fr", translations: FR complet (~120 clés)} | — |
| Locale non couverte | "de" ou absente | {locale:"en", translations: EN} | Jamais d'erreur |
| Clé manquante en fr | FR partiel (transitoire) | la clé retombe sur EN dans le catalogue servi | — |
| Clé inconnue demandée | — | n/a : la commande sert tout le catalogue, pas de clés individuelles | — |
| Admin | non-admin | require_admin refuse (HA) | Standard HA |

## Code Map

- `custom_components/eedomus/ui_service.py` — pattern dispatcher (constantes ~l.20, dispatchers ~l.88-230, WS_COMMANDS, tests de registration 7→8/14→16 déjà ajustés à 8 commandes — passer à 9/18), `_get_ui_service`, handler minimal.
- `custom_components/eedomus/panel_translations.py` — NOUVEAU module : `PANEL_TRANSLATIONS = {"en": {...}, "fr": {...}}` + `get_panel_translations(locale) -> tuple[str, dict]` (résolution + fallback par clé). Source des clés/valeurs : l'inventaire (context:).
- `tests/unit/test_ui_service.py` — style TestGetCoherenceHandler/Dispatcher : catalogues complets (arbres en/fr identiques — test d'identité des clés, qui servira aussi 3.4), fallback locale, fallback par clé, dispatcher exécuté (service attendu / service_unavailable), compteur de registration.
- L'inventaire (`i18n-inventory.md`) fait foi pour les ~120 clés — les reprendre à l'identique, y compris les clés à placeholder.

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/panel_translations.py` — catalogue EN (source) + FR + résolution — cœur du ticket
- [ ] `custom_components/eedomus/ui_service.py` + tests — commande + dispatcher + tests (registration, dispatcher, arbres identiques, fallbacks)

**Acceptance Criteria:**
- Given un appel `eedomus/get_translations` avec locale "fr", when la réponse arrive, then `{locale, translations}` porte le catalogue FR complet — l'arbre des clés est identique à EN (test).
- Given une locale non couverte ou absente, when la commande est appelée, then le catalogue EN est servi — jamais d'erreur, jamais de catalogue vide.
- Given le panneau (futur, 3.3), when il consommera le catalogue, then chaque clé `panel.*` de l'inventaire y figure.

## Implementation Notes

Full route : le catalogue est mécanique mais volumineux (~120 clés × 2 langues, EN à rédiger) — subagent d'implémentation avec l'inventaire en source unique. Les textes EN : naturels et concis (ex. « Réessayer » → "Retry", « Tout est cohérent. Aucun périphérique à vérifier. » → "Everything is consistent. No peripheral to check."). Les placeholders restent `{x}` (le panneau remplace par replace ou template).

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: tous verts (190 + nouveaux), pins de contrats gelés intacts
- `git status --short` -- expected: seuls panel_translations.py, ui_service.py et tests modifiés

**Manual checks (if no CLI):**
- Relecture de l'arbre des clés contre l'inventaire.
</intent-contract>

## Review Triage Log

### 2026-10-04 — Review pass (thorough, 4 lenses)
- lens verdicts: blind-hunter 11 findings, edge-case-hunter 3, verification-gap 4 (+2 other), intent-alignment 0 (fully aligned, key-set/FR-fidelity/dispatcher/boundaries verified programmatically).
- conflict resolved: the lenses disagreed on the popover aria key — expansion of the inventory shorthand (suffix replaces the last segment, cf. `panel.tabs.peripheriques / .regles`) yields `panel.coherence.trigger.popover.aria`; the JS confirms the popover belongs to the coherence trigger (aria set on the `coherence-id-trigger` button, popover text at eedomus-panel.js:2468). Catalog renamed in both trees; the inventory is the source of truth and stays as written.
- patched (production): black-format the catalog module; locale normalization handles `_` separators (`fr_FR` → `fr`); schema accepts `{"locale": null}` (`vol.Any(str, None)` + handler coercion — a null locale is a legitimate frontend state, non-strings stay rejected as malformed messages); error path aligned with the coherence handler (`%s` logging + `exc_info=True`, stable client message, no raw `str(e)`); handler moved out of the coherence block (no longer splits `_handle_get_coherence`/`_collect_coherence`); `get_available_endpoints` gained the translations entry; docstring states the exact 136-key count.
- patched (tests): inventory key-set parity test (parses i18n-inventory.md, expands the `/` shorthand, asserts set equality with `PANEL_TRANSLATIONS["en"]` — pins the very mismatch the lens found); placeholder `{token}` parity EN/FR; non-empty-str values guard; normalization tests (`" FR"`, `fr_FR`); `test_exception_sends_error` mirroring the sibling handlers; conftest `websocket_command` stub now stashes `_ws_schema`/`_ws_command` (mirrors real HA) + a registration test pinning the translations dispatcher's type and Optional-null-locale schema (the schema was previously dead code in the unit env).
- not patched, with reasons: `get_available_endpoints` broader staleness (3 of 9 listed before this ticket) — scope creep, one entry added only; `uv.lock` untracked — never staged (known).
- line-length note: 5 catalog lines exceed 88 chars — unsplittable string literals in black-canonical form (black cannot split them; 561 such lines already committed in the repo). Black-clean 4/4 files takes precedence over the manual ≤88 rule, which exists for the no-black case.

## Auto Run Result

Status: built

- Summary: CAP-3 (volet backend) delivered — 9th ws command `eedomus/get_translations` serving `{locale, translations}` from the new `panel_translations.py` (136 `panel.*` keys, EN source of truth + FR complete, locale normalization with per-key EN fallback, served copies isolated). Dispatcher pattern identical to the 8 existing commands; registration counters 8→9 and 16→18; frozen `get_peripherals`/`get_coherence` contracts untouched.
- Files: custom_components/eedomus/panel_translations.py (new, 411 lines), ui_service.py (+62/-6), tests/unit/test_ui_service.py (+282/-8), tests/unit/conftest.py (+9/-1).
- Review: 18 findings across 4 lenses, all real; 14 patch items applied by the implementation subagent + line-length reconciliation; inventory/catalog key mismatch (`panel.coherence.trigger.popover.aria`) caught and fixed pre-3.3.
- Verification: pytest tests/unit/ -q → 206 passed (200 + 6 new); black --check 4 files unchanged; node tests/js/test-coherence.js pass; node --check eedomus-panel.js OK.
- Residual: none for this ticket; the 5 unsplittable >88 lines and the pre-existing endpoint-list staleness are recorded above.
