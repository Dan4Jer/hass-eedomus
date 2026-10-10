# Forged idea — community idea mining (2026-10-10)

Sources: Dan4Jer/hass-eedomus issues, fork fmo01 (PR #119), forum.eedomus.com,
forum.hacf.fr, community.home-assistant.io.

## Locked decisions

1. **Box-origin logging, whole integration.** Every log line tags the
   emitting box (all platforms, not just coordinator + mapping_registry as
   fmo01 proposed). Rationale: multi-box bugs (#102, #103) were hard to
   diagnose; verified absent from current code.
2. **Simulator dump story.** Dedicated story in `epic-eedomus-simulator`:
   catalog eedomus peripheral types missing from the shipped anonymized dump
   (climate, color, ...), prioritize by code coverage.
   *Amended 2026-10-10 (ticketing): the epic was found done (35/35) at
   ticket-creation time — the story became a standalone backlog story
   (id 114), precedent AD-17 (architecture review 2026-10-06).*
3. **Format guarantee, local, not CI.** CI auto-fix (fmo01's practice) is
   rejected: GitHub jobs run after the local git-only deploy. Instead: git
   pre-push hook (`uvx black/isort --check`, refuses push) + the same check
   as a gate in `deploy_hass_eedomus.sh`. No permanent local install.
4. **Cohabitation recipe.** One documentation recipe: push an HA value into
   an eedomus virtual peripheral via the existing `eedomus.set_value`
   service (YAML automation example). No blueprint.

## Rejected, and why

- **#125 panel UX**: not an idea yet — wait for Ecirbaf69's screenshot;
  track as incoming bug.
- **Security/trust doc + forum presence**: deferred; README + GitHub issues
  are enough for adoption for now.
- **Dump contribution guide**: subsumed by decision 2; no formal format yet.
- **Blueprint HA for cohabitation**: overkill; the service exists.

## Weak points that survived scrutiny

- Decision 3 requires a per-machine hook install; the deploy-script gate is
  the actual enforcement, the hook is convenience.
- Decision 1 needs a naming convention for the box tag (config entry title
  vs box id) to be settled at story time.
