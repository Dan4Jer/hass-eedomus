---
title: 'Vue file de backfill + actions'
type: 'feature'
ticket: 3
created: '2026-10-06'
status: 'built'
route: 'full'
route_source: 'auto'
baseline_revision: '3b45de47429254fe5b22ffb323d82d9930c1dee8'
review: 'thorough'
review_source: 'auto'
lenses_ran: [blind-hunter, edge-case-hunter, verification-gap, intent-alignment]
review_loop_iteration: 0
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/initiative-eedomus-panel/epic-supervision-tab/epic-supervision-tab.md
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** L'onglet Supervision affiche les métriques mais pas la file de récupération d'historique : l'utilisateur ne peut ni voir l'état par périphérique ni déclencher les quatre actions CAP-5 livrées par le backend (4.1).

**Approach:** Une section file sous la vue métriques (ordre : sections box → lien Cohérence → file), rendue par le module supervision.js : une ligne par périphérique (nom, periph_id, statut TEXTUEL jamais couleur seule, position, détail erreur), les quatre actions par ligne (Réessayer maintenant, Prioriser, Pause/Reprendre selon l'état, Ignorer à confirmation deux gestes), l'interrupteur global en tête (bouton `role="switch"` 44px, le backend fait le fan-out), les ignorés en sous-section avec Réactiver ; chaque action rend un retour nominatif (région `role="status"` + aria-live) puis re-rend la file depuis le `{state}` de la réponse — jamais de second aller-retour.

## Boundaries & Constraints

**Always:** deux chargements parallèles par visite (`get_box_metrics` + `get_backfill_state`), slots d'état indépendants (erreur/squelette par zone, `data-retry="metrics"` / `data-retry="backfill"`), composition unique `_renderSupervisionTab` ; garde in-flight/génération sur les deux loads (miroir `_loadMetrics`) ; chaque action → `callWS` le verbe → `this._backfill = result.state` → re-rendu + annonce nominative ; en cas d'échec d'action : la file reste à l'état réel connu, erreur nominative dans la zone file, ligne toujours actionnable ; Ignorer = deux gestes au pointeur ET au clavier (pattern historique.js : swap du bouton + message inline `role="alert"` « Ignorer {name} ? Sa récupération sera abandonnée. », annulation si autre ligne confirmée) ; statuts mappés sur les 5 tokens 4.1 (priority/in_progress/error/paused/pending), token inconnu → texte neutre portant la valeur brute (précédent chip unknown cohérence) ; délégation `_onClick` : branche supervision AVANT la branche générique `.row-action`+`periphId` (collision `_createRuleFor`), attributs dédiés `data-bf-action`/`data-bf-periph` ; cibles ≥ 44px, quatre actions opérables au clavier, focus explicitement restauré sur la ligne/contrôle après chaque re-rendu (précédent `viewBtn.focus()`) ; détail erreur tronqué 40 car. avec texte complet en `title` (précédent cohérence) ; toutes les chaînes au catalogue `panel.supervision.backfill.*` EN+FR+fixtures (panel-catalog.json ET panel-keys.json) ; `retry_after` affiché depuis l'ISO local renvoyé par `_json_safe`.

**Never:** aucun changement backend (les 15 commandes sont gelées, 4.1 livré — la confirmation Ignorer est purement client) ; pas de second `get_backfill_state` après une action (le `{state}` de la réponse re-rend) ; pas de fusion des deux commandes en une ; pas de `ha-switch` ni de composant HA (vanilla, bouton `role="switch"`) ; pas de statut porté par la couleur seule ; pas de bouton muet — un refus backend est toujours rendu nominativement ; pas de touche aux contrats gelés ni aux tests Python.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Visite onglet | tab supervision | squelette cartes + squelette lignes file, puis les deux zones se résolvent indépendamment | chaque zone sa propre erreur + Réessayer |
| File chargée | queue non vide | interrupteur global en tête (état `global_paused`), une ligne par periph : nom, statut textuel, position (par box), 4 actions ; sous-section ignorés avec Réactiver | — |
| File vide | queue vide, ignored vide | état positif « Tout est récupéré. Aucun historique en attente. » | — |
| Ignorés présents | ignored non vide | sous-section « Périphériques ignorés » (nom + Réactiver) | — |
| Action réussie | clic Réessayer/Prioriser/Pause/Reprendre | commande → `{state}` → file re-rendue + retour nominatif aria-live, focus restauré | — |
| Action refusée | backend refuse (verrou occupé, periph inconnu…) | file inchangée (état réel connu), erreur nominative dans la zone file | jamais de bouton muet |
| Ignorer 1er geste | clic Ignorer | bouton swap + message inline « Ignorer {name} ? Sa récupération sera abandonnée. » `role="alert"`, AUCUN callWS | — |
| Ignorer 2e geste | clic confirmation | `backfill_set_ignored {ignored: true}` → retour nominatif « abandonnée » + re-rendu (ligne → sous-section ignorés) | — |
| Interrupteur global | bascule | `backfill_set_paused {global: true, paused}` → état re-rendu, annonce nominative globale | — |
| Ligne en erreur | status error | statut « en erreur » + message (tronqué, title complet) + tentatives + nouvel essai | error_message absent → libellé de repli |
| Statut inconnu | token non mappé | texte neutre portant la valeur brute, jamais vide | — |
| Re-rendu pendant confirmation | la ligne confirmée quitte la file | `_confirmIgnore` réinitialisé | — |

</intent-contract>

## Code Map

- `custom_components/eedomus/www/panel/supervision.js` (417 l.) — `SUPERVISION_STYLES` l.19-44 (à étendre file), helpers purs l.49-215 (`supervisionMetricCardHtml` échappé, `supervisionCycleSeries` filtrant), mixin l.219 : `_loadMetrics` l.223 (garde+génération, `_metricsErrorDetail` brut échappé jamais t()), `_renderSupervisionTab` l.277 (erreur→`data-retry="metrics"`/null→squelette/vide→positif), `_renderSupervisionSkeleton` l.319, `_renderSupervisionBox` l.335 (name échappé avant `t()`, lien `data-goto-coherence`).
- `custom_components/eedomus/www/eedomus-panel.js` — état l.127-131, lazy `set hass` l.153-155, branch supervision `_renderTabContent` l.873-876, Retry l.526-530, `_onClick` : branche générique `.row-action`+`periphId` → `_createRuleFor` ~l.744-748 (LA COLLISION), précédent de branchement par module `_onRulesEvent` ~l.751, focus restauré `viewBtn.focus()` l.700-706, `t()` placeholder l.183-198, `.row-action` ≥44px l.400-411.
- Précédents deux gestes + feedback : `regles.js` `_deleteRule` l.359-370 (swap sans timeout, `data-cancel-rule`), `historique.js` l.186-199 (swap + message inline `role="alert"` = LE pattern Ignorer) + `_historyStatus {key}` l.217-227 (`role="status"`), `shared.js` `_announceStatusNow(live, text)` l.87-92 ; chip statut jamais couleur seule : `coherence.js` `coherenceChipHtml` l.601-628, truncate 40 `coherenceTruncateText` l.580.
- Backend gelé (4.1) : `get_backfill_state` rend {queue[{periph_id,name,status,position,error_message,retry_after,attempts,entry_id}], ignored[{periph_id,name,entry_id}], global_paused, engine_active} ; chaque action rend `{...result, state}` ; statuts priority|in_progress|error|paused|pending ; refus : verrou occupé (`error`), invalid_format (inconnu/complété/ignoré/pause selon verbe).
- `custom_components/eedomus/panel_translations.py` — EN l.13, FR l.206 ; fixtures `tests/fixtures/panel-catalog.json` ET `panel-keys.json` (deux drift-checks).
- `tests/js/test-coherence.js` — asserts supervision l.1634-1871 (instance `supPanel`, delegation `_onClick` stub l.1860-1871), matrice lazy l.2085-2097 (`['supervision','eedomus/get_box_metrics']` → étendre avec `get_backfill_state`), FR via fixtures.
- `EXPERIENCE.md` — l.31 (placement sous métriques), l.70 (rangées + 4 actions), l.83/93/94 (squelettes lignes, vide positif, erreur zone), l.103 (deux gestes + retours nominatifs), l.119 (mobile ≥44px), l.134-135 (clavier bout en bout, statut jamais couleur seule), l.171-179 (Flow 4 : prioriser re-rend en tête, échec = erreur nominative + file cohérente).

## Tasks & Acceptance

**Execution:**
- [ ] `custom_components/eedomus/www/panel/supervision.js` -- `_loadBackfill` (miroir `_loadMetrics`, garde+génération, erreur brute échappée), état file dans le constructeur de l'entrée, `_renderSupervisionTab` composant les deux zones (cartes → lien → file), `_renderBackfillQueue` (interrupteur global `role="switch"`, lignes : nom/periph_id/statut textuel/position/détail erreur tronqué+title, 4 actions `data-bf-*`, Pause/Reprendre selon statut, sous-section ignorés + Réactiver), `_onSupervisionEvent` (délégation clic : actions, confirmation deux gestes `_confirmIgnore`, annulation), `_onBackfillAction` (callWS verbe → `{state}` → re-rendu + annonce nominative + focus restauré ; échec → file inchangée + erreur nominative) -- la vue CAP-5
- [ ] `custom_components/eedomus/www/eedomus-panel.js` -- état file (slots `_backfill*`), lazy branches (2 points), Retry `data-retry="backfill"`, branche `_onClick` supervision AVANT la branche générique `.row-action`+periphId, focus restoration au re-rendu -- branchement sans collision
- [ ] `custom_components/eedomus/panel_translations.py` + fixtures -- ~27 clés `panel.supervision.backfill.*` (titre, squelette aria, vide, erreur load, libellé interrupteur + annonces, 5 statuts + unknown, 5 actions + Réactiver, confirmation ignore, position/tentatives/nouvel essai, repli erreur, titre ignorés, 7 retours nominatifs + échec action) EN+FR, les DEUX fixtures régénérées -- garde i18n verte
- [ ] `tests/js/test-coherence.js` -- étendre la matrice lazy avec `get_backfill_state` ; file rendue (statut textuel, 4 actions, position), sous-section ignorés, interrupteur global, deux gestes Ignorer (1er = aucun callWS + message inline, 2e = commande), action → `{state}` re-rendu + retour nominatif, échec d'action (file inchangée + erreur nominative), statut inconnu porté, focus restauré, squelette/erreur dédiés de la file -- le harnais couvre la vue

**Acceptance Criteria:**
- Given la file chargée, when l'onglet rend, then chaque ligne porte nom + statut TEXTUEL + position + ses 4 actions (Pause/Reprendre selon l'état), l'interrupteur global est en tête, les ignorés sont en sous-section — jamais un statut porté par la couleur seule.
- Given un clic d'action, when la commande répond, then la file est re-rendue depuis `{state}` (aucun second get_backfill_state), le retour est nominatif (aria-live) et le focus revient sur la ligne/contrôle.
- Given un refus backend (verrou occupé, etc.), when l'action échoue, then la file reste à l'état réel connu avec une erreur nominative visible — aucun bouton muet.
- Given Ignorer, when le premier clic survient, then seul l'état de confirmation apparaît (swap + message inline « Ignorer {name} ? Sa récupération sera abandonnée. », aucun appel réseau) ; le deuxième clic exécute, le retour dit l'abandon, la ligne rejoint la sous-section ignorés.
- Given la file vide, when l'onglet rend, then « Tout est récupéré. Aucun historique en attente. » — le vide positif.
- Given les suites, when les tests tournent, then harnais node vert (file, deux gestes, re-rendu `{state}`, inconnu, focus), unitaires verts sans changement, E2E collect inchangé.

