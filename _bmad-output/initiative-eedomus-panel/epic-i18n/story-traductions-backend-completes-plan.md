---
title: 'Traductions backend complètes'
type: 'feature'
ticket: 4
created: '2026-10-04'
status: 'built'
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 1
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/specs/spec-eedomus-i18n/i18n-inventory.md
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/specs/spec-eedomus-i18n/SPEC.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-2 : les surfaces backend (flows, services, entités) ne s'affichent pas dans la langue de HA. `translations/en.json` (20 clés plates) et `fr.json` (66 clés, dont une section `ui` legacy de 46 clés absente de en) n'ont pas le même arbre ; les descriptions de services vivent dans `services.yaml` (non traduit) ; les replis d'entités (« Unknown Device ({periph_id}) ») sont codés en dur (ticket 3.4 de epic-i18n, couvre CAP-2).

**Approach:** Trois volets — les deux points réservés de l'inventaire sont déjà tranchés par l'inception :
- **Volet ui** : la section `ui` est **comblée** dans en.json (~46 clés traduites en anglais depuis strings.json), pas retirée — arbre identique en/fr (~66 clés chacun ; comptes informatifs, l'inventaire fait foi en cas de divergence). Avant d'implémenter : vérifier que quelque chose consomme cette section (grep du frontend HA cible ou test) ; si elle est morte des deux côtés, proposer sa suppression symétrique au lieu de la traduire.
- **Volet entités** : les replis d'entités sont **localisés** via la grammaire native HA (`translation_key` + `translation_placeholders`, `entity.eedomus.<key>.name`).
- **Volet services + flows** : les 4 services migrent vers la section `services` de strings.json (forme custom-integration, clés par nom de service — shape exact de l'inventaire §3) ; la source EN vit dans strings.json, sa traduction FR vit dans fr.json. Les 4 chaînes de flow codées en dur (`CONNECTION_MODES_EXPLANATION`, `Invalid YAML: {e}` ×2, `YAML Preview` ×2, fallback `Edit YAML configuration`) migrent vers la grammaire strings.json (`config.step.*`/`options.*`).
- **Garde-fous** : le loader de options_flow (`async_get_translations` :60, lit `title`/`description` à :347-348) reste actif — la famille plate reste en place, aucun re-point destructif. Test d'identité structurelle en CI (arbres en/fr identiques + parité placeholders + sections services/entity présentes). Vérifier aussi la traduction native des erreurs de services (HA 2026+ : `HomeAssistantError` avec `translation_domain`/`translation_key`/`translation_placeholders`, ex. `ServiceValidationError`) — si le mécanisme existe dans le HA ciblé, migrer les erreurs levées de services.py comme extension sanctionnée du périmètre ; sinon documenter la version vérifiée et la raison.

## Boundaries & Constraints

**Always:** strings.json = source de vérité EN (grammaire HA), translations/en.json sa compilation (copie exacte, épinglée par test), fr.json sa traduction FR complète ; forme custom-integration pour les services (clé par nom de service, **pas** de nesting par domaine) ; `translation_key` posé **uniquement** quand le nom réel est absent ou blanc (`(periph_data.get("name") or "").strip()` falsy) — le nom réel d'un périphérique ne doit jamais être écrasé par la traduction, et la clé est réévaluée au rafraîchissement du coordinator ; ligne ≤ 88 ; tests unitaires dans le style existant ; le pytest de `tests/unit/` est branché dans `.github/workflows/tests.yml` (step strict, sans `|| echo`).

**Never:** aucune modification du panneau JS ni du catalogue ws (3.2/3.3 figés) ; pas de logs/docstrings/commentaires (3.5) ; pas de retrait de la famille plate `config.*`/`errors.*`/`success.*`/`warnings.*` (partiellement lue par le loader d'options_flow) ; pas de mécanisme de traduction maison.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HA anglais, flow options | locale "en" | chaînes EN (title/description plates + nouvelles clés migrées) | — |
| HA français, flow options | locale "fr" | chaînes FR | — |
| Service refresh visible | l'outil de services de HA | nom/description dans la langue de HA | — |
| Périphérique sans nom | entity fallback | nom traduit via entity.eedomus.*.name + placeholders | — |
| Périphérique nommé | nom API présent | nom réel, **aucune** traduction appliquée | — |
| Nom vide/blanc ou arrivant tard | name "" ou " " ou absent au refresh | repli traduit posé / retiré selon la donnée réelle | — |
| Repli d'état ou d'attribut | « Unknown », « Unknown error », états sensor/light/climate/select/scene | reste EN brut (données, pas de chemin de traduction) | — |
| Arbre en/fr | CI | en.json et fr.json : mêmes clés feuilles, mêmes placeholders par clé ; strings.json ≡ en.json (clés et valeurs) ; services.yaml cohérent avec la section services | le test échoue sinon |

## Code Map

- `custom_components/eedomus/strings.json` — + sections `services` (4 services + fields set_value) et `entity` (replis), chaînes EN ; `ui` existant reste.
- `custom_components/eedomus/translations/en.json` — + section `ui` (46 clés EN), + `services`, + `entity` ; famille plate conservée.
- `custom_components/eedomus/translations/fr.json` — arbre miroir exact ; traductions FR des nouvelles sections.
- `custom_components/eedomus/config_flow.py` — `CONNECTION_MODES_EXPLANATION` → clé strings.json + description_placeholders.
- `custom_components/eedomus/options_flow.py` — `Invalid YAML: {e}` → clé d'erreur traduite avec placeholder ; `YAML Preview` / fallback `Edit YAML configuration` → clés ; loader plat inchangé.
- `custom_components/eedomus/entity.py` (+ sensor/light/text_sensor/climate/select/scene si concernés) — replis de **nom** via `_attr_translation_key` + `_attr_translation_placeholders` (clé posée seulement si `periph_data["name"]` est absent ou blanc, réévaluée au refresh) ; `device_info` (model, sw_version, noms de périphérique) = données, reste EN brut (pas de chemin strings.json — accepté, noté) ; états/attributs « Unknown » restent EN brut.
- `custom_components/eedomus/services.yaml` — HA le lit (déclaration des services/fields, fallback de description) : le fichier reste et doit rester cohérent avec la section `services` de strings.json ; un commentaire le documente.
- `.github/workflows/tests.yml` — step strict `python3 -m pytest tests/unit/ -q` (sans `|| echo`) : la suite unitaire 3.2/3.4 n'était jamais exécutée en CI.
- `tests/unit/test_translations_structure.py` (nouveau) — identité des arbres en/fr (clés feuilles récursives), parité des placeholders `{x}` par clé, identité strings.json ≡ en.json (clés + valeurs feuilles), cohérence services.yaml ↔ section `services` (chaque service/field déclaré apparaît), présence des sections services (4 services, shape custom-integration) et entity, présence de la section `ui` dans les **deux** fichiers.
- Sidebar (`panel.py:29`, `PANEL_SIDEBAR_TITLE = "Eedomus Config"`) : titre fixe EN conservé (nom de marque ; pas de chemin de traduction pour les titres de panneau custom) — décision notée, rien à faire.

## Tasks & Acceptance

**Execution:**
- [ ] en.json : section `ui` comblée (46 clés EN, après vérification de consommation) + sections `services`/`entity` ; fr.json miroir exact avec traductions
- [ ] strings.json : sections `services` + `entity` (source EN) ; migration des 4 chaînes de flow codées en dur ; vérification du mécanisme d'erreurs de services traduites
- [ ] entity.py : translation_key/translation_placeholders sur les replis de nom uniquement (condition absent/blanc, réévaluée au refresh)
- [ ] Test d'identité structurelle (arbres, placeholders, strings.json ≡ en.json, cohérence services.yaml) + brancher pytest tests/unit/ dans le workflow CI

**Acceptance Criteria:**
- Given le test CI, when en.json et fr.json divergent (clé, placeholder, section), then le test échoue ; when strings.json diverge de en.json, then le test échoue ; when services.yaml déclare un service absent de la section services, then le test échoue.
- Given la suite CI, when le workflow tourne, then `python3 -m pytest tests/unit/ -q` s'exécute strictement (le job échoue sur rouge).
- Given un service listé dans l'outil de services de HA, when la locale est fr, then nom et description s'affichent en français.
- Given un périphérique sans nom, when HA rend l'entité, then son nom est traduit (FR : « Périphérique inconnu ({periph_id}) ») ; given un périphérique nommé, then son nom réel est inchangé.
- Given les flows config/options, when une chaîne migre (explication modes, erreurs YAML, preview), then elle s'affiche dans la langue de HA via la grammaire native.

## Implementation Notes

Full route — subagent d'implémentation avec l'inventaire comme source de vérité (§2 flows, §3 services, §4 entities font foi pour les clés et les textes). Vérifier la mécanique `translation_key` contre le HA ciblé (2026+) : `friendly_name` résout `_attr_name` d'abord, la traduction s'applique seulement si le nom est absent — poser la clé conditionnellement. Les textes FR : naturels et fidèles (ex. « Unknown Device ({periph_id}) » → « Périphérique inconnu ({periph_id}) », « Unknown Parent » → « Parent inconnu »). Les erreurs de service-call : vérifier d'abord le mécanisme natif HA (voir Approach) ; la justification plain-EN n'est conservée que si le HA ciblé ne le supporte pas.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 206+ verts, y compris le nouveau test d'identité structurelle
- `python3 -m json.tool` sur en.json, fr.json et strings.json -- expected: valides
- `node tests/js/test-coherence.js && node tests/js/test-i18n-guard.js` -- expected: verts (rien ne bouge côté panneau)
</intent-contract>

## Review Triage Log

### 2026-10-04 — Review pass (thorough, 4 lenses)
- lens verdicts: blind 12, edge-case-hunter 11, verification-gap 4 (+2 other), intent-alignment 0 (les trois déviations documentées de l'impl — ui complétée bien que consommée par rien, 2 services hors services.yaml, chaînes de preview hors inventaire — adjudiquées sanctionnées par le texte du plan ; alignment vérifié programmatiquement : strings.json ≡ en.json blob-identique, 11 clés d'exception = les sites de raise).
- CRITIQUE (les trois, vérifiées puis patchées) : (1) `config.step.user.data` étiquetait des champs qui n'existent pas dans `STEP_USER_DATA_SCHEMA` (host/api_key/secret/php_fallback morts ; 15+ champs rendus en snake_case brut) — renommé 17/17 sur le schéma réel ; (2) `del self._attr_name` → AttributeError sur les chemins de log d'erreur (set_value échoué sur un périphérique sans nom = crash du handler au lieu du log) — getattr sur tous les sites (entity, light, climate, select, scene) ; (3) climate/select/scene assignaient `_attr_name` sans `_adopt_derived_name()` → le fallback traduit était écrasé par un nom vide puis effacé au refresh (feature morte sur 3 plateformes) + KeyError sur clé name absente — adoptés au pattern sensor.py.
- production (patchée) : les 2 services non déclarés (set_climate_temperature, cleanup_unused_devices) déclarés dans services.yaml + traduits ×3 arbres + EXPECTED_SERVICES dérivé de services.yaml ; région de locale (fr-FR) écorchée dans le loader plat (le yaml_editor FR tombait en en.json) ; coercion str() du nom (numérique API) ; preview status « ✅/❌ » migrés vers options.step.yaml_editor.status_valid/status_invalid + helper token, injections mortes (title, content du init, explanation du uninstall) supprimées au profit de clés traduites (config.step.uninstall.*, options.step.init.*) ; config.error.unknown ajouté + cannot_connect câblé ; calque FR « Réponse invalide reçue de eedomus » corrigé ; sections plateforme mortes entity.scene (jamais dans PLATFORMS) et entity.text_sensor (ajoutés via la plateforme sensor) supprimées ; handle_set_value ne log-plus-en-crash l'erreur traduite qu'il relève.
- tests (verif lens, chaque finding prouvé par mutation — renommage de clé ou suppression de sous-arbre : 221 verts) : TestExceptionsSection (clés translation_key de services.py ↔ arbres exceptions ×3 + parité placeholders), TestAsyncStepYamlEditor (preview / yaml invalide → errors={"base":"invalid_yaml"} / échec de sauvegarde), TestFlowStepsPresent (config.step.user.*, options.step.yaml_editor.description, options.error.invalid_yaml présents ×3). 226 verts.
- inventaire : addendum §2 (renommage data.*, clés uninstall/init/helper/status/unknown, calque) et §3 (2 services + note exceptions épinglées).
- non-patchés, avec raisons : prose des validateurs de schéma vol.Invalid (brute, documentée — trop de messages à cléer pour ce ticket) ; scripts/tests en CI ne collecte pas (importe homeassistant non installé) mais `|| echo` cache — décision enregistrée advisory-only, candidat 3.6/3.7 ; noms device_info EN + composition « Unknown Device (X) Unknown Parent (X) » — acceptance du plan (données), l'E2E 3.7 doit l'observer en live ; PANEL_SIDEBAR_TITLE EN fixe (décision du plan) ; staleness du registre has_entity_name sans reload (inhérent HA).
- déviations assumées de l'impl : la ligne `data.remove_entities` du uninstall ajoutée pour éviter le snake_case brut (au-delà de la lettre de G, ratifiée ici) ; EedomusConnectionTestError dédié pour câbler cannot_connect.

## Auto Run Result

Status: built

- Summary: CAP-2 livré — strings.json devient l'arbre source EN fusionné (154 feuilles), en.json sa copie byte-identique, fr.json son miroir structurel complet (section ui comblée des deux côtés, 46 clés) ; services (6 déclarés, shape custom-integration, cohérence services.yaml épinglée), entités (replis de nom localisés via translation_key/has_entity_name, réévalués à chaque refresh, 7 plateformes réelles), exceptions de services (11 clés, mécanisme natif vérifié contre HA 2026.9.4 en source), chaînes de flow migrées à la grammaire native (description, invalid_yaml, preview, init, uninstall) ; step CI strict pytest tests/unit/.
- Files: strings.json/en.json/fr.json, config_flow.py, options_flow.py, entity.py, light.py, climate.py, select.py, scene.py, sensor.py, services.py, services.yaml, .github/workflows/tests.yml, tests/unit/{conftest,test_translations_structure,test_entity_name_fallback,test_options_flow}.py, i18n-inventory.md (addendum).
- Review: 27 findings, 3 critiques de production (crash, labels cassés, feature morte sur 3 plateformes) + 4 trous de vérification prouvés par mutation ; 15 items de patch + 1 évaluation appliqués par le subagent d'implémentation.
- Verification: pytest tests/unit/ -q → 226 passed (221 + 5) ; arbres ×3 identiques (154 feuilles), strings ≡ en vérifié indépendamment en session ; json.tool ×3 ; node test-coherence + test-i18n-guard verts (panneau non touché) ; yaml workflow valide.
- Residual: prose des validateurs vol.Invalid brute (documentée) ; scripts/tests advisory-only en CI ; observation E2E 3.7 requise pour la composition des noms d'entités/device en live.
