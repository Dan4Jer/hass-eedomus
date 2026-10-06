---
epic: epic-supervision-tab
date: 2026-10-06
verdict: accepted-with-open-items
criteria: declared
headless: false
---

# Rétrospective — epic-supervision-tab (onglet Supervision, CAP-9 + CAP-5)

## Epic summary

Épique exécutée en builds non assistés (bmad-build-auto), 5 tickets, tous **done** (aucun `built` en attente, `pending_tickets` vide) :

| Ref | Titre | Plage (baseline → baseline suivante) | Commits |
|---|---|---|---|
| 4.1 | Commandes websocket file de backfill (état + 4 actions) | 7357145..3b5745c | 2125461 (feat), 5bbf58b, 3b5745c (docs) |
| 4.2 | Onglet Supervision : vue métriques + lien Cohérence | 3b5745c..3b45de4 | 9b5e619 (feat), 192c4f4, 3b45de4 (docs) |
| 4.3 | Vue file de backfill + actions | 3b45de4..1f9a6b8 | e328a5a (feat), 26e6379, 1f9a6b8 (docs) |
| 4.4 | Refactor sweep | 1f9a6b8..3fe01eb | 3fe01eb (refactor) |
| 4.5 | Validation E2E + live | 3fe01eb..0343f20 (HEAD, inféré) | f96a9f7, f6c6146 (test), 0343f20 (docs) |

13 commits au total, aucun merge, aucune révision binaire. Aucun ticket raffiné (story_file null partout) — l'intention vivait dans les entrées + plans (2 plan_checkpoint utilisateur : 4.1 et 4.3).

**Inventaire des preuves** : fichier épique (Done when déclaré, 5 critères) ✓ ; initiative Requirements (CAP-9, CAP-5) ✓ ; 5 plans complets (Triage Logs + Auto Run Result + post-déploiements datés) ✓ ; plages git par plan ✓ ; rétro précédente (epic-i18n) ✓ ; journaux de session : la trajectoire de builds est la preuve vivante (récitée dans les plans), pas de fichier journal séparé — l'analyse process s'appuie sur les plans, narrowing consigné.

**Exécution** : chaque ticket = recon subagent → plan (2 checkpoints validés par ask_user) → impl subagent → revue thorough 4 lens → triage → patchs → re-vérif → built → commit + push → déploiement + validation live (E2E sur le Pi + validation visuelle utilisateur par ticket). À partir de la revue 4.3, la limite de noms de subagents a été atteinte : les lens verification-gap et intent-alignment sont passés inline par l'orchestrateur (narrowing consigné dans les triage logs).

## Findings

### Vues agrégées (dérivations déterministes, aucune délégation possible)

- **Delta d'architecture** — DAG d'imports vérifié sur les 8 modules + entrée : entry → {shared, peripheriques, regles, historique, coherence, supervision}, coherence → {shared, coherence-helpers}, coherence-helpers/supervision/peripheriques → shared. Aucun cycle, aucune violation de couche. Côté backend, `ui_service.py` gagne un import `coordinator` (EedomusBackfillError, commit 2125461) — une couche UI qui référence l'exception métier : cohérent avec le pattern dispatcher existant, accepté.
- **Croissance god-class** — mesuré (wc -l) : le monolithe de 4 322 lignes (story 102) vit désormais en modules ≤ 1 054 lignes (supervision.js 1 054, regles.js 1 054, coherence.js 1 041, entrée 946). La cohérence a été scindée en 4.4 (byte-identique, vérifié 501/501). **Points de vigilance, pas des verdicts** : supervision.js porte deux zones (métriques + file) dans un module « par onglet » — conforme au design ; si la file grossit (backfill-queue de la spine UX), une scision supervision-queue est le candidat suivant. coordinator.py 2 370 et ui_service.py 1 550 grossissent respectivement de +561 et +440 lignes net sur l'épique — l'axe moteur reste concentré dans le coordinator comme l'exige AD-7.
- **Carte de duplication** — la duplication truncate (supervision/coherence) repérée en revue 4.3 a été centralisée en `truncateDetailText` (shared.js, commit e328a5a + 3fe01eb) ✓. Les miroirs de garde (load/action génération) sont délibérés et documentés dans le code — accepté. Le pattern retry E2E (6 × 5 s) est répliqué sur les deux lectures live (4.5) : trois occurrences du même idiome (peripherals préexistant + 2 nouvelles) — candidat helper si une quatrième apparaît, defer.
- **Divergence de pattern** — aucune détectée : recette dispatcher 5 pièces respectée sur les 6 nouvelles commandes (contrat testé), catalogue i18n systématique (garde 919 littéraux verte), squelettes/erreur conformes à EXPERIENCE.md sur les deux zones.
- **Réconciliation spec ↔ impl** — Done when contre preuves :
  1. `get_backfill_state` rend l'état complet en live ✓ — test E2E 4.5 (file non vide, 157 periphs, plan 4.5 Auto Run Result) + retours nominatifs testés (4.1, triage log).
  2. Onglet affichant les métriques en chart cards thémées + équivalents textuels, lien Cohérence ✓ — validation visuelle utilisateur (plans 4.2 et 4.3, post-déploiement).
  3. Ignorage survit à un restart ✓ (test first-refresh + Store, plan 4.1 P10a) ; pause globale stoppe le drain sans casser la reprise ✓ (tests drain 4.1) ; temps réel jamais bloqué ✓ (verrou + drain-skip testé, 4.1 P10b).
  4. Tout l'onglet localisé via le catalogue ✓ (garde i18n, 35 clés backfill + 12 supervision, 193 clés au total).
  5. Déployé et validé sur le Pi ✓ — 29 E2E verts × 2 passes consécutives (plan 4.5), actions vérifiées non destructivement, contrôle visuel final de fin d'épique CONFORME (utilisateur, 2026-10-06).
  **Déviation acceptée enregistrée** : « graphiques natifs HA » (énoncé épique) → SVG inline thémé. Justification sourcée : aucun composant graphique du frontend HA n'est exposé au contexte du panneau (chunks esbuild internes, URLs hachées par version — recon 4.2), et la spine UX (EXPERIENCE.md l.69) impose elle-même le repli dans ce cas ; plan validé au passage. Consigné pour que les rétros futures ne re-flaguent pas.

