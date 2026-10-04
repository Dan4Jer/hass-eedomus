# Source extraction — Cohérence tab (2026-10-04)

## SPEC contracts
- Data from coordinator.data (AD-7) / config_manager (AD-13); no direct file/API reads from the panel.
- WS convention: `eedomus/<verb>`, reuse existing commands; `require_admin: true`.
- HA CSS variables only; vanilla JS custom element, no build toolchain.
- Non-goals: no HA entity registry editing, no backfill UI, no writes to the box. Entity-settings navigation = scope extension (new CAP needed).

## Architecture constraints
- AD-7 (coordinator sole API access), AD-8 (entity registry sole periph→entity_id resolution, multi-box), AD-9 (_get_config_value), AD-13 (HA storage canon, yaml mirror; badge = user overrides only), AD-3/AD-6 (statistics = numeric sensors; resolution float then value_list).
- Coordinator polls ~1 s; live state available via hass.states/registry.

## Existing ws commands (all require_admin)
validate_config, get_suggestions, get_schema, get_peripherals ({periph_id, name, usage_id, entity_id, platform, device_class, unit, modified, modified_by_rule, modified_date}), get_mapping, save_mapping (write), get_mapping_versions.

## Gaps (absent today)
- No command exposes the mapping registry (ha_subtype, parent_periph_id, justification), live state value, or raw API fields.
- No coherence-status concept; derivable signals: no-HA-entity = entity_id null; rule active = modified_by_rule; in-error = coordinator retry queue; questionable mapping = no live state/unit (partial).
- Registry rows exist only for MAPPED devices — the full ~165-row table needs a cross-join of registry × get_peripherals on periph_id.
- Needed: a new ws command (e.g. eedomus/get_coherence) following the module-dispatcher pattern.

## Frontend patterns
- Tabs: TABS const + TAB_LABELS, data-tab nav, _renderTabContent switch, URL hash routing. New tab = 4 edits.
- Lazy per-tab loading via hass.callWS, skeletons, .state-message error card + retry, aria-live.
- Rows are card-based (.periph-row grid), NOT a <table>; no sorting exists yet; search/filter patterns exist (_filteredPeriphs).
- Mobile: @media (max-width: 900px) flattens rows to flex-column.
- Theming: HA vars only (--primary-text-color, --secondary-text-color, --primary-color, --divider-color, --card-background-color, --input-fill-color, --ha-card-border-radius, --accent-color, --text-accent-color, --error-color, --success-color, --warning-color, --code-font-family).
- No popover component, no entity-navigation link — both new UI.

## mapping_registry fields (six)
periph_id, periph_name, parent_periph_id (nullable), ha_entity, ha_subtype, justification (default "No justification provided"). Accessors get_mapping_registry()/clear_mapping_registry().
