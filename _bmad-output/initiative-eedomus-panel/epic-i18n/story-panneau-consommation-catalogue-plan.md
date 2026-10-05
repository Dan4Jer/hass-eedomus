---
title: 'Panneau : consommation du catalogue (zéro chaîne en dur)'
type: 'feature'
ticket: 3
created: '2026-10-04'
status: done
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

**Problem:** CAP-3 (volet frontend) : le panneau JS code en dur ~120 chaînes user-facing en français (microcopie, chips, statuts, aria-labels, états vides, constantes module). Le catalogue existe depuis 3.2 (`eedomus/get_translations`) mais rien ne le consomme (ticket 3.3 de epic-i18n, covers CAP-3).

**Approach:** Le panneau charge le catalogue une fois au premier `set hass` : locale lue depuis `hass.locale.language` (normalisation backend déjà en place : `fr-FR`/`fr_FR` → `fr`), appel `eedomus/get_translations`, stockage `(locale, strings)`. Un helper `t(key, params)` (méthode du composant) fait l'interpolation `{n}`, `{err}`, `{q}`, `{rule}`, `{ts}`, `{periph_id}`, `{name}`, `{usageId}`, … (remplacement simple, échappement inchangé : l'interpolation se produit AVANT injection dans les template literals qui passent déjà par `escapeHtml`). Toutes les chaînes user-facing migrent vers les clés `panel.*` de l'inventaire : constantes module (`TAB_LABELS`, `COHERENCE_SIGNALS[].label`, `COHERENCE_OK_SIGNAL.label`, `COHERENCE_COLUMNS[].label` → résolues au rendu via `t()`), template literals du `_render` (~120 sites, y compris la ligne spine `panel.peripheriques.empty.search` marquée « to add in 3.3 » dans l'inventaire), annonces aria-live, statuts asynchrones, messages d'erreur des commandes.

## Boundaries & Constraints

**Always:** clés de l'inventaire (l'inventaire fait foi ; un ajustement de nommage se note dans le plan et se répercute dans l'inventaire + le catalogue 3.2 — les 136 clés du catalogue et l'inventaire sont déjà épinglés égaux par un test 3.2, toute divergence casse la suite) ; squelettes pendant le chargement du catalogue (rendu de contenu tab gated sur la présence du catalogue — le panneau a déjà des squelettes, pattern existant) ; la commande peut échouer → `t()` renvoie la clé (jamais de texte FR en dur), le panneau reste en squelette et recharge au prochain `set hass` ; tests node du harnais (tests/js/test-coherence.js) restent verts — les fonctions pures testées qui reçoivent des libellés prennent le catalogue en fixture ; style JS existant (pas de framework, pas de lib i18n) ; ligne ≤ 88 ; JS `node --check` OK.

**Never:** pas de toucher au backend (ui_service/panel_translations figés, contrat 3.2) ; pas de traductions flows/services/entities (3.4) ; pas de commentaires/logs JS (3.5) ; aucun changement de structure DOM/aria existant (seul le texte change) ; pas de texte FR fallback codé dans le JS.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HA en français | hass.locale.language "fr" (ou "fr-FR") | catalogue FR servi (normalisation 3.2), panneau 100 % français | — |
| HA en anglais | "en" (ou "en-US") | catalogue EN, panneau 100 % anglais | — |
| Locale non couverte | "de" | backend sert EN (contrat 3.2), panneau anglais | Jamais d'erreur |
| Catalogue en vol | avant la réponse ws | squelettes (pattern existant), aucun texte clé visible | t() → clé uniquement si rendu forcé |
| Échec commande catalogue | ws error | panneau reste en squelette, retry au prochain set hass | _LOGGER rien (JS) — état d'échec silencieux mais visible |
| Clé manquante (dev) | clé absente du catalogue | t() renvoie la clé telle quelle | Développeur voit la clé |
| Rechargement locale | set hass avec nouvelle locale | catalogue rechargé si locale change, re-render | — |

## Code Map

