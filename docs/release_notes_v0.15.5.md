# Release Notes - Version 0.15.5 / Notes de version - Version 0.15.5

## English

### New Features

**Box-origin tag on every log line (multi-box installs)**
- Every log line emitted during a box-scoped operation ends with
  ` [box: <name>]` - the config entry title, falling back to the API
  host, then the entry id. On a multi-box install the log trail says
  which box spoke: refreshes, backfills, services, entity commands,
  webhooks. Lines emitted outside any box context (startup, config
  flow) stay untagged by design.

**Catalog of missing hardware types in the simulator dump**
- `scripts/simulateur/03_catalog.py` computes `CATALOG.md` statically
  from the shipped dump and the device mapping: 27 handled-but-absent
  usage ids prioritized in four tiers (climate, cover and the RGBW
  color structure first), present-but-unmapped ids, structural gaps
  and findings - exactly what to extract next, in what order.

**Local format guarantee (black + isort, no CI dependency)**
- The whole tree passes the pinned formatters (`black==26.10.1`,
  `isort==9.0.2`), enforced by a pre-push git hook (any remote, tracked
  files only, ephemeral uv environments, fails open without uv) and a
  format gate in the deploy script that also asserts local HEAD equals
  `origin/unstable` - the gate always checks what actually deploys.

