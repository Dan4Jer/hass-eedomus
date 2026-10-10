"""Guard: no French in the Python source outside named exemptions (7).

The i18n epic moved every log message, docstring and comment of the
integration to English (rule 3.5). This guard keeps it that way: it scans
every line of ``custom_components/eedomus/**/*.py`` for French signals -
accented characters, guillemets and a small French lexicon - and fails
loudly with file:line on any hit outside the EXPLICIT exemption list
below. The scan covers all lines (stricter than only logs, docstrings
and comments) so a French literal in a code string is caught too; the
known French data literals are exactly what the exemptions name.

An exempted literal is REMOVED from its line before the indicators run,
so French added beside an exemption (co-location) still fails; only the
named literal itself is tolerated. The committed self-test plants
French into a tmp_path tree to keep that property proven.

Frozen trees are excluded wholesale: ``translations/`` and
``panel_translations.py`` are the translation catalogs themselves.

Run: python3 -m pytest tests/unit/test_no_french_source.py
"""

import re
from pathlib import Path
from typing import List, NamedTuple

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / "custom_components" / "eedomus"

EXCLUDED_DIRS = ("translations",)
EXCLUDED_FILES = ("panel_translations.py",)

# French signals: accented characters and guillemets. Curly quotes,
# em-dashes, ellipses and emoji are legitimate English/unicode typography
# and deliberately NOT flagged.
ACCENTED_CHARS = "àâäçéèêëîïôöùûüÿœÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒ"
ACCENT_RE = re.compile("[" + ACCENTED_CHARS + "]")
GUILLEMET_RE = re.compile(r"[«»]")
# Small French lexicon (word-bounded, case-insensitive): function words
# and domain words that do not occur in English. Catches accent-free
# French such as "Sauvegarde du mapping". Deliberately minimal: "est",
# "champ" and "gel" were dropped - they false-positive on legitimate
# English (the timezone abbreviation; "Hors Gel" is covered by its
# full-literal exemption).
FRENCH_LEXICON = [
    "le",
    "la",
    "les",
    "des",
    "du",
    "une",
    "pas",
    "avec",
    "pour",
    "dans",
    "cette",
    "que",
    "qui",
    "sur",
    "au",
    "vous",
    "nous",
    "être",
    "échec",
    "erreur",
    "inconnu",
    "inconnue",
    "aucun",
    "aucune",
    "veuillez",
    "sauvegarde",
    "fichier",
    "valider",
    "échoué",
    "libre",
    "espace",
    "porte",
    "fenêtre",
    "fumée",
    "présence",
    "arrêt",
    "désactiver",
    "confort",
    "hors",
    "arret",
]
LEXICON_RE = re.compile(r"\b(" + "|".join(FRENCH_LEXICON) + r")\b", re.IGNORECASE)

# The integration ships far more files; a smaller count means SOURCE_DIR
# moved and the scan would silently guard nothing.
MIN_SCANNED_FILES = 20


class Exemption(NamedTuple):
    """One named, documented French literal allowed in one file."""

    file: str  # full repo-relative path
    literal: str
    reason: str


# EXPLICIT exemption list: file + literal + reason. Every entry is
# drift-checked (test_exemptions_still_apply) - a stale literal fails the
# guard instead of silently rotting. Anything French outside these
# literals must fail.
EXEMPTIONS: List[Exemption] = [
    Exemption(
        file="custom_components/eedomus/binary_sensor.py",
        literal='"porte"',
        reason="data matcher: eedomus device names are French (door)",
    ),
    Exemption(
        file="custom_components/eedomus/binary_sensor.py",
        literal='"fenêtre"',
        reason="data matcher: eedomus device names are French (window)",
    ),
    Exemption(
        file="custom_components/eedomus/binary_sensor.py",
        literal='"fumée"',
        reason="data matcher: eedomus device names are French (smoke)",
    ),
    Exemption(
        file="custom_components/eedomus/binary_sensor.py",
        literal='"présence"',
        reason="data matcher: eedomus device names are French (presence)",
    ),
    Exemption(
        file="custom_components/eedomus/climate.py",
        literal='"arrêt"',
        reason="data matcher: French off-value variants sent by the box",
    ),
    Exemption(
        file="custom_components/eedomus/climate.py",
        literal='"désactiver"',
        reason="data matcher: French off-value variants sent by the box",
    ),
    Exemption(
        file="custom_components/eedomus/climate.py",
        literal='"Confort, Eco, Hors Gel, Arret"',
        reason=(
            "data value: the box reports the French HVAC mode names "
            "(Confort, Eco, Hors Gel, Arret) in supported_modes"
        ),
    ),
    Exemption(
        file="custom_components/eedomus/coordinator.py",
        literal="'Confort'",
        reason=(
            "docstring data example: the periph.history API returns "
            "French labels such as 'Confort' for list-type peripherals"
        ),
    ),
    Exemption(
        file="custom_components/eedomus/coordinator.py",
        literal='"Espace libre"',
        reason=(
            "data matcher: the eedomus box names its free-storage "
            "system periph in French (usage 23), matched to sample "
            "the Supervision system card"
        ),
    ),
    Exemption(
        file="custom_components/eedomus/sensor.py",
        literal="Espace libre Box",
        reason=(
            "system name: French name of the box system peripheral "
            "(periph 1061604, free space), used in debug comments"
        ),
    ),
    Exemption(
        file="custom_components/eedomus/eedomus_client.py",
        literal="Configuration du PHP fallback",
        reason=(
            "pre-3.5 French comment left in place (production frozen in "
            "this ticket); any edit to the line re-triggers the guard"
        ),
    ),
    Exemption(
        file="custom_components/eedomus/eedomus_client.py",
        literal="Configuration du timeout HTTP",
        reason=(
            "pre-3.5 French comment left in place (production frozen in "
            "this ticket); any edit to the line re-triggers the guard"
        ),
    ),
    Exemption(
        file="custom_components/eedomus/eedomus_client.py",
        literal="Normalisation du champ success",
        reason=(
            "pre-3.5 French comment left in place (production frozen in "
            "this ticket); any edit to the line re-triggers the guard"
        ),
    ),
]