## Implementation Notes

Full route — recon faite. Décisions structurantes : deux loads parallèles à slots indépendants (les zones « cartes OU file » ont des états d'erreur séparés, EXPERIENCE l.94) ; la file en dernier sous les métriques ; ignorés en sous-section avec Réactiver (`backfill_set_ignored {ignored: false}`, décision 4.1 ratifiée) ; interrupteur = bouton vanilla `role="switch"` (pas de ha-switch), le fan-out par box est côté backend ; boutons jamais désactivés silencieusement — les refus backend (verrou occupé, periph complété) remontent nominativement ; `_confirmIgnore` réinitialisé quand la ligne quitte la file ; `entry_id` reste dans l'identité de ligne mais PAS dans la payload de commande (mono-box, collisions latentes comme get_peripherals).

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 324 verts inchangés (aucun changement Python)
- `node tests/js/test-coherence.js && node tests/js/test-i18n-guard.js` -- expected: verts (file rendue, deux gestes, aucune chaîne en dur)
- `python3 -m pytest tests/e2e/ --collect-only -q` -- expected: 27 collectés
</intent-contract>

## Review Triage Log

### 2026-10-06 — Review pass (thorough: blind-hunter + edge-case-hunter en subagents ; verification-gap + intent-alignment inline par l'orchestrateur — limite de noms de subagents atteinte)
- verdicts: 30 findings — high 0, medium 15, low 11, false 3, maybe-false 0 (1 intent note ratifiée)
- findings:
  - `[medium]` `[patch]` (blind, edge) aucune garde in-flight/génération sur _onBackfillAction (double-clic = verbe ×2, résolutions concurrentes en ordre arbitraire) — P2 : _backfillActionLoading + _backfillActionGen, résolution supersedée droppée.
  - `[medium]` `[patch]` (blind) file vide + ignorés non vides : « Tout est récupéré » affiché au-dessus de la liste des ignorés (contradictoire) — P3 : combinaison rend le titre + sous-section ignorés seuls ; test ajouté.
  - `[medium]` `[patch]` (blind, verif) confirmation armée survit aux changements d'onglet et aux actions échouées (« volatile par visite » non implémenté) — P4 : reset dans _setTab/_onHashChange (navigation par hash incluse) et sur action échouée ; test.
  - `[low]` `[reject]` (blind) engine_active reçu jamais rendu — non-usage délibéré, le plan ne le demande pas, aucune clé de catalogue.
  - `[medium]` `[patch]` (blind) retry_after ISO brut affiché — P5 : supervisionFormatTimestamp (07/10 21:04), ISO complet en title, texte imparsable passe tel quel.
  - `[medium]` `[patch]` (blind, edge) annonce de succès même sans {state} (feedback et état rendu divergent) — P2 : validation state (truthy + queue array) sinon refus nominal, AUCUNE annonce de succès.
  - `[medium]` `[patch]` (blind) région live détruite/recréée par chaque swap innerHTML puis remplie dans la même tâche (annonce non fiable) — P6 : région déplacée dans le shell, hors fragment re-rendu.
  - `[low]` `[patch]` (blind) BACKFILL_FOCUS_ACTION sans entrée reactivate — P7 : reactivate → 'retry', mapping documenté.
  - `[false]` (blind, intent) sémantique de l'interrupteur inversée — réfuté : le nom accessible EST « Pause globale », aria-checked=true = la pause est active = le switch nommé est ON ; cohérent.
  - `[low]` `[patch]` (blind) supervisionTruncateText duplique coherenceTruncateText — P8 : helper unique truncateDetailText dans shared.js (Array.from, coupe jamais une paire de substitution), les deux modules importent.
  - `[medium]` `[patch]` (blind, verif) la branche de délégation _onClick (collision _createRuleFor) n'est testée par aucun test avec cible data-bf-* — P9a : test de délégation (cible matchant ET data-bf-action ET .row-action+periphId → _onSupervisionEvent, _createRuleFor jamais).
  - `[medium]` `[patch]` (blind, verif) re-rendu de résolution metrics brouille le focus clavier sur un bouton de file (seuls les flux d'action restaurent) — P7 : capture de l'identité focus avant swap + restauration après, pour TOUS les re-rendus supervision ; tests.
  - `[low]` `[reject]` (blind) artefact plan (~27 clés vs 35, statut) — le fix édite le plan ; le frontmatter est l'état vivant.
  - `[medium]` `[patch]` (edge) _loadBackfill garde le dernier _backfill au démarrage (miroir incomplet de _loadMetrics) — P1 : _backfill = null au départ ; Retry après refus → squelette, pas la file périmée ; test.
  - `[medium]` `[patch]` (edge) claim « miroir » falsifié (vérifié : _loadMetrics nulle _metrics l.354) — groupé, P1.
  - `[medium]` `[patch]` (edge, dup) pas de garde d'action — groupé, P2.
  - `[medium]` `[patch]` (edge, dup) réponse sans state — groupé, P2.
  - `[low]` `[reject]` (edge) position/attempts non échappés dans les params t() — types figés par le contrat 4.1 (ints du coordinator, testés), pas d'entrée utilisateur.
  - `[low]` `[reject]` (edge) vérif Array.isArray de state.queue/ignored — contrat gelé 4.1 ; P2 valide state une fois à l'adoption.
  - `[low]` `[reject]` (edge) ligne sans periph_id ('undefined' envoyé) — contrat gelé : le coordinator émet toujours periph_id (testé 4.1).
  - `[false]` (edge) token de statut = clé prototype ('toString') — le backend n'émet que les 5 tokens du contrat gelé.
  - `[low]` `[patch]` (edge) coupe à 40 car. dans une paire de substitution (emoji cassé) — P8 : truncation par points de code.
  - `[medium]` `[patch]` (verif, dup) délégation non testée — groupé, P9a.
  - `[medium]` `[patch]` (verif, dup) combinaison vide+ignorés non testée — groupé, P3.
  - `[medium]` `[patch]` (verif, dup) focus des flux de load non testé — groupé, P7.
  - `[low]` `[patch]` (verif) entry_id jamais dans les payloads : décision structurante non épinglée — P9b : assertion sur tous les callWS enregistrés.
  - `[low]` `[patch]` (verif, dup) reset de confirmation non testé — groupé, P4.
  - `[ratifié]` (intent) lecture stricte de l'entrée implémentée (file sous métriques, 4 actions, deux gestes, interrupteur en tête, vide positif).
  - `[false]` (intent, dup) sémantique interrupteur — groupé avec B9.
  - `[low]` `[reject]` (intent) verify à distance (chaînes template, événements stubbés) — philosophie de harnais constante du repo ; surface navigateur couverte par E2E live + validation visuelle au déploiement.

Patches P1-P9 appliqués par impl-42-supervision (tour 3), re-vérifiés indépendamment (324 unitaires inchangés, harnais 210 PASS). Pas d'intent_gap, pas de bad_plan. Aucun changement backend : contrat 4.1 intact.

## Auto Run Result

**Route:** full — recon par subagent, plan validé au plan_checkpoint utilisateur (ask_user, 2026-10-06 : plan approuvé ; boutons actifs + refus nominaux), impl par subagent, review thorough 4 lens (2 en subagents, 2 inline — limite de noms), triage, 9 groupes de patchs, re-vérif.

**Vérifications exécutées (orchestrateur, 2026-10-06) :**
- `python3 -m pytest tests/unit/ -q` — 324 passed (inchangés : aucun changement Python)
- `node tests/js/test-coherence.js` — exit 0, 210 PASS (195 pré-patch, +15)
- `node tests/js/test-i18n-guard.js` — 918 littéraux / 7 fichiers, 193 clés catalogue, aucun texte en dur
- `python3 -m pytest tests/e2e/ --collect-only -q` — 27 collectés
- Audit de matrice : les 12 lignes de la matrice I/O ont chacune leurs tests, tous passés (visite/squelettes, file chargée, vide, ignorés, actions, refus, deux gestes ×2, interrupteur, erreur, inconnu, confirmation réinitialisée).

**Contrats gelés :** les 15 commandes websocket intactes, aucun fichier Python touché, catalogue 193 clés (35 nouvelles clés backfill EN+FR + fixtures synchronisées).

**Post-déploiement :** à consigner après validation live.
