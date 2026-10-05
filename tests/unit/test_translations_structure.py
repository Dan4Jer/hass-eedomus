"""Structural identity tests for the eedomus translation trees (CAP-2).

strings.json is the EN source of truth (HA grammar), translations/en.json
is its exact compilation (copy), translations/fr.json is the FR mirror.
The three trees must stay structurally identical:

- en.json and fr.json have the same recursive leaf key sets;
- every leaf carries the same {placeholder} set in both languages;
- strings.json leaf keys AND values are identical to en.json;
- the services section matches the services.yaml declaration (service
  and field names), with the 4 documented services and the set_value
  fields device_id/value;
- the entity (translated name fallbacks) and ui (legacy options UI)
  sections exist in the three files.

Run: python3 -m pytest tests/unit/test_translations_structure.py
"""

import json
import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

COMPONENT_DIR = Path(__file__).resolve().parents[2] / "custom_components/eedomus"

STRINGS_PATH = COMPONENT_DIR / "strings.json"
EN_PATH = COMPONENT_DIR / "translations" / "en.json"
FR_PATH = COMPONENT_DIR / "translations" / "fr.json"
SERVICES_YAML_PATH = COMPONENT_DIR / "services.yaml"
SERVICES_PY_PATH = COMPONENT_DIR / "services.py"
CONFIG_FLOW_PATH = COMPONENT_DIR / "config_flow.py"
OPTIONS_FLOW_PATH = COMPONENT_DIR / "options_flow.py"
CONST_PATH = COMPONENT_DIR / "const.py"


def _declared_services():
    """The expected service set, derived from the services.yaml declaration."""
    with open(SERVICES_YAML_PATH, "r", encoding="utf-8") as f:
        return set(yaml.safe_load(f))


EXPECTED_ENTITY_PLATFORMS = [
    "binary_sensor",
    "climate",
    "cover",
    "light",
    "select",
    "sensor",
    "switch",
]
EXPECTED_ENTITY_KEYS = ["unknown_device", "unknown_parent"]


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _leaves(tree, prefix=""):
    """Return {dotted.leaf.path: value} for every scalar leaf."""
    leaves = {}
    for key, value in tree.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            leaves.update(_leaves(value, path))
        else:
            leaves[path] = value
    return leaves


