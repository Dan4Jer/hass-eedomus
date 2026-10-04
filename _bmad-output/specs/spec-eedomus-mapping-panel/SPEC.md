---
id: SPEC-eedomus-mapping-panel
companions: [../../planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md, ../../planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/DESIGN.md, ../../planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md]
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Side panel Eedomus — éditeur UI du mapping custom avec aide à la saisie

## Why

**Douleur à résoudre (discussion #28) + dette technique existante.** Un utilisateur demande des outils pour paramétrer les périphériques détectés (types de sensors, unités de mesure). La réponse actuelle est le mapping YAML custom (`custom_mapping.yaml`) — puissant mais uniquement éditable à la main, ce qui exclut les utilisateurs non techniques. Le code contient déjà un panneau et un backend d'aide à la saisie, mais les deux sont **débranchés** : `panel.py` n'est jamais appelé et repose sur une API HA inexistante (`panel_custom.async_register_panel`), `_async_init_ui_service` n'est jamais invoqué, les assets `www/` sont des squelettes non thémés, et `frontend.yaml` n'est pas un mécanisme HA réel. HA 2026.9.3 offre un mécanisme de panneau supporté et éprouvé (`async_register_built_in_panel` + `StaticPathConfig`, pattern utilisé par 412 intégrations custom), vérifié dans le source. Les AD cités sont ceux du companion `ARCHITECTURE-SPINE.md`. Le panneau est aussi l'outil de vérification : s'assurer que le mapping des périphériques eedomus est cohérent avec les entités HA selon l'usage réel (onglet Cohérence, spec étendu le 2026-10-04).

## Capabilities

- **CAP-1 — Panneau dans la barre latérale**
  - **intent:** Un panneau « Eedomus Config » apparaît dans la barre latérale de HA, réservé aux administrateurs, enregistré par le mécanisme supporté et retiré proprement au déchargement.
  - **success:** Après le setup de l'intégration, le panneau s'affiche dans la sidebar et fonctionne ; à l'unload il disparaît ; aucune erreur dans les logs ; aucun `frontend.yaml`.

- **CAP-2 — Liste des périphériques**
  - **intent:** Le panneau liste les périphériques eedomus avec leur `usage_id`, leur nom et leur mapping courant (entité HA, `device_class`, unité), lu depuis `coordinator.data`.
  - **success:** Les ~165 périphériques de l'instance s'affichent avec leur mapping, recherche/filtrage par nom ou `usage_id` fonctionnel.

- **CAP-3 — Édition du mapping avec aide à la saisie**
  - **intent:** L'utilisateur crée, modifie et supprime des règles de mapping custom depuis l'UI, dans les deux modes — formulaire structuré par règle et édition YAML brut — avec autocomplete (`usage_id`, `device_class`, unité) et validation temps réel via les commandes websocket existantes (`ui_service.py` : validate / suggestions / schema).
  - **success:** La règle « capteur de température » de la discussion #28 se crée entièrement par l'UI ; une règle invalide est signalée avant sauvegarde, jamais silencieusement acceptée.

- **CAP-4 — Sauvegarde et application automatique**
  - **intent:** La sauvegarde persiste les règles dans le **HA storage** (`eedomus.mapping`, canon AD-13 du companion architecture) via `config_manager`, réplique le miroir éditable `custom_mapping.yaml`, puis auto-applique : le rechargement de l'intégration est déclenché, le mapping prend effet immédiatement. Réciproquement, une modification manuelle du fichier est **ingérée au chargement** comme une nouvelle version si son texte diffère du fingerprint stocké (un fichier invalide n'écrase jamais le canon).
  - **success:** Une règle sauvée survit à un redémarrage HA et change effectivement l'entité concernée (ex. : une unité corrigée s'affiche corrigée dans HA après sauvegarde) ; une édition manuelle du fichier prend effet au rechargement suivant et apparaît comme une version dans l'Historique.

