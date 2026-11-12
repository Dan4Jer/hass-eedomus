# REALITY-CHECK Review — ARCHITECTURE-SPINE.md (architecture-hass-eedomus-2026-09-27)

**Lens:** verify every committed decision was web-researched / reality-checked, not asserted from training data.
**Date of review:** session date; spine dated 2026-09-27, updated 2026-09-28.
**Method:** read-only. Repo inspection via git/grep/bash; live SSH to the Pi (`ssh 192.168.1.5 'sudo -i ha core info'`) **failed** this session (`Permission denied (publickey,password)` in BatchMode), so instance claims were verified against the Pi log captured in the repo (`rasp.log`, header dated 2026-09-27, plus `rasp.0.log` from 2026-09-05) and against upstream sources fetched live: raw.githubusercontent.com at HA tags `2026.9.3` / `2026.3.0`, github.com releases (frenck/spook), PyPI (pytest, black), doc.eedomus.com, home-assistant.io blog.

## Verdict

**PASS WITH FINDINGS — 1 HIGH, 3 MEDIUM, several verified-OK.** The spine's external version claims are almost all real and verifiable (HA 2026.9.3, HAOS 18.2, recorder schema 53 at both 2026.3 and 2026.9.3, eedomus 10 000-point limit, pytest 9.1.1, black 26.10.1, Spook v5.5.1 tag exists). The one material misstatement is the **Python floor**: the spine says "Python 3.11+ (runtime HA)" but HA Core 2026.9.3 hard-requires Python ≥ 3.14.2, and the repo's own artifacts disagree with each other (3.9+ in AGENTS.md, py39 black target, 3.11 in all CI workflows, 3.14 on the actual Pi).

## Findings

### F1 [HIGH] Python floor incoherent across artifacts; spine's "3.11+ (runtime HA)" is wrong
- Spine Stack table (ARCHITECTURE-SPINE.md:177): "Python 3.11+ (runtime HA ; tests locaux sous 3.14)".
- **Reality:** `homeassistant/const.py` at tag **2026.9.3** (raw.githubusercontent.com) contains `REQUIRED_PYTHON_VER: Final[tuple[int, int, int]] = (3, 14, 2)`. The Pi log `rasp.log` shows `python3.14` paths throughout (1038 occurrences) — the HAOS 18.2 / Core 2026.9.3 instance runs Python 3.14, not 3.11.
- Repo artifacts disagree with each other:
  - `AGENTS.md:6` — "Python 3.9+"
  - `pyproject.toml` `[tool.black] target-version = ['py39']`
  - `.github/workflows/{tests,lint,hacs_validation,release}.yml` — all `python-version: '3.11'` (bumped from 3.9 by commit `7b8aad2`, "Ubuntu 26.04 runners dropped 3.9")
  - local `.venv` is Python 3.11.15, but `tests/unit/__pycache__/` contains both `cpython-311` and `cpython-314` pytest-9.1.1 artifacts — tests have run under both.
- **Assessment:** CI 3.11 is test-only (requirements-test.txt deliberately excludes `homeassistant`), so it is viable for stub unit tests — but the spine's phrasing "3.11+ (runtime HA)" mislabels the production runtime, which is 3.14.2+. The floor is not coherent across artifacts: four different numbers (3.9 / py39 / 3.11 / 3.14). Recommend the spine state "runtime HA 2026.9 = Python ≥ 3.14.2 (per const.py @2026.9.3); CI/tests 3.11+; drop the stale 3.9+ from AGENTS.md and the py39 black target".

### F2 [MEDIUM] "cible compat ≥ 2026.3" is asserted in docs but not enforced in manifest or code
- Spine: "cible compat >= 2026.3, schema recorder 53" (line 178). Recorder schema part **verified**: `db_schema.py` `SCHEMA_VERSION = 53` at both tag `2026.3.0` and tag `2026.9.3` (raw.githubusercontent.com) — the schema-53 claim holds across the whole declared compat range.
- But `custom_components/eedomus/manifest.json` has **no `"homeassistant"` minimum-version key** (the key HA uses to refuse old cores), and no code in `custom_components/eedomus/*.py` checks a min HA version. `docs/2026_compatibility.md:54` itself lists "Mettre à jour manifest.json pour refléter la compatibilité avec 2026.3.0" as an **open action** — never done. The compat floor is documentation-only.

### F3 [MEDIUM] "pytest 9.x" true for dev pins, not for the CI test path
- `pytest==9.1.1` pinned in `requirements.txt` and `requirements_dev.txt`; pytest **9.1.1 exists on PyPI** (published 2026-06-19, per releasealert/PyPI); local pycache confirms `pytest-9.1.1` ran the unit tests.
- But CI (`tests.yml`) installs `-r requirements-test.txt` (commit `8143e5e`), which only says `pytest>=7.0.0` — CI can resolve 7.x/8.x today. Spine claim "pytest 9.x (unitaires…)" is accurate for the dev environment, not guaranteed for CI.

