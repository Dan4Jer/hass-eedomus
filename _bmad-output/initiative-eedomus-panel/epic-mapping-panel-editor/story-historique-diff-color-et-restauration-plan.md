---
title: "P.1.6 Historique, diff coloré et restauration"
type: 'feature'
ticket: 6
created: '2026-09-28'
status: done
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
baseline_revision: '5ef4ed9'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Les versions archivées (P.1.8/P.1.9) ne sont visibles nulle part — impossible de voir l'historique du mapping, de le comparer ou de revenir en arrière.

**Approach:** Onglet Historique conforme au mock-03 et DESIGN.md (traitement C1) : cartes de version (la config actuelle en état « actuelle » + les 3 archives horodatées avec leur origine), diff type git entre la version sélectionnée et la précédente, restauration confirmée en deux gestes qui emprunte le chemin auto-apply de CAP-4 et archive la version remplacée.

</frozen-after-approval>

## Implementation Notes

- Backend : 8e commande ws `eedomus/get_mapping_versions` (admin) → `{versions, current}` depuis `config_manager.async_get_mapping_versions` + canon courant. La restauration N'EST PAS une nouvelle commande : save_mapping avec le config de la version (chemin CAP-4 : archive du canon remplacé + reload).
- Frontend : cartes « Configuration actuelle » (état actuelle, pas de restauration sur elle-même) + une carte par version archivée (horodatage, origine via `reason` — défaut « sauvegarde » pour les versions pré-AD-14 sans le champ, libellés FR : sauvegarde panneau / édition manuelle du fichier / migration de schéma).
- Diff : LCS ligne à ligne (DP O(n·m), quelques centaines de lignes) sur les dumps YAML des configs ; un run removed+added est apparié par clé (texte avant `:`) → lignes `~` modifiées, les non-appariées restent `+`/`−` honnêtes. Rendu C1 : texte en couleur primaire du thème, fond teinté `color-mix` 16 % success/error/warning, barre gauche + préfixes `+`/`−`/`~` en vrais nœuds texte, `aria-label` par ligne, région scrollable focusable. Une seule version → « Première version — le diff apparaîtra à la prochaine sauvegarde. »
- Restauration : deux gestes (« Restaurer » puis « Confirmer la restauration ? » + message « Le mapping actuel sera archivé. » en alert), puis « Sauvegarde… puis Application… », rechargement des versions, feedback nominatif. La 4e sauvegarde purge la plus ancienne (cap 3, déjà en place).
- Le test de l'algorithme de diff a révélé puis corrigé un appariement adjacent erroné (removed(v1) orphelin + cum:{} apparié à version:"2") : l'appariement par préfixe de clé donne un diff sémantiquement juste (v1→v2 en `~`, cum en `~`, ajouts en `+`).

## Review Triage Log

Review quick (self), itération 1 :

- [checked] Contraste : le texte du diff est en `--primary-text-color` sur fond teinté à 16 % — hérite le contraste du thème (calage DESIGN 12 %) ; préfixes et barres portent le sens, jamais la couleur seule.
- [checked] `color-mix` est supporté par les navigateurs HA 2026 (Chrome 111+) ; sans support, fond dégradé transparent — le sens reste porté par préfixe + barre.
- [checked] Versions pré-AD-14 sans `reason` → libellé par défaut (retro-compat testée au niveau du rendu).
- [low, defer→P.1.7] Le diff compare les dumps YAML client (format stable `_yamlDumpFull`) — pas les textes historiques originaux (les éditions manuelles reformattées au boot ne se distinguent pas d'un reformat). Acceptable : le contenu sémantique est identique.
- [low] La restauration archive le canon remplacé : après restauration, la version restaurée apparaît comme la plus récente archive et l'ancienne canon est archivée — boucle conforme à CAP-5.

## Verification

**Commands:**

- `python3 -m pytest tests/unit -q` -- expected: 153 verts (dont 2 nouveaux get_mapping_versions)
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: OK
- Algorithme de diff vérifié hors navigateur (cas modifié/ajouté/supprimé appariés par clé)

**Manual checks (déploiement requis) :**

- `eedomus/get_mapping_versions` live : versions (avec reason) + current
- Onglet Historique : carte actuelle + cartes horodatées, diff coloré +/−/~ lisible en thème clair et sombre
- Restauration en deux gestes : version restaurée appliquée (entité change), ancien canon archivé, versions rechargées
