"""Unit tests for the config flow (config_flow.py).

Behavioral regression tests for async_step_user: an invalid payload
must re-show the user form with the exact rendered errors dict — a
keyed, field-scoped error (config.error.<key> on the offending field)
for the field-specific validators, "base" for form-level errors.
The raw English exception messages stay in the logs; the form only
ever shows translated keys.
"""

from unittest.mock import MagicMock

import pytest

from custom_components.eedomus.config_flow import EedomusConfigFlow

pytestmark = pytest.mark.unit


def make_flow():
    flow = EedomusConfigFlow()
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    return flow


def base_payload(**overrides):
    """A payload that passes every field-specific validator."""
    payload = {
        "api_host": "https://192.168.1.10",
        "api_eedomus": True,
        "enable_api_proxy": False,
        "api_user": "user",
        "api_secret": "secret",
        "scan_interval": 300,
        "http_request_timeout": 10,
        "max_concurrent_requests": 5,
        "min_request_delay": 0.5,
        "history": False,
    }
    payload.update(overrides)
    return payload


class TestAsyncStepUserErrors:
    """Invalid payloads render the keyed error on the offending field."""

    CASES = [
        ({"api_host": "  "}, {"api_host": "empty_api_host"}),
        ({"api_host": ""}, {"api_host": "empty_api_host"}),
        ({"scan_interval": 10}, {"scan_interval": "invalid_scan_interval"}),
        (
            {"http_request_timeout": 200},
            {"http_request_timeout": "invalid_http_timeout"},
        ),
        (
            {"max_concurrent_requests": 0},
            {"max_concurrent_requests": "invalid_max_concurrent_requests"},
        ),
        (
            {"min_request_delay": 0.0},
            {"min_request_delay": "invalid_min_request_delay"},
        ),
        ({"api_user": "  "}, {"api_user": "missing_api_user"}),
        ({"api_secret": ""}, {"api_secret": "missing_api_secret"}),
        (
            {"api_eedomus": False},
            {"base": "no_mode_enabled"},
        ),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("overrides, expected_errors", CASES)
    async def test_invalid_payload_renders_keyed_field_error(
        self, overrides, expected_errors
    ):
        """The exact errors dict is rendered on the re-shown user form."""
        flow = make_flow()

        result = await flow.async_step_user(base_payload(**overrides))

        flow.async_show_form.assert_called_once()
        kwargs = flow.async_show_form.call_args.kwargs
        assert kwargs["step_id"] == "user"
        assert kwargs["errors"] == expected_errors
        assert result == {"type": "form"}


class TestHistoryApiHostPassThrough:
    """The optional history_api_host lands in the created entry's data.

    async_step_user creates the entry with data=user_input verbatim —
    the knob (schema default "") is part of that payload, so the
    E2E-sim harness can supply it through the real flow (story 5.3).
    """

    @pytest.mark.asyncio
    async def test_knob_lands_in_entry_data(self):
        from unittest.mock import AsyncMock

        flow = make_flow()
        flow.validate_input = AsyncMock(return_value={"title": "127.0.0.1:8199"})
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

        result = await flow.async_step_user(
            base_payload(
                api_host="127.0.0.1:8199",
                history_api_host="127.0.0.1:8199",
            )
        )

        assert result == {"type": "create_entry"}
        kwargs = flow.async_create_entry.call_args.kwargs
        assert kwargs["data"]["history_api_host"] == "127.0.0.1:8199"

    @pytest.mark.asyncio
    async def test_empty_knob_lands_as_empty_string(self):
        from unittest.mock import AsyncMock

        flow = make_flow()
        flow.validate_input = AsyncMock(return_value={"title": "box"})
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

        result = await flow.async_step_user(base_payload(history_api_host=""))

        assert result == {"type": "create_entry"}
        kwargs = flow.async_create_entry.call_args.kwargs
        assert kwargs["data"]["history_api_host"] == ""
