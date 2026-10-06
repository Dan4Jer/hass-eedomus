---
id: SPEC-eedomus-simulator
companions: [../spec-eedomus-history/SPEC.md]
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Simulateur d'API eedomus — strate E2E multi-box et destructive

## Why

**Douleur à résoudre + opportunité à saisir.** La strate E2E actuelle (live Pi, jamais mockée — AGENTS.md) est mono-box : l'agrégation multi-box, les collisions `periph_id` latentes (routing premier-match, consigné dans trois rétrospectives), le fan-out de la pause globale et les quatre actions destructives du backfill (ignore deux-gestes, pause) ne peuvent s'exercer nulle part — l'instance réelle est unique et les actions destructives y sont interdites. La PR #119 (fmo01) apporte un simulateur local de l'API eedomus (Flask + dump JSON + outillage d'extraction/anonymisation) qui rend cette strate possible ; sa base pré-BMAD rend le merge impossible — le salvage ciblé (AD-16, revue architecture 2026-10-06, validée) est la voie.

## Capabilities

- **CAP-1 — Simulateur d'API eedomus local**
  - **intent:** Un serveur HTTP local sert l'API eedomus depuis un dump JSON — `auth.test`, `periph.list`, `periph.value_list` (all/ids/listes), `periph.caract` (all/ids/listes, `show_config`), `periph.value` (set + règles thermostat), et `/simulate/change` pour injecter un changement d'état côté box ; auth `api_user`/`api_secret`, port configurable, plusieurs instances simultanées sur des ports distincts.
  - **success:** La config flow de HA valide la connexion et crée les entités depuis le dump, sans aucune modification du code d'intégration.

- **CAP-2 — Historique synthétique**
  - **intent:** L'endpoint `periph.history` sert un historique généré depuis le dump — points horaires sur plusieurs années, chunking/pagination conformes au client (≤ 10 000 points/appel), déterministe (même dump + même ancrage temporel = même historique).
  - **success:** Le backfill d'une box simulée importe des statistics horaires via le chemin production (spec-eedomus-history CAP-1) sans modification du client.

- **CAP-3 — Ajout d'une box simulée dans HA**
  - **intent:** Une deuxième config entry pointant vers le simulateur (`api_host=host:port`) traverse la config flow réelle — entités créées depuis le dump, cycle de vie de l'entry géré par le test (création, coexistence, suppression propre).
  - **success:** L'instance porte deux boxes (réelle + simulée) qui coexistent sans interférer ; l'entry simulée disparaît proprement après le test.

- **CAP-4 — Strate E2E simulateur**
  - **intent:** Une suite E2E dédiée (marqueur distinct de la strate live-Pi) couvre l'intestable : multi-box (agrégation `get_backfill_state`/`get_box_metrics` sur deux boxes, collisions `periph_id`, fan-out de la pause globale, sections box du panel) et actions destructives du backfill (ignore deux-gestes exécuté, pause/reprise, prioriser) sur la box simulée ; config flow ok/ko (auth refusée).
  - **success:** Les quatre actions backfill s'exercent de bout en bout sur la box simulée, la file de Supervision rend les deux boxes, et la strate live-Pi reste verte et inchangée.

- **CAP-5 — Outils d'extraction et d'anonymisation**
  - **intent:** Les scripts d'extraction/renommage/anonymisation permettent d'enrichir le dépôt avec des dumps d'autres matériels eedomus, la passe de vie privée étant documentée comme étape obligatoire avant tout commit d'un nouveau dump.
  - **success:** Un contributeur extrait sa box, anonymise, et son dump alimente le simulateur sans exposer de données personnelles.

## Constraints

- La strate live-Pi reste la vérité de régression, jamais mockée (AD-16) ; la strate simulateur la complète, ne la remplace jamais.
- Le simulateur est une infrastructure de test, jamais une dépendance de production — Flask en `requirements-test` uniquement.
- Anglais partout (AGENTS.md) : le code de la PR est traduit au salvage ; crédit fmo01 dans les commits de salvage.
- Déterminisme des E2E-sim : aucune assertion sur temps muré, ancres temporelles explicites.
- Le simulateur simule l'API eedomus, pas Home Assistant — aucun doublon de logique d'intégration dans les tests.
- La PR #119 n'est pas mergée (base pré-BMAD) — salvage fichier par fichier uniquement.
- Vie privée : le dump commité passe une passe complète (noms, ids, adresses, MACs, tokens) avant commit — l'outillage CAP-5 ne garantit rien à lui seul.

## Non-goals

- Pas de merge de la PR #119 au-delà du salvage (les rewrites coordinator/entity pré-BMAD, la suite `scripts/tests/`, les CI/semantic-release : hors périmètre).
- Pas d'instance HA conteneurisée en CI (dépend du backlog 101 self-hosted runner) — la strate E2E-sim vise d'abord l'exécution locale.
- Pas de simulation du temps réel push ni du fallback PHP `/script` (option off par défaut) — à réviser si un E2E l'exige.
- Pas de simulation de l'API proxy webhook (`api_proxy.py`) — hors des surfaces consommées par la config flow et le backfill.
- L'amélioration des logs de la PR (box d'origine dans coordinator/mapping_registry) est un salvage séparé — autre périmètre, hors de ce spec.

## Success signal

Un E2E-sim ajoute une deuxième box simulée sur l'instance Home Assistant via la config flow réelle, en voit les 69 entités, exécute les quatre actions backfill destructives dessus — et la suite live-Pi reste verte et inchangée. Le multi-box et le destructif, intestables jusqu'ici, sont sous test.

## Assumptions

- L'instance live (le Pi) reste le support de la strate E2E-sim pour la phase 1 : la 2e entry pointe vers le simulateur tenu sur la machine de dev, joignable depuis le Pi.
- Le dump de fmo01 est réellement anonymisé (vérification rapide faite — ids synthétiques, noms de modèles) ; la passe de vie privée complète reste une contrainte de commit.

## Open Questions

- La suppression propre de l'entry simulée (CAP-3) : via l'API config entries dans le test, ou un nettoyage manuel documenté si l'API ne suffit pas ?
- La profondeur N (années) et la densité (points/heure) de l'historique synthétique (CAP-2) : à fixer au premier E2E backfill mesuré.
