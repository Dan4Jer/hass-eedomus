## Description

<!-- Que fait cette PR et pourquoi ? Issue liée : Closes #NN -->

## Type de changement

- [ ] Correction de bug
- [ ] Nouvelle fonctionnalité
- [ ] Documentation / chore

## Checklist

- [ ] Vise `unstable` (pas `main`)
- [ ] `python3 -m pytest tests/unit/ -q` — vert
- [ ] Harnais JS verts (`node tests/js/test-coherence.js`, et les autres dans `tests/js/`)
- [ ] `bash scripts/hooks/pre-push` — exit 0
- [ ] Tout le code, les logs et les textes exposés en anglais ; FR uniquement dans les fichiers de traduction (`strings.json` + `translations/en.json` + `translations/fr.json`, ou `panel_translations.py` + fixtures pour le panneau)
- [ ] Aucun token, PAT ou secret dans le diff
