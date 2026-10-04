---
name: Eedomus Config
status: final
updated: 2026-10-04
sources:
  - _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md
  - _bmad-output/specs/spec-eedomus-history/SPEC.md
  - _bmad-output/specs/spec-eedomus-i18n/SPEC.md
---

# EXPERIENCE.md — Eedomus Config

## Références visuelles

L'inventaire des mocks (mock-01 Périphériques, mock-02 Règles, mock-03 Historique config) et le statut spine-only des onglets Cohérence et Supervision vivent dans `DESIGN.md` §Références visuelles. Les spines priment sur tout mock en cas de conflit.

## Foundation

Panneau web dans la barre latérale de Home Assistant (« Eedomus Config »), réservé aux administrateurs (`require_admin`). L'accès est gardé par HA lui-même : son propre traitement d'accès écarte les non-administrateurs en amont — le panneau ne rend jamais d'état « accès refusé ». **Parité desktop + mobile** : l'édition du mapping doit être confortable sur téléphone, pas seulement consultable. Le système UI est le **thème HA** — `DESIGN.md` est la référence d'identité visuelle et nomme la couche sémantique (diff, badge, cohérence, supervision) ; cette spine ne décrit que le comportement. Frontend JS vanilla sans toolchain de build, thémé par les variables CSS HA. Les nouvelles commandes websocket backend suivent toutes la même convention : `eedomus/<verb>`, `require_admin`.

## Information Architecture

Cinq onglets, conservés sur mobile (contenu adaptatif — jamais un onglet masqué ou replié en menu).

| Surface | Contenu |
|---|---|
| **Périphériques** | Entrée du parcours. Liste des ~165 périphériques eedomus avec nom, `usage_id` et mapping courant (entité HA, `device_class`, unité), lus depuis `coordinator.data`. Recherche/filtrage par nom ou `usage_id`, plus filtre « Périphériques touchés » — équivalent textuel du badge, annoncé en `aria-live`. Badge `{components.badge-modified}` sur les périphériques touchés par la dernière règle en vigueur. |
| **Règles** | Éditeur du mapping custom en deux modes : formulaire structuré par règle (création, modification, suppression) et édition YAML brut avec coloration syntaxique et validation temps réel. Autocomplete `usage_id` / `device_class` / unité — suggestions via le schéma (voir Component Patterns). |
| **Historique config** | Les 3 dernières versions horodatées du mapping (`.storage` HA). Vue diff type git entre la version sélectionnée et la précédente (`{components.diff-line-added}` / `{components.diff-line-removed}` / `{components.diff-line-modified}`). Restauration confirmée : elle emprunte le chemin d'application de la sauvegarde et archive la version remplacée. Nom « Historique config » — versions du mapping de configuration, à distinguer de la récupération des données historiques eedomus (vue Supervision). |
| **Cohérence** | 4e onglet. Tableau plat des ~165 périphériques eedomus. Colonnes : `periph_id` (clé de survol), nom, entité HA (lien `{components.entity-link}`), type/sous-type, puces de statut `{components.coherence-chip-*}`. Tri par colonne, en-tête collant au défilement, filtre rapide ; bascule « Tout afficher » / « À vérifier ». Ambition : être un point d'entrée. Le tableau signale les incohérences et renvoie vers l'endroit où les corriger — aucune édition directe dans cette vue. |
| **Supervision** | 5e onglet. Vue unique des informations de la box en graphiques (`{components.metric-chart-card}`) : temps de refresh, nombre de périphériques, sollicitations de l'API proxy — métriques existantes du coordinator ; tout complément de données passe par de nouvelles commandes websocket backend (contrat comportemental — l'implémentation backend n'est pas prescrite). Lien « Voir le tableau de cohérence » qui bascule sur l'onglet Cohérence (mécanisme de hash existant). Sous la vue métriques : visualisation de la récupération d'historique en cours (`{components.backfill-queue}`) — une ligne par périphérique avec ses quatre actions de contrôle (voir Component Patterns). |

Onglets = navigation de premier niveau ; l'état de l'onglet actif se reflète dans l'URL du panneau (retour/arrière fonctionne entre onglets). Depuis une ligne de périphérique, l'action « Créer une règle pour ce périphérique » bascule sur l'onglet Règles avec le formulaire pré-rempli du `usage_id`. Depuis le popover de cohérence, les mêmes chemins de correctif existent : « Créer une règle » bascule sur l'onglet Règles avec le `usage_id` pré-rempli (chemin existant de la liste) ; « Config HA » ouvre la page de réglages standard de l'entité HA — extension de périmètre (nouveau CAP, hors des 5 du SPEC).

