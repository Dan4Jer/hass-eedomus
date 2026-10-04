# i18n inventory — hass-eedomus

> Companion of [SPEC.md](SPEC.md), CAP-1. Every user-facing string with its surface, current text, target mechanism, and target key. The migration tickets (3.2–3.5) consume this catalog; nothing user-facing may ship outside it.

Mechanisms: **ws-catalog** = panel string served by `eedomus/get_translations` (EN source of truth, FR translation, EN fallback) · **backend-i18n** = `strings.json` (HA config-flow grammar, source of truth) + `translations/en.json`/`fr.json` (structurally identical trees) · **plain-EN** = English in source (logs, docstrings, comments — no runtime translation).

## 1. Panel — `www/eedomus-panel.js` (~120 sites, all hardcoded FR, all → ws-catalog)

### Shell / navigation
| Current | Context | Key |
|---|---|---|
| Eedomus Config | panel header h1 | panel.common.title |
| Sections du panneau | tab-nav aria-label | panel.nav.aria |
| Périphériques / Règles / Historique / Cohérence | tab buttons (Historique renders as « Historique config » per the UX spine) | panel.tabs.peripheriques / .regles / .historique / .coherence |
| Onglet inconnu. | unknown-hash fallback | panel.common.unknown_tab |

### Common (shared across tabs)
| Current | Context | Key |
|---|---|---|
| Réessayer | retry buttons (periphs/mapping/versions/coherence) | panel.common.retry |
| commande refusée | WS error fallback | panel.common.command_refused |
| erreur inconnue | saveState error fallback | panel.common.unknown_error |
| aucune entité | inert `<em>` (rows, detail) | panel.common.no_entity |
| date inconnue | badge/timestamp fallback | panel.common.unknown_date |
| inconnu | null field fallback (detail) | panel.common.unknown_value |
| Annuler / Enregistrer / Sauvegarde… / Application… | form buttons & states | panel.common.cancel / .save / .saving / .applying |

### Périphériques
| Current | Context | Key |
|---|---|---|
| Rechercher par nom ou usage_id | search placeholder | panel.peripheriques.search.placeholder |
| Rechercher un périphérique par nom ou usage_id | search aria-label | panel.peripheriques.search.aria |
| Périphériques touchés / ({n}) | filter button + count | panel.peripheriques.filter.label / .count |
| {n} périphériques | status + live region | panel.peripheriques.status.total |
| — filtre « Périphériques touchés » actif : {n} résultats | filtered status suffix | panel.peripheriques.status.filtered |
| Impossible de charger les périphériques : {err}. | error state | panel.peripheriques.error.load |
| Aucun périphérique détecté. Vérifiez que l'intégration eedomus est configurée. | empty state | panel.peripheriques.empty |
| Aucun périphérique ne correspond à “{q}”. Effacez le filtre pour restituer la table. | filter-no-result state (spine row, to add in 3.3 with the migration) | panel.peripheriques.empty.search |
| usage_id / ? | row meta label + missing fallback | panel.peripheriques.row.usage_id_label / .usage_id_missing |
| modifié / Modifié par {rule}, {date} / Modifié par la règle « {rule} », {date} | badge label/title/aria | panel.peripheriques.badge.label / .title / .aria |
| Créer une règle pour ce périphérique | row action | panel.peripheriques.row.create_rule |

