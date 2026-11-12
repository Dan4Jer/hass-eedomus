# Review REGATE — re-check read-only de la spine après update du gate de validation 2026-11-01

- **Spine reviewée :** `ARCHITECTURE-SPINE.md` (updated 2026-11-01) + `.memlog.md` (updated 2026-11-12T09:22)
- **Base code :** `unstable@3dfa99e` (`custom_components/eedomus/`)
- **Méthode :** read-only. Chaque claim file:line du spine et de la section « Violations connues » a été vérifiée à la source ; les refs de commits ont été résolues dans git. Aucune modification, aucun commit.

## Verdict

**PASS AVEC RÉSERVES (2 findings médians/mineurs, 0 bloquant).** La spine ratifie fidèlement le code brownfield : toutes les refs file:line spot-checkées pointent sur le code décrit, AD-1..5 / AD-13 / AD-14 / AD-17 sont réellement implémentées (commits résolus et conformes), la section « Violations connues » est exacte sur 6 des 7 entrées — mais l'énumération AD-9 est incomplète (trouve F1) et le marqueur AD-6 est périmé (F2).

## (1) Divergence points — fixés, aucun manqué ?

Les vrais points de divergence sont tous couverts : primitive de mutation AD-12 (writers directs), ingestion mapping AD-13 (triple violation), ordonnancement worker AD-8, clip AD-11, parsing legacy AD-2, lectures d'options AD-9, appel API hors coordinator AD-7 (config_flow). **Un manquement partiel :** l'énumération des violations AD-9 ne liste que `__init__.py:453` et `coordinator.py:2168/2746`, alors que `__init__.py` contient ~9 lectures directes d'options supplémentaires hors `_get_config_value` (voir F1) — dont `__init__.py:453` qui lit `entry.data.get(CONF_ENABLE_HISTORY)` seul, ignorant l'option posée via l'options flow : divergence réelle non listée.

## (2) Chaque AD Rule est enforceable et prévient sa divergence stated

Oui pour les 17 AD. AD-1 (import exclusif `async_import_statistics`) : vérifié — seul appel recorder du repo : `coordinator.py:2710` ; aucun `async_set`/appel de service Spook dans le code. AD-2 (worker de fond + clés `.storage` `<entry_id>_<periph_id>` + unload await+flush) : vérifié (`coordinator.py:208,1460-1487,1670-1681,1826-1833,1883-1887` ; `__init__.py:724-725`). AD-12 prévient bien la régression 9abc03f (toujours vivante : `services.py:167` refresh juste après le set — confirmé). AD-10/AD-16 sont des règles de process (enforceables via CI/script de deploy), assumées comme telles. Nuance F2 : la règle AD-11 resserrée (clip `min(first_native_start, début heure courante)` + sérialisation) est citée avec `coordinator.py:2667-2683`, mais ce code ne fait le clip que si des stats natives existent — la moitié zéro-native de la règle n'est pas dans le code (correctement listée en violation, mais la ref de la règle est trompeuse).

## (3) Deferred — aucune divergence entre unités