## Voice and Tone

Microcopie sobre, centrée sur des messages d'erreur utiles. La voix du panneau est celle d'un assistant technique : dire précisément quoi, pourquoi, et quoi corriger.

**Régime de localisation** : la source de vérité est l'anglais ; le français est une traduction complète, livrée avant la mise en production. Le panneau charge ses chaînes depuis le catalogue servi par le backend via une commande websocket, selon la locale de l'utilisateur (`hass.locale`) — toute chaîne utilisateur codée en dur dans le panneau est interdite. La règle est portée par `AGENTS.md` et `spec-eedomus-i18n` (références adoptées) ; cette spine s'y conforme sans la dupliquer.

Les exemples Do/Don't ci-dessous sont les traductions françaises valides ; la source anglaise vit dans le catalogue backend.

| Do | Don't |
|---|---|
| « Unité invalide : “degré” attendu, “degres” saisi. » | « Erreur dans le formulaire. » |
| « Règle appliquée. sensor.tempureau est maintenant en °C. » | « Succès ! » |
| « 3 versions conservées. La plus ancienne est purgée à la prochaine sauvegarde. » | « Historique limité. » |
| « Aucun périphérique ne correspond à “temp”. » | « Recherche infructueuse. » |
| « Restaurer la version du 26/09 21:04 ? Le mapping actuel sera archivé. » | « Restaurer ? » |

Une règle invalide n'est jamais acceptée silencieusement : chaque erreur de validation nomme le champ et la correction attendue.

## Component Patterns

Comportement. Les specs visuelles vivent dans `DESIGN.md` §Components — mêmes noms de composants que ce tableau.