**Local brand assets (PR #133, @frenck)**
- The integration ships its own brand assets from
  `custom_components/eedomus/brand/` (Home Assistant 2026.3+), keeping
  the icons with the integration directly.

### Bug Fixes

- **Startup blocked by the backfill worker** (issue #126, PR #135): the
  worker is an endless loop started during setup; as a tracked task it
  made Home Assistant wait for it until the bootstrap timeout (~5-6 min
  on a real two-box install). It now runs as a background task
  (`async_create_background_task`) which bootstrap does not wait for -
  live-verified: the integration initializes ~1s after its first log
  line.
- **Custom mappings never applied** (PR #135): `map_device_to_ha_entity`
  read the module-level mapping loaded once at import time - a custom
  rule saved in the panel displayed but never applied. It now reads the
  coordinator's cache (the HA storage canon), and rules that define no
  mapping (state-conditional `custom_rules`) are skipped instead of
  crashing the engine.
- **Coherence pointed at orphaned entities after a remap** (PR #135):
  after remapping a peripheral (e.g. sensor -> switch) the registry keeps
  the old entry under the same unique_id; resolution now prefers the
  entry whose domain matches the mapped entity.
- **cleanup_unused_entities dead, behind a mass-deletion trap**
  (issue #136): the service responded success while an ImportError made
  it clean nothing, and the orphan lookup was still mono-box - fixing
  the import naively would have flagged every entity at once. The id
  set is now the union of every box's coordinator data, the criterion
  is remap-aware (an old-domain twin is removed only when the mapped
  one exists), a digit in an entry prefix can never orphan an entity,
  and a guard refuses runs flagging over half of a substantial entity
  set. 8 unit tests.
- **Mobile: no way out of the Eedomus Config panel** (issue #125): HA
  renders no app-header for custom panels and hides the sidebar on
  narrow viewports - the user was trapped. A hamburger button appears
  on narrow viewports (hidden on desktop): it opens HA's drawer via
  the standard `hass-toggle-menu` event.
- **entity.py import crash on unreadable manifest**: when
  `manifest.json` could not be read at import, the warning path itself
  raised `NameError` and killed the module import. The logger is now
  assigned before the read: the failure logs and the import survives
  with `VERSION = "unknown"`.

### Documentation

- `EXPERIENCE.md` (UX spine) gains the mobile escape pattern: a
  Foundation note (no HA app-header for custom panels), the `Menu`
  interaction primitive (`hass-toggle-menu`, narrow viewports only)
  and the "Sortie mobile" responsive rule.
- AGENTS.md: the formatting rule now points at the pre-push hook and
  the pinned formatters instead of "keep lines <= 88 manually".
- `scripts/simulateur/README.md`: catalog section + the regeneration
  step wired into the recommended workflow.

### Technical

- Dependency bumps (supersedes dependabot PRs #127, #128, #129, #130,
  #131, #132, #134): aiohttp 3.14.5, mypy 2.4.0, black 26.10.1
  (aligned with the format hook pin), websockets >= 17.2,
  flask >= 3.1.3.
- Test suite: 452 unit, 39 E2E (29 live-Pi + 9 simulator + 1 history
  statistics), strict JS harness - green on the target Pi (2 live E2E
  tests are state-dependent: the reference box's backfill queue is
  drained, expected on an up-to-date box).
- Self-hosted GitHub Actions runner on the Raspberry Pi: runbook
  prepared (ticket 101); registration is a manual step and the E2E
  workflow switch follows it.

---

## Français

### Nouveautés

**Balise box d'origine sur chaque ligne de log (installations multi-box)**
- Chaque ligne de log émise pendant une opération liée à une box se
  termine par ` [box: <nom>]` - le titre du config entry, puis l'hôte
  API, puis l'id d'entrée en repli. Sur une installation multi-box, la
  trace dit quelle box a parlé : refreshs, backfills, services,
  commandes d'entité, webhooks. Les lignes hors contexte de box
  (démarrage, config flow) restent non balisées, par conception.

**Catalogue des types matériels manquants du dump simulateur**
- `scripts/simulateur/03_catalog.py` calcule `CATALOG.md` statiquement
  depuis le dump livré et le mapping : 27 usage_id gérés mais absents,
  priorisés en quatre paliers (climate, cover et la structure couleur
  RGBW en tête), les ids présents non mappés, les écarts structurels et
  les constats - exactement quoi extraire ensuite, et dans quel ordre.

**Garantie de format locale (black + isort, sans dépendance CI)**
- Tout l'arbre passe les formateurs épinglés (`black==26.10.1`,
  `isort==9.0.2`), garantis par un hook git pre-push (tout remote,
  fichiers trackés seulement, environnements uv éphémères, échec ouvert
  sans uv) et une porte de format dans le script de deploy qui vérifie
  aussi que le HEAD local égale `origin/unstable` - la porte contrôle
  toujours ce qui se déploie réellement.

**Brand assets locaux (PR #133, @frenck)**
- L'intégration embarque ses propres icônes depuis
  `custom_components/eedomus/brand/` (Home Assistant 2026.3+) - les
  icônes vivent directement avec l'intégration.

### Corrections

- **Démarrage bloqué par le worker de backfill** (issue #126, PR #135) :
  le worker est une boucle infinie lancée pendant le setup ; en tâche
  suivie, il faisait attendre Home Assistant jusqu'au timeout de
  bootstrap (~5-6 min sur une vraie installation à deux box). Il
  tourne désormais en tâche d'arrière-plan
  (`async_create_background_task`), que le bootstrap n'attend pas -
  vérifié en live : l'intégration s'initialise ~1s après sa première
  ligne de log.
- **Mappings custom jamais appliqués** (PR #135) :
  `map_device_to_ha_entity` lisait le mapping de module chargé une
  fois pour toutes à l'import - une règle custom sauvegardée dans le
  panneau s'affichait sans jamais s'appliquer. La fonction lit
  désormais le cache du coordinator (le canon HA storage), et les
  règles sans mapping (les `custom_rules` à condition/actions) sont
  ignorées proprement au lieu de faire planter le moteur.
- **La Cohérence visait les entités orphelines après un remappage**
  (PR #135) : après un remappage (ex. sensor -> switch), le registre
  garde l'ancienne entrée sous le même unique_id ; la résolution préfère
  désormais l'entrée dont le domaine correspond à l'entité mappée.
- **cleanup_unused_entities mort, derrière un piège de suppression de
  masse** (issue #136) : le service répondait success pendant qu'un
  ImportError l'empêchait de nettoyer quoi que ce soit, et le lookup
  d'orphelins était resté mono-box - réparer l'import naïvement aurait
  marqué toutes les entités d'un coup. L'ensemble d'ids est désormais
  l'union des données de chaque box, le critère connaît les remappages
  (un doublon d'ancien domaine n'est supprimé que si le jumeau mappé
  existe), un chiffre dans un préfixe d'entrée ne peut plus
  orpheliniser une entité, et une garde refuse toute exécution qui
  flague plus de la moitié d'un ensemble substantiel. 8 tests
  unitaires.
- **Mobile : impossible de sortir du panneau Eedomus Config**
  (issue #125) : HA ne rend aucun app-header pour les panels custom et
  masque la sidebar sur viewport étroit - l'utilisateur était piégé. Un
  bouton hamburger apparaît sur viewport étroit (masqué sur desktop) :
  il ouvre le drawer de HA via l'événement standard `hass-toggle-menu`.
- **entity.py : plantage à l'import si le manifeste est illisible** :
  quand `manifest.json` était illisible à l'import, le chemin
  d'avertissement levait lui-même un `NameError` et tuait l'import du
  module. Le logger est désormais assigné avant la lecture : l'échec
  journalise et l'import survit avec `VERSION = "unknown"`.

### Documentation

- `EXPERIENCE.md` (spine UX) gagne le pattern de sortie mobile : une
  note de Foundation (pas d'app-header HA pour les panels custom), la
  primitive d'interaction `Menu` (`hass-toggle-menu`, viewports étroits
  seulement) et la règle responsive « Sortie mobile ».
- AGENTS.md : la règle de format renvoie désormais au hook pre-push et
  aux formateurs épinglés au lieu de « lignes <= 88 à la main ».
- `scripts/simulateur/README.md` : section catalogue + l'étape de
  régénération câblée dans le workflow recommandé.

### Technique

- Montées de versions (supersède les PR dependabot #127, #128, #129,
  #130, #131, #132, #134) : aiohttp 3.14.5, mypy 2.4.0,
  black 26.10.1 (aligné sur l'épingle du hook de format),
  websockets >= 17.2, flask >= 3.1.3.
- Suite de tests : 452 unitaires, 39 E2E (29 live-Pi + 9 simulateur +
  1 statistics historiques), harnais JS strict - vert sur le Pi cible
  (2 tests E2E live sont état-dépendants : la file de backfill de la
  box de référence est drainée, attendu sur une box à jour).
- Runner GitHub Actions self-hosted sur le Raspberry Pi : runbook
  préparé (ticket 101) ; l'enregistrement est une étape manuelle et la
  bascule du workflow E2E la suit.
