# Release Notes - Version 0.15.6 / Notes de version - Version 0.15.6

## English

### New Features

**Mapping rules: value_type and unit conditions (PR #137, @Ecirbaf69)**
- The rule engine can now distinguish peripherals the usage id alone
  could not separate: a rule may require a `value_type` (numeric /
  text / list, or any alias) or a `unit` (case-insensitive, blank
  counts as empty). Usage id 35, which covers both numeric counters
  and free-text peripherals, can finally be mapped differently per
  kind.
- `value_resolver.py` (new) is the single display-value resolver: the
  description of the matching value entry, then `last_value_text`, then
  the raw value - empty strings are skipped and the `-9999` error entry
  yields no state. Text sensors lose their "Unknown (...)" and
  "Error: ..." states.
- `text_sensor` rules, offered by the rules panel but previously served
  by no platform, now create real entities (served by the sensor
  platform as text sensors).
- No default mapping changes: existing installs behave identically
  unless a custom rule uses the new conditions. 14 new unit tests,
  built from real peripheral payloads.

### Bug Fixes

- **Vulnerable pin shipped in the HACS package** (ticket 120):
  `requirements_prod.txt` - copied into every release package - still
  pinned `aiohttp==3.14.3`, the exact version of the open Dependabot
  alerts (server without initial request timeout, multipart file
  descriptor exhaustion, unbounded memory, request smuggling and
  associated CVEs). It now pins 3.14.5, matching the rest of the
  release line, and `requirements.lock` - a stale pip-compile artifact
  pinning `aiohttp==3.9.3` with no consumer anywhere - is removed.

### Documentation

- `docs/CHANGELOG.md`: release-alignment policy recorded - every
  release cut also fast-forwards `main` to the tagged state, because
  Dependabot alerts scan the default branch and a stale `main` keeps
  security alerts red long after the fixes shipped.

### Technical

- Security guard (4 new tests): scans every tracked requirements
  surface - requirements files and the TOML-quoted pins of
  `pyproject.toml` - and fails on any pin matching a documented
  vulnerable version, with a version-floor check (future legitimate
  bumps pass) and a load-bearing test proving the TOML scan extracts
  the real pins.
- Test suite: 470 unit, 39 E2E (29 live-Pi + 9 simulator + 1 history
  statistics), strict JS harness - green on the target Pi (2 live E2E
  tests are state-dependent: the reference box's backfill queue is
  drained, expected on an up-to-date box).
- Release pipeline: `main` fast-forwarded to the 0.15.6 tagged state
  (the Dependabot alerts on the default branch flip to fixed at the
  next scan cycle).

---

## Français

### Nouveautés

**Règles de mapping : conditions value_type et unit (PR #137, @Ecirbaf69)**
- Le moteur de règles sait désormais distinguer ce que l'usage id seul
  ne séparait pas : une règle peut exiger un `value_type`
  (numérique / texte / liste, ou n'importe quel alias) ou une `unit`
  (insensible à la casse, vide compte pour vide). L'usage id 35, qui
  couvre à la fois les compteurs numériques et le texte libre, peut
  enfin être mappé différemment par nature.
- `value_resolver.py` (nouveau) est l'unique résolveur de valeur
  d'affichage : description de l'entrée de valeur correspondante, puis
  `last_value_text`, puis la valeur brute - les chaînes vides sont
  ignorées et l'entrée d'erreur `-9999` ne produit pas d'état. Les
  text sensors perdent leurs états « Unknown (...) » et « Error: ... ».
- Les règles `text_sensor`, proposées par le panneau de règles mais
  servies par aucune plateforme, créent désormais de vraies entités
  (servies par la plateforme sensor comme text sensors).
- Aucun changement de mapping par défaut : les installations existantes
  se comportent à l'identique sauf si une règle custom utilise les
  nouvelles conditions. 14 nouveaux tests unitaires, construits sur des
  payloads réels.

### Corrections

- **Pin vulnérable embarquée dans le paquet HACS** (ticket 120) :
  `requirements_prod.txt` - copié dans chaque paquet de release -
  épinglait encore `aiohttp==3.14.3`, la version exacte des alertes
  Dependabot ouvertes (serveur sans timeout initial, épuisement de
  descripteurs de fichiers multipart, mémoire non bornée, request
  smuggling et CVEs associées). Il épingle désormais 3.14.5, aligné sur
  le reste de la ligne de release, et `requirements.lock` - artefact
  pip-compile périmé épinglant `aiohttp==3.9.3` sans aucun
  consommateur - est supprimé.

### Documentation

- `docs/CHANGELOG.md` : politique d'alignement des releases consignée
  - chaque coupe de release fast-forwarde aussi `main` vers l'état
  taggé, parce que les alertes Dependabot scannent la branche par
  défaut et qu'un `main` périmé maintient des alertes de sécurité au
  rouge longtemps après que les correctifs sont livrés.

### Technique

- Garde sécurité (4 nouveaux tests) : balaye chaque surface d'exigences
  suivie - fichiers requirements et pins quotés TOML de
  `pyproject.toml` - et échoue sur tout pin correspondant à une version
  vulnérable documentée, avec un contrôle de plancher de version (les
  bumps légitimes futurs passent) et un test load-bearing qui prouve
  que le scan TOML extrait les vrais pins.
- Suite de tests : 470 unitaires, 39 E2E (29 live-Pi + 9 simulateur +
  1 statistics historiques), harnais JS strict - vert sur le Pi cible
  (2 tests E2E live sont état-dépendants : la file de backfill de la
  box de référence est drainée, attendu sur une box à jour).
- Pipeline de release : `main` fast-forwardé vers l'état taggé 0.15.6
  (les alertes Dependabot sur la branche par défaut passeront en fixed
  au prochain cycle de scan).
