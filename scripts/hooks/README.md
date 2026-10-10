# Git hooks — hass-eedomus

Versioned git hooks for this repository. The hook file is committed, so
it stays in sync with the branch; each machine that pushes installs it
once.

## What the pre-push hook does

Refuses **any push** — any remote, any branch — when the repository's
**tracked** Python files fail the format checks:

- `black --check` (pinned `black==26.10.1`)
- `isort --check-only` (pinned `isort==9.0.2`)

Both versions are pinned to the ones that formatted the tree, so an
upstream formatter release cannot silently start blocking pushes, and
two machines cannot disagree on what "clean" means. Untracked scratch
files are never pushed, so they are ignored by the gate. If `uv` is
not installed the hook fails open with a warning — the deploy-script
gate is the enforcement backstop.

Configuration lives in `pyproject.toml` (`[tool.black]` line-length 88,
`[tool.isort]` profile black). Both tools run in **ephemeral uv
environments** (`uv run --no-project --with black==… --`) — nothing is
installed permanently, and no project environment is synced. `uvx` is
deliberately not used: its generated bin shims rely on `realpath`,
which is missing on stock macOS.

The same checks also run as a gate in the deploy script
(`.vibe/skills/hass-eedomus-deploy/deploy_hass_eedomus.sh`) — after
verifying local HEAD equals `origin/unstable`, since that is what the
Pi pulls and deploys (ticket 115).

## Install (per machine)

```bash
bash scripts/hooks/install.sh
```

The installer sets `core.hooksPath` to this directory (absolute path,
so re-run it if you move the clone).
