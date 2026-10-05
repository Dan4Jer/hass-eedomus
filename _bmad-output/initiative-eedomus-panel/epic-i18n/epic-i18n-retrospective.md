---
epic: epic-i18n
date: 2026-10-05
verdict: accepted-with-open-items
criteria: declared
headless: false
---

# Rétrospective — epic-i18n (audit et migration vers les mécanismes natifs Home Assistant)

## Epic summary

Épique 3 de l'initiative eedomus-panel : 7 tickets, **tous `done`** (le dernier, 3.7, validé live sur le Pi le 2026-10-05). CAP-1 (inventaire), CAP-2 (traductions backend structurellement identiques), CAP-3 (catalogue websocket panneau, zéro chaîne en dur), CAP-4 (anglais-source complet). Tickets au statut `built` non passés à `done` : aucun. Tickets non terminés acceptés en rétro : aucun.

Ranges : `baseline_revision` présente sur 3 plans (3.5/3.6/3.7) ; 3.1-3.4 sans baseline — range d'épique **inférée** `177eeb5..6a9f0d4` (26 commits dont 8 merges dependabot intercalés). Le story 104 (JSON brut, backlog) et la rétro cohérence sont des travaux ADJACENTS intercalés dans la fenêtre — notés comme contexte, pas des tickets de l'épique. Diff code : `/tmp/epic-3-code.diff` (11 381 lignes, custom_components + tests).

## Evidence inventory

- **Epic file** — `epic-i18n/epic-i18n.md` : 4 CAPs, 5 critères Done when, 4 décisions utilisateur (passe complète, repli EN + FR complet, checkpoints 3.3/3.5, épique AVANT supervision).
- **Plans** — 7, tous `done`, chacun avec Review Triage Log (revue 4-lens par ticket) — le record des revues par ticket est complet pour 3.2-3.7 (3.1 : revue quick 19 findings).
- **Volumes (git_evidence, non-merge)** — `tests/js/test-coherence.js` +1262/−63, `eedomus-panel.js` +965/−322 (la migration i18n a rétréci le panneau), `test-i18n-guard.js` +678/−151, `test_ui_service.py` +568/−58, `panel_translations.py` +454/−17 (144 clés ×2), `test_translations_structure.py` +303, fixtures +294, `test_no_french_source.py` +276, `fr-catalog.js` +160/−100, `translations/en.json` +256/−2, options/flows/services/entity/exceptions sur 3.4.
- **Preuve live (3.7, ce jour)** — Pi déployé à 6a9f0d4, HA 2026.9.4 RUNNING, `pytest tests/e2e/ -v` → **27 passed in 62.31s** dont 7 tests i18n (égalité de valeurs en/fr vs fixtures, parités, replis de→EN, fr-FR→fr, null→EN) ; logs post-restart sains, zéro erreur ws/eedomus.
- **Gardes CI** — JS hardcode (union EN+FR, self-test 5/5) + Python no-french (self-test 3 sondes dont colocalisation) — mutation-prouvées.
- **Rétro précédente** — `epic-coherence-tab-retrospective.md` (accepted-with-open-items, 2026-10-05) : 11 action items routés vers 3.6/3.7 — landing à vérifier en Phase 4.
- **Session logs** — les builds 3.2-3.7 ont eu lieu dans CETTE session (une compaction à mi-parcours) ; le record = plans (triage logs), commits, E2E live. Les conversations complètes ne sont pas archivées — écart enregistré ; les triage logs par ticket sont le substitut.
- **Behavior check** — frais : run E2E live 27/27 du 2026-10-05 (voir ci-dessus), plus suites : pytest 244, node ×2 verts à l'état final.

## Findings (Phase 2)

Consolidation de 3 lens (adversarial 12, edge-case 9, verification-gap 5+3) sur le diff d'épique + l'arbre courant + les preuves live du jour. Chaque finding porte sa source et son statut.

### Défauts réels encore ouverts (candidats fix-now)