def _iter_source_files(source_dir: Path):
    """Every scanned .py file under source_dir, frozen trees excluded."""
    for path in sorted(source_dir.rglob("*.py")):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.name in EXCLUDED_FILES:
            continue
        yield path


def _strip_exempted_literals(line: str, exemptions: List[Exemption]) -> str:
    """Remove the exempted literals so co-located French still trips."""
    for ex in exemptions:
        if ex.literal in line:
            line = line.replace(ex.literal, "")
    return line


def _french_indicators(line: str) -> List[str]:
    """The French signals found on a line (empty when clean)."""
    indicators = []
    if ACCENT_RE.search(line):
        indicators.append("accented characters")
    if GUILLEMET_RE.search(line):
        indicators.append("guillemets")
    match = LEXICON_RE.search(line)
    if match:
        indicators.append(f"lexicon:{match.group(1)}")
    return indicators


def _scan(source_dir: Path, repo_root: Path) -> List[str]:
    """Violations as file:line strings, exemptions applied by removal."""
    repo_root = repo_root.resolve()
    violations = []
    for path in _iter_source_files(source_dir):
        rel_repo = path.resolve().relative_to(repo_root).as_posix()
        exemptions = [ex for ex in EXEMPTIONS if ex.file == rel_repo]
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            remainder = _strip_exempted_literals(line, exemptions)
            indicators = _french_indicators(remainder)
            if not indicators:
                continue
            violations.append(
                f"{path.relative_to(source_dir)}:{lineno} "
                f"[{' + '.join(indicators)}]: {line.strip()}"
            )
    return violations


def test_exemptions_still_apply():
    """Drift check: every named exemption must exist in its file."""
    for ex in EXEMPTIONS:
        path = REPO_ROOT / ex.file
        assert path.is_file(), f"exemption targets a missing file: {ex.file}"
        assert ex.literal in path.read_text(encoding="utf-8"), (
            f"stale exemption: {ex.file} no longer contains {ex.literal!r} "
            f"({ex.reason}) - remove the exemption"
        )


def test_scan_covers_the_source_tree():
    """Loud failure if the scan walks nothing (SOURCE_DIR moved)."""
    files = list(_iter_source_files(SOURCE_DIR))
    assert (
        len(files) >= MIN_SCANNED_FILES
    ), f"implausible scan: only {len(files)} .py files under {SOURCE_DIR}"


def test_no_french_outside_exemptions():
    """The guard: zero French lines outside the named exemptions."""
    violations = _scan(SOURCE_DIR, REPO_ROOT)
    if violations:
        pytest.fail(
            "French found in the eedomus source outside the named "
            "exemptions (translate it, or name it in EXEMPTIONS with a "
            "reason):\n" + "\n".join(violations),
            pytrace=False,
        )


def _plant(root: Path, rel_path: str, text: str) -> None:
    """Write a planted source file under the tmp_path tree."""
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestScanSelfTest:
    """Committed mutation proof (pattern of the JS guard's self-test)."""

    def test_scan_catches_french_and_spares_clean_sources(self, tmp_path):
        src = tmp_path / "custom_components" / "eedomus"
        # (a) accented French
        _plant(
            tmp_path,
            "custom_components/eedomus/accented.py",
            "# Échec de la sauvegarde du mapping\n",
        )
        # (b) accent-free, lexicon-only French
        _plant(
            tmp_path,
            "custom_components/eedomus/lexicon.py",
            "# Le fichier de mapping est absent\n",
        )
        # (c) French CO-LOCATED with an exempted literal: the strip must
        # leave the French part visible to the indicators. The clean
        # counterpart (exempted literal alone, line 1) must stay exempt.
        _plant(
            tmp_path,
            "custom_components/eedomus/binary_sensor.py",
            'x = "porte"\ny = "porte"  # Le fichier de mapping est absent\n',
        )
        violations = "\n".join(_scan(src, tmp_path))
        assert "accented.py:1" in violations
        assert "lexicon.py:1" in violations
        assert "binary_sensor.py:2" in violations
        assert "binary_sensor.py:1" not in violations