| Component | Utilisation | Règles comportementales |
|---|---|---|
| Ligne de périphérique (`periph-row`) | Onglet Périphériques | Ligne = nom, `usage_id`, mapping courant. Recherche filtre en temps réel sur nom et `usage_id`. Badge (`badge-modified`) si le périphérique est touché par la dernière règle en vigueur : point de teinte + icône, `aria-label` obligatoire « modifié par la règle {nom}, {date} » — jamais un signal uniquement chromatique. Action « Créer une règle pour ce périphérique » sur chaque ligne : bascule sur l'onglet Règles avec le `usage_id` pré-rempli. Sur mobile : la ligne se replie en deux niveaux (identité / mapping), le badge reste visible. |
| Champ de formulaire de règle (`rule-form-field`) | Onglet Règles | Un formulaire par règle (condition `usage_id`/regex + mapping : entité HA, `device_class`, unité, `state_class`, priorité). Autocomplete temps réel (`eedomus/get_suggestions` ; suggestions de schéma via `eedomus/get_schema`) ; validation à la frappe via `eedomus/validate_config`. Sauvegarde unique en bas de formulaire, désactivée tant que la validation ne passe pas. |
| Éditeur YAML (`yaml-editor`) | Onglet Règles | Coloration syntaxique YAML complète + validation temps réel. Bascule formulaire ↔ YAML sans perte (le YAML reflète l'état du formulaire et réciproquement). Une règle invalide est signalée avant sauvegarde — jamais acceptée silencieusement. Lib légère vendorisée minifiée dans `www/`, à trancher à l'implémentation (CodeMirror complet exclu : trop lourd). **Critère de sélection avant vendorisation** : la lib doit être opérable au clavier complet et accessible aux lecteurs d'écran (texte exposé à l'AT, erreurs annoncées `aria-live` avec numéro de ligne — sinon repli `<textarea>`). La bascule formulaire ↔ YAML préserve le focus et annonce le changement de mode. |
| Lignes de diff (`diff-line-added` / `diff-line-removed` / `diff-line-modified`) | Onglet Historique config | Diff entre la version sélectionnée et la précédente. Le texte est en couleur de texte primaire du thème ; la sémantique est portée par le fond teinté, les préfixes `+` / `-` / `~` (vrai nœud texte) et la barre gauche (specs visuelles : voir `DESIGN.md` §Components). Critère de contraste : voir DESIGN.md §Colors. |
| Carte de version (`version-card`) | Onglet Historique config | 3 cartes maximum, horodatées, de la plus récente à la plus ancienne. Chaque carte : horodatage, résumé du changement, bouton « Restaurer ». La version courante porte l'état « actuelle » et ne peut pas être restaurée sur elle-même. Restaurer = deux gestes : clic, puis confirmation « Restaurer la version du {date} ? Le mapping actuel sera archivé. » ; l'application suit le chemin CAP-4 avec le même feedback nominatif que la sauvegarde, et la version remplacée est archivée. La 4e sauvegarde purge la plus ancienne. |
| Tableau de cohérence (`coherence-table`) | Onglet Cohérence | Tableau plat, sans regroupement : une ligne par périphérique, tri par colonne, en-tête collant au défilement, filtre rapide texte, bascule « Tout afficher » / « À vérifier ». Contrat de données (comportemental ; l'implémentation backend n'est pas prescrite) : la donnée vient d'une nouvelle commande websocket `eedomus/get_coherence` (convention : voir Foundation), chargée en différé à l'ouverture de l'onglet — squelettes pendant l'appel, reprise par « Réessayer » en cas d'échec (voir State Patterns). Vue strictement en lecture : le tableau signale, il n'édite pas — chaque correctif se fait ailleurs (onglet Règles, réglages HA). |
| Puce de statut de cohérence (`coherence-chip`) | Onglet Cohérence | Un à plusieurs signaux par périphérique, cumulables et listés : « sans entité HA » (`entity_id` null), « mapping douteux » (pas d'état vivant ni d'unité, `device_class` discutable), « règle active » (`modified_by_rule`), « en erreur/retry ». Chaque puce est icône + texte — jamais un signal uniquement chromatique (spec visuelle : voir `DESIGN.md` §Components). En vue « Tout afficher », un périphérique sans signal porte la puce « cohérent ». |
| Popover de périphérique (`periph-popover`) | Onglet Cohérence (desktop) | Au survol du `periph_id` : popover riche. État vivant (valeur courante, `usage_id`, pièce/parent, dernière mise à jour) ; identité de mapping (`ha_entity`, `ha_subtype`, justification) ; actions de correctif inline (« Créer une règle » → onglet Règles, `usage_id` pré-rempli, via le chemin existant ; « Config HA » → page de réglages standard de l'entité HA) ; champs bruts de l'API eedomus en section secondaire repliable à deux niveaux : la liste triée clé→valeur (lisibilité), puis le JSON brut du payload coordinator en dessous — ordre des clés d'origine, le document tel que mis en cache par le coordinator, sans tri ni transformation — avec un bouton « Copier le JSON » (bouton standard HA, retour de copie annoncé via le pattern d'annonce existant ; parité mobile : voir Responsive). |
| En-tête de tri (`sort-header`) | Onglet Cohérence | Bouton de tri focusable dans chaque en-tête de colonne du tableau de cohérence (comportement complet dans Interaction Primitives — Tri de colonnes). |
| Lien d'entité HA (`entity-link`) | Onglet Cohérence | L'entité HA de chaque ligne est un lien texte inline vers la page de réglages standard de l'entité HA — un lien, pas un contrôle d'édition. Opérable au clavier, focus visible, destination portée par le libellé de l'entité. |
| Carte de graphique de métrique (`metric-chart-card`) | Onglet Supervision | Une carte par métrique box (temps de refresh, nombre de périphériques, sollicitations de l'API proxy), alimentée par les métriques du coordinator. Priorité aux composants de graphique du frontend HA exposés dans le contexte du panneau — les plus natifs ; repli SVG inline thémé (variables CSS HA uniquement) si un composant n'est pas disponible ; disponibilité à vérifier à l'implémentation. Chaque valeur porte un équivalent textuel (voir Accessibility). |
| File de backfill (`backfill-queue`) | Onglet Supervision | Une ligne par périphérique en récupération d'historique : `periph_id`, nom, statut — en attente / en cours / en erreur / ignoré / en pause. Quatre actions par ligne : « Réessayer maintenant », « Prioriser » (remonter dans la file), « Pause » / « Reprendre », « Ignorer ». Contrat comportemental : les actions passent par de nouvelles commandes websocket backend (convention : voir Foundation) — l'implémentation backend n'est pas prescrite. « Ignorer » est destructif : confirmation deux gestes. Chaque action donne un retour nominatif, puis la file est re-rendue. Périmètre : le domaine du backfill vit dans `spec-eedomus-history` ; ces actions étendent ce spec (note de périmètre), sans le dupliquer ici. |

## State Patterns

| État | Surface | Traitement |
|---|---|---|
| Vide — aucun périphérique | Périphériques | « Aucun périphérique détecté. Vérifiez que l'intégration eedomus est configurée. » Aucune action locale (la donnée vient du coordinator). |
| Vide — aucune règle | Règles | « Aucune règle de mapping. Le mapping par défaut s'applique. » + action primaire « Créer une règle ». |
| Vide — aucune version | Historique config | « Aucune sauvegarde encore. La première sauvegarde archivera la version courante. » |
| Vide — rien à vérifier | Cohérence | État vide positif : « Tout est cohérent. Aucun périphérique à vérifier. » + bascule « Tout afficher » pour parcourir le tableau complet. Le vide est une bonne nouvelle, pas une erreur. |
| Filtre sans résultat | Cohérence | « Aucun périphérique ne correspond à “{requête}”. » — aucune ligne, mais l'état est explicite et annoncé en `aria-live` ; effacer le filtre ou basculer « Tout afficher » restitue le tableau. Jamais un tableau vide sans explication. |
| Filtre sans résultat — Périphériques | Périphériques | « Aucun périphérique ne correspond à “{requête}”. » — aucune ligne, mais l'état est explicite et annoncé en `aria-live` ; effacer la recherche ou désactiver « Périphériques touchés » restitue la liste. Jamais une liste vide sans explication. |
| Une seule version | Historique config | Première sauvegarde : pas de version précédente, pas de diff. La carte affiche horodatage et résumé seuls, avec « Première version — le diff apparaîtra à la prochaine sauvegarde. » |
| Chargement | Tous | Squelettes (skeletons) au format du contenu attendu — lignes de liste, champs de formulaire, cartes de version, lignes du tableau de cohérence, cartes de graphique et lignes de la file de backfill. Se résout à l'arrivée des données. |
| Erreur de validation | Règles (formulaire + YAML) | Temps réel, dans le champ : message en `{colors.error}` nommant le champ et la correction attendue. Bouton de sauvegarde désactivé. Jamais d'acceptation silencieuse. |
| Sauvegarde en cours | Règles | Bouton en état occupé (spinner), champs verrouillés. Message court : « Sauvegarde… » |
| Rechargement après save | Règles | Après persistance dans le HA storage (canon, AD-13) et réplication du miroir `custom_mapping.yaml`, l'intégration se recharge automatiquement : message « Application… » puis confirmation nominative — « Règle appliquée. {entité} est maintenant {unité}. » Le feedback est le contrat : le changement est visible immédiatement, sans redémarrage ni action manuelle. Une édition manuelle du fichier miroir prend le même chemin : ingérée comme nouvelle version au rechargement suivant, visible dans l'Historique config. |
| Erreur de sauvegarde | Règles | Toast d'erreur : le contenu édité est conservé dans le formulaire, rien n'est perdu, bouton de nouvelle tentative. L'erreur nomme la cause quand le backend la donne. |
| Erreur de commande websocket | Tous | Message d'état dans la zone concernée, bouton « Réessayer ». Jamais de spinner infini. |
| Erreur — commande de cohérence | Cohérence | Même pattern que l'erreur de commande websocket : message d'état dans la zone du tableau, bouton « Réessayer ». Un tableau à moitié chargé n'est jamais présenté comme complet. |
| Vide — rien à récupérer | Supervision | État vide positif : « Tout est récupéré. Aucun historique en attente. » Le vide est une bonne nouvelle, pas une erreur — même discipline que « Vide — rien à vérifier » de la Cohérence. |
| Erreur — métriques ou file indisponibles | Supervision | Même pattern que l'erreur de commande websocket : message d'état dans la zone concernée (cartes ou file), bouton « Réessayer ». Jamais de graphique ou de file à moitié chargés présentés comme complets. |

## Interaction Primitives

- **Recherche** — champ de filtrage en tête de l'onglet Périphériques ; filtre temps réel sur nom et `usage_id` ; insensible à la casse ; résultat compté (« 12 périphériques »). Filtre « Périphériques touchés » : son activation et son compte de résultats sont annoncés en `aria-live`.
- **Autocomplete** — dans le formulaire de règle sur `usage_id`, `device_class` et unité : suggestions via le schéma (voir Component Patterns) ; navigation clavier (flèches + Entrée), suggestion sélectionnable au toucher.
- **Tri de colonnes** — onglet Cohérence : chaque en-tête de colonne est un bouton de tri focusable ; clics successifs → croissant, décroissant, neutre ; l'état est exposé par `aria-sort` sur la cellule d'en-tête. Le tri réordonne localement les données déjà chargées, sans nouvel appel réseau.
- **Bascule « Tout afficher » / « À vérifier »** — l'état « À vérifier » restreint le tableau aux périphériques portant au moins un signal ; activation et compte de résultats annoncés en `aria-live`, même pattern que le filtre « Périphériques touchés ».
- **Popover de périphérique** — le `periph_id` de la ligne est le déclencheur : focusable, opérable au clavier (`Entrée` ouvre), `aria-expanded` sur le déclencheur. À l'ouverture, le focus est piégé dans le popover (`Tab` boucle dedans) ; `Échap` referme et rend le focus au déclencheur. Une seule ouverture à la fois : ouvrir un autre popover referme le premier.
- **Save + auto-apply** — un seul geste persiste ET applique : save → persistance `config_manager` → rechargement auto de l'intégration → feedback nominatif sur l'entité concernée (voir « Rechargement après save »). Pas de bouton « recharger » séparé à demander à l'utilisateur.
- **Restauration** — deux gestes depuis une carte de version : « Restaurer », puis confirmation (« Le mapping actuel sera archivé. ») ; même chemin d'application que la sauvegarde, même feedback.
- **Suppression de règle** — deux gestes : clic sur « Supprimer », puis confirmation « Supprimer la règle {nom} ? » — même discipline que la restauration destructrice ; feedback nominatif après suppression.
- **Actions de backfill** — sur chaque ligne de la file de l'onglet Supervision, opérables au clavier de bout en bout (les quatre actions : voir Component Patterns). « Ignorer » exige deux gestes : clic, puis confirmation « Ignorer {nom} ? Sa récupération sera abandonnée. » Chaque action donne un retour nominatif, puis la file est re-rendue — jamais d'action muette.
- **Lien d'onglet interne** — le lien « Voir le tableau de cohérence » de l'onglet Supervision bascule sur l'onglet Cohérence via le mécanisme de hash existant de la navigation d'onglets ; retour/arrière fonctionnel.
- **Clavier** — `Tab` suit l'ordre de lecture, `Échap` referme/annule, Entrée soumet depuis l'autocomplete. Le panneau est entièrement opérable au clavier.

Interdit partout : accepter une entrée invalide en silence, permettre l'édition sans que la sauvegarde soit désactivée, laisser tourner un spinner sans issue (toujours un état d'erreur avec reprise).