- `custom_components/eedomus/www/eedomus-panel.js` — seul fichier de production touché. `EedomusConfigPanel` (l.631), `set hass` (l.696) : point d'entrée du chargement. Constantes module l.16-60 (`TAB_LABELS`, `COHERENCE_SIGNALS`, `COHERENCE_COLUMNS`) → clés. 7 sites `callWS` (l.796, 1681, 1944, 2830, 2897, 2982, 3052, 3343) : messages d'erreur/confirmation associés via clés. ~120 sites de texte (microcopie, chips, aria, statuts, états vides) listés clé par clé dans l'inventaire.
- `tests/js/test-coherence.js` — harnais node existant (charge le JS en VM, teste les fonctions pures) : les fonctions dépendant de libellés reçoivent le catalogue en fixture ; + nouveau test garde.
- `tests/js/` (nouveau) : test garde « zéro chaîne en dur » — extrait les littéraux string du JS (VM/parsing), normalise les placeholders (`${...}` et `{...}` → `{x}`, whitespace collapsé), et assert qu'aucun ne correspond aux 136 textes FR de l'inventaire (même normalisation). Exemptions explicites : chemins SVG, classes CSS, ids, href, clés backend (`eedomus/…`), attributs techniques.

## Tasks & Acceptance

**Execution:**
- [ ] Chargement catalogue + helper `t()` (locale depuis hass.locale.language, gate de rendu, squelettes)
- [ ] Migration des ~120 sites + constantes module vers les clés inventaire (ajustements de nommage → répercutés inventaire + catalogue + tests 3.2)
- [ ] Harnais node : fixtures catalogue, garde « zéro chaîne en dur », suite existante verte

**Acceptance Criteria:**
- Given HA anglais, when le panneau charge, then tous les textes affichés (tabs, microcopie, chips, statuts, aria) viennent du catalogue EN — aucune chaîne en dur.
- Given HA français, when le panneau charge, then tous les textes viennent du catalogue FR.
- Given la commande catalogue en échec, when le panneau rend, then squelettes uniquement — aucun texte FR en dur n'est affiché.
- Given la garde CI (node), when une chaîne user-facing en dur est réintroduite, then le test échoue.

## Implementation Notes

Full route : migration mécanique mais exhaustive — subagent d'implémentation avec l'inventaire en source unique (colonne FR = texte actuel à retrouver dans le JS, colonne clé = cible). Les clés à placeholder : le JS utilise `${...}` interpolé, la valeur catalogue `{n}` — `t()` remplace puis le rendu échappe. Les commentaires JS restent en français (3.5). Le ticket marque `panel.peripheriques.empty.search` comme spine row ajoutée en 3.3 (inventaire l.38).

Checkpoint validé par l'utilisateur (2026-10-04) : plan tel quel ; échec catalogue → squelette + retry au prochain set hass ; garde CI = test node normalisé contre les 136 textes FR de l'inventaire.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 206 verts (rien ne bouge côté backend ; le test de parité inventaire/catálogo protège la cohérence)
- `node tests/js/test-coherence.js && node tests/js/test-i18n-guard.js` -- expected: verts, garde active
- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: OK
- Grep manuel : aucun texte des 136 valeurs FR de l'inventaire ne subsiste en littéral dans le JS (la garde l'automatise)
</intent-contract>

## Review Triage Log

