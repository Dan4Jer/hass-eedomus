# Release Notes - Version 0.15.5 / Notes de version - Version 0.15.5

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

**Local brand assets (PR #133, @frenck)**
- The integration ships its own brand assets from
  `custom_components/eedomus/brand/` (Home Assistant 2026.3+), keeping
  the icons with the integration directly.

### Bug Fixes

**Startup no longer blocked by the backfill worker (issue #126, PR #135)**
- The backfill worker is an endless loop started during setup: as a
  tracked task it made Home Assistant wait until the bootstrap timeout
  (~5-6 minutes on a real two-box install) before wrapping up startup.
  It now runs as a background task (`async_create_background_task`),
  which bootstrap does not wait for.

**Custom mappings are now actually applied (PR #135)**
- `map_device_to_ha_entity` read the module-level mapping loaded once at
  import time: a custom mapping saved in the panel was displayed but
  never applied. It now reads the coordinator's cache (the HA storage
  canon), and rules that define no mapping (state-conditional
  `custom_rules`) are skipped instead of crashing.

**Coherence points at the right entity after a remap (PR #135)**
- After remapping a peripheral (e.g. sensor → switch), the registry keeps
  the old entry with the same unique_id: resolution now prefers the entry
  whose domain matches the mapped entity, so Coherence no longer points
  at the orphan.

**cleanup_unused_entities works again, and can no longer mass-delete (issue #136)**
- The service was dead (an ImportError swallowed on every call: it cleaned
  nothing) behind a latent trap: a mono-box lookup that would have marked
  every entity orphan at once and deleted them all. The lookup is now the
  union of every box's coordinator data, the orphan criterion is
  remap-aware (an old-domain twin is removed only when the correctly
  mapped one exists), a digit in an entry prefix can never orphan an
  entity, and a mass-deletion guard refuses any run flagging over half of
  a substantial entity set.

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
  cleanup service (8), mapping/backfill/resolution from PR #135 (12),
  manifest-failure path (1); the node harness grows 7 menu-button
  assertions. Suite: 452 unit tests, all green.
- Dependency bumps applied (supersedes dependabot PRs #127, #128, #129,
  #130, #131, #132, #134): aiohttp 3.14.5, mypy 2.4.0,
  black 26.10.1 (aligned with the format hook pin), websockets ≥ 17.2,
  flask ≥ 3.1.3.
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

**Brand assets locaux (PR #133, @frenck)**
- L'intégration embarque ses propres icônes depuis
  `custom_components/eedomus/brand/` (Home Assistant 2026.3+) — les
  icônes vivent directement avec l'intégration.

### Corrections

**Le démarrage n'est plus bloqué par le worker de backfill (issue #126, PR #135)**
- Le worker de backfill est une boucle infinie lancée pendant le setup :
  en tâche suivie, il faisait attendre Home Assistant jusqu'au timeout de
  bootstrap (~5-6 minutes sur une vraie installation à deux box). Il
  tourne désormais en tâche d'arrière-plan
  (`async_create_background_task`), que le bootstrap n'attend pas.

**Les mappings custom sont désormais réellement appliqués (PR #135)**
- `map_device_to_ha_entity` lisait le mapping de module chargé une fois
  pour toutes à l'import : une règle custom sauvegardée dans le panneau
  s'affichait mais n'était jamais appliquée. La fonction lit désormais le
  cache du coordinator (le canon HA storage), et les règles sans mapping
  (les `custom_rules` à condition/actions) sont ignorées proprement au
  lieu de planter le moteur.

**La Cohérence vise la bonne entité après un remappage (PR #135)**
- Après un remappage (ex. sensor → switch), le registre garde l'ancienne
  entrée sous le même unique_id : la résolution préfère désormais
  l'entrée dont le domaine correspond à l'entité mappée — plus de lien
  vers l'orphelin.

**cleanup_unused_entities refonctionne, et ne peut plus supprimer en masse (issue #136)**
- Le service était mort (un ImportError avalé à chaque appel : il ne
  nettoyait rien) derrière un piège latent : un lookup mono-box qui
  aurait marqué toutes les entités orphelines d'un coup — suppression
  totale. Le lookup est désormais l'union des données de chaque box, le
  critère d'orphelin connaît les remappages (un doublon d'ancien domaine
  n'est supprimé que si le jumeau correctement mappé existe), un chiffre
  dans un préfixe d'entrée ne peut plus orpheliniser une entité, et une
  garde refuse toute exécution qui flague plus de la moitié d'un
  ensemble substantiel d'entités.

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

- Nouveaux tests unitaires : moteur de balisage box (22), générateur du
  catalogue (13), service de nettoyage (8), mapping/backfill/résolution
  de la PR #135 (12), chemin d'échec du manifeste (1) ; le harnais node
  gagne 7 assertions sur le bouton menu. Suite : 452 tests unitaires,
  tous verts.
- Bumps de dépendances appliqués (supersède les PR dependabot #127,
  #128, #129, #130, #131, #132, #134) : aiohttp 3.14.5, mypy 2.4.0,
  black 26.10.1 (aligné sur l'épingle du hook de format),
  websockets ≥ 17.2, flask ≥ 3.1.3.
- Runner GitHub Actions self-hosted sur le Raspberry Pi : runbook
  préparé (ticket 101) ; l'enregistrement du runner est une étape
  manuelle, et la bascule du workflow E2E la suit.
