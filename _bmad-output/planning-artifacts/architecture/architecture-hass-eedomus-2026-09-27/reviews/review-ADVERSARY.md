---
name: 'review-ADVERSARY'
type: architecture-review
lens: adversarial-divergence
spine: architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md (AD-1..AD-14)
repo: /Users/danjer/mistral/hass-eedomus (custom_components/eedomus, read-only inspection)
date: 2026-11-01
verdict: DIVERGENT — the spine is internally consistent at initiative altitude but under-specified at the unit level; 6 concrete divergence holes found where two AD-compliant units build incompatibly.
---

# Adversarial review — ARCHITECTURE-SPINE hass-eedomus (AD-1..AD-14)

**Method.** For each AD, I constructed two units one level down (modules / epic stories) that each obey the AD *to the letter* yet still build incompatibly. I then verified against the actual code which of the two variants (or which interleaving) the repo already contains. Evidence is cited as `file:line`. Read-only: nothing in the repo was modified.

**Who mutates `coordinator.data` today (asked explicitly):** no merge primitive exists (AD-12 is `[ADOPTED, à implémenter]`). Actual writers found by grep over all modules:

| # | Writer | Site | Shape of mutation |
|---|--------|------|-------------------|
| W1 | first refresh | `coordinator.py:463` | `self.data = aggregated_data` (wholesale replace) |
| W2 | full refresh | `coordinator.py:991` | `self.data = aggregated_data` (wholesale replace) |
| W3 | partial refresh | `coordinator.py:1102` | `self.data[periph_id].update(periph_data)` (blind dict update; `last_value_change` is never compared anywhere — only read at `coordinator.py:1256`) |
| W4 | optimistic set_value | `coordinator.py:2888` | `self.data[periph_id]["last_value"] = value` + `async_update_listeners()`; writes **no** timestamp field, so nothing can arbitrate against W3 |
| W5 | platform setup (×6) | `light.py:69`, `switch.py:46`, `switch.py:154`, `cover.py:68`, `sensor.py:77`, `binary_sensor.py:89` | `coordinator.data[periph_id].update(eedomus_mapping)` — platforms write mapping keys into the coordinator's dict during entity setup |

**Panel websocket commands (`ui_service.py`):** they never touch `coordinator.data` directly. `get_peripherals`/`get_coherence` are read-only projections (`ui_service.py:741-980`); the write commands (`save_mapping` → `config_manager.async_save_custom_mapping`, `ui_service.py:1046`; `backfill_retry_now/prioritize/reset/set_paused/set_ignored`, `ui_service.py:1271-1460`) call coordinator methods that mutate `_history_progress`, **not** `coordinator.data`. The only `coordinator.data` write reachable from UI/service layer is `eedomus.set_value` (`services.py:160` → `coordinator.async_set_periph_value` → W4). So: not all mutation paths go through an AD-12 primitive — none do, and W5 (platforms) is not even bound by AD-12's scope clause.

---

## Findings (adversarial pairs)

