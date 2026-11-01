"""Security pin guard for the requirements surfaces (ticket 120).

The 0.15.5 dependency batch missed requirements_prod.txt - it kept
aiohttp==3.14.3, exactly inside the vulnerable range of the open
Dependabot alerts, and that file ships in the HACS release package
(release.yml copies it). This guard scans every tracked requirements
surface and fails on any pin matching the vulnerable pins documented
by the ticket, so the miss cannot repeat silently.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]

# Tracked requirements surfaces. requirements.lock was deleted as a
# dead artifact by this same ticket (stale pip-compile output,
# consumed by nothing) - it is intentionally absent.
SCAN_TARGETS = [
    "requirements.txt",
    "requirements_dev.txt",
    "requirements_prod.txt",
    "requirements-test.txt",
    "pyproject.toml",
]

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

_PIN_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*(?:==|>=)\s*([0-9][^\s#;]*)")


def _pins_in(path: Path):
    """Yield (name, version) pins found in a requirements-style file."""
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        # Strip inline comments the way pip does (space + #)
        code = line.split(" #")[0].strip()
        match = _PIN_RE.match(code)
        if match:
            yield match.group(1).lower(), match.group(2).strip(), lineno


def test_no_vulnerable_pin_in_requirements_surfaces():
    """No tracked requirements surface carries a vulnerable pin."""
    offenders = []
    for name in SCAN_TARGETS:
        path = REPO_ROOT / name
        if not path.exists():
            offenders.append(f"{name}: MISSING SCAN TARGET")
            continue
        for package, version, lineno in _pins_in(path):
            for vulnerable_name, vulnerable_version in VULNERABLE_PINS:
                if package == vulnerable_name and version == vulnerable_version:
                    offenders.append(
                        f"{name}:{lineno}: {package}=={version} "
                        "(vulnerable pin, see ticket 120)"
                    )
    assert not offenders, "Vulnerable dependency pins found:\n" + "\n".join(offenders)


def test_release_package_pin_file_is_clean():
    """requirements_prod.txt - the file shipped in the HACS package -
    pins the patched aiohttp line, matching the release line."""
    prod = (REPO_ROOT / "requirements_prod.txt").read_text(encoding="utf-8")
    assert "aiohttp==3.14.3" not in prod
    assert re.search(r"aiohttp==3\.14\.(5|[6-9]|[1-9][0-9])", prod), prod


def test_stale_lock_file_stays_deleted():
    """requirements.lock was removed as a dead artifact (ticket 120) -
    if it ever comes back, this test forces the decision to be
    re-argued instead of drifting in silently."""
    assert not (REPO_ROOT / "requirements.lock").exists(), (
        "requirements.lock reappeared: either regenerate it from the "
        "current requirements_prod.txt or delete it again with a "
        "recorded decision (ticket 120)"
    )
