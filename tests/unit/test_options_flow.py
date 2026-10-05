"""Unit tests for the options flow (options_flow.py).

Regression tests for the bug fixed in commits 69ed3f4..2e6b6b3:
submitting the options form used a nonexistent API
('OptionsFlowManager' object has no attribute 'async_update_entry')
and options were never saved.

The correct behavior: submitting user_input calls
self.async_create_entry(data=<options dict>).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.options_flow import EedomusOptionsFlow


pytestmark = pytest.mark.unit


def make_flow(options=None, data=None):
    flow = EedomusOptionsFlow(SimpleNamespace(data=data or {}, options=options or {}))
    # In real HA, OptionsFlow.config_entry is set by the framework.
    flow.config_entry = SimpleNamespace(data=data or {}, options=options or {})
    flow.hass = MagicMock()
    return flow


def capture_create_entry(flow):
    """Patch async_create_entry and return the mock."""
    mock = MagicMock(return_value={"type": "create_entry"})
    flow.async_create_entry = mock
    return mock


class TestAsyncStepInitSubmit:
    @pytest.mark.asyncio
    async def test_submit_calls_async_create_entry_with_data(self):
        """The fix: submit must call async_create_entry(data=options)."""
        flow = make_flow(options={"scan_interval": 300})
        mock = capture_create_entry(flow)

        result = await flow.async_step_init(user_input={"scan_interval": 600})

        mock.assert_called_once()
        kwargs = mock.call_args.kwargs
        assert "data" in kwargs, "options must be passed via the data parameter"
        assert kwargs["data"]["scan_interval"] == 600

    @pytest.mark.asyncio
    async def test_submit_does_not_use_forbidden_apis(self):
        """Regression: the old code called nonexistent APIs and crashed.

        If the flow were to call self.async_update_entry or
        self.hass.config_entries.options.async_update_entry, Python
        would raise AttributeError - the test would fail loudly.
        """
        flow = make_flow(options={})
        capture_create_entry(flow)

        # No AttributeError raised = the forbidden code path is not used
        await flow.async_step_init(user_input={})

    @pytest.mark.asyncio
    async def test_submit_builds_full_options_dict(self):
        """All supported options are present in the saved dict."""
        flow = make_flow(options={})
        mock = capture_create_entry(flow)

        await flow.async_step_init(
            user_input={"scan_interval": 120, "history": True}
        )

        data = mock.call_args.kwargs["data"]
        expected_keys = {
            "api_eedomus", "enable_api_proxy", "history",
            "history_peripherals_per_scan", "scan_interval",
            "enable_set_value_retry", "enable_webhook",
            "api_proxy_disable_security", "php_fallback_enabled",
            "php_fallback_script_name", "php_fallback_timeout",
            "http_request_timeout",
        }
        assert expected_keys.issubset(data.keys()), (
            f"Missing options: {expected_keys - set(data.keys())}"
        )
        assert data["scan_interval"] == 120
        assert data["history"] is True

    @pytest.mark.asyncio
    async def test_submit_falls_back_to_current_config(self):
        """Unspecified fields keep their current value."""
        flow = make_flow(options={"scan_interval": 300, "history": False})
        mock = capture_create_entry(flow)

        await flow.async_step_init(user_input={"scan_interval": 600})

        data = mock.call_args.kwargs["data"]
        assert data["scan_interval"] == 600
        assert data["history"] is False


class TestAsyncStepInitForm:
    @pytest.mark.asyncio
    async def test_no_input_shows_form(self):
        flow = make_flow(options={"scan_interval": 300})
        form_result = {"type": "form", "step_id": "init"}
        flow.async_show_form = MagicMock(return_value=form_result)

        result = await flow.async_step_init(user_input=None)

        assert result == form_result
        flow.async_show_form.assert_called_once()
        call_kwargs = flow.async_show_form.call_args.kwargs
        assert call_kwargs["step_id"] == "init"
        # Form defaults reflect current config
        schema = call_kwargs["data_schema"]
        schema_dict = dict(schema.schema)
        vol_keys = [str(getattr(k, "schema", k)) for k in schema_dict]
        assert "scan_interval" in vol_keys


class TestCopyConfigToOptions:
    def test_copies_data_values_not_in_options(self):
        flow = make_flow(options={}, data={"scan_interval": 300, "history": True})
        result = flow._copy_config_to_options()
        assert result["scan_interval"] == 300
        assert result["history"] is True

    def test_options_take_precedence_over_data(self):
        flow = make_flow(
            options={"scan_interval": 120}, data={"scan_interval": 300}
        )
        result = flow._copy_config_to_options()
        assert result["scan_interval"] == 120

    def test_defaults_when_empty(self):
        flow = make_flow(options={}, data={})
        result = flow._copy_config_to_options()
        assert result["api_eedomus"] is True
        assert result["enable_api_proxy"] is False
        assert result["history"] is False
        assert result["scan_interval"] == 300
        assert result["http_request_timeout"] == 10


def make_yaml_flow(options=None, data=None):
    """Flow whose hass mock runs executor jobs synchronously.

    The yaml_editor step loads translations and the current YAML through
    hass.async_add_executor_job (awaited), so the mock must be awaitable
    and invoke the submitted job.
    """
    flow = make_flow(options=options, data=data)
    flow.hass.config.language = "en"
    flow.hass.async_add_executor_job = AsyncMock(
        side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)
    )
    return flow


def capture_show_form(flow):
    """Patch async_show_form and return (result, mock)."""
    form_result = {"type": "form", "step_id": "yaml_editor"}
    flow.async_show_form = MagicMock(return_value=form_result)
    return form_result, flow.async_show_form


class TestAsyncStepYamlEditor:
    @pytest.mark.asyncio
    async def test_preview_path_shows_form_with_translated_status(self):
        """Valid YAML preview: no errors, placeholders carry the preview."""
        flow = make_yaml_flow()
        form_result, show_form = capture_show_form(flow)

        result = await flow.async_step_yaml_editor(
            user_input={"action": "preview", "yaml_content": "custom_rules: []"}
        )

        assert result is form_result
        kwargs = show_form.call_args.kwargs
        assert kwargs["step_id"] == "yaml_editor"
        assert kwargs["errors"] == {}
        placeholders = kwargs["description_placeholders"]
        assert "```yaml\ncustom_rules: []\n```" == placeholders["preview_content"]
        # Translated status (options.step.yaml_editor.status_valid)
        assert placeholders["preview_status"] == "✅ YAML is valid"
        assert placeholders["helper"]

    @pytest.mark.asyncio
    async def test_invalid_yaml_preview_sets_invalid_yaml_error(self):
        """Invalid YAML preview: errors == {"base": "invalid_yaml"}."""
        flow = make_yaml_flow()
        form_result, show_form = capture_show_form(flow)

        result = await flow.async_step_yaml_editor(
            user_input={"action": "preview", "yaml_content": "custom_rules: ["}
        )

        assert result is form_result
        kwargs = show_form.call_args.kwargs
        assert kwargs["errors"] == {"base": "invalid_yaml"}
        placeholders = kwargs["description_placeholders"]
        assert placeholders["error"]
        assert placeholders["preview_status"]
        assert "preview_content" in placeholders

    @pytest.mark.asyncio
    async def test_failed_save_shows_form_with_error_placeholder(self):
        """A save that fails validation re-displays the form with the error."""
        flow = make_yaml_flow()
        form_result, show_form = capture_show_form(flow)

        result = await flow.async_step_yaml_editor(
            user_input={"yaml_content": "custom_rules: ["}
        )

        assert result is form_result
        kwargs = show_form.call_args.kwargs
        assert kwargs["errors"] == {"base": "invalid_yaml"}
        placeholders = kwargs["description_placeholders"]
        assert placeholders["error"]
        assert placeholders["preview_content"]
        assert "preview_status" in placeholders


class TestFrRegionNormalization:
    """fr-FR (a region subtag) resolves the fr tree, not the en fallback.

    async_get_translations strips the region before looking for the
    language file: a regression would silently render the YAML editor
    in English for every fr-FR/fr-CA user.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("language", ["fr-FR", "fr-CA"])
    async def test_fr_language_yields_french_placeholders(self, language):
        """Same flow as the EN tests, only the language changes."""
        flow = make_yaml_flow()
        flow.hass.config.language = language
        form_result, show_form = capture_show_form(flow)

        result = await flow.async_step_yaml_editor(
            user_input={"action": "preview", "yaml_content": "custom_rules: []"}
        )

        assert result is form_result
        placeholders = show_form.call_args.kwargs["description_placeholders"]
        assert placeholders["preview_status"] == "✅ YAML valide"
        assert placeholders["helper"] == (
            "Modifiez le YAML ci-dessous. Cliquez sur « Prévisualiser » "
            "pour valider avant d'enregistrer."
        )
        assert placeholders["description"] == (
            "Modifiez la configuration de l'intégration eedomus "
            "directement en YAML."
        )
