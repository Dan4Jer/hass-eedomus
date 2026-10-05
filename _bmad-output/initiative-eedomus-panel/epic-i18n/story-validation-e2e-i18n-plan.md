---
title: 'Validation E2E i18n (live + gardes CI)'
type: 'test'
ticket: 7
created: '2026-10-05'
status: done
route: 'full'
route_source: 'auto'
baseline_revision: '36aae166b3c54f3b718421025eb41dc6f3bb32b3'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 0
followup_review_recommended: false
context:
  - /Users/danjer/mistral/hass-eedomus/_bmad-output/specs/spec-eedomus-i18n/i18n-inventory.md
warnings: []
deferred:
  - summary: >-
      Three pre-3.5 French comments in eedomus_client.py (:80/:91/:173) remain,
      exempted by exact literal (any edit re-triggers the guard) — one-line
      English translations worth a follow-up touch of that file.
    evidence: >-
      The 3.5 English pass missed them (accent-free French caught by this
      ticket's lexicon); production was frozen for 3.7, so they are
      grandfathered rather than translated.
    location: custom_components/eedomus/eedomus_client.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Clôture de l'épique i18n : la validation live fait défaut (les arbres en/fr du catalogue `eedomus/get_translations` n'ont jamais été appelés sur l'instance déployée) et le second garde CI du ticket (zéro log/docstring/commentaire FR côté Python) n'existe pas encore — le premier garde (zéro chaîne user-facing en dur dans le panneau) est déjà en CI depuis 3.3 avec self-test depuis 3.6.

**Approach:** Trois volets : (1) E2E live — tests `tests/e2e/test_e2e_i18n.py` (nouveau fichier, pattern des tests panel existants : `ws_call`, `ha_headers`) : appel live de `eedomus/get_translations` pour "en" et "fr" — clés identiques entre les deux, 144 clés, placeholders paritaires par clé, EN non vide ; (2) garde Python — `tests/unit/test_no_french_source.py` : scan Unicode (accents + guillemets + lexique) des logs/docstrings/commentaires de `custom_components/eedomus/*.py`, avec liste d'exemptions EXPLICITE et documentée (matchers de données : binary_sensor porte/fenêtre/fumée/présence, climate arrêt/désactiver ; arbres gelés exclus : translations/, panel_translations.py ; exemples de données dans docstrings : 'Confort', noms système FR) — échoue sur toute nouvelle chaîne FR, preuve par mutation ; (3) validation post-déploiement sur le Pi (exécutée par l'orchestrateur après le build, autorisation utilisateur du 2026-10-05, précédent 2.8) : déploiement git-only, restart HA, logs propres, `pytest tests/e2e/ -v` vert sur l'instance live.

## Boundaries & Constraints

**Always:** les tests E2E suivent le pattern conftest existant (HA_TOKEN/.env, ws_call) et sont conçus pour tourner UNIQUEMENT sur l'instance live (pas de mock) ; le garde Python est déterministe (pas de réseau), liste d'exemptions minimale et nommée fichier:littéral ; échec loud avec le fichier:ligne en message ; le premier garde (test-i18n-guard.js) n'est pas retouché — juste vérifié vert ; ligne ≤ 88 ; anglais partout (règle 3.5).

