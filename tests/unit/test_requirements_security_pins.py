"""Security pin guard for the requirements surfaces (ticket 120).

The 0.15.5 dependency batch missed requirements_prod.txt - it kept
aiohttp==3.14.3, exactly inside the vulnerable range of the open
Dependabot alerts, and that file ships in the HACS release package
(release.yml copies it). This guard scans every tracked requirements
surface - requirements-style files AND the TOML-quoted pins in
pyproject.toml - and fails on any pin matching the vulnerable pins
documented by the ticket, so the miss cannot repeat silently.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]

# Tracked requirements surfaces. requirements.lock was deleted as a
# dead artifact by this same ticket (stale pip-compile output,
# consumed by nothing) - it is intentionally absent.
REQUIREMENTS_FILES = [
    "requirements.txt",
    "requirements_dev.txt",
    "requirements_prod.txt",
    "requirements-test.txt",
]
TOML_FILES = ["pyproject.toml"]

# Vulnerable pins from the open Dependabot alerts (2026-11-01):
# - aiohttp 3.14.3: CVE-2026-111063/-111064/-111065/-111066/-111748/
#   -111749/-111750 and GHSA-2g87-pp6c-29x5 (alert ranges are exactly
#   "= 3.14.3")
# - black 26.10.0: CVE-2026-114134 (RCE via the psf/black GitHub
#   Action with use_pyproject - path unused in this repo, pin bumped
#   anyway)
VULNERABLE_PINS = {
    ("aiohttp", "3.14.3"),
    ("black", "26.10.0"),
}

# The patched floor the release line must meet or exceed (a future
# legitimate bump must never fail this guard).
AIOHTTP_FLOOR = (3, 14, 5)

_REQUIREMENTS_PIN_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*(==|>=)\s*([0-9][^\s#;]*)")
_TOML_PIN_RE = re.compile(r"""["']([A-Za-z0-9_.-]+)\s*(==|>=)\s*([0-9][^"']*)["']""")


def _version_tuple(version: str):
    """Parse a version string into a comparable tuple of ints."""
    parts = []
    for part in version.split("."):
        digits = re.match(r"\d+", part)
        if not digits:
            break
        parts.append(int(digits.group(0)))
    return tuple(parts)


def _requirements_pins(path: Path):
    """Yield (name, version) pins from a requirements-style file."""
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        code = line.split(" #")[0].strip()
        match = _REQUIREMENTS_PIN_RE.match(code)
        if match:
            yield match.group(1).lower(), match.group(3).strip(), lineno


def _toml_pins(path: Path):
    """Yield (name, version) pins from TOML-quoted dependency strings.

    pyproject.toml declares pins as "name==version" inside arrays;
    the requirements-style line parser cannot see them.
    """
    text = path.read_text(encoding="utf-8")
    for match in _TOML_PIN_RE.finditer(text):
        yield (
            match.group(1).lower(),
            match.group(3).strip(),
            text.count("\n", 0, match.start()) + 1,
        )


def _all_pins():
    """Yield (surface, name, version, lineno) for every tracked pin."""
    for name in REQUIREMENTS_FILES:
        path = REPO_ROOT / name
        assert path.exists(), f"{name}: MISSING SCAN TARGET"
        for package, version, lineno in _requirements_pins(path):
            yield name, package, version, lineno
    for name in TOML_FILES:
        path = REPO_ROOT / name
        assert path.exists(), f"{name}: MISSING SCAN TARGET"
        for package, version, lineno in _toml_pins(path):
            yield name, package, version, lineno


def test_no_vulnerable_pin_in_requirements_surfaces():
    """No tracked requirements surface carries a vulnerable pin.

    Covers requirements-style files AND the TOML-quoted pins of
    pyproject.toml (the review of this ticket caught the TOML scan
    silently extracting nothing - this test must never go back to
    that).
    """
    offenders = []
    for surface, package, version, lineno in _all_pins():
        for vulnerable_name, vulnerable_version in VULNERABLE_PINS:
            if package == vulnerable_name and version == vulnerable_version:
                offenders.append(
                    f"{surface}:{lineno}: {package}=={version} "
                    "(vulnerable pin, see ticket 120)"
                )
    assert not offenders, "Vulnerable dependency pins found:\n" + "\n".join(offenders)


def test_pyproject_toml_scan_actually_extracts_pins():
    """The TOML parser is load-bearing: it must find the pins
    pyproject.toml actually carries (at least aiohttp), otherwise the
    no-op-scan regression this ticket's review caught comes back."""
    pyproject_pins = {
        package
        for surface, package, _version, _lineno in _all_pins()
        if surface == "pyproject.toml"
    }
    assert "aiohttp" in pyproject_pins, (
        "pyproject.toml pin scan extracted nothing - the TOML branch " "is broken"
    )


def test_release_package_pin_file_is_clean():
    """requirements_prod.txt - the file shipped in the HACS package -
    pins aiohttp at or above the patched floor (3.14.5): a future
    legitimate bump must pass, a regression below the floor must
    fail. Line-aware: a comment mentioning an old pin is not a pin."""
    pins = {
        package: version
        for package, version, _lineno in _requirements_pins(
            REPO_ROOT / "requirements_prod.txt"
        )
    }
    assert "aiohttp" in pins, "requirements_prod.txt lost its aiohttp pin"
    assert _version_tuple(pins["aiohttp"]) >= AIOHTTP_FLOOR, (
        f"requirements_prod.txt aiohttp pin {pins['aiohttp']} is below "
        f"the patched floor {'.'.join(map(str, AIOHTTP_FLOOR))}"
    )


def test_stale_lock_file_stays_deleted():
    """requirements.lock was removed as a dead artifact (ticket 120) -
    if it ever comes back, this test forces the decision to be
    re-argued instead of drifting in silently."""
    assert not (REPO_ROOT / "requirements.lock").exists(), (
        "requirements.lock reappeared: either regenerate it from the "
        "current requirements_prod.txt or delete it again with a "
        "recorded decision (ticket 120)"
    )
