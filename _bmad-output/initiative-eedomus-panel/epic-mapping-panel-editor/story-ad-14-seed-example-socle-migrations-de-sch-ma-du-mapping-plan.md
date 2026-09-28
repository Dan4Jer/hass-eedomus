---
title: "P.1.9 AD-14 — seed .example + socle migrations de schéma"
type: 'feature'
ticket: 9
created: '2026-09-28'
status: 'built'
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
baseline_revision: '5e3cad5'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** AD-13 ne fixe pas la montée de version : les utilisateurs de l'ère pré-AD-13 peuvent avoir leurs éditions dans le fichier intégré (écrasé silencieusement par un update HACS), et rien ne prévoit l'évolution de la structure de configuration.

**Approach:** AD-14 du spine : le fichier intégré devient un exemple non éditable (`custom_mapping.yaml.example`, en-tête « ne pas éditer ») ; `config_schema_version` dans le storage (absent = 1, version de naissance) + chaîne ordonnée de migrations pures appliquées au chargement ; une migration réussie archive l'ancien canon comme version (`reason: migration` — décision utilisateur) et régénère miroir+fingerprint ; un échec conserve le canon + warning. Les paramètres utilisateur (canon + miroir) restent hors de l'arbre de code.

</frozen-after-approval>

## Implementation Notes

- Renommage : `git mv config/custom_mapping.yaml → custom_mapping.yaml.example` + en-tête bilingue d'avertissement ; `CUSTOM_MAPPING_FILE` et `get_custom_mapping_paths` pointent le `.example`. La migration legacy v3→v4 d'entry (backup du fichier intégré) saute gracieusement si le fichier n'existe plus — code mort à nettoyer en P.1.7.
- `config_manager` : `MAPPING_CONFIG_SCHEMA_VERSION = 1`, `_MAPPING_MIGRATIONS` (vide — le mécanisme est le livrable), `_async_migrate_mapping_document(hass)` appelé **avant** la comparaison d'ingestion (elle doit voir le canon migré et son fingerprint régénéré). Absent de version = estampillage 1 sans migration ; chaîne ordonnée par version cible ; échec → canon conservé + warning.
- Archive versionnée : champ `reason` ajouté aux entrées (`save` / `ingestion` / `migration`) — P.1.6 l'affichera. La classe `async_archive_mapping_version` délègue à la fonction de module.
- Save UI estampille `config_schema_version` à chaque écriture.
- Cas pré-AD-13 HACS : les éditions du fichier intégré déjà écrasées à l'update ne sont pas récupérables à chaud (le contenu est parti avant que l'ingestion tourne) — le `.example` empêche le risque FUTUR, la note de version documente le chemin de migration (copier le fichier intégre vers `/config/eedomus/` avant l'update).

## Review Triage Log

Review quick (self), itération 1 :

- [checked] L'estampillage « absent = 1 » ne réécrit NI le fingerprint NI le miroir ( `{**data, version}` ) — un boot post-update sur storage existant est un strict no-op pour la config.
- [checked] Migration avant comparaison d'ingestion : le fichier miroir régénéré par la migration porte le dump migré → le diff suivant est nul, pas de version parasite.
- [checked] `reason` rétro-compatibles : les versions existantes du storage Pi (2 entrées) n'ont pas le champ — P.1.6 doit afficher un libellé par défaut (ex. « save ») quand `reason` est absent.
- [low, defer→P.1.7] La migration v3→v4 d'entry (backup du fichier intégré, `async_migrate_entry`) est du code mort pour AD-13/14 : le seed `.example` n'est plus une cible de sauvegarde utilisateur.
- [low] Cas HACS pré-AD-13 non récupérable à chaud — la protection est PRÉVENTIVE (.example + note de version) ; documenté dans l'Intent.

## Verification

**Commands:**

- `python3 -m pytest tests/unit -q` -- expected: 151 verts (dont 5 nouveaux : 4 migrations + 1 seed .example)
- `uv run --with flake8 --no-project flake8 tests/unit/test_config_manager.py` -- expected: vide

**Manual checks (déploiement requis) :**

- Boot : `.storage/eedomus.mapping` estampillé `config_schema_version: 1`, fingerprint/miroir inchangés, aucune version archivée
- Le seed `.example` existe sur le Pi, l'ancien `config/custom_mapping.yaml` intégré disparaît du checkout
- E2E verte, mapping identique (165 periphs / 100 dynamiques)
