---
title: 'Fix-now de la rétro i18n : valeur FR dans l''arbre EN, surfaces de flow, sondes de garde'
type: 'bugfix'
ticket: 'story-fix-now-r-tro-i18n-arbre-en-surfaces-de-flow'
created: '2026-10-05'
status: 'built'
route: 'full'
route_source: 'auto'
baseline_revision: 'd6879ee1a2b3acd2c67585c82f92d5281831325f'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 1
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/initiative-eedomus-panel/epic-i18n/epic-i18n-retrospective.md
warnings: []
deferred: []
---

<!-- The two >88 lines the last wrap left behind were re-wrapped in-session
     (config_flow.py STEP_USER_DATA_SCHEMA) — 262 tests green after. -->
---

<intent-contract>

## Intent

**Problem:** La rétro epic-i18n a trouvé cinq fix-now : une valeur française dans l'arbre EN (« Connexion Eedomus », strings.json/en.json:15), le contrat config-flow ↔ strings.json épinglé par aucun test avec des erreurs vol.Invalid brutes (~config_flow.py:158), les labels du flow d'options hors de la grammaire native (13 champs sans section data, un label keyé sur un champ inexistant, le yaml_editor rendant le blurb intégration), la normalisation de région du flow d'options sans témoin, et deux petites sondes de garde (canari trompeur, course de commande dupliquée).

