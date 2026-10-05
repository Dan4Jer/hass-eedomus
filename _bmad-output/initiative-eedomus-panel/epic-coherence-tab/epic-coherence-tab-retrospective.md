---
epic: epic-coherence-tab
date: 2026-10-05
verdict: accepted-with-open-items
criteria: declared
headless: false
---

# Rétrospective — epic-coherence-tab (Onglet Cohérence, eedomus ↔ HA)

## Epic summary

Épique 2 de l'initiative eedomus-panel : 8 tickets, tous `done` (validés par l'utilisateur, commit ce2f79f). CAP-6 (tableau de cohérence + 4 signaux backend, lecture seule), CAP-7 (popover desktop / ligne étendue mobile en parité stricte), CAP-8 (lien vers les réglages standard d'entité HA). Tickets au statut `built` non passés à `done` : aucun. Tickets non terminés acceptés en rétro : aucun.

Ranges : pas de `baseline_revision` dans 7 plans sur 8 (seul 2.8 : `9d05f0f`) — range d'épique **inférée** `7cfd310..04cf1e4` (9 commits non-merge, 0 merge, identifiés par subjects). Diff code : `/tmp/epic-2-code.diff` (4 136 lignes, custom_components + tests).

## Evidence inventory

- **Epic file** — `epic-coherence-tab/epic-coherence-tab.md` : Description, Outcome, 3 Requirements (CAP-6/7/8), 5 critères Done when, Boundaries, Notes (4 décisions utilisateur 2026-10-04 ; 2 unknowns : navigation HA, glyphes chips).
- **Initiative requirements** — l'initiative n'a pas de section Requirements (les épiques portent les leurs) ; enregistré comme fait, pas comme écart.
- **Entries** — 2.1 (commande get_coherence) → 2.8 (suite E2E), ordre de build ; descriptions/verify/covers relues via find. Story files : aucun (aucun raffinement en fichier propre).
- **Plans** — 8, tous `status: done` ; les triage logs des plans (revues 4-lens par ticket) sont le record des revues.
- **Volumes (git_evidence.py, non-merge)** — `www/eedomus-panel.js` +1980/−164, `tests/js/test-coherence.js` +990/−6, `tests/unit/test_ui_service.py` +687/−12, `ui_service.py` +256/−39, `tests/e2e/test_e2e_panel.py` +20/−3, workflows +13. Aucun `binary_revisions`, 0 merge.
- **Preuve E2E live (2.8)** — `04cf1e4` + plan 2.8 : déploiement git-only, logs propres (chargement différé, aucune erreur ws), `pytest tests/e2e/ -v` → **20 passed in 67.5 s**, dont `test_get_coherence_lists_every_peripheral` (ensembles de periph_id **identiques** get_coherence ↔ get_peripherals sur les ~165 périphériques réels).
- **Rétro précédente** — `epic-mapping-panel-editor-retrospective.md` (accepted-with-open-items, 2026-10-03).
- **Session logs** — **absents** (conversation des builds 2.x compactée). Le record survivant = plans, commits, E2E. L'analyse process-lessons s'appuie sur ces artefacts — écart enregistré.

## Findings (Phase 2)

Chaque finding porte sa provenance (lens + source) et son statut contre l'arbre courant (post-3.5) : *still-present*, *since-changed*, *since-closed*.

### Vues agrégées

- **God-file growth (mesuré)** — `eedomus-panel.js` : 1 852 lignes au début de l'épique → **3 668** à la fin (+1 816 net sur la range) → 4 187 aujourd'hui (i18n 3.3 + story 104 depuis). La rétro précédente avait déféré le découpage à 1 852 lignes ; l'épique l'a presque doublé et la chaîne i18n a continué. Le candidat découpage existe : backlog **story 102**. Sources : `git_evidence.py` (range), `git show <rev>:…panel.js | wc -l` (1 852/3 668/4 187).
- **Duplication map** — le copy d'état vide « Aucun périphérique détecté… » dupliqué entre onglets (lens adversarial, eedomus-panel.js, migrated en 3.3 vers deux clés catalogues distinctes) ; deux conventions de temps dans un même détail (`last_update` naïf vs `retry_after` UTC — ui_service.py:723/:732) alors que le commentaire 2.1 revendique « one time convention » (adversarial #12). Le formatter `_formatTimestamp` existant (onglet Historique) n'est pas réutilisé par le détail cohérence.
- **Pattern divergence** — le bouton « À vérifier » réutilise la classe `.filter-touches` de l'onglet Périphériques et ne dispatche que par l'ordre des branches de `_onClick` (`[data-coherence-view]` avant `.filter-touches`), sans test épinglant l'ordre (adversarial #10). Contraste avec les contrats de restauration de focus explicites du tri/popover (voir focus, ci-dessous).
- **Spec-to-implementation (Done when vs preuves)** — voir Acceptance verdict : les 5 critères sont satisfaits dans les preuves, avec des réserves enregistrées ci-dessous (critères 2 et 3 : validateur humain pour le clavier/popover, aucun témoin automatisé).

### Lens adversarial (15 findings, floor N=10 — 151,75 kB)

1. **Deep-link corrigé sur un seul onglet** — le fix `set hass` de la revue 2.2 (ed05be6) couvre `#coherence` ; `#historique` est filed (bug backlog id 1) ; **`#regles` n'est ni corrigé ni filed** (l.3260-3262 même classe de bail). *still-present*. [fix-now proposé : généraliser le restart aux onglets lazy + étendre le bug filed]
2. **Cache cohérence jamais invalidé** — `set hass` rafraîchit `_loadPeripherals()` à chaque assignation mais jamais la cohérence (`_renderTabContent` :1947-1950) ; créer une règle depuis le popover puis revenir montre les anciens signaux jusqu'au rechargement complet. Frontière 2.2 cache ↔ 2.6 actions d'écriture. *still-present*. [fix-now — user-visible]
3. **Le registre ressuscite les mappings supprimés** — `clear_mapping_registry()` (mapping_registry.py:36) n'est appelé nulle part ; last-wins global (`_registry_by_periph_id`, ui_service.py:643) : un mapping supprimé continue d'alimenter `ha_entity`/`justification` dans la cohérence. Le cas removed-mapping est non testé (seul le cas changed est épinglé). *still-present*. [fix-now]
4. **`en_erreur` confond échec d'import d'historique et santé du périphérique** — la source est `_retry_queue`, peuplée uniquement par les échecs de fetch d'historique (coordinator.py:1183-1212) ; un périphérique sain porte la puce pendant toute la fenêtre de retry (heures) ; la queue n'est jamais purgée (ui_service.py:704-715). *still-present*. [décision produit + fix]
5. **Heuristique `douteux` sur-drape** — seuls les `enum` sont exemptés (ui_service.py:692-698) ; `timestamp`/`date` sans unité légitime seraient « mapping douteux » ; et le check `is None` laisse passer `unit == ""` (edge #6, :695). *still-present*. [fix]
6. **Pluriel « 1 périphériques » livré et épinglé par les tests** — tests/js:1017/1037/1049 assertent la forme fautive ; la migration i18n l'a figée dans les DEUX catalogues (panel_translations.py:223/:329). *still-present (migraté, pas corrigé)*. [fix-now — split one/other comme attempts]
7. **Collisions periph_id multi-box** — periph_id unique par box seulement ; popover/ligne étendue indexés par periph_id seul (`find()` premier match js:2545/:2817, ids DOM dupliqués via `coherenceExpandedRowId` :586) ; le test E2E compare des ensembles d'ids, ce qui masque les doublons. Le registre est joint globalement last-wins (edge #4). *still-present*. [fix — d' autant que main a déjà fixé des collisions multibox unique_id]
8. **Contrat breakpoint unidirectionnel** — `_onCoherenceBreakpoint` (js:2572) ne gère que `!ev.matches` ; entrer en étroit avec un popover ouvert n'est couvert par personne (survit par effet de bord du resize-dismiss de 2.4) — dépendance inter-tickets non documentée. Plus la fenêtre de course 250 ms du hover-intent qui peut ouvrir le popover sous le breakpoint (edge #1/#7). *still-present*. [fix — re-check `coherenceNarrowView()` dans le callback du timer + gérer l'entrée narrow]
9. **Course hover sweep** — balayer d'un trigger ouvert vers un autre : le leave-timer ferme le popover, dont `_closeCoherencePopover` annule la nouvelle intention pendante — aucun popover ne s'ouvre (edge #2, :2794). *still-present*. [fix une ligne : `_cancelCoherenceLeave()` en nouvelle intention]
10. **Focus clavier perdu sur « Tout afficher »** — le bouton vit dans `coherence-body` remplacé en bloc par le re-render (:1642-1646, :2474), sans restauration, contrairement aux contrats explicites du tri et du popover. Contredit le Done when 2 « opérable au clavier ». *still-present*. [fix-now a11y]
11. **Course de courses d'écriture (TAB_LABELS)** — `TABS` a reçu `coherence`, la constante parallèle `TAB_LABELS` jamais — dérive invisible aux revues par ticket. *since-changed* (3.3 a supprimé TAB_LABELS, piège latent éliminé). [leçon process : registres parallèles]
12. **Test du contrat de signaux unidirectionnel et regex-lâche** — `re.search(rf"{signal}:\s*\{{")` sur tout le fichier panel (test_ui_service.py:1377-1398) ; la direction inverse (clé chip morte) est non testée. Convergent verif-lens « chip rendering never executed ». *still-present*. [voir trous de vérification]
13. **Régression post-épique sur un contrat épinglé par l'épique** — `coherenceDetailAttempts` gardait `Number.isFinite && > 1` (non-numérique singulier, test « never pluralize as NaN ») ; 3.3 l'a remplacé par `count === 1 ? one : other` (js:399-405) — les non-finis pluralisent désormais (« (beaucoup tentatives) »), le test porte toujours le label « never pluralize as NaN » en assertant le pluriel. *since-changed (régression post-épique ; l'écart était assumé au triage 3.3 mais le label de test ment)*. [3.6 : renommer le test ou rétablir le garde non-fini]
14. **json_safe latent** (edge #5) — `error_message`/`attempts` du retry-queue non passés par `_json_safe` (ui_service.py:735-738) ; latent (le coordinator écrit str/int aujourd'hui). [accept as-is, note]
15. **Time conventions dupliquées** (voir Duplication map). *still-present*. [3.6]

### Lens verification-gap (5 findings + 2 autres — tous still-open côté wiring)

Les seams BACKEND sont bien épinglés (`TestGetCoherenceHandler`, `TestProjectCoordinatorWithRaw`, E2E live parité des ensembles). Les trous restants sont les coutures FRONTEND 2.2↔2.5 — chaque ticket testait ses helpers purs, rien n'exécute la colle :

- **Chip rendering jamais exécuté** — `coherenceChipsHtml`/`coherenceChipHtml` (js:635-671) exportés nulle part dans le harnais ; le composé (js:739-757) génère les chips sans jamais les asserter ; le garde Python est un grep. La sortie visible principale de l'épique peut se dégrader en vert total. [patch harnais : 5 cas]
- **Bascule narrow/wide jamais exécutée** — aucun `matchMedia` dans le sandbox (`coherenceNarrowView()` toujours false en node) ; la surface mobile de 2.5 peut régresser en bloc invisiblement. [patch : 1 cas dispatch stubé]
- **Teardown popover/orphelin non observé** — le `_closeCoherencePopover()` de chaque `_renderCoherenceTable` (:2407) et l'éviction d'expansion (:2434-2439) n'ont aucun test ; le commentaire « never floats orphaned » n'a pas de témoin. [patch : 1 cas au pattern stub-document existant]
- **Cycle de chargement lazy de la cohérence non exécuté** — l'entrée directe `#coherence` (branche `set hass` :789-790) et le bouton Réessayer (:1623-1625) ne sont testés nulle part. [patch : 1 cas lifecycle]
- **Debounce de frappe Périphériques à moitié testé** — la moitié immediate-announce est since-closed (story 104), la moitié typing/debounce est still-open. [patch : miroir du cas cohérence]
- Autres : `test_panel.py:87-88` = assertions substring sur le source JS (pas une exécution) ; le signal-contract grep (convergent #12).

### Champs vérifiés et propres (pour la distinction « checked » vs « never checked »)

Edge lens a tracé et **écarté comme gérés** : fenêtrage du retry `en_erreur`, NaN/Infinity dans raw, échappement des ids hostiles (+ CSS.escape), dismiss du popover (scroll/resize/reshuffle/tab-switch/disconnect), éviction d'expansion au filtre, restaurations de focus du tri/popover, annonces d'états vides, contrat de chaînes backend↔frontend (le pin tient contre la structure `labelKey` post-i18n). Deletion check : refacteurs intentionnels uniquement.

## Behavior verification

- **Exercé (record live, 2.8)** : déploiement Pi + `pytest tests/e2e/ -v` → 20 passed (67,5 s) ; parité des ensembles periph_id prouvée live ; logs de boot propres.
- **Exercé (arbre courant, cette rétro)** : `pytest tests/unit/ -q` → 229 verts ; `node tests/js/test-coherence.js` et `node tests/js/test-i18n-guard.js` verts — sur l'état POST-3.5 (l'épique a depuis évolué : i18n 3.3, raw-JSON 104).
- **Non exercé dans cette rétro** : aucun run live ni DOM/navigateur (pas de déploiement) — les critères Done when 2/3 côté clavier/popover reposent sur la validation visuelle de l'utilisateur (consignée au passage en done, ce2f79f) et restent sans témoin automatisé (trous ci-dessus). Le comportement du popover sous breakpoint, la parité au tactile et les thèmes clair/sombre restent des vérifications à l'œil.

## Previous-retro follow-through (epic-mapping-panel-editor, 2026-10-03)

Tous les items ont atterri ou sont tracés :

- **fix-now A1/A2 (config_schema_version à l'ingestion)** — appliqués : commit `cadd373` « fix(mapping): apply the retrospective fix-now items A1 and A2 » ; `config_manager.py` porte le stamp dans toutes les écritures (:115/:184/:212).
- **spec-reconciliation (CAP-4 épic/initiative vs AD-13)** — appliqué : la ligne CAP-4 de l'épic 1 dit désormais « canon HA storage (`eedomus.mapping`) via config_manager + réplication du miroir `custom_mapping.yaml` … aligné AD-13/14 (rétroconcilié 2026-10-03) » ; l'initiative ne porte plus de Requirements (les épiques les portent).
- **defer split du panel (1 852 lignes)** — tracé : backlog **story 102** « Découper eedomus-panel.js par onglet ». Non exécuté ; l'épique 2 a porté le fichier à 3 668 lignes (voir God-file growth) — l'item reste pertinent.
- **defer double chemin du canon** — tracé : backlog **story 103** « Unifier la lecture du canon du mapping sur config_manager ». Non exécuté.
- **accept as-is ×3** (contraste visuel, autocomplete datalist, storage orphelin) — déviations enregistrées, non re-flaggées ici.

## Action items (proposées, en attente de décision humaine — rien n'a été appliqué par cette rétro)

1. **[fix-now] Invalider le cache de cohérence** après toute écriture (save mapping, création de règle) — signaux périmés jusqu'au rechargement complet. Owner : dev ; cible naturelle : 3.6.
2. **[fix-now] Registre : mappings supprimés** — brancher `clear_mapping_registry()` (ou joindre par entry) + test du cas removed-mapping. Owner : dev ; 3.6.
3. **[fix-now] Pluriel « 1 périphériques »** — split one/other dans le catalogue (pattern attempts) + status text ; corriger les 3 épingles de test fautives. Owner : dev ; 3.6 (attention : touche le catalogue → parité inventaire).
4. **[fix-now] Deep-link : généraliser le restart `set hass`** à tous les onglets lazy (`#regles` non corrigé et non filed — étendre le bug backlog id 1 ou corriger en une passe). Owner : dev ; 3.6 ou backlog.
5. **[fix-now a11y] Restauration du focus sur « Tout afficher »** (contraste avec les contrats du tri/popover). Owner : dev ; 3.6.
6. **[fix batch, petit] Courses hover/breakpoint** — re-check `coherenceNarrowView()` dans le callback hover ; `_cancelCoherenceLeave()` en nouvelle intention ; gérer l'entrée narrow dans `_onCoherenceBreakpoint`. Owner : dev ; 3.6.
7. **[fix] Heuristique `douteux`** — exemptions device-class sans unité + `not base["unit"]` au lieu de `is None`. **[décision produit] `en_erreur`** : distinguer échec d'import d'historique et santé du périphérique (source + purge de queue). Owner : dev + user pour la décision sémantique ; 3.6/spec.
8. **[fix, quand multibox] Collisions periph_id multi-box** — clés composites (entry/periph) pour le join et les surfaces de détail. Owner : dev ; ticket dédié (latent en mono-box).
9. **[3.6 — trous de vérification, tous au pattern harnais existant]** : exécution des chips (5 cas), dispatch narrow/wide stubé, teardown popover/éviction, lifecycle lazy #coherence + Réessayer, debounce Périphériques, renommage du test « never pluralize as NaN », bidirectionnalisation du contrat de signaux.
10. **[3.7] Témoins E2E clavier/popover** (Échap, focus rendu, une seule ouverte) — ferme le trou « validation visuelle uniquement » des Done when 2/3.
11. **[process, leçon] Registres parallèles** : mettre à jour les deux côtés (TAB_LABELS a été éliminé par i18n — la classe de dérive reste une leçon) ; **baselines de plans** : 7/8 plans 2.x sans `baseline_revision` ont forcé une range inférée — la pratique des baselines (systématique depuis 3.3) doit être conservée.

## Acceptance verdict

**accepted-with-open-items** — critères **déclarés** (5 Done when dans l'epic file), tous satisfaits dans les preuves :

1. `get_coherence` live, une ligne par périphérique (~165, aucun perdu) ✓ — E2E live : ensembles de periph_id identiques (04cf1e4, plan 2.8) ; **réserve** : sémantique `en_erreur` (finding 7) et removed-mappings (finding 3) nuancent « signaux corrects sur des cas réels ».
2. Tableau complet, tri/filtre/bascule, états squelette/erreur/vide ✓ — validé visuellement par l'utilisateur (ce2f79f) ; **réserve** : focus perdu sur « Tout afficher » (finding 5), aucun témoin automatisé du clavier.
3. Parité popover/ligne étendue, popover focusable ✓ — parité par renderer partagé + validation visuelle ; **réserve** : le wiring clavier (Échap, focus rendu) n'a aucun test d'exécution (trous de vérification), et les courses hover/breakpoint peuvent brièvement faire coexister les surfaces.
4. Clic entité → réglages standard HA ✓ (2.6, E2E ws + visuel) ; chips glyphe + libellé ✓ (DESIGN, validé visuellement).
5. Suite E2E verte sur l'instance déployée ✓ — 20 passed, logs propres (plan 2.8, 04cf1e4).

Le verdict machine est **accepted-with-open-items** ; la décision humaine (le passage en done de 2.1-2.8 suite à validation visuelle, ce2f79f) confirme. Les open items sont les findings fix-now ci-dessus et les trous de vérification — routés vers 3.6/3.7 par les action items.

## Open questions

- Sémantique de `en_erreur` (action 7) : faut-il une puce distincte pour « import d'historique en retry » vs « périphérique en erreur » ? Réponse utilisateur requise — change le contrat de signaux du spec.
- Multibox : l'instance visée est-elle multi-box ? Détermine la priorité de l'action 8 (latent en mono-box).
- Le découpage du panel (story 102) doit-il être fait avant l'épique 4 (Supervision ajoute un 5e onglet au même fichier) ou après ? Décision de séquencement.

## Assumptions

(Omis — run interactif ; les choix de l'utilisateur sont consignés dans les sections ci-dessus.)