### Règles
| Current | Context | Key |
|---|---|---|
| Impossible de charger la configuration : {err}. | error state | panel.regles.error.load |
| Mode d'édition des règles | mode group aria | panel.regles.mode.aria |
| Formulaire / YAML | mode buttons (+ announce) | panel.regles.mode.form / .yaml |
| usage_id pré-rempli : {id} | prefill note | panel.regles.prefill_note |
| Créer une règle | new-rule (+ popover action) | panel.regles.create_rule |
| Aucune règle de mapping. Le mapping par défaut s'applique. | empty list | panel.regles.empty |
| usage_id | rules-row prefix | panel.regles.row.usage_id_label |
| Modifier / Supprimer / Confirmer la suppression ? | row buttons | panel.regles.row.edit / .delete / .delete_confirm |
| usage_id / ex. 7 | form field + placeholder | panel.regles.form.usage_id / .usage_id_placeholder |
| Nom de la règle / ex. Unité température salon | form field + placeholder | panel.regles.form.name / .name_placeholder |
| Plateforme HA / Classe de périphérique / (aucune) / hint « La classe détermine… » | form selects | panel.regles.form.ha_entity / .ha_subtype / .ha_subtype_none / .ha_subtype_hint |
| Éditeur YAML du mapping custom | textarea aria | panel.regles.yaml.aria |
| ligne {n} : {msg} | YAML error prefix | panel.regles.yaml.error_line |
| Mode {mode}. / bascule refusée (2 variantes) | mode announce | panel.regles.mode.announce / .switch_refused / .switch_refused_generic |
| configuration invalide / validation impossible | validation fallbacks | panel.regles.validation.invalid / .unavailable |
| Configuration appliquée. / Règle appliquée. {entity} est maintenant en {unit}. (+ fallbacks) | save statuses | panel.regles.status.applied / .rule_applied / .rule_applied_unit_fallback / .rule_applied_entity_fallback |
| Échec de la sauvegarde : {err}. Le formulaire conserve vos modifications. | save error | panel.regles.status.save_failed |
| règle {usageId} / supprimée | delete status | panel.regles.status.deleted_entity / .deleted_unit |

### Historique config
| Current | Context | Key |
|---|---|---|
| Impossible de charger l'historique : {err}. | error state | panel.historique.error.load |
| Aucune sauvegarde encore. La première sauvegarde archivera la version courante. | empty | panel.historique.empty |
| Configuration actuelle / actuelle / en vigueur | current card | panel.historique.current.title / .badge / .meta |
| Version du {timestamp} | version card | panel.historique.version.title |
| édition manuelle du fichier / migration de schéma / sauvegarde depuis le panneau | reason labels | panel.historique.reason.ingestion / .migration / .panel |
| Restaurer / Confirmer la restauration ? / Restaurer la version du {ts} ? … | restore flow | panel.historique.restore.action / .confirm / .confirm_message |
| Première version — le diff apparaîtra à la prochaine sauvegarde. | diff placeholder | panel.historique.diff.first_version |
| Sauvegarde… puis Application… | status while restoring (pending message) | panel.historique.restore.progress |
| ligne ajoutée / supprimée / modifiée / Différences avec la version précédente | diff aria | panel.historique.diff.line_added / .line_removed / .line_modified / .region_aria |
| Version du {ts} restaurée. … / Échec de la restauration. … | restore statuses | panel.historique.restore.success / .failed |

