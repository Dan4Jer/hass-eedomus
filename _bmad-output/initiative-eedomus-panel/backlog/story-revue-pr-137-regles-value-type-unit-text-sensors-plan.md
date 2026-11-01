---
ticket: "119"
status: done
---

# Plan — ticket 119 (revue PR #137)

Executed 2026-11-01 (Winston, architect review + live validation).

## What was done

- Full diff review: value_resolver.py (pure module, single display resolver), value_type/unit conditions in the rule engine, text_sensor rules served by the sensor platform, text_sensor.py deduplicated (-43 lines, "Unknown (x)" states dropped).
- Compatibility check with the #135 mapping canon: conditions evaluate through map_device_to_ha_entity which reads the coordinator cache - custom rules from HA storage work with the new conditions.
- Merged into unstable as 7b7029d. Suites: 466 unit tests green (452 + 14), JS green, format gate clean.
- Live validation on the Pi: clean restart, zero errors, integration up in ~1.5s, dynamic text sensors created as before. E2E live-Pi: 28 passed, 2 known state-dependent failures identical to the pre-merge baseline - no regression.
- PR #137 closed on GitHub with the validation evidence.

## Residual

- The content rides unstable and awaits the next release cut (0.15.5 already tagged).
- Old text sensors may change state rendering slightly (descriptions preferred, "Unknown (x)" gone) - by design, documented in the PR comment.