- **CAP-5 — Historique et restauration des 3 dernières versions**
  - **intent:** Chaque sauvegarde archive la version précédente du mapping (horodatée) dans le `.storage` HA ; le panel affiche les 3 dernières versions et permet de restaurer l'une d'elles en un clic — la restauration emprunte le chemin d'application de CAP-4 et archive la version qu'elle remplace ; seules les 3 dernières sont conservées.
  - **success:** Après 3+ sauvegardes, le panel montre exactement 3 versions horodatées ; restaurer la version précédente remet son contenu et l'applique ; la 4e sauvegarde purge la plus ancienne.

- **CAP-6 — Vue de cohérence (onglet Cohérence)**
  - **intent:** Un 4e onglet du panneau présente un tableau triable de tous les périphériques eedomus (~165) — `periph_id`, nom, entité HA cliquable, type/sous-type, puces de statut — avec en-tête collant, filtre rapide et bascule « Tout afficher » / « À vérifier ». Quatre signaux cumulables, dérivés côté backend : sans entité HA (`entity_id` null), mapping douteux (pas d'état vivant ni d'unité, `device_class` discutable), règle active (`modified_by_rule`), en erreur (file de retry du coordinator) ; un périphérique sans signal porte « cohérent ». La vue est strictement en lecture : le tableau signale et relie vers où corriger (onglet Règles, réglages HA), aucune édition directe.
  - **success:** Les ~165 périphériques s'affichent avec leur statut ; les 4 signaux s'affichent correctement sur des cas réels de l'instance ; la bascule filtre la vue ; le tri réordonne localement sans nouvel appel réseau ; l'état vide positif « Tout est cohérent » apparaît quand aucun signal n'est présent.