## Responsive & Platform

Parité desktop + mobile engagée : tout ce qui est éditable sur desktop l'est sur mobile — rien n'est différé en lecture seule. Le panneau vit dans la zone de contenu HA et suit son reflow ; pas de breakpoints propriétaires.

- **Onglets** — conservés sur mobile (jamais masqués ni repliés en menu), hauteur ≥ 44 px, cibles espacées de 8 px.
- **Périphériques** — la ligne se replie en deux niveaux (identité / mapping), le badge reste visible ; l'action de ligne couvre la pleine hauteur de la zone tactile.
- **Formulaire de règle** — mono-colonne sur mobile ; colonne unique largeur max ~760 px sur desktop ; cibles ≥ 44 px, autocomplete et restauration confortables au pouce.
- **Éditeur YAML** — sur petits viewports, le scroll horizontal est admis (mono non retouché), avec focus visible en débordement ; jamais de troncature silencieuse du contenu.
- **Vue diff** — reflow avec la colonne ; les lignes longues défilent horizontalement comme l'éditeur YAML, préfixe et barre gauche toujours visibles.
- **Cohérence** — le survol n'existe pas au toucher : la ligne de périphérique s'étend à la demande et montre exactement le même contenu que le popover desktop (état vivant, identité de mapping, actions « Créer une règle » / « Config HA », champs bruts repliables) — parité de contenu, surface différente. Tri, filtre et bascule restent opérables ; cibles ≥ 44 px ; l'en-tête reste collant au défilement.
- **Supervision** — les cartes de graphique se recomposent avec la largeur de la zone de contenu (une colonne sur mobile, plusieurs sur desktop) ; les lignes de la file gardent leurs quatre actions opérables, cibles ≥ 44 px, l'action de ligne couvre la pleine hauteur de la zone tactile.

