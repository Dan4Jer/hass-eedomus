# Release Notes - Version 0.15.4 / Notes de version - Version 0.15.4

## English

### New Features

**Box-origin tag on every log line (multi-box installs)**
- Every log line emitted during a box-scoped operation now ends with
  ` [box: <name>]` — the config entry title, falling back to the API host,
  then the entry id. On a multi-box install the log trail says which box
  spoke, across refreshes, backfills, services, entity commands and
  webhooks. Lines emitted outside any box context (startup, config flow)
  stay untagged by design.

**Catalog of missing hardware types in the simulator dump**
- `scripts/simulateur/03_catalog.py` computes `CATALOG.md` statically from
  the shipped dump and the device mapping: 27 handled-but-absent usage
  ids prioritized in four tiers (climate, cover and the RGBW color
  structure rank first), unmapped present ids, structural gaps and
  findings — exactly what to extract next, in what order.

**Local format guarantee (black + isort, no CI dependency)**
- The whole tree now passes the pinned formatters (`black==26.10.1`,
  `isort==9.0.2`), enforced by a pre-push git hook (any remote, tracked
  files only, ephemeral uv environments, fails open without uv) and by a
  format gate in the deploy script that also asserts local HEAD equals
  `origin/unstable` — the gate always checks what actually deploys.

### Bug Fixes

**Mobile: no way out of the Eedomus Config panel (issue #125)**
- Home Assistant renders no app-header for custom panels, and on narrow
  viewports it hides the sidebar — panel users were trapped. A hamburger
  button now appears on narrow viewports (hidden on desktop): it opens
  HA's drawer through the standard `hass-toggle-menu` event. Labeled in
  both languages, 44px target.

**entity.py: import crash on unreadable manifest**
- When `manifest.json` could not be read at import, the warning path
  itself raised `NameError` and killed the module import. The logger is
  now assigned before the read: the failure logs a warning and the
  import survives with `VERSION = "unknown"`.

### Technical

- New unit tests: box-tagging engine (22), catalog generator (13),
  manifest-failure path (1); node harness grows 7 menu-button
  assertions. Suite: 432 unit tests, all green.
- Self-hosted GitHub Actions runner on the Raspberry Pi: runbook
  prepared (ticket 101); runner registration is a manual step and the
  E2E workflow switch follows it.

## Français

### Nouveautés

**Balise box d'origine sur chaque ligne de log (installations multi-box)**
- Chaque ligne de log émise pendant une opération liée à une box se
  termine par ` [box: <nom>]` — le titre du config entry, puis l'hôte
  API, puis l'id d'entrée en repli. Sur une installation multi-box, la
  trace dit quelle box a parlé : refreshs, backfills, services,
  commandes d'entité et webhooks. Les lignes hors contexte de box
  (démarrage, config flow) restent non balisées, par conception.

**Catalogue des types matériels manquants du dump simulateur**
- `scripts/simulateur/03_catalog.py` calcule `CATALOG.md` statiquement
  depuis le dump livré et le mapping : 27 usage_id gérés mais absents,
  priorisés en quatre paliers (climate, cover et la structure couleur
  RGBW en tête), les ids présents non mappés, les écarts structurels et
  les constats — exactement quoi extraire ensuite, et dans quel ordre.

**Garantie de format locale (black + isort, sans dépendance CI)**
- Tout l'arbre passe les formateurs épinglés (`black==26.10.1`,
  `isort==9.0.2`), garantis par un hook git pre-push (tout remote,
  fichiers trackés seulement, environnements uv éphémères, échec ouvert
  sans uv) et par une porte de format dans le script de deploy qui
  vérifie aussi que le HEAD local égale `origin/unstable` — la porte
  contrôle toujours ce qui se déploie réellement.

### Corrections

**Mobile : impossible de sortir du panneau Eedomus Config (issue #125)**
- Home Assistant ne rend aucun app-header pour les panels custom, et
  masque la sidebar sur viewport étroit — l'utilisateur était piégé. Un
  bouton hamburger apparaît désormais sur viewport étroit (masqué sur
  desktop) : il ouvre le drawer de HA via l'événement standard
  `hass-toggle-menu`. Étiqueté dans les deux langues, cible de 44 px.

**entity.py : plantage à l'import si le manifeste est illisible**
- Quand `manifest.json` était illisible à l'import, le chemin
  d'avertissement levait lui-même un `NameError` et tuait l'import du
  module. Le logger est désormais assigné avant la lecture : l'échec
  journalise un warning et l'import survit avec `VERSION = "unknown"`.

### Technique

- Nouveaux tests unitaires : moteur de balisage box (22), générateur
  du catalogue (13), chemin d'échec du manifeste (1) ; le harnais node
  gagne 7 assertions sur le bouton menu. Suite : 432 tests unitaires,
  tous verts.
- Runner GitHub Actions self-hosted sur le Raspberry Pi : runbook
  préparé (ticket 101) ; l'enregistrement du runner est une étape
  manuelle, et la bascule du workflow E2E la suit.