- **CAP-7 — Détail périphérique (popover / ligne étendue)**
  - **intent:** Au survol du `periph_id` (desktop) ou par extension de ligne (mobile), le panneau montre le même contenu sur les deux surfaces : état vivant (valeur courante, `usage_id`, pièce/parent, dernière mise à jour), identité de mapping (`ha_entity`, `ha_subtype`, justification du registry), actions de correctif inline (« Créer une règle » vers l'onglet Règles avec `usage_id` pré-rempli, lien vers les réglages HA), champs bruts de l'API eedomus en section secondaire repliable.
  - **success:** Parité de contenu stricte popover desktop / ligne étendue mobile ; popover opérable au clavier (focus piégé, `Échap` referme, focus rendu au déclencheur, `aria-expanded`), une seule ouverte à la fois ; les actions de correctif aboutissent (règle pré-remplie dans l'onglet Règles).

- **CAP-8 — Navigation vers les réglages d'entité HA**
  - **intent:** Cliquer l'entité HA d'une ligne du tableau de cohérence ouvre la page de réglages standard de cette entité (fonctionnement standard Home Assistant, pas de page propriétaire) ; le lien est un lien texte inline, pas un bouton d'action.
  - **success:** Le clic ouvre les réglages standard de l'entité visée dans HA (web et mobile) ; aucune édition du registry depuis le panneau ; focus et retour de navigation corrects.

- **CAP-9 — Onglet Supervision**
  - **intent:** Un 5e onglet du panneau présente en une vue les informations de la box — temps de refresh, nombre de périphériques, sollicitations de l'API proxy — en graphiques (composants du frontend HA disponibles dans le contexte du panneau, repli SVG inline thémé), un lien vers l'onglet Cohérence (mécanisme de hash existant), et la vue de la file de récupération d'historique en cours (en attente, en cours, en erreur, ignorés, en pause) ; les données et les quatre actions de la file relèvent de `spec-eedomus-history` (CAP-5) — le panneau affiche, il ne réimplémente pas le moteur.
  - **success:** L'onglet affiche les métriques en chart cards thémées avec équivalents textuels ; le lien Cohérence bascule d'onglet ; la file de backfill rendue depuis une commande websocket alimentée par le coordinator se pilote depuis cette vue, avec retour nominatif par action.

Le libellé d'onglet « Historique » (CAP-5) devient « Historique config » — désambiguïsation avec la récupération des données historiques eedomus ; le libellé vit dans la spine UX, l'intent de CAP-5 est inchangé (décision 2026-10-04).

## Constraints

- Enregistrement du panneau **exclusivement** via l'API supportée HA 2026.9.3 — `async_register_built_in_panel(component_name="custom", config={"_panel_custom": {"module_url": ...}})` + `StaticPathConfig` pour servir les assets depuis le répertoire de l'intégration. Jamais d'API inventée ; `panel.py` actuel et `frontend.yaml` sont remplacés.
- Frontend thémé HA : variables CSS de HA (`--primary-text-color`, etc.), pas de style codé en dur ; custom element JS vanilla **sans toolchain de build**, servi depuis le répertoire de l'intégration.
- Réutilisation du backend existant — brancher, ne pas réinventer : les commandes websocket `ui_service.py` (`eedomus/validate_config`, `eedomus/get_suggestions`, `eedomus/get_schema`, cache stats) et `config_manager.py` pour la persistance.
- Persistance du mapping custom selon AD-13 (companion architecture) : le HA storage est le canon lu par tout le runtime ; `<config_dir>/eedomus/custom_mapping.yaml` est le miroir éditable (ingéré au chargement, régénéré par le save, auto-réparé). Jamais le fichier intégré comme cible d'écriture.
- Le `coordinator` reste l'unique point d'accès aux données eedomus (AD-7) ; la lecture de config passe par `_get_config_value` (AD-9).
- `require_admin: true` sur le panneau et sur toute commande websocket d'écriture.
- Nouvelle commande websocket `eedomus/get_coherence` (require_admin, pattern dispatcher `ui_service` existant) : vue fusionnée par `periph_id` — mapping registry (`ha_entity`, `ha_subtype`, `parent_periph_id`, justification) × données `get_peripherals` × état vivant (`hass.states`) × champs bruts de l'API depuis `coordinator.data` (AD-7 : jamais d'appel direct à l'API eedomus) × signaux de cohérence. Le registry ne couvre que les périphériques mappés : la jointure doit produire une ligne par périphérique pour les ~165 (jamais une ligne perdue). Le contrat de `eedomus/get_peripherals` reste inchangé pour l'onglet Périphériques.

## Non-goals

- Pas un éditeur YAML généraliste : seule la grammaire du mapping custom est éditable.
- Pas d'édition de l'entity registry (noms, icônes, zones HA).
- Pas d'UI pour l'historique/backfill (épique séparé `eedomus-history`).
- Aucune écriture vers la box eedomus depuis le panneau (lecture `coordinator.data` + mapping uniquement).
- Pas d'édition du mapping depuis la vue Cohérence : elle signale et relie ; l'édition reste dans l'onglet Règles.
- Pas de toolchain de build JS (webpack, npm) — assets vanilla livrés dans le repo.

## Success signal

Un utilisateur comme celui de la discussion #28 corrige le type et l'unité d'un capteur depuis la barre latérale de HA, sans jamais ouvrir un fichier YAML, voit le changement appliqué immédiatement — et, d'un coup d'œil sur l'onglet Cohérence, sait quels périphériques demandent une vérification de mapping.

## Assumptions

- La grammaire du mapping YAML custom (conditions `usage_id`/regex, `mapping` ha_entity/device_class/unit/state_class/priority — documentée dans la discussion #28) reste la source de vérité ; le panneau l'édite, ne la remplace pas.
- Instance HA 2026.9.3+ (API panel vérifiée dans le source de cette version).
- Le choix exact des glyphes des puces de statut (jeu d'icônes HA) est laissé à l'implémentation ; seule contrainte : un glyphe distinct par signal, redondant avec le libellé. Résolution opérationnelle des signaux « mapping douteux » (absence d'état vivant/d'unité) et « en erreur » (file de retry du coordinator) fixée par le run UX 2026-10-04 (companion EXPERIENCE.md).