### Cohérence
| Current | Context | Key |
|---|---|---|
| Rechercher par nom ou periph_id / aria | search | panel.coherence.search.placeholder / .aria |
| À vérifier / ({n}) | view filter + count | panel.coherence.filter.label / .count |
| {n} périphériques / — vue « À vérifier » active : {n} résultats / Aucun périphérique ne correspond à “{q}”. / Tout est cohérent. Aucun périphérique à vérifier. | statuses + live region | panel.coherence.status.total / .filtered / .no_result / .all_clear |
| Cohérence du mapping des périphériques eedomus | sr-only caption | panel.coherence.table.caption |
| periph_id / Nom / Entité HA / Type / sous-type / Statut | column labels (desktop + mobile data-labels) | panel.coherence.columns.periph_id / .name / .entity_id / .type / .status |
| Périphérique (mobile data-label) | mobile reflow | panel.coherence.cell_labels.periph_id |
| Trier par {label} (+ croissant/décroissant suffixes) | sort aria | panel.coherence.sort.aria / .aria_asc / .aria_desc |
| sans entité HA / mapping douteux / règle active / en erreur / cohérent / {raw} / en erreur : {truncated} / title {msg} | chips | panel.coherence.chips.sans_entite / .douteux / .regle_active / .en_erreur / .coherent / .unknown / .en_erreur_detail / .error_title |
| Voir {entity_id} dans Home Assistant | entity-link aria (table + detail button) | panel.coherence.entity_link.aria |
| Détails du périphérique {periph_id} / Détail du périphérique {name} ({periph_id}) | trigger + popover aria | panel.coherence.trigger.aria / .popover.aria |
| État vivant / Identité de mapping | detail section headings | panel.coherence.detail.section_live / .section_identity |
| {error_message} / — nouvelle tentative {retry_after} / ({n} tentative(s)) | error details | panel.coherence.detail.error_message / .retry_after / .attempts |
| Entité HA / Valeur courante / usage_id / Périphérique parent / Dernière mise à jour | live field labels | panel.coherence.detail.entity_id / .current_value / .usage_id / .parent / .last_update |
| ha_entity / ha_subtype / Justification | identity field labels | panel.coherence.detail.ha_entity / .ha_subtype / .justification |
| Voir dans HA | detail action | panel.coherence.detail.view_in_ha |
| Créer une règle | popover/expanded-row action (distinct from the Périphériques row and the Règles tab buttons) | panel.coherence.detail.create_rule |
| Champs bruts de l'API eedomus | raw summary | panel.coherence.detail.raw_summary |
| Impossible de charger la cohérence : {err}. | error state | panel.coherence.error.load |
| Aucun périphérique détecté. Vérifiez que la box eedomus est joignable… / Aucun périphérique ne correspond… Effacez le filtre… / Tout est cohérent… / Tout afficher | empty states | panel.coherence.empty / .empty.search / .empty.all_clear / .empty.show_all |
| Chargement de la cohérence… | skeleton aria | panel.coherence.skeleton.aria |

## 2. Config / options flows — backend-i18n (already native; record + gaps)

The sidebar label registered with the panel (`PANEL_SIDEBAR_TITLE = "Eedomus Config"`, `panel.py:29`) is a distinct user-facing string — mechanism to settle in 3.4 (HA panel-title translation path vs fixed English title).