### 2026-10-04 — Review pass (thorough, 4 lenses)
- lens verdicts: blind 11, edge 13, verification-gap 6 (+1 other), intent-alignment 4 (alignement global vérifié : 136 clés consommées 1:1, squelette, retry, zéro Python hors ajustement sanctionné).
- CRITIQUE (vérifié en session) : `coherenceDetailHtml(row)` appelé sans son argument traducteur en production (eedomus-panel.js:2686) → TypeError à chaque ouverture de popover. Le harnais passait une fixture, masquant le bug. Corrigé : `coherenceDetailHtml(row, this._t)`.
- patchs production : t() échappé aux ~23 sites d'attributs (params bruts, pas de double-échappement — les tests hostiles du harnais ont validé) ; bloc errorHtml mort supprimé ; squelette sans catalogue doté de role="status" aria-busy="true" (pas de texte — politique squelette+retry du checkpoint) ; _historyStatus et fallbacks _saveState.applied convertis au modèle clé-résolue-au-rendu (changement de locale mid-session ne rejoue plus la langue obsolète) ; TAB_LABELS mort supprimé.
- régression de copy FR corrigée (ajustement de catalogue sanctionné) : le pluriel conditionnel pré-existant (« 1 tentative / 3 tentatives ») avait été aplati en « (s) » par la migration. Clé `panel.coherence.detail.attempts` scindée en `.attempts_one` / `.attempts_other` (EN « (1 attempt) / ({n} attempts) », FR « ({n} tentative) / ({n} tentatives) »), inventaire ligne 93 + docstring (137 clés) mis à jour, JS restaure le conditionnel. Écart assumé : les comptes non finis vont à la forme plurielle (règle de revue).
- renforcement de la garde (échec-then-vert prouvé pour chaque) : le markup SVG est strippé du littéral avant matching (l'exemption ne blinde plus le template entier) ; règle substring étendue aux littéraux quotes ; les littéraux panel.* sont validés contre le catalogue (une clé typo = échec) ; provenance text→toutes les clés (126 textes / 137 clés documentés) ; heuristique FR (accents, guillemets) sur le chemin non-exempté — tout FR nouveau en dur échoue, même hors catalogue.
- CI : la garde est ajoutée au step JS de .github/workflows/tests.yml (elle n'était lancée nulle part).
- tests ajoutés : lifecycle vm complet (commande émise avec la locale, échec→squelette→retry au set hass, changement de locale, réponse stale écartée, rendu squelette sans texte clé, re-render à l'arrivée, listeners attachés une seule fois + un clic délégué exécuté une fois) ; search-no-result (message panel.peripheriques.empty.search + compte annoncé).
- non-patchés, avec raisons : touched-only 0 lignes = liste vide silencieuse (préexistant, annoncé au SR par le compte, pas de clé inventaire) ; callWS jamais résolu (HA settle toujours, théorique) ; message ws brut == clé panel.* (absurde, garde isKey en place) ; popover ouvert au changement de locale mid-session → focus perdu (rare, différé) ; \uXXXX dans le parser fr-catalog (catalogue gelé en unicode littéral) ; edge regex-division du scanner (faux positifs visibles en dev).
- déviations acceptées : nouveaux commentaires JS en anglais (l'épique les migre de toute façon en 3.5 — la frontière est réduite, pas violée à l'envers) ; garde = textes du catalogue, pas colonne Current de l'inventaire (prose shorthand impossible à matcher ; l'heuristique FR referme l'essentiel de l'écart) ; restructuration des listeners (first-build) — modification logique minimale requise par le re-render du catalogue, documentée ici.

## Auto Run Result

Status: built

- Summary: CAP-3 volet frontend livré — le panneau charge eedomus/get_translations au premier set hass (hass.locale.language), 131 sites t() couvrent les 137 clés du catalogue (137e paire ajoutée par le split pluriel), squelettes pendant le chargement, retry au set hass suivant, zéro chaîne user-facing en dur dans le JS, garde CI active (échoue sur tout texte du catalogue ou FR accentué réintroduit, et sur toute clé panel.* inconnue).
- Files: eedomus-panel.js (+849/−277), tests/js/test-i18n-guard.js (438 l.), tests/js/test-coherence.js (+338), tests/js/fr-catalog.js (141 l., parser du catalogue gelé), panel_translations.py (split pluriel, docstring 137), i18n-inventory.md (ligne 93), .github/workflows/tests.yml (garde en CI).
- Review: 28 findings, dont 1 bug critique de production (popover cassé, invisible aux tests) ; 13 items de patch appliqués par le subagent d'implémentation avec preuves fail-then-pass pour chaque renforcement de la garde.
- Verification: node test-coherence.js (vert, +7 tests lifecycle/search) ; node test-i18n-guard.js (vert, 704 littéraux scannés) ; node --check OK ; pytest tests/unit/ -q → 206 passed (parité inventaire/catálogo et arbres EN/FR verts à 137 clés) ; black --check OK ; YAML workflow valide.
- Residual: écart assumé comptes non finis → pluriel ; 49 lignes CSS/markup >88 préexistantes non reflowées (périmètre 3.6/3.5 possible) ; la garde vit sur les textes du catalogue + heuristique accents (documenté).
