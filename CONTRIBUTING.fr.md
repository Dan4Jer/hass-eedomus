# Contribuer à hass-eedomus

Merci de ton intérêt. Issues et PRs sont les bienvenues — rédige-les en **français ou en anglais** (le code, les logs et la doc restent en anglais ; le français vit dans les fichiers de traduction).

## Avant de commencer

- Bug ou fonctionnalité ? Ouvre d'abord une **issue** (ou demande dans **Discussions**) pour qu'on s'aligne avant que tu écrives du code.
- Cherche dans les issues/PR existantes pour éviter les doublons.
- Problème de sécurité ? Voir [SECURITY.fr.md](SECURITY.fr.md) — jamais d'issue publique.

## Déroulement

- Les PR visent **`unstable`**, jamais `main` (`main` est le miroir de release, fast-forwardé à chaque release).
- Branche : `fix/<issue-ou-ticket>-<slug-court>` ou `feat/<slug>`. Une branche par changement, supprimée après merge.
- Messages de commit : `<type>(<scope>): <sujet>`, ex. `fix(panel): ...`. Un changement logique par commit.

## Règles de code

- **Tout en anglais** : code, commentaires, logs, textes exposés aux utilisateurs. Le français uniquement dans les fichiers de traduction.
- Nouveau texte backend : l'ajouter à `strings.json` **et** `translations/en.json` **et** `translations/fr.json` (structurellement identiques — un test de dérive veille).
- Nouveau texte du panneau : `panel_translations.py` (EN+FR) + `tests/fixtures/panel-catalog.json` + `tests/fixtures/panel-keys.json`.
- JS du panneau : modules ES purs importés via `from './x.js'`. Le serveur réécrit les spécificateurs avec `?v=<version du manifest>` — n'introduis jamais une autre forme d'import (un test unitaire échoue bruyamment).
- Le formatage est imposé : black + isort via le hook pre-push.

## Vérifications avant de pousser (toutes doivent passer)

```bash
python3 -m pytest tests/unit/ -q
node tests/js/test-coherence.js   # + les autres harnais dans tests/js/
bash scripts/hooks/pre-push
```

## Ce qu'il ne faut PAS faire

- Ne jamais committer un token, un PAT ou un secret — relis le diff avant de pousser.
- Ne jamais « réparer » une installation en éditant des fichiers sur le Raspberry Pi : le déploiement est **git-only** (côté mainteneur).
- Les tests E2E tournent contre une instance réelle — ne mocke pas la box.

## Pull request

Remplis le template de PR : issue liée, type de changement, checklist. Un mainteneur relit, merge sur `unstable`, et valide en live sur le Pi de référence avant la prochaine release.