## Accessibility Floor

Comportemental. Le contraste visuel vit dans `DESIGN.md` — il dérive du thème HA de l'utilisateur. Le panneau ne spécifie par lui-même qu'une seule exigence de contraste : le texte du diff sur son fond teinté, et elle porte un critère explicite.

- Contraste : le texte du diff est en couleur de texte primaire du thème (contraste hérité) — discipline sémantique : voir DESIGN.md §Colors.
- Focus visible sur tout élément interactif (outline du thème), jamais supprimé ; ordre de `Tab` = ordre de lecture.
- Cibles tactiles ≥ 44 px sur mobile — parité d'édition oblige : le formulaire, l'autocomplete et la restauration sont confortables au pouce.
- Annonces `aria-live` sur : résultats de validation temps réel, fin de sauvegarde/application, erreurs, activation et compte du filtre « Périphériques touchés », activation et compte de la bascule « Tout afficher » / « À vérifier ».
- Le diff porte son sens par la couleur ET par les préfixes `+` / `-` / `~` (vrai nœud texte) et la barre gauche — chaque type de ligne porte un glyphe distinct ; jamais la couleur seule.
- Équivalent textuel partout où la couleur porte du sens : badge avec `aria-label` « modifié par la règle {nom}, {date} », filtre « Périphériques touchés » comme équivalent de liste.
- Le popover de périphérique est opérable au clavier de bout en bout : déclencheur focusable avec `aria-expanded`, focus piégé pendant l'ouverture, `Échap` referme, focus rendu au déclencheur.
- Les puces de statut de cohérence ne portent jamais leur sens par la couleur seule : chaque puce est icône + texte ; plusieurs signaux par périphérique sont listés, jamais fusionnés en un signal unique.
- Les graphiques de Supervision portent un équivalent textuel : chaque valeur est aussi lisible en texte ou en tableau — le graphique n'est jamais l'unique porteur de l'information.
- Les quatre actions de la file de backfill sont opérables au clavier de bout en bout ; « Ignorer » suit le schéma de confirmation deux gestes au clavier comme au pointeur.
- Le statut d'une ligne de la file n'est jamais porté par la couleur seule : chaque statut (en attente, en cours, en erreur, ignoré, en pause) est un texte explicite.