**Never:** pas de changement de production (`custom_components/eedomus/**` intouché — ce ticket est tests + CI seulement) ; pas de modification des contrats ws ; pas de fixture dépendante de `_bmad-output` (règle 3.6 : lire `tests/fixtures/panel-catalog.json` pour la parité en/fr attendue, drift-checké) ; pas de mock des appels live.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| get_translations "en" live | instance déployée | {locale:"en", translations: 144 clés, toutes valeurs non vides | échec loud |
| get_translations "fr" live | idem | {locale:"fr", translations: 144 clés | échec loud |
| Parité en/fr live | les deux appels | mêmes ensembles de clés, mêmes placeholders {x} par clé | assertion nommée |
| Locale non couverte live | "de" | repli EN (contrat 3.2) : {locale:"en", ...} | échec loud |
| Garde Python | arbre actuel | zéro français hors exemptions nommées | échec fichier:ligne |
| Garde Python | chaîne FR plantée | échec avec fichier:ligne | preuve par mutation |
| CI | push | les deux gardes tournent (tests/unit + tests/js déjà branchés) | rouge sur régression |

</intent-contract>

## Code Map

- `tests/e2e/test_e2e_i18n.py` — NOUVEAU. Pattern : `tests/e2e/test_e2e_panel.py` (fixtures `ws_call`, `ha_headers` du conftest :97/:38) ; la parité attendue se lit depuis `tests/fixtures/panel-catalog.json` (clés + placeholders, PAS depuis `_bmad-output`).
- `tests/unit/test_no_french_source.py` — NOUVEAU. Scan : accents/guillemets + petit lexique FR sur les lignes de commentaires/docstrings/messages de log de `custom_components/eedomus/*.py` (exclusions : `translations/`, `panel_translations.py`, et la liste d'exemptions EXPLICITE : `binary_sensor.py` « porte »/« fenêtre »/« fumée »/« présence » (:169/:171/:175), `climate.py` « arrêt »/« désactiver » (:598), exemples de données docstrings « Confort », commentaire système `sensor.py` (~:200 « reports these system periphs in French »)). Chaque exemption nommée en constantes avec sa raison.
- `.github/workflows/tests.yml` — vérifier que les deux gardes tournent en CI (pytest tests/unit inclut le nouveau test automatiquement ; le garde JS est déjà branché depuis 3.3 — ne rien changer sauf omission réelle).
- Le déploiement + l'exécution live ne sont PAS dans le build : l'orchestrateur déploie après le commit (autorisation utilisateur, mode précédent 2.8 : git-only + restart + logs + `pytest tests/e2e/ -v`).

## Tasks & Acceptance

**Execution:**
- [ ] `tests/e2e/test_e2e_i18n.py` — arbres en/fr live + parité clés/placeholders + repli "de"
- [ ] `tests/unit/test_no_french_source.py` — garde Python avec exemptions nommées, preuve par mutation (plant FR → échec → retiré)
- [ ] Vérification du branchement CI des deux gardes

**Acceptance Criteria:**
- Given l'instance déployée, when les tests i18n E2E tournent, then les deux arbres live ont 144 clés identiques avec placeholders paritaires (le repli "de" sert l'anglais).
- Given le garde Python, when une chaîne FR est ajoutée à un log/docstring/commentaire hors exemptions, then le test échoue en nommant fichier:ligne (preuve par mutation dans le rapport du build).
- Given la CI, when un push arrive, then les deux gardes s'exécutent (i18n guard JS + no-french Python).

## Implementation Notes

Full route — deux fichiers tests neufs, patterns établis. Le compte de clés (144) se lit depuis la fixture plutôt qu'en dur, pour survivre à la prochaine clé. Le build ne peut PAS exécuter les tests E2E (instance live requise, HA_TOKEN absent localement) — sa vérification : import/collect propre (`python3 -m pytest tests/e2e/ --collect-only -q`), garde Python vert + mutation-prouvé, suite unitaire verte. L'exécution live est la phase post-déploiement de l'orchestrateur.

## Verification

**Commands:**
- `python3 -m pytest tests/unit/ -q` -- expected: 240+ verts (le nouveau garde inclus)
- `python3 -m pytest tests/e2e/ --collect-only -q` -- expected: collect propre, nouveaux tests listés (exécution = post-déploiement)
- `node tests/js/test-i18n-guard.js` -- expected: vert (inchangé)
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/tests.yml'))"` -- expected: OK
</intent-contract>

## Review Triage Log

### 2026-10-05 — Review pass
- verdicts: 26 findings — high 1, medium 5, low 15, false 0, maybe-false 0 ; convergences fortes sur l'égalité de valeurs live (le cœur du ticket), l'échappatoire de colocalisation des exemptions et le self-test du garde Python.
- production (patchée, tests seulement) : **égalité de valeurs live vs fixture** ajoutée par locale avec diff nommé (count+clés+placeholders seuls laissaient passer des textes faux — high, c'était la raison d'être du ticket) ; check non-vide ajouté au FR ; 2 tests live neufs (fr-FR → base fr, locale null → EN — la prémisse « jamais exercé en live » du ticket) ; fixture échoue nommé + lru_cache ; websockets épinglé dans requirements-test.txt.
- garde Python (patchée) : **colocalisation fermée** (strip du littéral exempté puis re-scan du reste — preuve par mutation du revoir : « Le mode Confort est active » passait silencieusement) ; exemption climate élargie au littéral complet "Confort, Eco, Hors Gel, Arret" ; exemption inerte supprimée ; chemins d'exemption en relatif-repo complet (fichier imbriqué homonyme ne peut plus hériter) ; lexicon amputé de est/champ/gel (faux positifs anglais — « Hors Gel » couvert par le littéral complet) ; assert scan non-vide (≥ 20 fichiers) ; **self-test committé** (pattern du garde JS : 3 sondes dont la colocalisée, + contrepartie propre) ; ACCENT_RE sous 88.
- rejets avec raisons : numéros de ligne périmés du Code Map (correctif = éditer le plan ; les exemptions sont content-matched, la garde est sûre) ; formes de placeholder non-identifiantes {0} (spéculatif — les placeholders du catalogue sont des identifiants par construction, fixture ≡ catalogue épinglé) ; français sans accents hors lexicon qui passe (limitation documentée de l'heuristique — accent + lexique, pas un modèle de langue) ; KeyError cosmétique du test de parité (nommé par le test frère) ; tension R1 du lens intent (les 3 commentaires FR grandfathered = déviation documentée, pas un défaut du ticket).
- différé : traduction des 3 commentaires FR d'eedomus_client.py (production gelée pour ce ticket ; le garde les tient par littéral exact — toute retouche les réexpose).

## Auto Run Result

Status: built

- Summary: clôture E2E i18n — 7 tests live (test_e2e_i18n.py : arbres en/fr à égalité de VALEURS avec la fixture, non-vide ×2, parité clés, parité placeholders par clé, fr-FR → base fr, null → EN) collectés et prêts pour le run post-déploiement ; garde Python no-french-source (accents + lexique + exemptions strip-then-rescan, 12 entrées nommées fichier+littéral+raison, drift-checkées, self-test committé 3 sondes) ; websockets épinglé ; les deux gardes tournent en CI sans changement de workflow.
- Files: tests/e2e/test_e2e_i18n.py (nouveau), tests/unit/test_no_french_source.py (nouveau), requirements-test.txt (+websockets).
- Review: 26 findings sur 4 lens — 11 items de patch appliqués (1 high : l'égalité de valeurs, la raison d'être du ticket ; 5 mediums dont la colocalisation prouvée par mutation), 1 différé (3 commentaires FR grandfathered), 5 rejets motivés.
- Verification: pytest tests/unit/ -q → 244 passed (240 + 4) ; tests/e2e/ --collect-only → 27 tests collectés (dont les 7 i18n) ; garde JS verte avec self-test 5/5 ; production inchangée (git diff vide) ; lignes ≤ 88.
- Live run: phase post-déploiement (déploiement git-only sur le Pi autorisé par l'utilisateur, précédent 2.8) — résultats consignés ci-dessous après exécution.

### Post-deployment validation (Pi)

Exécuté 2026-10-05, mode précédent 2.8 (déploiement git-only autorisé par l'utilisateur) :

- **Déploiement** — `deploy_hass_eedomus.sh` : le Pi (`/homeassistant/custom_components/hass-eedomus`) est monté à `6a9f0d4` (toute la chaîne i18n : 3.1→3.7 + fixes), restart HA déclenché.
- **Instance** — HA **2026.9.4**, état `RUNNING` après restart (API `/api/config`).
- **E2E live** — `python3 -m pytest tests/e2e/ -v` → **27 passed in 62.31s**, dont les 7 tests i18n : arbres en/fr à égalité de valeurs avec la fixture (144 clés, non-vides), parité clés, parité placeholders par clé, repli `de`→EN, normalisation `fr-FR`→fr, `null`→EN ; plus toute la suite existante (connectivité, refresh, set_value roundtrip, options flow avec cycle de restart, panneau en sidebar, commandes ws, save identique).
- **Logs post-restart** — activité coordinator saine (imports d'historique, PARTIAL REFRESH, « Error sensors created: 0 devices in retry queue ») ; zéro erreur websocket, zéro erreur eedomus (les seuls matches « error » du grep sont les lignes saines de création de capteurs d'erreur).
- **Gardes CI** — vérifiées au build : garde i18n JS (union EN+FR, self-test 5/5) + garde Python no-french (self-test 3 sondes) toutes deux dans le chemin CI.

Verdict de validation : l'épique i18n est **validé en live** — les deux gardes CI échouent sur toute régression, et l'instance déployée sert les catalogues conformes aux fixtures. Le passage de 3.7 à `done` reste le geste de l'utilisateur.