Les 5 items Deferred sont sûrs : agrégation des warnings (ergonomie de log), fusion multi-box (explicitement aucune), purge des statistics fantômes (nettoyage d'artefacts passés, pas de divergence runtime), rôle webhook/api_proxy (gel sans croissance), compat min HA (item **ouvert** explicite, pas un deferral caché). Aucun ne permet à deux unités de diverger. ✓

## (4) Ratification vs code brownfield — spot-checks

| Claim spine | Vérification | Résultat |
| --- | --- | --- |
| AD-1..5 implémentées, commits cf8b642/8f71efc/f2136ae/20d3639 | commits résolus (2026-10-09/10, messages conformes) ; worker `coordinator.py:208/1460-1482` ; import `recorder_statistics.async_import_statistics` seul (`coordinator.py:2710`) ; progression `.storage` `eedomus.backfill_<entry_id>`, clés `<entry_id>_<periph_id>` (`coordinator.py:1826-1833,1883-1887`) ; unload await+flush (`coordinator.py:1485-1487`, `__init__.py:724-725`) | ✓ |
| AD-13/14 dans `config_manager.py`, commits fce3ba8/5e3cad5/051c6b4 | `Store eedomus.mapping` (:38) avec `current`+`file_fingerprint`+`config_schema_version` (:111-113), archive versions cap 3 (:41, :80-82), `_MAPPING_MIGRATIONS` + `_async_migrate_mapping_document` (:24-25, :156+), miroir `_async_write_mirror` (:129-131) ; commits résolus (2026-09-28) | ✓ |
| AD-17 dans `panel.py` (`PanelEntryView`), commit 0572863 | `PanelEntryView` (:100) sert chaque JS avec specifiers réécrits `from './x.js?v=<version>'` (:74-97), enregistrée avant le static path (:159-163), URL entry `?v=` (:71), version manifest 0.15.7 ; test de garde `tests/unit/test_panel.py:229-262,302-316` ; commit résolu (2026-11-01) | ✓ |
| AD-12 non appliqué : writers `coordinator.py:463/991/1102/2888` + setup plateformes ; `services.py:167` | 463/991 `self.data = aggregated_data`, 1102 `self.data[periph_id].update(...)`, 2888 `self.data[periph_id]["last_value"] = value` ; writers plateformes : `light.py:69`, `switch.py:46/154`, `cover.py:68`, `sensor.py:77`, `binary_sensor.py:89` ; `services.py:167` `await target_coordinator.async_request_refresh()` juste après le set | ✓ (count « 5 writers » groupe les 6 sites plateformes en 1 — voir F3) |
| AD-13 : `__init__.py:181` ingestion par entry ; `device_mapping.py:983/388` fallback lecture fichier | `__init__.py:181` `await async_ingest_custom_mapping(hass)` (par entry, hors init domaine ConfigManager) ; `device_mapping.py:388` `load_custom_yaml_mappings()`, `:983` `read_custom_mapping_file` | ✓ |
| AD-8 : worker `coordinator.py:208` vs forward `__init__.py:366/617` ; misses `coordinator.py:2406` | worker démarré au setup du coordinator (:208), avant `async_config_entry_first_refresh` (:366) et `async_forward_entry_setups` (:617) ; :2406 `self._history_progress.pop(...)` + save après 3 misses | ✓ |
| AD-11 : clip seulement si stats natives `coordinator.py:2667-2683` | confirmé : `if native_rows:` garde le clip ; cas zéro-native non traité | ✓ |
| AD-2 : migration `split("_")[-1]` `coordinator.py:1649` | confirmé tel quel | ✓ |
| AD-9 : lectures directes `__init__.py:453`, `coordinator.py:2168/2746` | confirmé, mais **liste incomplète** — voir F1 | ⚠ |
| AD-7 : `config_flow.py:291,340` `auth_test` hors coordinator | confirmé (`EedomusClient(...)` :291, `client.auth_test()` :340). `__init__.py:306` instancie le client mais le remet au coordinator sans appel direct — correctement non listé | ✓ |
| Stack : compat min non déclarée dans `manifest.json` | `manifest.json` (v0.15.7) n'a aucune clé `homeassistant` — item ouvert exact | ✓ |

## (5) Toutes les dimensions decided / deferred / open

✓ Complet : paradigme, état (AD-12 décidé, violation connue), accès API (AD-7), history (AD-1..6), identification (AD-8), config (AD-9), déploiement (AD-10), propriété ligne horaire (AD-11), primitive de mutation (AD-12), mapping (AD-13/14), versioning (AD-14), strates E2E (AD-16), cache panel (AD-17) — tous décidés ; 5 items Deferred sûrs ; 1 item ouvert (compat min HA).

## Findings

- **F1 (moyen) — Violations connues AD-9 sous-énumérée.** La spine liste `__init__.py:453`, `coordinator.py:2168/2746` comme seules lectures restantes hors `_get_config_value`. Or `__init__.py` contient aussi : :255-256, :270-276, :313-315, :406-407, :563-565, :583-584, :640, :755 — des lectures directes `entry.options.get(...)` / `entry.data.get(CONF_...)` qui réimplémentent à la main l'ordre options>data>défaut. La plus grave : `__init__.py:453` lit `entry.data.get(CONF_ENABLE_HISTORY, False)` seul — la branche setup des history sensors diverge si l'option est posée via l'options flow. Le point de divergence est réel et non listé.
- **F2 (moyen) — Marqueur AD-6 périmé + ref AD-11 trompeuse.** AD-6 porte « [ADOPTED, à resserrer] / Resserrage cible » pour le gel de la `value_list`, mais le code l'implémente déjà : `coordinator.py:2211` (`_value_list_fingerprint`), :2249 (persistée avec la progression), :2257-2278 (variation → invalidation + reset à zéro). Le marqueur devrait être « implémenté ». À l'inverse, la règle AD-11 resserrée cite `coordinator.py:2667-2683` comme si le clip `min(first_native_start, début heure courante)` y était écrit — ce n'est le cas que quand des stats natives existent (moitié zéro-native absente, listée en violation mais pas dans la règle).
- **F3 (mineur) — Comptage « 5 writers ».** 4 sites coordinator + 6 sites plateformes (`light.py:69`, `switch.py:46/154`, `cover.py:68`, `sensor.py:77`, `binary_sensor.py:89`) = 10 sites d'écriture ; « 5 » ne tient que si « setup des plateformes » compte pour un. Préciser.
- **F4 (info) — AD-7 propre ailleurs.** Aucun appel API hors coordinator hors `config_flow.py:291/340` : `__init__.py:306` se contente de construire le client remis au coordinator (aucun `client.*` direct dans `__init__.py`) ; `webhook.py`/`api_proxy.py`/`ui_service.py` n'importent pas `eedomus_client`.
- **F5 (info) — Commits et Stack vérifiés.** cf8b642, 8f71efc, f2136ae, 20d3639, fce3ba8, 5e3cad5, 051c6b4, 0572863, 9abc03f tous présents sur unstable avec les messages revendiqués ; `manifest.json` v0.15.7 sans clé de compat min (item ouvert exact).

## Conclusion

La spine post-gate est une **bonne spine** : elle ratifie le code réel sans le contredire (les violations connues sont honnêtement listées plutôt que niées), couvre toutes les dimensions, et aucun Deferred ne laisse diverger deux unités. Deux corrections de précision à apporter au prochain passage : élargir l'énumération AD-9 (F1) et aligner les marqueurs AD-6/AD-11 sur le code (F2). Aucun bloquant.