## Key Flows

### Flow 1 — Corriger une unité erronée (un utilisateur type de HACS, issu de la discussion #28, un soir, sur ordinateur)

1. Il constate qu'un capteur de température affiche une unité erronée dans HA. Il ne veut pas ouvrir un fichier YAML à la main.
2. Barre latérale → panneau « Eedomus Config ». L'onglet Périphériques se charge ; il tape le nom du capteur dans la recherche.
3. La liste se réduit à quelques lignes ; il voit le mapping courant du périphérique — l'entité HA, son `device_class`, l'unité fautive.
4. Il crée une règle depuis le formulaire : condition sur le `usage_id` (autocomplete), `device_class` température, unité corrigée. La validation temps réel passe ; le bouton de sauvegarde s'active.
5. Il sauvegarde. « Sauvegarde… » puis « Application… »
6. **Climax :** l'entité se corrige sous ses yeux — la confirmation nomme le capteur et sa nouvelle unité, et le mapping affiché sur la ligne du périphérique reflète le changement immédiatement. Pas de redémarrage, pas de rechargement manuel : le panneau a tenu sa promesse.
7. Le lendemain, il ouvre l'onglet Historique config : la carte de version de la veille affiche son horodatage, et le diff montre sa ligne ajoutée — préfixe `+`, fond teinté, barre verte à gauche. Il réalise que l'unité corrigée casse une automatisation ; il clique « Restaurer », confirme (« Restaurer la version du 26/09 21:04 ? Le mapping actuel sera archivé. ») et la version précédente s'applique avec le même feedback nominatif que la sauvegarde.