- **Valeur française dans l'arbre EN** — `"title": "Connexion Eedomus"` (strings.json:15, en.json:15), portée telle quelle par la reconstruction 3.4 : un utilisateur anglais voit un titre de flow en français. Invisible à toutes les gardes (le no-french scanne les *.py hors translations/, le JS scanne le panneau, les tests de structure comparent les arbres entre eux, jamais la langue des valeurs). [adv]
- **Contrat config-flow ↔ strings.json épinglé nulle part** — les labels `config.step.user.data` réécrits par 3.4 ne sont liés au schéma par aucun test ; `config_flow.py:158` injecte encore `errors = {"base": str(err)}` (message brut vol.Invalid comme clé d'erreur — la grammaire rate et montre le texte brut), pendant que les chemins frères (cannot_connect, invalid_yaml) sont traduits. [verif+other]
- **Labels du flow d'options hors des deux mécanismes** — ~13 champs rendus (options_flow.py:183-195) sans section `options.step.init.data` ; la famille legacy `config.options` couvre 6/13 avec `php_fallback_script` (strings.json:56) keyée sur un champ qui n'existe pas (`php_fallback_script_name`, const.py:51). [adv]
- **Le yaml_editor rend le blurb de l'intégration** — le placeholder `description` résout la description top-level (« Integration for the eedomus home automation box. ») au lieu d'une intro d'éditeur ; `description_fallback` est mort (options_flow.py:219-226). [edge+verif]
- **Normalisation fr-FR du flow d'options non testée** — le split de région (3.4) n'a aucun test (tous les yaml_editor tournent en "en") ; une régression rendrait l'éditeur EN pour tout fr-FR/fr-CA sans bruit. [verif]
- **Sonde canari du self-test trompeuse** — le garde JS plante `panel.coherence.status.total` (clé morte depuis 3.6) comme sonde unknown-key : si la clé renaît, l'échac parle du self-test, pas de la régression (test-i18n-guard.js:476). [adv]
- **Course get_translations dupliquée post-timeout** — une continuation tardive peut effacer le marqueur d'un second appel de même locale (eedomus-panel.js:859-896). [edge]

### Surfaces bilingues assumées (décisions enregistrées — le rétro les consigne pour ne pas les re-flagger)

- Badge `modified_by_rule` : préfixes serveur « custom mapping {key} »/« rule {key} » interpolés dans la phrase FR « Modifié par la règle « … » » — décision plain-EN validée au checkpoint 3.5 ; le rétro PROPOSE la migration en descripteur clé+params (le modèle que l'épique a appliqué aux statuts frères `_saveState.applied`) — surface étroite (règles sans nom uniquement). [adv+verif]
- `PANEL_SIDEBAR_TITLE`, device_info (Unknown Device/Parent/model/sw_version), noms dérivés de capteurs (« X Battery », « X (History Progress) » — sensor.py:505/546) : anglais sous FR, pas de chemin strings.json pour DeviceInfo ; les noms dérivés sont un candidat ticket. [adv+edge]
- Squelettes perpétuels si get_translations échoue durablement (non-admin, service_unavailable) — squelette+retry-au-set-hass = décision du checkpoint 3.3 ; pas d'affordance d'erreur au-delà. [adv+edge]

### Trous de vérification encore ouverts

- **La moitié client du Done when 5 n'a jamais d'E2E** — les 7 tests live valident le catalogue servi (3.2), jamais le rendu du webcomponent (détection hass.locale, gating squelette, sélection pluriel, discard stale) — la moitié panneau du critère repose sur la validation visuelle manuelle. [adv]
- **Le repli de nom d'entité traduit n'est observé que sur un stub** — la résolution réelle HA (`_name_internal`, composition device+entity) n'est vue par aucune suite ; le live E2E ne regarde aucun nom ; risque de dépendance à la version HA. Deux edges associés : renommage box-side jamais propagé sur les noms adoptés (entity.py:239-241) et `del _attr_name` contournant peut-être l'invalidation de cache (non vérifié contre le vrai HA — maybe-false, ce qui trancherait : observation live d'un périphérique sans nom). [verif+edge]
- **La garde est aveugle aux NOUVELLES chaînes anglaises** — elle attrape les textes du catalogue réintroduits et le français, mais une nouvelle prose EN codée en dur passe (le contrôle d'exhaustivité n'existe pas) — angle mort documenté, à revisiter au prochain ajout de surface. [verif]
- **`scripts/tests` advisory en CI** — décision enregistrée en 3.4, jamais revisitée ; les linters lint.yml sont tous `|| echo` non fatals — l'asymétrie de strictesse (les gardes de l'épique strictes, le CI préexistant mou) est une dette de release-prep, pas de l'épique. [adv]
- **Familles plates mortes cimentées** — errors/success/warnings (27 clés sur les 3 arbres) lues par rien (le loader lit title/description seulement) : la décision keep/drop du loader a été tranchée de fait, non enregistrée. [adv]

### Leçons de process (seams inter-tickets)

- **L'aveugle EN du garde a été vivant trois tickets** (3.3→3.6) : une chaîne EN codée en dur passait la CI ; la maturité complète du garde (union EN+FR, substring, self-test) n'est arrivée qu'au sweep. Catalogue vérifié : 137 (3.2) → 140 (104) → 144 (3.6), parités intactes à chaque hop.
- **L'inventaire est devenu source de GÉNÉRATION seulement** (décision 3.6 de découplage des fixtures) : le critère Done-when 1 est mécaniquement invérifiable depuis — trade conscient, coût résiduel enregistré.
- **Le diff de rétro a exclu le wiring CI** (46 fichiers sur 63) — les lens ont re-dérivé depuis l'arbre ; leçon : le diff de rétro doit inclure .github/ et requirements.
- **Baseline discipline** : 3.1-3.4 sans baseline (range inférée), 3.5+ systématique — la leçon de la rétro cohérence a été appliquée en cours d'épique.
- Claim falsifié : « le fallback scene est patché » — scene.py route dans la grammaire entity.scene que 3.4 a supprimée ; **injoignable** (scene n'est pas dans PLATFORMS — établi en 3.4 avec const.py) : code mort, pas un défaut vivant.

## Behavior verification

- **Live (le jour même)** : Pi déployé à 6a9f0d4, HA 2026.9.4 RUNNING, `pytest tests/e2e/ -v` → **27/27 en 62 s** dont les 7 tests i18n (égalité de valeurs en/fr vs fixtures, parités clés/placeholders, de→EN, fr-FR→fr, null→EN). Logs post-restart en anglais, sains, zéro erreur ws/eedomus.
- **Suites à l'état final** : pytest unit 244 verts, harnais node 141 assertions, gardes JS (self-test 5/5) et Python (self-test 3 sondes) vertes.
- **Non exercé** : le rendu DOM du panneau sous les deux locales (moitié client du critère 5 — validation visuelle manuelle seulement), la résolution réelle HA du repli de nom d'entité.

## Previous-retro follow-through (epic-coherence-tab, 2026-10-05)

Sur les 11 action items de la rétro cohérence : **10 atterris**, 1 partiel.

1. Cache cohérence → 3.6 ✓ (garde de génération, témoins).
2. Registre mappings supprimés → 3.6 ✓ (tagging entry + retrait de vague après refresh réussi, tests wiring).
3. Pluriel « 1 périphériques » → 3.6 ✓ (total + filtered, one/other).
4. Deep-link #regles + bug 105 → 3.6 ✓ (les 3 onglets lazy, bug 105 done).
5. Focus « Tout afficher » → 3.6 ✓ (témoin).
6. Courses hover/breakpoint → 3.6 ✓ (3 gardes + témoins).
7. douteux + en_erreur → 3.6 ✓ (exemptions + chaîne vide ; libellé clarifié « import en reprise » selon décision utilisateur).
8. Multi-box → décision utilisateur mono-box ✓ (ticket latent, enregistré).
9. Trous de vérification (chips/dispatch/teardown/lifecycle/debounce) → 3.6 ✓.
10. **Témoins E2E clavier/popover → PARTIEL** : 3.6 a livré les témoins au niveau harnais node, mais les témoins E2E live (Échap/focus/une seule ouverte dans un vrai navigateur) restent à faire — routés de nouveau ci-dessous.
11. Leçons process (registres parallèles, baselines) → ✓ (baselines systématiques 3.5+, TAB_LABELS éliminé par 3.3).
La garde grep falsifiable (item différé de la rétro) → 3.7 ✓ (no-french guard, exemptions nommées, self-test).

## Action items (proposées, en attente de décision humaine — rien n'a été appliqué par cette rétro)

1. **[fix-now] Valeur FR dans l'arbre EN** — « Connexion Eedomus » → valeur EN dans strings.json/en.json + test de structure asserting aucune valeur marquée FR dans l'arbre EN (la classe de trou que les trois gardes ne voient pas). Owner : dev.
2. **[fix-now] TestConfigFlowSection** — champs de STEP_USER_DATA_SCHEMA ≡ `config.step.user.data` sur les 3 arbres + clés d'erreur (cannot_connect) ; traduire le `errors = {"base": str(err)}` restant en clés. Owner : dev.
3. **[fix-now] Labels du flow d'options** — section `options.step.init.data` (13 champs, 3 arbres), réparer `php_fallback_script` → `php_fallback_script_name`, pointer la description yaml_editor sur une clé dédiée au lieu du blurb intégration, épingler par test de structure. Owner : dev.
4. **[fix-now] Test fr-FR options** — un test unitaire de normalisation de région (make_yaml_flow ne change que la langue). Owner : dev.
5. **[fix-now trivial] Garde** — commenter/renommer la sonde canari (clé morte total) ; token de génération contre la course get_translations dupliquée. Owner : dev.
6. **[proposition — décision utilisateur] Badge modified_by_rule en descripteur clé+params** — le backend sert `{"rule_kind": "custom_mapping"|"rule", "key": k}`, le panneau résout via une clé panel.* ; ferme la dernière surface bilingue user-visible du pipeline panneau (contraste avec les statuts frères migrés en 3.6). Owner : dev, après décision.
7. **[ticket] Noms dérivés localisés** — « X Battery » / « (History Progress) » via la grammaire entity (translation_key) ou clé panel ; périmètre à trancher (noms d'entités dans le scope i18n ?). Owner : user + dev.
8. **[3.7-complément / E2E] Témoins live du critère 5** — (a) le rendu du panneau sous deux locales (harnais DOM ou validation visuelle formalisée), (b) observation du friendly_name d'un périphérique sans nom sur l'instance (résolution réelle HA — trancherait aussi le maybe-false du cache), (c) témoins clavier/popover en E2E. Owner : dev + user (validation visuelle).
9. **[release-prep] CI préexistant** — décision scripts/tests advisory à revisiter + linters `|| echo` (les gardes de l'épique sont strictes, le CI hérité ne l'est pas) ; drop des familles plates mortes errors/success/warnings (27 clés) après vérification du loader. Owner : user + dev.
10. **[process] Diff de rétro** — inclure .github/ et requirements dans le diff d'épique (le wiring d'application est un seam central) ; angle mort exhaustivité de la garde à documenter dans son en-tête. Owner : process.

## Acceptance verdict

**accepted-with-open-items** — critères **déclarés** (5 Done when), tous satisfaits dans les preuves :

1. Inventaire couvrant ✓ (3.1 + grep croisé + revue quick) — résiduel : l'inventaire est désormais source de génération (trade 3.6), et la rétro trouve deux surfaces de flow que l'inventaire avait manquées (options data labels, title FR).
2. Arbres en/fr identiques y compris ui ✓ — tests de structure + égalité de valeurs live (27/27).
3. Zéro chaîne user-facing en dur + garde CI ✓ — garde pleine force depuis 3.6, self-testée, mutation-prouvée ; angle mort exhaustivité documenté.
4. Zéro log/docstring FR + logs live EN ✓ — garde Python self-testée + logs du jour observés en anglais.
5. Déployé et validé sur le Pi ✓ — 27/27 live dont 7 i18n ; **la moitié rendu-panneau repose sur la validation visuelle manuelle** (user), les surfaces bilingues assumées sont consignées ci-dessus.

Le verdict machine est **accepted-with-open-items** ; la décision humaine (passage en done de 3.7 après validation live, ce jour) confirme. Les open items sont les fix-now (arbre EN FR, surfaces de flow) et les propositions ci-dessus.

## Open questions

- Le badge modified_by_rule (item 6) : migrer en descripteur ou tenir la décision plain-EN ?
- Les noms dérivés de capteurs (item 7) : dans le périmètre i18n ou ticket séparé ?
- La moitié client du critère 5 : investir dans un harnais DOM E2E, ou formaliser la validation visuelle manuelle comme la procédure de release ?

## Assumptions

(Omis — run interactif ; les choix de l'utilisateur (décisions plain-EN, mono-box, découpage avant épique 4, validation 3.7) sont consignés dans les sections ci-dessus et les plans.)
