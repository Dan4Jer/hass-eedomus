"""Unit tests for the eedomus API client (eedomus_client.py).

Covers: multi-encoding response decoding, secret redaction in logs,
error response formatting, eedomus error handling, and the
set_periph_value success/failure paths.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.eedomus_client import EedomusClient


pytestmark = pytest.mark.unit


def make_config_entry(data=None, options=None):
    """A minimal config entry compatible with _get_config_value."""
    return SimpleNamespace(data=data or {}, options=options or {})


def make_client(data=None, options=None):
    return EedomusClient(
        MagicMock(),
        make_config_entry(
            data={
                "api_user": "user",
                "api_secret": "secret",
                "api_host": "192.168.1.2",
                **(data or {}),
            },
            options=options,
        ),
    )


class TestDecodeResponse:
    def test_utf8(self):
        client = make_client()
        assert client._decode_response("café".encode("utf-8")) == "café"

    def test_latin1_fallback(self):
        """Bytes invalid in utf-8 but valid in latin-1 decode correctly."""
        client = make_client()
        raw = "café".encode("iso-8859-1")  # b'caf\xe9' invalid utf-8
        assert client._decode_response(raw) == "café"

    def test_undecodable_in_utf8_still_decodes(self):
        """All byte sequences decode: single-byte encodings (latin-1)
        accept every byte value, so the replacement path is a last
        resort that in practice is never reached."""
        client = make_client()
        raw = b"\xfe\xff\xfa"
        result = client._decode_response(raw)
        assert isinstance(result, str)
        assert len(result) == 3


class TestSecretRedaction:
    def test_safe_url_strips_query(self):
        client = make_client()
        client.url = "http://192.168.1.2/api/get?action=periph.value&api_user=user&api_secret=secret"
        assert client._get_safe_url_for_logging() == "http://192.168.1.2/api/get"
        assert "api_secret" not in client._get_safe_url_for_logging()

    def test_safe_url_without_query(self):
        client = make_client()
        client.url = "http://192.168.1.2/api/get"
        assert client._get_safe_url_for_logging() == client.url

    def test_safe_url_strips_script_query(self):
        """URLs with a query part are stripped entirely (conservative)."""
        client = make_client()
        client.url = "http://192.168.1.2/script/?exec=fallback.php"
        assert client._get_safe_url_for_logging() == "http://192.168.1.2/script/"

    def test_safe_params_redacts_credentials(self):
        client = make_client()
        client.params = {"api_user": "user", "api_secret": "secret", "periph_id": "123"}
        safe = client._get_safe_params_for_logging()
        assert safe["api_user"] == "***redacted***"
        assert safe["api_secret"] == "***redacted***"
        assert safe["periph_id"] == "123"

    def test_safe_params_non_dict(self):
        client = make_client()
        client.params = None
        assert client._get_safe_params_for_logging() == {}


class TestErrorFormatting:
    def test_format_error_response_basic(self):
        client = make_client()
        result = client._format_error_response("Boom")
        assert result == {"success": 0, "error": "Boom"}

    def test_format_error_response_full(self):
        client = make_client()
        result = client._format_error_response("Boom", raw_response="raw", http_status=500)
        assert result["success"] == 0
        assert result["error"] == "Boom"
        assert result["http_status"] == 500
        assert result["raw_response"] == "raw"


class TestEedomusErrorHandling:
    def test_known_error_code_translated(self):
        """A known eedomus error code is translated to its message."""
        client = make_client()
        response = {
            "success": 0,
            "body": {"error_code": 6, "error_msg": "Unknown peripheral value"},
        }
        result = client._handle_eedomus_error(response)
        assert result["success"] == 0
        assert result["error_code"] == 6
        assert "code: 6" in result["error"]

    def test_unknown_error_keeps_message(self):
        client = make_client()
        response = {
            "success": 0,
            "body": {"error_code": 999, "error_msg": "Something odd"},
        }
        result = client._handle_eedomus_error(response)
        assert "Something odd" in result["error"]

    def test_missing_body_defaults(self):
        client = make_client()
        result = client._handle_eedomus_error({"success": 0})
        assert result["success"] == 0
        assert result["error"] == "Unknown eedomus error"


class TestSetPeriphValue:
    @pytest.mark.asyncio
    async def test_success_normalizes_body_result(self):
        client = make_client()
        client.fetch_data = AsyncMock(
            return_value={"success": 1, "body": {"result": "OK done"}}
        )
        result = await client.set_periph_value("3485837", "100")
        client.fetch_data.assert_awaited_once_with(
            "periph.value", {"periph_id": "3485837", "value": "100"}, use_set=True
        )
        assert result["success"] == 1
        assert result["message"] == "OK done"

    @pytest.mark.asyncio
    async def test_api_error_is_returned(self):
        """An API error (success=0) propagates without exceptions."""
        client = make_client()
        error = {
            "success": 0,
            "error": "Unknown peripheral value (code: 6)",
            "error_code": 6,
        }
        client.fetch_data = AsyncMock(return_value=error)
        result = await client.set_periph_value("3485837", "off")
        assert result["success"] == 0
        assert result["error_code"] == 6

    @pytest.mark.asyncio
    async def test_non_dict_result_passed_through(self):
        client = make_client()
        client.fetch_data = AsyncMock(return_value="garbage")
        result = await client.set_periph_value("1", "1")
        assert result == "garbage"


class TestHistoryEndpointResolution:
    """The history endpoint honors the history_api_host override.

    Default (empty/unset): the eedomus cloud — the real box does not
    serve periph.history locally (verified 2026-10-09). The simulated
    box of the E2E-sim strate points the knob at the local simulator
    (spec-eedomus-simulator, story 5.3).
    """

    @pytest.mark.asyncio
    async def test_history_defaults_to_the_cloud(self):
        client = make_client()
        client.fetch_data = AsyncMock(return_value={"success": 0})
        await client.get_device_history("123")
        url = client.fetch_data.call_args.kwargs["url"]
        assert url == "https://api.eedomus.com/get"

    @pytest.mark.asyncio
    async def test_history_api_host_routes_to_the_override(self):
        client = make_client(data={"history_api_host": "127.0.0.1:8199"})
        client.fetch_data = AsyncMock(return_value={"success": 0})
        await client.get_device_history("123")
        url = client.fetch_data.call_args.kwargs["url"]
        assert url == "http://127.0.0.1:8199/api/get"

    def test_empty_history_api_host_resolves_to_none(self):
        client = make_client(data={"history_api_host": ""})
        assert client.history_api_host is None

    def test_absent_history_api_host_resolves_to_none(self):
        client = make_client()
        assert client.history_api_host is None
