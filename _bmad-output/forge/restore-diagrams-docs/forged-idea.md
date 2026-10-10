# Forged idea: restore the ASCII + mermaid diagrams into the docs

Decisions:

- Faithful doublettes: every restored diagram ships as ASCII art AND
  mermaid, side by side, like the early README. Dual-maintenance
  accepted.
- English labels everywhere (repo policy); the FR doc may mirror later.
- README.md gets 5 doublettes: global architecture (after Features),
  three connection modes (API pull / webhook push / combined, under
  Connection modes), granularity mapping (near YAML device mapping).
- docs/mapping-format.md gets the exhaustive mapping diagram, cleaned
  against config/device_mapping.yaml — the canonical usage_id
  mappings plus the 4 advanced rules.
- Wireframes (WIREFRAME_DESIGN.md, RICH_EDITOR_DESIGN.md) dropped:
  they describe an editor the ES-module panel replaced.

Rejected:

- Mermaid-only (no doublette): user wants the original ASCII+mermaid
  pattern despite the maintenance cost.
- Faithful-to-origin French labels: violates the all-English policy;
  the README is English.

Facts discovered during forging (shape the restored diagrams):

- RGBW lamps are detected by >= 4 children with usage_id=1
  (rule rgbw_lamp_by_children) — the old diagram's
  "PRODUCT_TYPE_ID=2304" claim is stale.
- Canonical mappings (config/device_mapping.yaml): 0/2/4/50/52 switch,
  1 light, 7 temperature, 14/42 select shutter_group, 15 climate
  setpoint, 19/20/38 fil pilote/heating, 22 moisture, 24 illuminance,
  26/29 energy, 27 smoke, 28 power, 36 flood, 37 motion, 43 select
  automation, 48 cover, 82 color preset, 999 virtual, 100+ text
  sensors, 127 button camera_trigger.
- No emoji in the restored diagrams (current README style is plain).