`strings.json` carries the HA config-flow grammar (`config.step.user.*`, `config.error.*`, `config.options.*`) — **the flow itself is native**. Hardcoded flow strings outside it: `CONNECTION_MODES_EXPLANATION` (`config_flow.py:62`, injected via `description_placeholders`), `errors["base"] = f"Invalid YAML: {e}"` (`options_flow.py:229/:293`), `"YAML Preview"` (`options_flow.py:222/:236`), `"Edit YAML configuration"` fallback (`options_flow.py:348`) — all → backend-i18n with keys in `strings.json` (`config.step.*`/`options.*` placeholders/sections). Gaps found:
- `translations/en.json` + `fr.json` use flat keys (`config.*`, `errors.*`, `success.*`, `warnings.*`) that HA's flow machinery does not read — **but the integration's own loader does**: `options_flow.py` (`async_get_translations`, :60) reads the top-level `title`/`description` at runtime (:347-348). The flat family is partially live code, not dead — 3.4's re-point/drop decision must account for that loader. Trees stay identical.
- `fr.json` has a `ui` section (46 keys, legacy options UI — nothing references it at runtime) absent from `en.json`: the documented structural break; 3.4 completes `en.json` or retires the legacy family (destructive change needs the plan checkpoint's confirmation).
- `strings.json` also has a `ui.*` section (46 keys) — same legacy family, to reconcile in 3.4.

## 3. Services — backend-i18n (to migrate in 3.4)

`services.yaml` (English, no translation keys): 4 services — `refresh`, `set_value` (+ fields `device_id`, `value`), `reload`, `cleanup_unused_entities` — names + descriptions move to the `services` section of `strings.json`, translated in `en.json`/`fr.json`. Keys (custom-integration shape, keyed by service name directly — NOT domain-nested): `services.refresh.name`/`.description`, `services.set_value.name`/`.description` + `services.set_value.fields.device_id.name`/`.description` + `services.set_value.fields.value.name`/`.description`, `services.reload.name`/`.description`, `services.cleanup_unused_entities.name`/`.description`.

**Service-call error strings** (`services.py:118-234`, raised to callers): "device_id and value are required", "Device {device_id} not found on any configured eedomus box", "Failed to set value: …", "No eedomus config entry found", the temperature validations — mechanism **plain-EN** (English source; HA does not runtime-translate service exceptions for custom integrations).

## 4. Entity fallbacks — backend-i18n (to migrate in 3.4)

Hardcoded English today: `entity.py` (`Unknown Device ({periph_id})`, `Unknown Parent ({parent_id})`, `Unknown` ×2), `sensor.py` (`Unknown Device`, `Unknown` ×2), `light.py` (`Unknown` ×2), `text_sensor.py` (`Unknown`, `Unknown ({last_value})`), `climate.py`/`select.py`/`scene.py` (`Unknown error` ×4), sw_version `Unknown` fallbacks (history_sensor, refresh_timing_sensor, endpoint_volume_sensor). Mechanism decision for 3.4's checkpoint: HA's entity-translation grammar is `entity.<platform>.<translation_key>.name` and requires a per-entity `translation_key` (none exists today); the `device_info` fallbacks (model/sw_version `Unknown`) have no strings.json path at all. Either a `translation_key` rollout makes these translatable, or they are accepted as plain-EN data fallbacks — CAP-2's "render in the display language" is only reachable with the first option; the choice is explicit scope for 3.4.

## 5. Logs / docstrings / comments — plain-EN (full pass in 3.5)

Scope correction (review-verified, line-level): the debt is larger than the first pass reported.
- **Logs**: 7 French log calls — `coordinator.py` (5: lines 115, 1196, 1199, 1250, 1289) and `__init__.py` (2: lines 221, 262). All other log calls are English.
- **Docstrings**: 26 French blocks across 8 files — `coordinator.py` (9), `ui_service.py` (4), `light.py` (3), `mapping_registry.py` (3), `mapping_rules.py` (3), `eedomus_client.py` (2), `sensor.py` (1), `config_flow.py` (1 FR section header).
- **Comments**: French comments are pervasive — 17 Python files (notably `coordinator.py` ~43 lines, `light.py` 17, `entity.py` 10, plus `__init__.py`, `switch.py`, `cover.py`, `const.py`, `binary_sensor.py`, `climate.py`, `webhook.py`, `scene.py`, `select.py`, `api_proxy.py`, …) and ~54 lines in `www/eedomus-panel.js`. 3.5's pass and its CI grep cover all of them.

3.5 migrates these files file-by-file with the unit suite green at each step; the log migration preserves message semantics (only the language changes).

## 6. Backend strings surfaced to the panel — plain-EN (migrate with 3.5)

- `coordinator.py` French `ValueError`s visible to service callers (:1816, :1822, :1825 — « Aucune valeur disponible… », « La valeur cible… n'est pas un nombre valide. », « Aucune valeur numérique valide trouvée… ») — plain-EN; without this, an English user still sees French after the full migration.
- `ui_service.py` hardcoded French served through websocket data: `f"mapping personnalisé {key}"` (:849) and `f"règle {key}"` (:858) flow into the panel badge (« Modifié par la règle {nom} ») and coherence rows — plain-EN (the rule NAME stays user data; the label prefix migrates).
- `ui_service.py` ws error fallbacks surfaced in the panel ("Validation failed", "invalid", "UIService not available" — :355/:780/:999/:1011) — plain-EN.
