"""E2E: the backfilled history really lands in the recorder (story 1.6).

End-to-end proof of the history pipeline: a peripheral that the
backfill drained (its progress row carries an oldest timestamp) must
answer Home Assistant's recorder statistics query with hourly rows
(mean/min/max) around that retrieved window — pause-independent (the
rows are already imported, whatever the engine state).

Marker `e2e`: the live-Pi strate (never mocked — AD-16).
"""

from datetime import datetime, timedelta, timezone

import pytest

pytestmark = [pytest.mark.e2e]


def _to_utc_datetime(value):
    """Parse the ISO timestamps the backend reports (naive local or
    tz-aware) into an aware UTC datetime."""
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone(timezone.utc)


class TestHistoryStatistics:
    def test_backfilled_periph_has_hourly_statistics(self, ws_call):
        """A drained peripheral's oldest retrieved window exists in the
        recorder as hourly statistics with mean/min/max."""
        state = ws_call("eedomus/get_backfill_state")
        rows = [
            r for r in state.get("queue", [])
            if r.get("oldest_timestamp") and r.get("entry_id")
        ]
        assert rows, "no drained peripheral found (nothing to assert)"

        row = rows[0]
        periph_id = row["periph_id"]

        # Resolve the peripheral's real entity through the coherence view
        coherence = ws_call("eedomus/get_coherence")
        target = next(
            (
                c for c in (coherence.get("peripherals") or coherence)
                if c.get("periph_id") == periph_id
                and c.get("entity_id")
            ),
            None,
        )
        assert target, f"peripheral {periph_id} has no resolvable entity"
        entity_id = target["entity_id"]

        oldest = _to_utc_datetime(row["oldest_timestamp"])
        start = oldest.isoformat()
        end = (oldest + timedelta(days=7)).isoformat()
        stats = ws_call(
            "recorder/statistics_during_period",
            {
                "start_time": start,
                "end_time": end,
                "statistic_ids": [entity_id],
                "period": "hour",
            },
        )
        series = stats.get(entity_id) or []
        assert series, (
            f"no hourly statistics for {entity_id} in its backfilled "
            f"window [{start}, {end}]"
        )
        sample = series[0]
        assert "mean" in sample and "min" in sample and "max" in sample