**Approach:** (1) « Connexion Eedomus » → valeur EN (ex. "Eedomus connection") dans strings.json + en.json, la FR reste la traduction ; + test de structure : aucune valeur de l'arbre EN ne porte de marqueur FR (accents/guillemets). (2) TestConfigFlowSection : champs de `STEP_USER_DATA_SCHEMA` ≡ clés de `config.step.user.data` sur les 3 arbres + les clés d'erreur posées par le code présentes dans `config.error` ; migrer les `errors = {"base": str(err)}` en clés `config.error.*` traduites (lister les validateurs de validate_input : hôte vide, plages scan/timeout, identifiants manquants en mode API, au moins un mode). (3) Section `options.step.init.data` pour les ~13 champs réellement rendus (options_flow.py ~:183-195) sur les 3 arbres, réparer `php_fallback_script` → `php_fallback_script_name`, description yaml_editor sur une clé dédiée (`options.step.yaml_editor.description` déjà existe — pointer le placeholder `description` du template sur le contenu d'éditeur au lieu du blurb top-level), épinglé par test de structure (champs du flow d'options ≡ labels). (4) Test unitaire fr-FR : `make_yaml_flow` avec `hass.config.language = "fr-FR"` → placeholders FR (ex. preview_status « ✅ YAML est valide »). (5) Garde JS : documenter/renommer la sonde canari (clé morte `panel.coherence.status.total`, ajouter un commentaire canari) ; token de génération contre la course get_translations dupliquée (le timeout libère le slot, une continuation tardive ne doit pas écraser le marqueur d'un second appel en vol).

## Boundaries & Constraints

**Always:** les trois arbres restent structurellement identiques (tous les tests de parité existants verts) ; les valeurs EN naturelles, FR fidèle ; nouvelles clés ajoutées aux trois arbres en même temps ; l'inventaire §2 reçoit une ligne d'addendum pour les nouvelles clés (config.error.*, options.step.init.data.*) ; grammaire HA native uniquement ; ligne ≤ 88 ; anglais partout (règle 3.5).

**Never:** pas de touche au catalogue `panel_translations.py` ni aux clés panel.* ; pas de changement des contrats ws gelés ; pas de refonte de la garde JS au-delà de la sonde documentée et du token ; pas de migration des items 6-10 de la rétro (badge descripteur, noms dérivés, témoins live, CI préexistant).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Arbre EN | valeur avec marqueur FR ajoutée | le test de structure échoue (nomme fichier:clé) | preuve par mutation |
| Config flow | champ ajouté/renommé sans label | TestConfigFlowSection échoue | — |
| Config flow | vol.Invalid de validate_input | clé config.error.* traduite rendue | — |
| Options flow | chaque champ rendu | label traduit des 3 arbres | — |
| yaml_editor | description du step | intro d'éditeur dédiée, pas le blurb | — |
| fr-FR options | hass.config.language="fr-FR" | placeholders FR (normalisation de région) | — |
| Garde self-test | sonde unknown-key échoue | message parle de la sonde (commentaire canari) | — |
| get_translations timeout + 2e appel | continuation tardive | le marqueur du 2e appel survit (token) | test harnais |

</intent-contract>

## Code Map

- `custom_components/eedomus/strings.json` + `translations/en.json` + `translations/fr.json` — :15 title EN ; + `config.error.*` (validateurs) ; + `options.step.init.data` (~13 champs) ; `php_fallback_script` → `php_fallback_script_name` (config.options) ; yaml_editor description (la clé `options.step.yaml_editor.description` existe déjà — vérifier son contenu vs le blurb).
- `custom_components/eedomus/config_flow.py` — ~:158 `errors = {"base": str(err)}` → clés ; les validateurs de `validate_input` (~:74-107) listent les échecs à cléer.
- `custom_components/eedomus/options_flow.py` — ~:219-226 le placeholder `description` résout la description top-level → pointer sur le contenu d'éditeur ; ~:183-195 les champs rendus (vérifier la vraie liste pour la section data).
- `custom_components/eedomus/const.py:51` — `php_fallback_script_name` (le vrai nom de champ).
- `custom_components/eedomus/www/eedomus-panel.js` — `_loadStrings` ~:853-908 : token de génération contre la course.
- `tests/unit/test_translations_structure.py` — + TestConfigFlowSection (champs ≡ labels, clés d'erreur) ; + test valeurs EN sans marqueur FR ; + section options épinglée (champs ≡ labels).
- `tests/unit/test_options_flow.py` — + test fr-FR (make_yaml_flow, seule la langue change).
- `tests/js/test-i18n-guard.js` — sonde canari ~:476 : commentaire/rénomage.
- `tests/js/test-coherence.js` — + test de la course (timeout → 2e appel → continuation tardive écartée).
- `_bmad-output/specs/spec-eedomus-i18n/i18n-inventory.md` — addendum §2 pour les nouvelles clés.

## Tasks & Acceptance

**Execution:**
- [ ] Volet 1 : arbre EN (title + garde de valeurs) — la classe de trou que les 3 gardes ne voient pas
- [ ] Volet 2 : TestConfigFlowSection + erreurs vol.Invalid → clés
- [ ] Volet 3 : options.step.init.data + label keyé réparé + description yaml_editor
- [ ] Volet 4 : test fr-FR options
- [ ] Volet 5 : canari garde + token get_translations + test de course

**Acceptance Criteria:**
- Given l'arbre EN, when un marqueur FR apparaît dans une valeur, then le test échoue en nommant la clé (preuve par mutation).
- Given le schéma config flow, when un champ dérive des labels, then le test échoue ; given une vol.Invalid de validate_input, when le flow la montre, then elle est traduite.
- Given le flow d'options, when il rend, then chaque champ porte un label traduit et le yaml_editor une intro dédiée.
- Given fr-FR, when le yaml_editor rend, then les placeholders sont FR.
- Given la garde, when la sonde échoue, then le message parle de la sonde ; given la course timeout, then le second appel survit.

## Implementation Notes

Full route — cinq volets indépendants, tous petits, sources ancrées dans la rétro (fichier:ligne). Ordre suggéré : 1 (arbre EN) → 2 → 3 (les tests de structure ensemble) → 4 → 5. Les valeurs EN choisies naturelles (ex. title : "Eedomus connection" — cohérent avec le nom de domaine et les libellés existants).

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 244+ verts (nouveaux tests de structure + fr-FR)
- `node tests/js/test-coherence.js && node tests/js/test-i18n-guard.js` -- expected: verts (course couverte, canari documenté)
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: OK
- `python3 -m pytest tests/e2e/ --collect-only -q` -- expected: 27 collectés (aucun changement E2E requis — les valeurs du catalogue live seront revalidées au prochain déploiement)
</intent-contract>

## Review Triage Log

### 2026-10-05 — Review pass (thorough, 4 lens ; relance des 3 lens fermés par la limite d'enfants)
- verdicts: 29 findings — high 1, medium 6, low 19, false 0, maybe-false 3 (tranchés en patch ou rejet)
- findings:
  - `[high]` `[patch]` TestEnTreeLanguage ne pouvait PAS attraper « Connexion Eedomus » — le bug motivateur, sans accent ni guillemet (3 lens convergents ; la preuve par mutation de l'impl avait planté un mot accentué, prouvant la regex, pas la classe de trou). Patch : Œ/œ/U+2019 ajoutés à la classe de marqueurs + lexique FR (connexion, activer, parametres, peripherique, sauvegarde, veuillez, echec, reessayer) sur les valeurs EN ; preuve par mutation AVEC le cas motivateur (plant « Connexion Eedomus » → échec nommant la clé → retrait → vert).
  - `[medium]` `[patch]` Aucun test comportemental du mapping d'erreurs (la précédence except EedomusValidationError / vol.Invalid n'était épingle par rien) : tests comportementaux paramétrés (nouveau test_config_flow.py, 9 cas).
  - `[medium]` `[patch]` EedomusValidationError sous-classait vol.Invalid (danger silencieux d'ordre de clauses) : plain Exception portant error_key + error_field.
  - `[medium]` `[patch]` Erreurs par champ au lieu de « base » partout : {error_field: error_key} pour les 7 validateurs de champ, base pour no_mode_enabled et le repli générique.
  - `[low]` `[patch]` Branche morte « History can only be enabled » (injoignable : if api_eedomus_enabled: testing not api_eedomus_enabled) supprimée + commentaire trompeur corrigé.
  - `[low]` `[patch]` 9 lignes > 88 dans config_flow.py → repliées sous 88 (les 2 restantes, préexistantes, re-repliées en session post-patch).
  - `[medium]` `[patch]` Section morte config.options SUPPRIMÉE des 3 arbres (aucun consommateur, contenait encore la clé fantôme enable_history) — le split vivant/mort que la rétro i18n demandait ; ligne d'addendum inventaire retirée.
  - `[medium]` `[patch]` Champs du yaml_editor sans labels : options.step.yaml_editor.data ajouté (yaml_content, preview_mode × 3 arbres) + pin TestOptionsFlowSection étendu.
  - `[low]` `[patch]` Step uninstall hors du contrat : pin étendu à config.step.uninstall.data.
  - `[medium]` `[patch]` Clés d'erreur du flow d'options hors de la règle (verif gap) : extraction errors["base"] = "<key>" de options_flow.py épingle à options.error × 3 arbres.
  - `[low]` `[patch]` Regex durcies (quotes simples/doubles dans les marqueurs vol et le dict d'erreurs) ; _vol_marker_args échoue loud sur forme non reconnue (silence supprimé).
  - `[low]` `[patch]` Garde null sur editor_intro (or-chaining description_fallback → littéral de dernier recours).
  - `[low]` `[patch]` Test fr-FR paramétré sur fr-FR + fr-CA (la docstring promettait les deux).
  - `[low]` `[patch]` Course test : poignée de timer capturée par set hass (plus de delay===10000 ni de position).
  - `[medium]` `[patch]` Chemin SUCCÈS du token de génération non testé : cas 15 ajouté (un appel supersédé qui résout n'écrit pas le catalogue, le marqueur du plus récent survit).
  - `[low]` `[reject]` Littéral anglais de dernier recours « Edit YAML configuration » dans options_flow (intent D3) : repli volontaire pour le cas fichier de traductions absent — accepté par design (3.4).
  - `[low]` `[accept]` Pins statiques vs runtime (intent D2) : trade assumé (tests de structure sans import HA) ; les fragilités nommées (regexes, slicing) sont patchées ; le trade fondamental est enregistré.
  - `[low]` `[reject]` Plan cite la clé yaml_editor.description existante vs nouvelle clé editor_intro (intent D3) : la clé description reste le template {description}, editor_intro est son contenu — lecture cohérente, les deux vivent.
  - `[maybe-false→patched]` Renommage box-side jamais propagé sur les noms adoptés (entity.py:239-241) : enregistré comme différé — edge réel mais toucher _adopt_derived_name dépasse le périmètre fix-now (candidat ticket entity).
  - `[maybe-false→deferred]` del _attr_name contournant l'invalidation de cache HA : ce qui trancherait = observation live d'un périphérique sans nom (déjà dans la rétro i18n, item 8).
  - `[low]` `[reject]` Fr-CA/normalisation de région plus large que testée : patchée (paramétrage).

## Auto Run Result

Status: built

- Summary: les cinq fix-now de la rétro i18n livrés ET durcis par la revue : (1) « Connexion Eedomus » → « Eedomus connection » + garde de valeurs EN à deux étages (marqueurs élargis Œ/œ/U+2019 + lexique FR) prouvée sur le cas motivateur lui-même ; (2) TestConfigFlowSection (champs user + uninstall ≡ labels, clés d'erreur extraites du source) + erreurs vol.Invalid migrées en clés traduites PAR CHAMP ({error_field: error_key}, 8 validateurs) + tests comportementaux 9 cas ; (3) options.step.init.data (13 champs) + yaml_editor.data (2 champs) + intro d'éditeur dédiée + section morte config.options supprimée des 3 arbres ; (4) normalisation fr-FR/fr-CA testée ; (5) canari de garde renommé documenté + token de génération avec les DEUX chemins testés (timeout tardif + succès supersédé).
- Files: strings.json, en.json, fr.json (title EN, config.error ×8, options.step.init.data ×13, yaml_editor.data ×2 + editor_intro, config.options supprimée), config_flow.py (EedomusValidationError plain Exception + error_field, branche morte supprimée, ≤88), options_flow.py (or-chaining), www/eedomus-panel.js (token), tests/unit/test_translations_structure.py (+garde EN 2 étages, +pins uninstall/yaml_editor/options-erreurs, regex durcies), tests/unit/test_config_flow.py (NOUVEAU, 9 cas comportementaux), tests/unit/test_options_flow.py (+fr-FR/fr-CA), tests/unit/conftest.py (stub ConfigFlow subclassable), tests/js/test-i18n-guard.js (canari), tests/js/test-coherence.js (course + succès supersédé, poignées de timers), i18n-inventory.md (addendum).
- Review: 29 findings sur 4 lens (relance des 3 lens perdus à la limite d'enfants) — 15 patchs (1 high : le garde EN n'attrapait pas le bug motivateur ; 6 mediums), 4 rejets motivés (repli de dernier recours accepté, trade static/runtime enregistré, 2 maybe-false routés), l'agent d'impl originel ayant été fermé par erreur, les patchs ont été menés par un agent frais avec contexte inline complet.
- Verification: pytest tests/unit/ -q → 262 passed (244 + 18) ; node test-coherence.js verts (course + succès supersédé) ; garde i18n verte self-test 5/5 ; node --check OK ; strings.json ≡ en.json byte-identiques ; config.options absente, yaml_editor.data présente ×3 ; 0 ligne > 88 dans config_flow.py ; 27 tests E2E collectés.
- Residual: le littéral anglais de dernier recours de l'éditeur YAML (accepté par design) ; les pins statiques restent sensibles aux refontes majeures des schémas (les formes non reconnues échouent désormais loud) ; renommage box-side des noms adoptés et l'observation live du friendly_name sans nom restent dans la rétro i18n (items 7-8).
