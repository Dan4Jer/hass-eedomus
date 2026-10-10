"""Unit tests for the simulator dump catalog generator (ticket 114).

03_catalog.py computes CATALOG.md statically from the shipped dump
and the integration's device_mapping.yaml. These tests pin the
catalog's consistency: every "missing" id is handled in the YAML map,
climate and the parent/child color structure rank in the top priority
tier, regeneration is byte-stable, and the committed CATALOG.md
never drifts from the generation.
"""

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SIM_DIR = Path(__file__).resolve().parents[2] / "scripts" / "simulateur"
DUMP_FILE = SIM_DIR / "eedomus_dump.json"
MAPPING_FILE = (
    SIM_DIR.parents[1]
    / "custom_components"
    / "eedomus"
    / "config"
    / "device_mapping.yaml"
)
COMMITTED_CATALOG = SIM_DIR / "CATALOG.md"


def _load_catalog_module():
    """Import 03_catalog.py as a module (argparse lives in main())."""
    spec = importlib.util.spec_from_file_location(
        "eedomus_catalog", SIM_DIR / "03_catalog.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def catalog():
    return _load_catalog_module()


@pytest.fixture(scope="module")
def analysis(catalog):
    dump = json.loads(DUMP_FILE.read_text(encoding="utf-8"))
    mapping = catalog.load_mapping(MAPPING_FILE)
    return catalog.analyze(dump, mapping)


def test_every_missing_id_is_handled(analysis):
    """A "missing" row must always exist in the YAML usage map."""
    handled = set(analysis["handled"])
    assert analysis["missing"], "the shipped dump covers everything?"
    for row in analysis["missing"]:
        assert row["usage_id"] in handled


def test_climate_usage_ids_rank_in_top_tier(analysis):
    """Climate is dead in the e2e_sim strate — 15/19/20/38 rank first."""
    climate_rows = [row for row in analysis["missing"] if row["platform"] == "climate"]
    assert {row["usage_id"] for row in climate_rows} == {"15", "19", "20", "38"}
    assert all(row["priority"] == 1 for row in climate_rows)


def test_rgbw_parent_child_gap_ranks_in_top_tier(analysis):
    """The RGBW parent/child color structure is a tier-1 gap."""
    gaps = {gap["id"]: gap for gap in analysis["structural_gaps"]}
    assert gaps["rgbw-light"]["priority"] == 1
    assert gaps["rgbw-light"]["status"] == "unreachable"


def test_cover_platform_gap_ranks_in_top_tier(analysis):
    """The cover platform (usage 48) is unreachable — tier 1."""
    gaps = {gap["id"]: gap for gap in analysis["structural_gaps"]}
    assert gaps["cover-slats"]["priority"] == 1
    assert gaps["cover-slats"]["status"] == "unreachable"


def test_unmapped_present_ids_are_reported(analysis):
    """The dump's unmapped usage ids show up in section 2."""
    assert {row["usage_id"] for row in analysis["unmapped"]} == {
        "16",
        "32",
        "41",
        "119",
    }


def test_dangling_button_mapping_is_flagged(analysis):
    """usage 127 maps to button/... but no button.py exists."""
    assert [entry["usage_id"] for entry in analysis["dangling"]] == ["127"]


def test_thermostat_setpoint_never_becomes_climate(analysis):
    """The shipped thermostat rule produces no climate entity."""
    finding = next(
        f
        for f in analysis["findings"]
        if "never becomes a climate entity" in f["finding"]
    )
    assert "mapped to switch" in finding["detail"]


def test_generation_is_byte_stable(catalog):
    """Same inputs render identical content — twice, and via main()."""
    first = catalog.build(DUMP_FILE, MAPPING_FILE)
    second = catalog.build(DUMP_FILE, MAPPING_FILE)
    assert first == second
    assert first.endswith("\n")


def test_main_rewrites_identical_output(catalog, tmp_path):
    out1 = tmp_path / "catalog1.md"
    out2 = tmp_path / "catalog2.md"
    assert catalog.main(["-o", str(out1)]) == 0
    assert catalog.main(["-o", str(out2)]) == 0
    assert out1.read_bytes() == out2.read_bytes()

    # --check passes on a fresh write, fails on drift.
    assert catalog.main(["-o", str(out1), "--check"]) == 0
    out1.write_text("drifted", encoding="utf-8")
    assert catalog.main(["-o", str(out1), "--check"]) == 1


def test_committed_catalog_matches_generation(catalog):
    """CATALOG.md in the repo is exactly what the generator emits."""
    generated = catalog.build(DUMP_FILE, MAPPING_FILE)
    committed = COMMITTED_CATALOG.read_text(encoding="utf-8")
    assert committed == generated


def test_enriched_dump_shrinks_the_missing_list(catalog):
    """A future dump with a climate periph drops its missing row."""
    dump = json.loads(DUMP_FILE.read_text(encoding="utf-8"))
    dump["periph_list"].append(
        {
            "periph_id": "heating-1",
            "parent_periph_id": "",
            "name": "Heating fixture",
            "usage_id": "38",
            "usage_name": "Chauffage",
            "value_type": "list",
        }
    )
    mapping = catalog.load_mapping(MAPPING_FILE)
    result = catalog.analyze(dump, mapping)
    assert "38" not in {row["usage_id"] for row in result["missing"]}
    # No new unmapped id appears: 38 is handled.
    assert "38" not in {row["usage_id"] for row in result["unmapped"]}


def test_missing_usage_id_mappings_fails_loud(catalog, tmp_path):
    """device_mapping.yaml without usage_id_mappings: error, exit 1."""
    bad_mapping = tmp_path / "bad_mapping.yaml"
    bad_mapping.write_text("metadata:\n  version: 1\n", encoding="utf-8")
    with pytest.raises(catalog.CatalogError):
        catalog.load_mapping(bad_mapping)

    out = tmp_path / "catalog.md"
    exit_code = catalog.main(
        [
            "--dump-file",
            str(DUMP_FILE),
            "--mapping-file",
            str(bad_mapping),
            "-o",
            str(out),
        ]
    )
    assert exit_code == 1
    assert not out.exists(), "no partial catalog on failure"