Échec : s'il tape une unité invalide à l'étape 4, la validation temps réel la signale dans le champ (« “degré” attendu, “degres” saisi ») et la sauvegarde reste désactivée — l'erreur ne peut pas atteindre le mapping. Si la sauvegarde échoue à l'étape 5, le formulaire conserve la règle et propose une nouvelle tentative.

### Flow 2 — Éditer en YAML brut (même utilisateur, depuis son téléphone)

1. Il ouvre l'onglet Règles et bascule l'éditeur en mode YAML brut ; le YAML reflète l'état du formulaire, le focus est préservé et le changement de mode est annoncé.
2. Il colle un bloc de mapping venu d'un ancien fichier ; la validation temps réel signale « ligne 12 : clé dupliquée » (annoncée `aria-live`), la sauvegarde reste désactivée.
3. Il corrige la ligne ; le retour au formulaire via la bascule montre exactement la même règle — le roundtrip n'a rien perdu.
4. **Climax :** il sauvegarde — même chemin que Flow 1 : « Sauvegarde… », « Application… », confirmation nominative. Le YAML collé depuis l'ancien fichier est appliqué sans rien perdre, depuis son téléphone.

Échec : un YAML qui ne peut pas round-tripper proprement (clés dupliquées, structure ambiguë) est refusé avant sauvegarde avec son numéro de ligne ; jamais d'acceptation silencieuse.

### Flow 3 — Dépannage express (Dan, une automatisation ne se déclenche plus, un soir, sur ordinateur)

1. Une automatisation du chauffage ne s'est pas déclenchée ce soir. Dan ne sait pas si la faute vient de l'automatisation, du capteur eedomus ou du mapping.
2. Barre latérale → panneau « Eedomus Config » → onglet « Cohérence ». Les squelettes du tableau cèdent la place aux ~165 périphériques ; la bascule « À vérifier » est déjà active.
3. Il tape le nom du périphérique dans le filtre rapide : le tableau se réduit à la ligne du capteur, qui porte une puce « mapping douteux ».
4. Il survole le `periph_id` : le popover montre l'état vivant — plus aucune valeur depuis 14 h, l'entité HA n'a plus d'état vivant — et l'identité de mapping, intacte, qui n'y est pour rien.
5. **Climax :** la cause est identifiée en deux clics. Le popover lui dit où agir : il clique « Config HA » et atterrit sur la page de réglages de l'entité — le problème est côté intégration, pas dans ses règles. Variante : si l'entité était absente, « Créer une règle » le basculerait sur l'onglet Règles, `usage_id` pré-rempli, via le chemin existant.
6. Une fois la cause corrigée, il rouvre l'onglet « Cohérence » : la puce a disparu ; en vue « Tout afficher », la ligne porte « cohérent ».

Échec : si la commande de cohérence échoue à l'étape 2, la zone du tableau affiche le message d'état avec « Réessayer » — jamais de spinner infini, jamais de tableau à moitié chargé présenté comme complet.

### Flow 4 — Surveiller la box et débloquer un backfill (Dan, un soir, sur ordinateur)

1. Un soir, Dan ouvre le panneau « Eedomus Config » → onglet « Supervision ». Les cartes de graphique se chargent : temps de refresh stables d'un cycle à l'autre, nombre de périphériques au complet, sollicitations de l'API proxy dans l'ordre de grandeur habituel — la box ne demande rien.
2. Un mapping l'intrigue : il suit le lien « Voir le tableau de cohérence » vers l'onglet Cohérence (retour/arrière fonctionnel), survole le `periph_id` — l'identité de mapping est saine, la faute n'est pas là — puis revient sur Supervision.
3. Sous les métriques, la file de backfill montre un périphérique « en erreur » : sa récupération d'historique est bloquée, le statut est un texte explicite, jamais la couleur seule.
4. Il clique « Prioriser » : le périphérique remonte dans la file.
5. **Climax :** la file est re-rendue avec le périphérique en tête, et la récupération repart immédiatement pour lui — le retour nominatif nomme le périphérique, sans rechargement ni action ailleurs.

Échec : si « Prioriser » échoue, un message d'erreur nominatif s'affiche dans la zone de la file ; la file reste cohérente avec l'état réel du backfill, et un bouton « Réessayer » propose de retenter — jamais d'action muette ni de file qui ment sur son état.
