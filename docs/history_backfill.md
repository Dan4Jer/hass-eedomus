# History retrieval: what happens when you enable it

This page documents the `history` option of the hass-eedomus
integration (spec-eedomus-history CAP-4).

## What activation does

When the `history` option is enabled, the integration starts a
**background backfill**: it fetches the history your peripherals hold
in the eedomus cloud and imports it into Home Assistant as **hourly
statistics** (mean / min / max per hour) through the official recorder
statistics API.

Key properties:

- **Scope**: only peripherals mapped as a `sensor` with a numerically
  resolvable value (AD-3). Discrete states (lights, switches, covers,
  climates) are never backfilled — for "on time" needs, use Home
  Assistant's `history_stats` helper, live.
- **Pace**: a background worker imports at most
  `history_peripherals_per_scan` peripherals per pass (default 1),
  one pass every 60 seconds — the real-time refresh of your entities
  is never slowed down by the backfill.
- **Cadence control**: everything is visible and controllable from
  the integration panel's **Supervision** tab (peripheral by
  peripheral: position in the queue, in progress, in error, ignored,
  paused; actions: retry now, prioritize, pause/resume, ignore,
  reset progress).

## Expected duration of the first activation

The first activation imports everything the cloud still holds for
every eligible peripheral (the API pages 10,000 points per call).
With the default pace (1 peripheral per minute), a box of ~60
eligible peripherals takes about an hour per 10,000-point page
involved; peripherals with years of dense history take several passes.
Raise `history_peripherals_per_scan` in the options to go faster at
the expense of more cloud API calls. The exact duration of your first
activation is measured in the integration's logs ("History fully
fetched for ...").

## Resume after a restart

Nothing is lost on a restart: the per-peripheral progress (last
imported timestamp, point counters, errors, retry queue) is persisted
in Home Assistant's `.storage` and the backfill **resumes where it
stopped** — no re-import from zero. Re-importing anyway is safe: each
hour is an upsert, never a duplicate (and "Reset progress" in the
Supervision tab re-queues one peripheral without deleting its already
imported statistics).

## What you will see in Home Assistant — and what you will not

- **You will see**: the long-term statistics of your sensors. Open a
  sensor, choose a long-term statistics chart (or a "Statistics graph"
  card with a week/month period): the curve extends **before the
  installation date** of the integration, back to what the eedomus
  cloud still holds.
- **You will NOT see**: the standard History panel (raw states) go
  back in time. Home Assistant offers no supported way to write past
  raw states, and the recorder purges raw states after a retention
  window anyway — the backfill deliberately never touches the state
  machine. The history it builds lives in the hourly statistics and
  the long-term graphs only.

## Errors and limits

- A peripheral whose cloud fetch fails lands in the retry queue
  (visible in the Supervision tab with the reason and the retry time).
- A peripheral whose `value_list` (label-to-value mapping) changes
  after its import restarts from scratch: the already imported
  statistics keep their meaning at import time, and re-importing with
  the new mapping is an upsert of the same hours.
- Imported statistics are never purged by the recorder; the raw-state
  purge window does not affect them.
