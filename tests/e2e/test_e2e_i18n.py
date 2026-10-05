"""E2E i18n tests for the panel translation catalog on the live instance (7).

Calls the live ``eedomus/get_translations`` websocket command for "en" and
"fr" and validates the served catalogs against ``tests/fixtures/
panel-catalog.json`` - the drift-checked source of truth for the expected
key set, placeholders and VALUES. An uncovered locale must fall back to
the English tree, a regional locale must normalize to its base, and an
explicit null locale must serve English (CAP-3 contract).

These tests run ONLY against the deployed instance (no mocks, live
websocket): the local build verifies collection, the orchestrator runs
the suite after deployment.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

CATALOG_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "panel-catalog.json"
PLACEHOLDER_RE = re.compile(r"{([a-zA-Z_][a-zA-Z0-9_]*)}")

MAX_REPORTED_DRIFTS = 10


@lru_cache(maxsize=1)
def _expected_catalog():
    """The expected en/fr trees, read once from the fixture (readable,
    named failure when the fixture is missing or unreadable)."""
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as err:
        pytest.fail(
            f"panel catalog fixture missing or unreadable: {CATALOG_PATH} ({err})",
            pytrace=False,
        )


def _placeholders(text):
    return set(PLACEHOLDER_RE.findall(str(text)))


def _assert_matches_fixture(live, expected, label):
    """Full VALUE equality with a named diff localizing the drift."""
    problems = []
    for key in sorted(set(live) | set(expected)):
        live_value = live.get(key)
        expected_value = expected.get(key)
        if live_value != expected_value:
            problems.append(f"{key}: live={live_value!r} expected={expected_value!r}")
    if problems:
        shown = "\n".join(problems[:MAX_REPORTED_DRIFTS])
        hidden = len(problems) - MAX_REPORTED_DRIFTS
        suffix = f"\n... and {hidden} more" if hidden > 0 else ""
        pytest.fail(
            f"{label} live catalog drifts from the fixture "
            f"({len(problems)} key(s)):\n{shown}{suffix}",
            pytrace=False,
        )


class TestGetTranslations:
    def test_en_serves_the_full_non_empty_catalog(self, ws_call):
        expected = _expected_catalog()["en"]
        result = ws_call("eedomus/get_translations", {"locale": "en"})
        assert result["locale"] == "en"
        translations = result["translations"]
        # The key count (144 today) is read from the fixture, not hardcoded,
        # so adding the next key only touches the fixture.
        assert len(translations) == len(expected)
        assert set(translations) == set(expected)
        empty = sorted(k for k, v in translations.items() if not str(v).strip())
        assert not empty, f"empty EN values served: {empty}"
        _assert_matches_fixture(translations, expected, "EN")

    def test_fr_serves_the_full_non_empty_catalog(self, ws_call):
        expected = _expected_catalog()["fr"]
        result = ws_call("eedomus/get_translations", {"locale": "fr"})
        assert result["locale"] == "fr"
        translations = result["translations"]
        assert len(translations) == len(expected)
        assert set(translations) == set(expected)
        empty = sorted(k for k, v in translations.items() if not str(v).strip())
        assert not empty, f"empty FR values served: {empty}"
        _assert_matches_fixture(translations, expected, "FR")

    def test_en_fr_key_parity(self, ws_call):
        en = ws_call("eedomus/get_translations", {"locale": "en"})["translations"]
        fr = ws_call("eedomus/get_translations", {"locale": "fr"})["translations"]
        en_keys, fr_keys = set(en), set(fr)
        missing_in_fr = sorted(en_keys - fr_keys)
        missing_in_en = sorted(fr_keys - en_keys)
        assert not missing_in_fr, f"keys missing from the FR tree: {missing_in_fr}"
        assert not missing_in_en, f"keys missing from the EN tree: {missing_in_en}"

    def test_en_fr_placeholder_parity_per_key(self, ws_call):
        en = ws_call("eedomus/get_translations", {"locale": "en"})["translations"]
        fr = ws_call("eedomus/get_translations", {"locale": "fr"})["translations"]
        mismatches = {}
        for key in sorted(en):
            en_ph = _placeholders(en[key])
            fr_ph = _placeholders(fr[key])
            if en_ph != fr_ph:
                mismatches[key] = {"en": sorted(en_ph), "fr": sorted(fr_ph)}
        assert not mismatches, f"placeholder parity breaks: {mismatches}"

    def test_uncovered_locale_falls_back_to_english(self, ws_call):
        """Contract 3.2: a locale without a tree serves the EN catalog."""
        en = ws_call("eedomus/get_translations", {"locale": "en"})
        de = ws_call("eedomus/get_translations", {"locale": "de"})
        assert de["locale"] == "en"
        assert de["translations"] == en["translations"]

    def test_regional_locale_normalizes_to_base(self, ws_call):
        """Contract 3.2: "fr-FR" is normalized to the base FR tree."""
        expected = _expected_catalog()["fr"]
        result = ws_call("eedomus/get_translations", {"locale": "fr-FR"})
        assert result["locale"] == "fr"
        _assert_matches_fixture(result["translations"], expected, "fr-FR")

    def test_null_locale_serves_the_english_tree(self, ws_call):
        """Contract 3.2: an explicit null locale serves the EN catalog."""
        expected = _expected_catalog()["en"]
        result = ws_call("eedomus/get_translations", {"locale": None})
        assert result["locale"] == "en"
        _assert_matches_fixture(result["translations"], expected, "null locale")
