---
epic: epic-mapping-panel-editor
date: 2026-10-03
verdict: accepted-with-open-items
criteria: declared
headless: false
---

# Rétrospective — epic-mapping-panel-editor

## Epic summary

**Épic** : Éditeur de mapping eedomus (side panel complet) — 10 tickets, **10 done, 0 built restant, 0 en attente** (`pending_tickets` vide). Aucun ticket accepté par-dessus : l'épic est complète.

Ordre de build et ranges (baselines des plans, ordre d'ancienneté vérifié par `git merge-base --is-ancestor`) :

| Range | Tickets | Commits | Churn dominant |
|---|---|---|---|
| `13dbdf7..20665e2` | 1.1 | 5 | ui_service.py +427/−233 |
| `20665e2..b690bc4` | 1.2 | 2 | test_panel.py +115 |
| `b690bc4..7b26de6` | 1.3 | 3 | eedomus-panel.js +494/−65 |
| `7b26de6..0499ec2` | 1.4 | 5 | eedomus-panel.js +556/−15 |
| `0499ec2..5e3cad5` | 1.8 | 2 | config_manager.py +166/−29 |
| `5e3cad5..5ef4ed9` | 1.9 | 2 | test_config_manager.py +119 |
| `5ef4ed9..5440932` | 1.5, 1.6 (build commun) | 4 | eedomus-panel.js +810/−40 |
| `5440932..a57f09f` (fin inférée) | 1.10, 1.7 (build commun) | 3 | −1436 net (nettoyage : data_service.py −277, rich-editor −313, scripts scp −248, config_manager legacy −229) |

**Inventaire des preuves** : épic file avec 6 critères Done-when déclarés ✓ ; initiative Requirements (5 CAPs) ✓ ; 10 plans avec Review Triage Log + Verification ✓ ; 26 commits mesurés via `git_evidence.py` (0 merge, 0 binaire) ✓ ; spine architecture 14 AD (amendé 2× pendant l'épic : AD-13, AD-14) ✓ ; SPEC + EXPERIENCE/DESIGN amendés en cours d'épic ✓. **Manquant** : journaux de session dédiés (la conversation de build est le seul record des détours ; les findings live sont consignés dans les triage logs des plans — l'analyse process s'appuie sur ces logs, pas sur des transcripts).

## Findings

### Vue agrégée — réconciliation spec/as-built

- **[spec-reconciliation, proposé]** L'épic file et l'initiative énoncent encore « CAP-4 : Sauvegarde dans custom_mapping.yaml via config_manager » ; l'as-built est AD-13/14 (canon HA storage `eedomus.mapping`, fichier = miroir éditable ingéré au chargement). Le SPEC a été amendé (commit `fce3ba8`) mais pas l'épic ni l'initiative. Sources : `epic-mapping-panel-editor.md` Requirements ; `initiative-eedomus-panel.md` Requirements ; vs `ARCHITECTURE-SPINE.md` AD-13.
- **[accept as-is]** Critère C1 (contraste diff ≥ 4.5:1 clair ET sombre) : validé **visuellement** par l'utilisateur sur les deux thèmes (28/09, « Tout est bon »), jamais **mesuré** automatiquement. Déviation acceptée enregistrée pour ne pas être re-flaggée.
- **[accept as-is]** CAP-3 autocomplete : le panel consomme une datalist alimentée par `get_peripherals` plutôt que `eedomus/get_suggestions` (resté enregistré et testé, non consommé par le panel). Déviation documentée au plan P.1.4, acceptée.

### Vue agrégée — invariants de données (le finding important)

- **[fix-now, latent à v1]** Les deux écritures d'**ingestion** du storage omettent `config_schema_version` : bootstrap `config_manager.py:306` et ingestion d'édition manuelle `config_manager.py:343`, alors que le save UI (`:111`) et le migrateur (`:183`, `:208`) l'estampillent. Chaîne vérifiée : après une édition manuelle, le champ disparaît ; au boot suivant, `_async_migrate_mapping_document` voit version absente et **estampille à la version courante sans exécuter les migrations** (comportement « version de naissance »). À schema v1 : aucun dommage. À schema v2+ : une édition manuelle ferait **sauter les migrations** en silence. Aucun test ne couvre la préservation du stamp par ingestion (trou de vérification).
- **[defer]** Double chemin de lecture du canon : le badge (P.1.3) lit via `device_mapping.async_get_canonical_custom_mapping` (`ui_service.py::_load_custom_mapping`) tandis que `get_mapping`/`save_mapping` passent par `config_manager.async_get_custom_mapping`. Convergents aujourd'hui (même Store, même repli fichier), mais deux résolutions de « le canon » divergeraient sans qu'aucun test ne les relie. Unification proposée sur config_manager lors du prochain passage sur ui_service.
- **[accept as-is]** Le storage `eedomus.config` orphelin demeure sur les instances existantes (inoffensif ; suppression volontairement évitée — documenté au plan P.1.7).

### Vue agrégée — taille et structure

- **[defer]** `www/eedomus-panel.js` : **1852 lignes / 64,8 Ko** en fin d'épic (+~1740 net sur les ranges 1.3/1.4/1.5-1.6) — trois onglets, éditeur YAML, moteur diff LCS et coloration dans un seul custom element. Contrainte délibérée (vanilla sans toolchain, SPEC Non-goals) donc pas un défaut aujourd'hui ; candidat au découpage par onglet si l'épic panel reprend. Mesuré : `wc -l` + `git_evidence.py` par range.
- `ui_service.py` (794 lignes) et `config_manager.py` (344 lignes après le nettoyage legacy) restent dans des tailles saines.

### Diff-scope (lenses inline, périmètre réduit — enregistré)

Le lens `bmad-review` a tourné **en inline sur un périmètre réduit** : les frontières inter-tickets (ui_service à travers 1.1/1.3/1.4/1.6 ; les trois couches de persistance 1.4→1.8→1.9 ; panel.py/__init__.py à travers 1.2/1.10) plutôt qu'une revue exhaustive des 3 000+ lignes de diff. Réduction enregistrée. Les findings frontières : le stamp de version ci-dessus (exactement un bug de frontière : P.1.8 a écrit l'ingestion avant que P.1.9 n'introduise le champ, P.1.9 n'a pas rétro-porté le stamp) ; le double chemin de lecture (frontière 1.3/1.4). `console.log` : 0 résiduel.

### Leçons de process (des triage logs des plans — source : chaque plan, section Review Triage Log)

1. **Vérification live obligatoire = le filet qui attrape ce que la review manque** : 4 findings majeurs découverts live (dispatch TypeError, @async_response, payload JSON, merge-loader ignorant le fichier config-dir) — chacun consigné dans son plan. Le pattern deploy-verify-fix doit rester non négociable.
2. **Tester le RENDU des callbacks regex en isolé** avant deploy (l'offset regex injecté comme « suffix » du highlighter — P.1.5, corrigé `67fdcb0`) : `node --check` ne voit pas ce genre de défaut.
3. **Lire le pipeline ENTIER** (lecture + écriture) : le merge-loader de P.1.4 lisait encore le fichier intégré — un save du panel aurait été invisible pour le mapping appliqué (`013a2a5`).
4. **Un mécanisme de données partagé se décide au spine AVANT le build** : la persistance a été reworkée deux fois (option B → AD-13 → AD-14) parce que la propriété du mapping custom n'était pas fixée par l'architecture. AD-13/14 comblent ; la règle générale est à retenir.
5. **Plan frontmatter** : `type` d'un plan doit être non-leaf (`feature`), sinon `tickets.py mark` refuse (P.1.7, corrigé `a57f09f`).

## Behavior verification

Exercé bout en bout, avec observation enregistrée :

- **E2E complète aujourd'hui (2026-10-03) : 19/19 verts** en ~32 s sur l'instance live — dont le round-trip save identique (persiste + recharge l'entry + zéro version archivée) et les 4 commandes ws du panel.
- Parcours #28 complet validé par l'utilisateur en UI (P.1.4, 28/09) : création de règle capteur de température, erreur de schema bloquant le save, unité corrigée visible après l'auto-apply.
- Écrans Périphériques, Règles (formulaire + YAML), Historique (diff + restauration en deux gestes) validés visuellement par l'utilisateur en thème clair et sombre.
- Stabilité production : **zéro erreur/traceback eedomus dans les logs d'octobre** (5 jours de recul depuis la clôture, pont de logs actif) ; 165 périphs / 100 dynamiques inchangés ; le fantôme « Configuration saved successfully » n'est plus réapparu depuis le boot du nettoyage (28/09 17:01).

## Previous-retro follow-through

Première rétrospective de l'initiative : **aucun fichier de rétrospective précédent n'existe** — rien à suivre, et c'est l'absence de fichier (pas une absence d'items) qui est enregistrée.

## Action items (proposées, en attente de décision humaine)

| # | Item | Propriétaire | Nature |
|---|---|---|---|
| A1 | Estampiller `config_schema_version` dans les deux écritures d'ingestion (`config_manager.py:306`, `:343`) + test de non-régression (une édition manuelle préserve le stamp et ne saute pas les migrations) | dev loop (prochain commit) | Remediation — fix-now |
| A2 | `mapping_registry` : passer les logs par-périph en DEBUG au boot (3 warnings « logging too frequently » le 28/09, rasp.log) | dev loop (prochain commit) | Remediation — fix-now |
| A3 | Réconcilier le texte CAP-4 de l'initiative et de l'épic file avec AD-13/14 (canon storage + miroir) | Dan4Jer via `bmad-spec` ou édition manuelle | Spec reconciliation |
| A4 | Découpage éventuel de `eedomus-panel.js` par onglet — à inscrire au backlog de l'initiative panel si elle reprend | backlog | Deferred |
| A5 | Unifier le chemin de lecture du canon (badge → config_manager) lors du prochain passage sur ui_service | backlog / prochain passage | Deferred |

Aucune de ces actions n'a été appliquée par cette rétrospective.

## Acceptance verdict

**accepted-with-open-items** — critères **déclarés** (6 Done-when dans l'épic file), tous satisfaits dans les preuves :

1. Panneau sidebar API supportée, frontend.yaml supprimé ✓ (P.1.2, E2E `get_panels` + option P.1.10).
2. Parcours #28 bout en bout ✓ (validation utilisateur P.1.4).
3. Traitement C1 ✓ — validé visuellement clair/sombre (mesure automatique : déviation acceptée, finding enregistré).
4. Mode YAML critère M9 ✓ (textarea natif + calque ; zéro lib vendorisée ne passait le critère) ; bascule sans perte ✓ (refusée tant qu'invalide).
5. Restauration confirmée + purge 4e save ✓ (validation utilisateur + test unitaire `test_fourth_save_purges_oldest`).
6. Suite E2E étendue + validation production ✓ (19/19 le 2026-10-03, logs prod propres).

`pending_tickets` vide — aucune raison machine de rejeter. Les items ouverts qui qualifient le verdict : A1 (défaut latent réel, non bloquant à v1), A3 (spec à réconcilier), A4/A5 (différés tracés). Décision humaine non sollicitée pour overrider : le verdict machine tient seul.

## Open questions

- La **cinématique approfondie** du panel que l'utilisateur veut encore tester (déclarée le 28/09) peut révéler des findings post-rétro — elle reste le chantier manuel ouvert.
- La **release** (version, tag, release notes) pour sceller l'épic : décision utilisateur en attente.
- Backlog id 101 (runner GHA RPi) non traité — hors périmètre de cette épic.