### F4 [MEDIUM] Instance-only claims not confirmable from the repo this session: Spook 5.5.1 version, purge_keep_days: 30
- Live SSH to 192.168.1.5 failed (auth), so `ha core info` could not be re-run. From `rasp.log`: HAOS 18.2 and Core 2026.9.3 **confirmed** (instance header, 2026-09-27); Spook **presence** confirmed (loader warnings for `spook` / `spook_inverse`) but its **version 5.5.1 is nowhere in the logs** — the exact version rests on the memlog's "verified in session" note, not on repo evidence. Upstream check: `v5.5.1` is a real release tag of frenck/spook (latest upstream is v5.11.1), so the number is plausible and real, just not instance-proven here.
- `purge_keep_days: 30` (spine line 200, AD-1 rationale) — Pi's configuration.yaml is not in the repo; **not independently confirmable** this session (memlog claims session verification).

### F5 [LOW] eedomus `periph.history` 10 000-point limit: documented claim verified; code uses a heuristic, not the documented overflow field
- Official doc (doc.eedomus.com/view/API_eedomus): "La réponse est limitée au 10 000 1ère valeurs, dans ce cas le champ suivant est ajouté dans le JSON de réponse: `history_overflow: 10000`" — **the "10 000 pts/appel, limite documentée" claim in the spine (AD-4, Stack table) is verified.**
- Code matches: `coordinator.py:2226` "Fetch a chunk of 10,000 history data points", `coordinator.py:2333` `len(chunk) < 10000` completion test; `rasp.log` shows "Successfully imported 10000 historical data points". Nuance: the code never reads the documented `history_overflow` field (grep: zero hits in repo) and instead relies on `len < 10000` plus a `stale_window` heuristic (comment "Bug 1.10"). Consistent with the doc, but the spine should not imply the code honors `history_overflow`.

### F6 [LOW] HA version claims verified; minor dev-pin drift
- `rasp.log` header (2026-09-27): "OS Version: Home Assistant OS 18.2 / Home Assistant Core: 2026.9.3" — **both spine claims verified on the instance log**. `rasp.0.log` (2026-09-05) shows Core 2026.9.0, consistent with an in-place upgrade to 2026.9.3. GitHub tag `2026.9.3` exists (raw file fetches succeeded); HA blog 2026.9 exists. HAOS 18.2 referenced in home-assistant/operating-system discussions — exists.
- Drift note: `requirements.txt` / `requirements_dev.txt` pin `homeassistant>=2026.9.4` while the verified instance runs 2026.9.3 — dev floor is one patch ahead of production; harmless but the spine's "2026.9.3 (vérifié sur l'instance)" and the dev pin should not be conflated.

### F7 [INFO] Tooling pins real
- `black==26.10.1` exists (psf/black releases; 26.x supports targets through py315 — the `py39` target in pyproject is still accepted but stale, see F1). `isort==9.0.2`, `mypy==2.4.0`, `flake8==7.4.1` are pinned consistently across requirements files; lint.yml still installs older ad-hoc pins (`black==23.12.1`, `isort==5.13.2`, `mypy==2.3.1`) — a separate internal inconsistency between lint.yml and the pinned hook versions, outside this lens's scope but worth noting.

## Verified-OK summary (no action)
| Spine claim | Evidence |
| --- | --- |
| HA Core 2026.9.3 on instance | rasp.log header 2026-09-27; GitHub tag 2026.9.3 exists |
| HAOS 18.2 | rasp.log header; HAOS discussions reference 18.2 |
| compat ≥ 2026.3 exists; recorder schema 53 | tag 2026.3.0 blog exists; `SCHEMA_VERSION = 53` at tags 2026.3.0 AND 2026.9.3 |
| periph.history 10 000 pts/appel "limite documentée" | doc.eedomus.com/view/API_eedomus (`history_overflow: 10000`); code + Pi log agree |
| pytest 9.x | pytest 9.1.1 on PyPI (2026-06-19); pinned in requirements*.txt; pycache pytest-9.1.1 |
| Spook present on instance, not a dependency | rasp.log loader warnings; AD-1 correctly removes the dependency; v5.5.1 tag exists upstream (version-on-instance unproven, F4) |
| black 26.10.1 | psf/black releases |

## Not confirmable from repo / this session
- Spook's exact version on the Pi (5.5.1) — presence proven, version not in any repo artifact.
- `purge_keep_days: 30` in the Pi's configuration.yaml — config not in repo, SSH failed.
- Live `ha core info` — SSH 192.168.1.5 denied this session; relied on the captured `rasp.log`.

## Recommended spine edits (not applied — read-only review)
1. Fix Stack row: "Python ≥ 3.14.2 (runtime HA 2026.9, per const.py @2026.9.3); CI/tests 3.11+" and reconcile AGENTS.md "3.9+" / black `py39` with the CI 3.11 bump (`7b8aad2`).
2. Either add `"homeassistant": "2026.3.x"` to manifest.json or soften "cible compat ≥ 2026.3" to "documented, not enforced".
3. Pin `pytest>=9` (or ==9.1.1) in requirements-test.txt if the spine wants "pytest 9.x" to hold in CI.
4. Qualify "Spook 5.5.1 présent" and "purge_keep_days: 30" as session-verified on the instance, not repo-verifiable.
