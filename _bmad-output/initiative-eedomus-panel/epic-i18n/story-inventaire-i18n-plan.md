---
title: 'Inventaire i18n'
type: 'chore'
ticket: 1
created: '2026-10-04'
status: done
route: 'oneshot'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/specs/spec-eedomus-i18n/SPEC.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-1 du spec i18n exige que chaque chaîne user-facing de l'intégration soit cataloguée — surface, mécanisme cible, clé — avant toute migration ; rien ne peut être construit sans ce vocabulaire (ticket 3.1 de epic-i18n, covers CAP-1).

**Approach:** Produire le companion `i18n-inventory.md` dans `_bmad-output/specs/spec-eedomus-i18n/` : énumération complète par surface — (1) panneau JS (`www/eedomus-panel.js`) : chaque site de chaîne user-facing (microcopie, libellés de chips/statuts, aria-labels, états vides, tooltips, boutons) avec une clé proposée `panel.*` pour le catalogue websocket ; (2) flows config/options : déjà natifs via `strings.json`/`translations/` — les enregistrer comme « déjà migré » + documenter la section `ui` manquante dans `en.json` ; (3) services : les 9 descriptions de `services.yaml` avec leurs clés cibles dans la section `services` de `strings.json` ; (4) replis d'entités (ex. `Unknown Device`) avec leurs clés cibles ; (5) logs/docstrings/commentaires français : inventaire par fichier (comptage + échantillons, pas ligne par ligne — la passe 3.5 les migre en bloc vers la source anglaise, mécanisme « plain English »). Chaque entrée porte : surface, texte actuel, mécanisme cible (catalogue websocket / translations backend / source anglaise), clé cible.

## Boundaries & Constraints

**Always:** inventaire = lecture seule du repo ; le livrable est le companion du spec (SPEC.md n'est pas touché — le memlog du spec reçoit une entrée pointant vers l'inventaire) ; clés proposées en anglais (source de vérité), préfixe par surface (`panel.`, `services.`, `entity.`) ; le fichier suit la discipline lean du spec.

**Never:** aucune modification de code ; pas de traduction réelle (les valeurs EN/FR viennent en 3.2/3.4) ; pas d'inventaire ligne par ligne des logs (par fichier, avec comptage).

## Code Map

- `custom_components/eedomus/www/eedomus-panel.js` — ~42 sites de chaînes user-facing : microcopie des onglets (Périphériques/Règles/Historique config/Cohérence/Supervision à venir), libellés des puces (COHERENCE_SIGNALS), statuts/annonces, aria-labels, états vides/erreur, boutons d'action, squelettes. Le pin du contrat de signaux (`test_panel_js_keys_every_backend_signal`) garantit la couverture des clés de signaux.
- `custom_components/eedomus/strings.json` + `translations/en.json` + `translations/fr.json` — clés existantes (title, config, errors, success, warnings, ui) : documenter la couverture et l'écart (ui absent de en.json).
- `custom_components/eedomus/services.yaml` — 9 descriptions de services (anglophones, hors mécanisme de traduction).
- `custom_components/eedomus/entity.py` (replis `Unknown Device`), `coordinator.py`/`config_manager.py`/`device_mapping.py` (logs/docstrings FR — comptage par fichier).

## Tasks & Acceptance

**Execution:**
- [ ] `_bmad-output/specs/spec-eedomus-i18n/i18n-inventory.md` — le companion inventaire (cœur du ticket)
- [ ] memlog du spec : entrée pointant vers l'inventaire (CAP-1 livré)

**Acceptance Criteria:**
- Given le panneau JS, when l'inventaire est relu, then chaque site de chaîne user-facing y figure avec une clé `panel.*` proposée — un grep croisé (sites de chaînes vs clés inventoriées) ne trouve aucun écart.
- Given les surfaces backend (flows, services, entités), when l'inventaire est relu, then chaque chaîne a son mécanisme cible et sa clé, et l'écart `ui` de `en.json` est documenté.
- Given les fichiers Python, when l'inventaire est relu, then chaque fichier portant des logs/docstrings FR y figure avec son comptage.

## Implementation Notes

Oneshot : livrable documentaire, aucun code. L'énumération des ~42 sites JS peut être menée par un subagent de scan (il retourne la liste brute) ; la composition de l'inventaire et le grep croisé restent dans la session. Les clés proposées doivent réutiliser les noms déjà établis (COHERENCE_SIGNALS → panel.signals.*, etc.).

## Verification

**Commands:**
- grep croisé : sites de chaînes user-facing dans `www/eedomus-panel.js` vs clés de l'inventaire — expected: zéro écart
- `python3 -m pytest tests/unit/ -q` -- expected: 190 passed (aucun changement de code)

**Manual checks (if no CLI):**
- Relire l'inventaire contre les cinq surfaces du spec (CAP-1).
</intent-contract>

## Implementation Notes

- Oneshot: the enumeration was produced by a read-only scan subagent; composition and cross-check in-session.
- Scope corrections from the review (quick lens, line-verified): the panel carries ~120 sites (not ~42); services.yaml has 4 services (not 9 descriptions); `config_manager.py`/`device_mapping.py` carry no French logs/docstrings (removed from the pass scope); FR logs are 7 calls across `coordinator.py` + `__init__.py` (not 2); docstrings span 8 files; French comments are pervasive (17 py files + the JS) — all corrections folded into the inventory.
- The review falsified the first "no gap" claim: 3 missed panel sites, missed flow/service/entity/backend-string surfaces, a wrong services key shape, and a partially-live "dead" translations family — all fixed in the inventory before commit.

## Review Triage Log

### 2026-10-04 — Review pass (quick)
- verdicts: 19 findings — all real (line-verified by the reviewer): 3 missed panel sites, overstated "already migrated" flows (4 hardcoded flow strings), wrong "dead family" claim (the flat translations family is partially read by the options_flow loader), count errors (logs 7 not 2, files 8 not 7, ui 46 keys, comments pervasive in 17 py files + 54 JS lines), wrong services key shape (domain-nested vs service-keyed), missed surfaces (service-call errors, coordinator FR ValueErrors, ui_service FR prefixes served via websocket, sidebar title), entity-translation grammar unreachable as catalogued, memlog/plan numbers stale.
- routes: all patched in place (the inventory is the deliverable; the corrections ARE the fix) + correcting memlog entry + plan Implementation Notes reconciliation. Nothing deferred, nothing rejected: every finding was a genuine gap in a catalog whose entire value is completeness.

## Auto Run Result

Status: built

- Summary: CAP-1 delivered as the spec companion i18n-inventory.md — ~120 panel sites with panel.* keys across the five tabs, flows (native grammar + hardcoded gaps + the partially-live flat family), 4 services with correct custom-integration key shapes + service-call errors, entity fallbacks with the translation_key decision flagged for 3.4, logs/docstrings/comments at line level (7 FR logs, 26 docstring blocks/8 files, comments in 17 py files + JS), and a new section for backend strings surfaced to the panel (FR ValueErrors, ws-served prefixes, ws fallbacks).
- Files: _bmad-output/specs/spec-eedomus-i18n/i18n-inventory.md (new companion), .memlog.md (+2), story plan.
- Review: 19 findings, all patched before commit — the review made the inventory.
- Verification: pytest tests/unit/ -q → 190 passed (no code changed); the reviewer's own line-verified cross-check replaces the naive grep claim.
- Residual: entity-fallback mechanism and the legacy ui family are explicit 3.4 checkpoint decisions, recorded as such.
