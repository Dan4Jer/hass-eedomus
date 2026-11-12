## Description

<!-- What does this PR do and why? Link the issue: Closes #NN -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation / chore

## Checklist

- [ ] Targets `unstable` (not `main`)
- [ ] `python3 -m pytest tests/unit/ -q` — green
- [ ] JS harnesses green (`node tests/js/test-coherence.js`, and the others in `tests/js/`)
- [ ] `bash scripts/hooks/pre-push` — exit 0
- [ ] All code, logs and user-facing strings in English; FR only in translation files (`strings.json` + `translations/en.json` + `translations/fr.json`, or `panel_translations.py` + fixtures for panel strings)
- [ ] No token, PAT or secret anywhere in the diff
