# Contributing to hass-eedomus

Thanks for your interest. Issues and PRs are welcome — write them in **English or French** (code, logs and docs stay in English; French lives in the translation files).

## Before you start

- Bug or feature? Open an **issue first** (or ask in **Discussions**) so we can align before you write code.
- Search existing issues and PRs to avoid duplicates.
- Security problem? See [SECURITY.md](SECURITY.md) — never a public issue.

## Workflow

- PRs target **`unstable`**, never `main` (`main` is the release mirror, fast-forwarded at each release).
- Branch name: `fix/<issue-or-ticket>-<short-slug>` or `feat/<slug>`. One branch per change, deleted after merge.
- Commit messages: `<type>(<scope>): <subject>`, e.g. `fix(panel): clamp the YAML editor scroll zone`. One logical change per commit.

## Code rules

- **Everything in English**: code, comments, log messages, user-facing strings. French only in translation files.
- New backend string: add it to `strings.json` **and** `translations/en.json` **and** `translations/fr.json` (structurally identical — a drift test enforces it).
- New panel string: `panel_translations.py` (EN+FR) + `tests/fixtures/panel-catalog.json` + `tests/fixtures/panel-keys.json`.
- Panel JS: plain ES modules imported as `from './x.js'`. The server rewrites the specifiers with `?v=<manifest version>` at serve time — never introduce another import form (a unit test fails loudly).
- Formatting is enforced: black + isort via the pre-push hook.

## Checks before pushing (all must pass)

```bash
python3 -m pytest tests/unit/ -q
node tests/js/test-coherence.js   # + the other harnesses in tests/js/
bash scripts/hooks/pre-push
```

## What not to do

- Never commit a token, PAT or any secret — review the diff before pushing.
- Never "fix" a production install by editing files on the Raspberry Pi: deployment is **git-only** (maintainer side).
- E2E tests run against a live instance — do not mock the box.

## Pull request

Fill in the PR template: linked issue, type of change, checklist. A maintainer reviews, merges to `unstable`, and live-validates on the reference Pi before the next release.