### F1 — AD-12 scope hole: the primitive binds only the coordinator, but platforms are a second owner of the same dict
- **Unit A (AD-12 module):** implements the unique merge primitive for "set_value optimiste + cycles de refresh" exactly as AD-12's binds say (`coordinator (set_value optimiste, cycles de refresh)`). Compliant.
- **Unit B (platform setup modules):** `light/switch/cover/sensor/binary_sensor.async_setup_entry` writing `coordinator.data[periph_id].update(eedomus_mapping)` (W5). No AD forbids it; AD-7/AD-8 don't cover it. Compliant.
- **Incompatibility:** two owners of one periph dict. W2 (`self.data = aggregated_data`, an *assignment*, not a merge — outside AD-12's "mutation" wording) wipes both the optimistic `last_value` (W4) and any keys W5 added after aggregation; W3's blind `.update()` overwrites the optimistic value with the stale polled value (the exact 9abc03f regression AD-12 exists to prevent — still live today, and `services.py:167` even fires `async_request_refresh()` right after a set). Conversely W5 can resurrect stale `ha_entity` keys after a remap, defeating AD-2's "progression invalidée à son remapping".
- **Hole name:** *unbound writers of `coordinator.data`*.
- **Closing AD:** tighten AD-12 — binds must read "**tout** writer de `coordinator.data`, y compris l'assignation wholesale des full refresh et les écritures des plateformes"; the merge primitive must be the only write path and full refresh must re-derive through it (re-applying pending optimistic values); platform setup must not write into `data` (mapping keys belong to the aggregation step).

### F2 — AD-11 boundary hole: "strictement antérieures à la première statistique native" is vacuous when there are zero native stats, and is check-then-act against the recorder compiler
- **Unit A (backfill importer, current code `_import_via_statistics`, `coordinator.py:2529-2721`):** clips to `stat["start"] < first_native_start` **only if `native_rows` is non-empty** (`coordinator.py:2667-2683`). With zero native statistics (fresh sensor, or a sensor whose stats are `sum`-only while the query filters `{"state"}`) there is no clip at all → it writes the current hour H. Letter of AD-11 obeyed ("strictement antérieures à la première statistique native" — none exists). Compliant.
- **Unit B (recorder compiler):** owns the current hour and all following per AD-11's own rule sentence ("l'heure courante et toutes les suivantes appartiennent exclusivement au recorder"). Compiles hour H at H+1:00. Compliant.
- **Incompatibility:** A writes hour H (mean from cloud), B compiles hour H natively → double ownership of H, divergent means / doubled `sum` — exactly what AD-11's "Prevents" names. Additionally the boundary is queried (`statistics_during_period` up to `dt_util.utcnow()`, `coordinator.py:2650-2666`) and the import happens later (`async_import_statistics`, `coordinator.py:2714`) — a TOCTOU window in which the recorder can create the first native stat; both units obeyed AD-11 at their own check time and still collide.
- **Hole name:** *hour-boundary race / vacuous lower bound*.
- **Closing AD:** tighten AD-11 — upper bound is `min(first_native_start, current_hour_start)` **always** (never write the current or later hours regardless of native stats), and the boundary+write must be atomic w.r.t. the recorder compile (serialize via the recorder's own queue, or accept-and-document the upsert with explicit recorder-wins priority).

### F3 — AD-8 timing hole: "attente de fin de setup des plateformes" is not a mechanism, and the code resolves *after* the fetch has advanced the frontier
- **Unit A (current code):** backfill worker started inside `async_config_entry_first_refresh` (`coordinator.py:208`), i.e. **before** `async_forward_entry_setups` (`__init__.py:366` vs `__init__.py:617`) — so at worker start the entity registry has no eedomus entries yet. Resolution miss → miss counter, and after 3 misses the periph's progress is **popped** (`coordinator.py:2406-2412`). Letter of AD-8's resserrage ("résolution exacte requise, repli interdit") obeyed. Compliant.
- **Unit B (registry-event-gated importer):** waits for the exact registry match ("attente de fin de setup des plateformes", the AD's own words) before doing anything. Also compliant.
- **Incompatibility:** A and B diverge on lazy/late platform loading: A burns fetched chunks and drops progress (progress popped → re-queued at zero → refetch), B blocks. Worse, in A the fetch advances `progress["last_timestamp"] = max(timestamps)` **and saves** (`coordinator.py:2340-2360`) *before* the import resolves the entity — a resolution miss (or a permanent import failure) means the frontier has moved past points never imported; if the periph is then remapped, AD-2's invalidation discards that progress and those points are gone silently.
- **Hole name:** *resolution-after-fetch frontier loss + undefined wait mechanism*.
- **Closing AD:** tighten AD-8 — the exact registry resolution must be acquired **before** the fetch (frontier only advances after a successful import into a resolved target); the wait is an explicit gate (platforms-forwarded event), never a miss counter that drops persisted progress; lazy/delayed platform loads are named as in-scope.

### F4 — AD-2 storage-key hole: the `<entry_id>_<periph_id>` rule is enforced on the .storage write path only; the legacy read path is neither entry-scoped nor underscore-safe
- **Unit A (current .storage path):** per-entry store `eedomus.backfill_{entry_id}` (`coordinator.py:1816-1831`) with progress keys `{entry_id}_{periph_id}` (`coordinator.py:1869-1875, 1907-1912`). Multi-box safe. Compliant with the key-format rule.
- **Unit B (legacy migration, `_load_history_progress`, `coordinator.py:1633-1668`):** reads `eedomus.history_progress_*` **state-machine** entities — a global, non-entry-scoped namespace — and derives the periph id with `state.entity_id.split("_")[-1]` (`coordinator.py:1649`). In multi-box, every box's coordinator migrates **every** box's legacy states into its own `_history_progress` keyed by bare periph_id, then persists them under its own prefix (cross-box bleed); and any periph_id containing `_` is truncated to its last segment (wrong key). Both paths claim AD-2's key rule.
- **Incompatibility:** same logical progression, two different key spaces (unprefixed state machine vs `<entry_id>_<periph_id>`); multi-box boxes adopt each other's progress; underscore periph_ids collide.
- **Hole name:** *legacy key space violates the multi-box key format*.
- **Closing AD:** tighten AD-2 — name the single canonical store (`eedomus.backfill_{entry_id}`) and require the legacy migration to be entry-scoped and prefix-stripped (`removeprefix`), never `split("_")[-1]`; also fix the stale docstring at `coordinator.py:1819` ("the PROGRESS itself stays in hass.states" contradicts the v2 code).

### F5 — AD-13 holes: per-entry ingestion (forbidden by the AD), a save-vs-concurrent-edit clobber, and a standing runtime file fallback
- **Unit A (save UI, `config_manager.async_save_custom_mapping`, `config_manager.py:82-131`):** load store → archive previous → save `current`+`file_fingerprint` → write mirror file. No re-read of the file before the mirror write.
- **Unit B (setup ingestion, `async_ingest_custom_mapping`, `config_manager.py:255-356`):** file text vs fingerprint → ingest/archive. **Called per entry** at `__init__.py:181` — exactly what AD-13 forbids ("jamais au setup par entry, qui s'exécuterait plusieurs fois en multi-box"; the function's own docstring admits it). In multi-box, two entries set up concurrently → both ingest the same file diff → duplicate "ingestion" archives and racing `Store.async_save` (last-write-wins, possible lost canon).
- **Interleaving A×B (the asked case):** user edits `custom_mapping.yaml` between A's store-load and A's mirror-write → A's mirror write silently clobbers the edit; at next reload fingerprint==mirror, so the edit is gone **without a version archive and without a warning**. Both units obeyed AD-13's letter ("save UI écrit current + régénère le miroir + fingerprint").
- **Runtime file fallback:** `async_get_canonical_custom_mapping` (`device_mapping.py:969-986`) falls back to `read_custom_mapping_file` when storage has no canon, and the sync `load_custom_yaml_mappings()` (`device_mapping.py:388`) reads the file directly — both violate "tout le runtime lit le storage uniquement — jamais le fichier directement" (only the bootstrap may read the file).
- **Hole name:** *mirror clobber without compare-and-swap; ingestion not domain-scoped; file fallback in the runtime read path*.
- **Closing AD:** tighten AD-13 — (1) ingestion runs only in the domain-level ConfigManager init: delete the per-entry call at `__init__.py:181`; (2) save must re-read the file text immediately before writing the mirror and refuse/merge with an explicit warning if it changed since load (CAS on the mirror); (3) the file fallback is bootstrap-only, removed from the steady-state read path.

### F6 — AD-9 exclusivity hole: two read paths for the same options can disagree
- **Unit A:** `_get_config_value(entry, key, default)` (options > data > default, `False` honoré) — used e.g. by `coordinator._history_enabled` (`coordinator.py:1454-1458`).
- **Unit B:** direct reads — `coordinator.py:2168` (`self.config_entry.options.get(CONF_HISTORY_RETRY_DELAY, …)`, no data fallback), `__init__.py:255,270-584` (`entry.options.get(key, entry.data.get(key, DEFAULT))` bypassing the helper), `__init__.py:453` (`entry.data.get(CONF_ENABLE_HISTORY, False)` — data only), and `_async_set_periph_value_untagged` reading a **snapshot** `hass.data[DOMAIN][entry_id]["config_entry"]` dict (`coordinator.py:2746-2763`) that can diverge from `entry.options`.
- **Incompatibility:** same option, two accessors with different fallback chains and a stale snapshot — e.g. `CONF_ENABLE_HISTORY` is read via AD-9 at `__init__.py:399-400` but via raw `entry.data` at `__init__.py:453`; divergent enable decisions are possible. The Consistency Conventions say "lecture exclusive via AD-9" — the code violates it.
- **Hole name:** *non-exclusive option reads / stale config snapshot in hass.data*.
- **Closing AD:** tighten AD-9 — `_get_config_value` is the only accessor; config snapshots in `hass.data` are forbidden (read `entry.options`/`entry.data` live).

---

## Spot-check results (as requested)

- **AD-2 key format vs multi-box:** .storage path is double-scoped (per-entry store + prefixed keys) and safe; the legacy state-machine migration is neither (`coordinator.py:1649`) → F4. Unload path (`async_shutdown_backfill`, `coordinator.py:1484-1497`, called at `__init__.py:730-732`) does cancel+await+flush as AD-2 requires. Mono-importer lock is a per-coordinator instance attr — OK per entry.
- **AD-8 resolution timing vs lazy platforms:** worker starts before platforms are forwarded (`coordinator.py:208` + `__init__.py:366` vs `617`); misses are counted and progress dropped after 3 (`coordinator.py:2406`), frontier advanced before resolution → F3.
- **AD-12 merge primitive vs set_value/refresh interleavings:** no primitive exists. W4 writes no timestamp; W3 blindly overwrites; W2 replaces wholesale; `services.py:167` refreshes right after a set → the optimistic value is regressed on the first partial refresh. Writers enumerated in the table above; panel ws commands do **not** touch `coordinator.data` → F1.
- **AD-13 save UI vs concurrent file edit:** clobber without CAS; ingestion called per entry; runtime file fallback present → F5.
- **AD-11 'strictement antérieures' vs recorder compile timing:** vacuous when zero native stats; TOCTOU between boundary query and import; `sum`-only sensors never clip (query filters `{"state"}`) → F2.
- **ui_service.py vs coordinator.data:** read-only projections + coordinator method calls; the only UI-reachable `data` write is `eedomus.set_value` → W4. However the backfill ws handlers and the background worker are **two owners of `_history_progress`** (a second mutation domain AD-12 doesn't bind), mutating + `_save_backfill_persistence()` without a common lock (only fetch+import hold `_backfill_import_lock`) → lost-update on save is possible. Worth a new AD binding `_history_progress` writers under one lock.

## Secondary gaps (not divergence holes, but letter-vs-code gaps)
- AD-3 "réévalué à chaque activation … progressions invalidées": no invalidation of out-of-scope periph progress exists in `options_flow.py` (no history handling there at all); stale entries linger in `_history_progress`.
- `_handle_fetch_error` (`coordinator.py:2155-2186`) sets `retry_after` only on the first error; subsequent failures never extend it → a persistently failing periph is retried on every worker pass once the original `retry_after` has passed (hot loop), diverging from "retry queue par périph + history_retry_delay persisté".
- AD-6bis is implemented (value_list fingerprint, `coordinator.py:2211-2223, 2255-2274`) but only when **both** frozen and current fingerprints are non-None; a periph whose `values` list appears later (merged at init) silently starts a new progression without invalidation — acceptable but undocumented.

## Verdict

**DIVERGENT (6 holes).** The spine's ADs are each locally reasonable, but at unit level: AD-12 doesn't bind all writers of `coordinator.data` (F1); AD-11's boundary is vacuous without native stats and racy against the recorder compile (F2); AD-8 doesn't pin where the "attente" happens and the code resolves after the frontier advanced (F3); AD-2's key rule isn't enforced on the legacy migration path (F4); AD-13 forbids per-entry ingestion yet the code does exactly that, and its save path can clobber a concurrent file edit (F5); AD-9's exclusive read is violated by direct/snapshot reads (F6). Each hole names the tightening (or new AD) that closes it, as listed per finding. Highest priority: F1 + F2 (silent state/statistics corruption), then F5 (silent loss of user config), then F3/F4 (multi-box correctness), then F6.