### Revue diff-scope (lens inline, périmètre réduit — les frontières entre tickets)

Narrowing : chaque ticket a eu sa revue thorough complète (triahge logs dans les plans) ; la passe rétro cible les coutures inter-sessions, exécutée inline (subagents indisponibles — limite de noms, consignée).

- **Couture 4.1↔4.3 (contrat backend ↔ consommation frontend)** : les 5 tokens de statut, la forme `{state}` et les refus nominaux consommés par 4.3 sont exactement les témoins testés côté 4.1 — aucun drift détecté (tests 4.3 + E2E live). Propre.
- **Couture 4.2↔4.3 (zones métriques ↔ file dans supervision.js)** : composition unique, slots indépendants, focus préservé à travers les re-rendus de l'autre zone — trouvé et patché en revue 4.3 (P7). Propre.
- **Couture 4.4↔épiphanie E2E** : la revue rétro a trouvé le marqueur `COHERENCE_SIGNALS` devenu faux après la scission (0 occurrence dans coherence.js — le test live aurait échoué) et `supervision.js` jamais couvert par la boucle des modules servis depuis 4.2 (404 silencieux = panneau mort, test vert). **Corrigé dans la 4.4 même** (commit 3fe01eb) : liste dérivée dynamiquement de www/panel/*.js + map de marqueurs, un module non marqué échoue loud. Leçon process : une liste manuelle de modules dérive toujours — l'automatisation l'empêche définitivement.
- **Couture 4.5 (courses de rechargement)** : les deux tests live ont échoué à leur première passe sur des courses réelles (reload d'entrée du test restart-cycle des OptionsFlow : tampon vide pendant le premier cycle ; service_unavailable pendant la fenêtre) — trouvés et blindés dans le ticket même (retry borné, commit f6c6146), 2 passes complètes vertes ensuite. Leçon : toute lecture live d'état fraîchement rechargé doit être retry-bornée (l'idiome `_get_peripherals_retrying` existant était le précédent).

### Behavior check

Exercé en réel à chaque ticket : 27→29 E2E verts sur le Pi après chaque déploiement (5 déploiements git-only, restarts HA, logs vérifiés), file live observée (157 periphs non complétés, API states), tampon métriques observé rempli (FULL et PARTIAL REFRESH capturés, logs 04:09-04:10), validations visuelles utilisateur sur 4.2, 4.3 (après rechargement forcé — cache) et contrôle final de fin d'épique CONFORME. Les quatre actions n'ont pas été exercées sur l'instance réelle (non destructif, conforme au plan 4.5) — leur comportement est couvert par 324 tests unitaires + harnais + validation visuelle des contrôles.

## Previous-retro follow-through (epic-i18n, 2026-10-05)

Sur les 10 action items de la rétro i18n : **5 atterris**, 5 restent des propositions/décisions en attente.

1. [fix-now] Valeur FR dans l'arbre EN → **atterri** : story 105, commit 6cc6c39 (« the i18n retro fix-now batch »).
2. [fix-now] TestConfigFlowSection → **atterri** : story 105 (6cc6c39).
3. [fix-now] Labels du flow d'options → **atterri** : story 105 (6cc6c39).
4. [fix-now] Test fr-FR options → **atterri** : story 105 (6cc6c39).
5. [fix-now trivial] Garde (sonde canary, token de génération) → **atterri** : story 105 (6cc6c39).
6. [proposition] Badge modified_by_rule en descripteur → **non atterri, décision utilisateur en attente** (aucune preuve d'implémentation ; aucune évidence trouvée ≠ pas fait).
7. [ticket] Noms dérivés localisés → **non atterri** — pas de ticket créé, décision de périmètre en attente.
8. [E2E] Témoins live du critère 5 (rendu multi-locale, friendly_name, clavier E2E) → **partiellement atterri** : la validation visuelle manuelle continue d'être la procédure (utilisée à chaque ticket de cette épique) ; pas de harnais DOM.
9. [release-prep] CI préexistant (linters advisory, familles mortes) → **non atterri** — à traiter en préparation de release (prochaine étape du board).
10. [process] Diff de rétro incluant .github/ et requirements → **non applicable à cette épique** (aucun commit ne touche ces chemins dans les 5 plages — vérifié par git_evidence, `files` ne les liste pas).

## Action items (proposées, en attente de décision humaine — rien n'a été appliqué par cette rétro)

1. **[ticket backlog — proposition] Cache-busting du module panneau** — l'URL `eedomus-panel.js` ne change pas entre déploiements ; l'utilisateur a dû faire un rechargement forcé à deux reprises (consigné : plan 4.3 post-déploiement, plan 4.5 post-déploiement). Proposition : suffixe de version (ex. `?v=<manifest version>`) sur le `module_url` servi par panel.py + test de contrat. Owner : dev, après décision.
2. **[observation → décision utilisateur] Cadence du drain backfill** — 157 periphs en file avec un quota par défaut de 1/scan (const.py:64) : le drain complet prend ~157 cycles de scan ; l'action Prioriser (CAP-5) est la valve prévue par le design. Question ouverte : le quota doit-il être relevé dans les options (CONF_HISTORY_PERIPHERALS_PER_SCAN est déjà réglable par l'utilisateur) ou la cadence est-elle acceptable ? Owner : user.
3. **[defer] Helper retry E2E** — l'idiome retry-borné (6 × 5 s) existe désormais en 3 exemplaires (peripherals + 2 lectures 4.5) ; centraliser à la 4e occurrence. Owner : dev.
4. **[process] Limite de noms de subagents** — la chaîne non assistée a épuisé la limite en cours d'épique, forçant les lens verif/intent en inline (narrowing consigné, qualité maintenue par triage évidence-based). Leçon : pour les chaînes longues, prévoir la revue inline dès le plan, ou segmenter les sessions. Owner : process.
5. **[proposition reportée de la rétro i18n] CI préexistant** — l'item 9 de la rétro i18n reste ouvert et devient naturellement la prochaine étape : à traiter avec la release 0.15.0 (linters advisory → strict, familles plates mortes). Owner : user + dev.

## Acceptance verdict

**accepted-with-open-items** — critères **déclarés** (5 Done when), tous satisfaits dans les preuves :

1. `get_backfill_state` rend l'état complet sur l'instance live ✓ (E2E 29 verts × 2, file 157).
2. Onglet Supervision affichant les métriques en chart cards thémées avec équivalents textuels ; lien Cohérence bascule ✓ (validation visuelle utilisateur, 3 fois).
3. Ignorage persistant au restart ✓ ; pause globale sans casser la reprise ✓ ; temps réel jamais bloqué ✓ (tests unitaires + drain vérifié en logs).
4. Onglet entièrement localisé via le catalogue ✓ (garde i18n pleine force, 193 clés EN+FR+fixtures).
5. Déployé et validé sur le Pi ✓ (29 E2E verts, actions non destructives, contrôle visuel final CONFORME — 2026-10-06).

Tous les tickets sont done (pending_tickets vide). Le verdict machine est **accepted-with-open-items** : les critères sont satisfaits et les items ouverts sont des propositions d'amélioration (cache-busting, cadence, CI) et non des défauts de l'épique ; la validation visuelle utilisateur de ce jour fait office de décision humaine confirmative.

## Open questions

- Cache-busting (item 1) : ticket backlog maintenant, ou avec la release ?
- Cadence du drain (item 2) : le quota par défaut 1/scan te convient-il, ou relever ?
- Les décisions i18n reportées (badge descripteur, noms dérivés) : les trancher avant ou après la release 0.15.0 ?

## Assumptions

Run interactif — pas d'hypothèse non confirmée. Les narrowing d'analyse (lens inline pour cause de limite de noms ; journaux de session = les plans, pas de fichiers séparés) sont consignés dans Epic summary et Findings.