def _placeholders(value):
    return set(re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", str(value)))


def _trees():
    """The three trees, labeled, as (label, loaded json) tuples."""
    return (
        ("strings.json", _load(STRINGS_PATH)),
        ("en.json", _load(EN_PATH)),
        ("fr.json", _load(FR_PATH)),
    )


def _source(path):
    return path.read_text(encoding="utf-8")


def _conf_token_map():
    """Map the flow CONF_* identifiers to their option/field id strings.

    Parsed from the source instead of imported: the structure tests
    stay dependency-free (json/yaml/re only, no Home Assistant).
    """
    values = {}
    for path in (CONST_PATH, CONFIG_FLOW_PATH):
        for match in re.finditer(
            r'^(CONF_[A-Z0-9_]+) = "([^"]+)"', _source(path), re.MULTILINE
        ):
            values[match.group(1)] = match.group(2)
    return values


def _vol_marker_args(source):
    """First arguments of every vol.Required/vol.Optional marker.

    Fails loudly when a marker's first argument is neither a quoted
    field id nor a CONF_* token: anything else would be silently
    skipped here, letting a real field ship without its pinned label.
    """
    tokens = _conf_token_map()
    fields = []
    for match in re.finditer(
        r"vol\.(?:Required|Optional)\(\s*([^\s,()]+)", source
    ):
        arg = match.group(1)
        if arg[:1] in ('"', "'"):
            assert len(arg) >= 2 and arg[-1] == arg[0], (
                f"unterminated string argument in a flow schema: {arg!r}"
            )
            fields.append(arg[1:-1])
        elif re.fullmatch(r"CONF_[A-Z0-9_]+", arg):
            assert arg in tokens, f"unknown CONF token in a flow schema: {arg}"
            fields.append(tokens[arg])
        else:
            raise AssertionError(
                f"unsupported first argument {arg!r} in a "
                f"vol.Required/vol.Optional marker: expected a quoted "
                f"field id or a CONF_* token, or the fields pin "
                f"silently skips a real field"
            )
    return fields


def _config_flow_schema_fields():
    """The field ids of the module-level STEP_USER_DATA_SCHEMA."""
    source = _source(CONFIG_FLOW_PATH)
    start = source.index("STEP_USER_DATA_SCHEMA = vol.Schema(")
    end = source.index("\n)\n", start)
    return _vol_marker_args(source[start:end])


def _options_init_schema_fields():
    """The field ids rendered by the options init form."""
    source = _source(OPTIONS_FLOW_PATH)
    start = source.index("async def async_step_init")
    end = source.index("async def _async_yaml_editor_placeholders", start)
    return _vol_marker_args(source[start:end])


def _options_yaml_editor_schema_fields():
    """The field ids rendered by the yaml_editor forms (deduplicated)."""
    source = _source(OPTIONS_FLOW_PATH)
    start = source.index("async def async_step_yaml_editor")
    end = source.index("async def async_load_mapping", start)
    return _vol_marker_args(source[start:end])


def _config_uninstall_schema_fields():
    """The field ids rendered by the uninstall form."""
    source = _source(CONFIG_FLOW_PATH)
    start = source.index("async def async_step_uninstall")
    end = source.index("async def async_step_remove", start)
    return _vol_marker_args(source[start:end])


def _assert_same_keys(reference, candidate, ref_label, cand_label):
    ref_keys = set(reference)
    cand_keys = set(candidate)
    missing = sorted(ref_keys - cand_keys)
    extra = sorted(cand_keys - ref_keys)
    assert not missing and not extra, (
        f"{cand_label} diverges from {ref_label}: "
        f"missing keys {missing}, extra keys {extra}"
    )


class TestEnFrTrees:
    def test_fr_mirrors_en_leaf_keys(self):
        """(a) en.json and fr.json have identical recursive leaf key sets."""
        _assert_same_keys(
            _leaves(_load(EN_PATH)),
            _leaves(_load(FR_PATH)),
            "en.json",
            "fr.json",
        )

    def test_placeholder_parity_per_leaf(self):
        """(b) Each leaf carries the same {placeholder} set in en and fr."""
        en_leaves = _leaves(_load(EN_PATH))
        fr_leaves = _leaves(_load(FR_PATH))
        for key, en_value in en_leaves.items():
            en_placeholders = _placeholders(en_value)
            fr_placeholders = _placeholders(fr_leaves[key])
            assert en_placeholders == fr_placeholders, (
                f"placeholder mismatch on '{key}': en has "
                f"{sorted(en_placeholders)}, fr has {sorted(fr_placeholders)}"
            )


class TestStringsCompilation:
    def test_strings_json_is_en_json_copy(self):
        """(c) strings.json leaf keys AND values identical to en.json."""
        strings_leaves = _leaves(_load(STRINGS_PATH))
        en_leaves = _leaves(_load(EN_PATH))
        _assert_same_keys(strings_leaves, en_leaves, "strings.json", "en.json")
        differing = sorted(
            key for key in strings_leaves if strings_leaves[key] != en_leaves[key]
        )
        assert not differing, (
            f"en.json is not an exact compilation of strings.json, "
            f"values differ on: {differing}"
        )


class TestServicesSection:
    def test_every_declared_service_and_field_exists(self):
        """(d) services.yaml services/fields appear in the three files."""
        with open(SERVICES_YAML_PATH, "r", encoding="utf-8") as f:
            declared = yaml.safe_load(f)
        trees = {
            "strings.json": _load(STRINGS_PATH),
            "en.json": _load(EN_PATH),
            "fr.json": _load(FR_PATH),
        }
        for label, tree in trees.items():
            services = tree.get("services")
            assert isinstance(services, dict), f"{label} has no 'services' section"
            for service, declaration in declared.items():
                assert service in services, (
                    f"service '{service}' from services.yaml missing "
                    f"from the services section of {label}"
                )
                for field in ("name", "description"):
                    assert (
                        field in services[service]
                    ), f"service '{service}' missing '{field}' in {label}"
                declared_fields = declaration.get("fields") or {}
                section_fields = services[service].get("fields") or {}
                for field in declared_fields:
                    assert field in section_fields, (
                        f"field '{field}' of service '{service}' missing "
                        f"from the services section of {label}"
                    )
                    for text in ("name", "description"):
                        assert text in section_fields[field], (
                            f"field '{field}' of service '{service}' missing "
                            f"'{text}' in {label}"
                        )

    def test_services_section_shape(self):
        """(e) Declared services, set_value has fields device_id/value."""
        expected_services = _declared_services()
        for label, tree in (
            ("strings.json", _load(STRINGS_PATH)),
            ("en.json", _load(EN_PATH)),
            ("fr.json", _load(FR_PATH)),
        ):
            services = tree.get("services")
            assert services is not None, f"{label} has no 'services' section"
            assert set(services) == expected_services, (
                f"{label} services section is {sorted(services)}, "
                f"expected {sorted(expected_services)}"
            )
            set_value_fields = set(services["set_value"].get("fields") or {})
            assert set_value_fields == {"device_id", "value"}, (
                f"{label} set_value fields are {sorted(set_value_fields)}, "
                "expected ['device_id', 'value']"
            )


class TestEntityAndUiSections:
    def test_entity_section_present_in_all_three_files(self):
        """(f) entity fallback section exists in strings/en/fr."""
        for label, tree in (
            ("strings.json", _load(STRINGS_PATH)),
            ("en.json", _load(EN_PATH)),
            ("fr.json", _load(FR_PATH)),
        ):
            entity = tree.get("entity")
            assert isinstance(entity, dict), f"{label} has no 'entity' section"
            missing_platforms = [
                platform
                for platform in EXPECTED_ENTITY_PLATFORMS
                if platform not in entity
            ]
            assert not missing_platforms, (
                f"{label} entity section is missing platforms: " f"{missing_platforms}"
            )
            for platform in EXPECTED_ENTITY_PLATFORMS:
                for key in EXPECTED_ENTITY_KEYS:
                    name = entity[platform].get(key, {}).get("name")
                    assert name, f"{label} entity.{platform}.{key}.name is missing"
                    assert "{periph_id}" in name or "{parent_id}" in name, (
                        f"{label} entity.{platform}.{key}.name carries no "
                        "peripheral identifier placeholder"
                    )

    def test_ui_section_present_in_en_and_fr(self):
        """(g) the legacy ui family exists in BOTH en.json and fr.json."""
        for label, path in (("en.json", EN_PATH), ("fr.json", FR_PATH)):
            ui = _load(path).get("ui")
            assert isinstance(ui, dict) and ui, f"{label} has no 'ui' section"
        strings_ui = _leaves(_load(STRINGS_PATH).get("ui", {}))
        en_ui = _leaves(_load(EN_PATH).get("ui", {}))
        _assert_same_keys(strings_ui, en_ui, "strings.json ui", "en.json ui")


class TestExceptionsSection:
    """Every translation_key raised by services.py exists in the trees.

    The keys and placeholders are extracted from the services.py source
    (same extraction style as the services.yaml check), so a raise that
    is added without its exceptions entry fails here.
    """

    RAISE_RE = re.compile(
        r'translation_key="(?P<key>[a-z0-9_]+)",?\s*'
        r'(?:translation_placeholders=\{(?P<placeholders>[^}]*)\})?'
    )

    def _raised_keys(self):
        source = SERVICES_PY_PATH.read_text(encoding="utf-8")
        raised = {}
        for match in self.RAISE_RE.finditer(source):
            key = match.group("key")
            block = match.group("placeholders") or ""
            placeholders = set(re.findall(r'"([a-z_][a-z0-9_]*)":', block))
            raised[key] = placeholders
        assert raised, "no translation_key found in services.py source"
        return raised

    def test_every_raised_key_exists_with_matching_placeholders(self):
        raised = self._raised_keys()
        for label, tree in (
            ("strings.json", _load(STRINGS_PATH)),
            ("en.json", _load(EN_PATH)),
            ("fr.json", _load(FR_PATH)),
        ):
            exceptions = tree.get("exceptions")
            assert isinstance(exceptions, dict), (
                f"{label} has no 'exceptions' section"
            )
            for key, call_placeholders in raised.items():
                assert key in exceptions, (
                    f"translation_key '{key}' raised by services.py missing "
                    f"from the exceptions section of {label}"
                )
                message = exceptions[key].get("message")
                assert message, (
                    f"{label} exceptions.{key}.message is missing"
                )
                message_placeholders = _placeholders(message)
                assert message_placeholders == call_placeholders, (
                    f"{label} exceptions.{key}.message placeholders "
                    f"{sorted(message_placeholders)} do not match the "
                    f"raise's translation_placeholders "
                    f"{sorted(call_placeholders)}"
                )


class TestFlowStepsPresent:
    """The flow steps referenced by the flows exist in the three trees."""

    REQUIRED_KEYS = [
        "config.step.user.title",
        "config.step.user.description",
        "options.step.yaml_editor.description",
        "options.step.init.title",
        "options.step.init.description",
        "options.error.invalid_yaml",
    ]

    def _dig(self, tree, dotted):
        node = tree
        for part in dotted.split("."):
            assert isinstance(node, dict), f"'{dotted}' crosses a non-dict"
            parent = dotted.rsplit(".", 1)[0]
            assert part in node, (
                f"missing translation key '{dotted}' (no '{part}' under "
                f"'{parent}')"
            )
            node = node[part]
        return node

    def test_flow_step_keys_exist_in_all_three_trees(self):
        for label, tree in (
            ("strings.json", _load(STRINGS_PATH)),
            ("en.json", _load(EN_PATH)),
            ("fr.json", _load(FR_PATH)),
        ):
            for dotted in self.REQUIRED_KEYS:
                value = self._dig(tree, dotted)
                assert value, f"{label} '{dotted}' is empty"


class TestEnTreeLanguage:
    """No EN-tree value may carry French.

    The committed guards cannot see this hole: they compare the trees
    with each other, never the language of the values, so a French
    value in strings.json/en.json (the title regression found by the
    epic retrospective) ships to English users unnoticed. Two signal
    channels, because the motivating regression (« Connexion Eedomus »)
    carries neither an accent nor a guillemet:
    - markers: accented Latin letters, guillemets, Œ/œ and the
      typographic apostrophe;
    - FR lexicon: accent-free French words that never appear in an
      English value (checked case-insensitively).
    Named exemption: the language token 'Français' of the
    documentation links in config.step.user.description.
    """

    MARKER_RE = re.compile("[À-ÖØ-öø-ÿŒœ«»’]")
    EXEMPT_TOKENS = ("Français",)
    FR_LEXICON = (
        "connexion",
        "activer",
        "parametres",
        "peripherique",
        "sauvegarde",
        "veuillez",
        "echec",
        "reessayer",
    )

    def test_en_values_carry_no_french_marker(self):
        for label, path in (("strings.json", STRINGS_PATH), ("en.json", EN_PATH)):
            for key, value in _leaves(_load(path)).items():
                text = str(value)
                for token in self.EXEMPT_TOKENS:
                    text = text.replace(token, "")
                marker = self.MARKER_RE.search(text)
                assert marker is None, (
                    f"{label} value of '{key}' carries the French "
                    f"marker {marker.group(0)!r} in "
                    f"{str(value)[:60]!r}: EN-tree values are English"
                )
                word = next(
                    (w for w in self.FR_LEXICON if w in text.lower()), None
                )
                assert word is None, (
                    f"{label} value of '{key}' carries the French word "
                    f"'{word}' in {str(value)[:60]!r}: "
                    f"EN-tree values are English"
                )


class TestConfigFlowSection:
    """The config-flow contract is pinned to the translation trees.

    - STEP_USER_DATA_SCHEMA field ids == config.step.user.data keys on
      the three trees: a field added or renamed without its label
      fails here;
    - every error key the flow can set (errors = {"base": ...} or a
      keyed EedomusValidationError) exists in config.error on the
      three trees: the form never renders a raw voluptuous message.
    """

    BASE_ERROR_RE = re.compile(
        r'errors\s*=\s*\{\s*["\']base["\']\s*:\s*["\']([a-z_]+)["\']\s*\}'
    )
    ERROR_KEY_RE = re.compile(r'error_key=["\']([a-z_]+)["\']')

    def test_step_user_fields_match_data_labels(self):
        fields = _config_flow_schema_fields()
        assert fields, "STEP_USER_DATA_SCHEMA not found in config_flow.py"
        assert len(fields) == len(set(fields)), (
            f"duplicated field in STEP_USER_DATA_SCHEMA: {fields}"
        )
        for label, tree in _trees():
            data = tree["config"]["step"]["user"]["data"]
            missing = sorted(set(fields) - set(data))
            extra = sorted(set(data) - set(fields))
            assert not missing and not extra, (
                f"{label}: config.step.user.data diverges from "
                f"STEP_USER_DATA_SCHEMA — fields without a label: "
                f"{missing}, labels without a field: {extra}"
            )

    def test_error_keys_set_by_the_flow_exist(self):
        source = _source(CONFIG_FLOW_PATH)
        keys = set(self.BASE_ERROR_RE.findall(source)) | set(
            self.ERROR_KEY_RE.findall(source)
        )
        assert keys, "no error key found in the config_flow.py source"
        for label, tree in _trees():
            errors = tree["config"]["error"]
            for key in sorted(keys):
                assert key in errors, (
                    f"error key '{key}' set by config_flow.py is missing "
                    f"from the config.error section of {label}"
                )

    def test_step_uninstall_fields_match_data_labels(self):
        fields = _config_uninstall_schema_fields()
        assert fields == ["remove_entities"], (
            f"the uninstall form renders unexpected fields: {fields}"
        )
        for label, tree in _trees():
            data = tree["config"]["step"]["uninstall"].get("data") or {}
            missing = sorted(set(fields) - set(data))
            extra = sorted(set(data) - set(fields))
            assert not missing and not extra, (
                f"{label}: config.step.uninstall.data diverges from "
                f"the uninstall form schema — fields without a label: "
                f"{missing}, labels without a field: {extra}"
            )


class TestOptionsFlowSection:
    """The options form fields are pinned to options.step.*.data.

    Every field rendered by the options init form carries a label in
    the options.step.init.data section of the three trees, every
    field rendered by the yaml_editor forms one in
    options.step.yaml_editor.data, and every error key the options
    flow sets exists in options.error.
    """

    BASE_ERROR_RE = re.compile(
        r'errors\[\s*["\']base["\']\s*\]\s*=\s*["\']([a-z_]+)["\']'
    )

    def test_init_fields_match_data_labels(self):
        fields = _options_init_schema_fields()
        assert fields, "options init schema not found in options_flow.py"
        assert len(fields) == len(set(fields)), (
            f"duplicated field in the options init schema: {fields}"
        )
        for label, tree in _trees():
            data = tree["options"]["step"]["init"].get("data") or {}
            missing = sorted(set(fields) - set(data))
            extra = sorted(set(data) - set(fields))
            assert not missing and not extra, (
                f"{label}: options.step.init.data diverges from the "
                f"options form schema — fields without a label: "
                f"{missing}, labels without a field: {extra}"
            )

    def test_yaml_editor_fields_match_data_labels(self):
        fields = _options_yaml_editor_schema_fields()
        assert fields, "options yaml_editor schema not found in options_flow.py"
        fields = set(fields)
        for label, tree in _trees():
            data = tree["options"]["step"]["yaml_editor"].get("data") or {}
            missing = sorted(fields - set(data))
            extra = sorted(set(data) - fields)
            assert not missing and not extra, (
                f"{label}: options.step.yaml_editor.data diverges from "
                f"the yaml_editor form schema — fields without a "
                f"label: {missing}, labels without a field: {extra}"
            )

    def test_error_keys_set_by_the_flow_exist(self):
        source = _source(OPTIONS_FLOW_PATH)
        keys = set(self.BASE_ERROR_RE.findall(source))
        assert keys, "no errors[base] assignment found in options_flow.py"
        for label, tree in _trees():
            errors = tree["options"]["error"]
            for key in sorted(keys):
                assert key in errors, (
                    f"error key '{key}' set by options_flow.py is missing "
                    f"from the options.error section of {label}"
                )
