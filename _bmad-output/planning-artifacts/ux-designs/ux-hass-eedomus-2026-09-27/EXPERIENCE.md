---
name: Eedomus Config
status: final
updated: 2026-09-27
sources:
  - _bmad-output/specs/spec-eedomus-mapping-panel/SPEC.md
---

# EXPERIENCE.md — Eedomus Config

## Références visuelles

Les mocks des trois écrans clés vivent dans `mockups/` (bascule clair/sombre incluse pour la vérification du contraste) :

- `mockups/mock-01-peripheriques.html` — onglet Périphériques : liste, filtre, badge « modifié », raccourci vers les règles
- `mockups/mock-02-regles.html` — onglet Règles : bascule Formulaire/YAML, validation temps réel
- `mockups/mock-03-historique.html` — onglet Historique : cartes de version, restauration confirmée, diff type git (traitement C1)

Les spines priment sur tout mock en cas de conflit.

## Foundation

Panneau web dans la barre latérale de Home Assistant (« Eedomus Config »), réservé aux administrateurs (`require_admin`). **Parité desktop + mobile** : l'édition du mapping doit être confortable sur téléphone, pas seulement consultable. Le système UI est le **thème HA** — `DESIGN.md` est la référence d'identité visuelle et nomme la couche sémantique (diff, badge) ; cette spine ne décrit que le comportement. Frontend JS vanilla sans toolchain de build, thémé par les variables CSS HA.

## Information Architecture

Trois onglets, conservés sur mobile (contenu adaptatif — jamais un onglet masqué ou replié en menu).

| Surface | Contenu |
|---|---|
| **Périphériques** | Entrée du parcours. Liste des ~165 périphériques eedomus avec nom, `usage_id` et mapping courant (entité HA, `device_class`, unité), lus depuis `coordinator.data`. Recherche/filtrage par nom ou `usage_id`, plus filtre « Périphériques touchés » — équivalent textuel du badge, annoncé en `aria-live`. Badge `{components.badge-modified}` sur les périphériques touchés par la dernière modification. |
| **Règles** | Éditeur du mapping custom en deux modes : formulaire structuré par règle (création, modification, suppression) et édition YAML brut avec coloration syntaxique et validation temps réel. Autocomplete `usage_id` / `device_class` / unité via `eedomus/get_suggestions` et `eedomus/get_schema`. |
| **Historique** | Les 3 dernières versions horodatées du mapping (`.storage` HA). Vue diff type git entre la version sélectionnée et la précédente (`{components.diff-line-added}` / `{components.diff-line-removed}` / `{components.diff-line-modified}`). Restauration confirmée : elle emprunte le chemin d'application du save et archive la version remplacée. |

Onglets = navigation de premier niveau ; l'état de l'onglet actif se reflète dans l'URL du panneau (retour/arrière fonctionne entre onglets). Depuis une ligne de périphérique, l'action « Créer une règle pour ce périphérique » bascule sur l'onglet Règles avec le formulaire pré-rempli du `usage_id`.

## Voice and Tone

Microcopie en français, sobre, orientée erreur utile. La voix du panneau est celle d'un assistant technique : dire précisément quoi, pourquoi, et quoi corriger.

| Do | Don't |
|---|---|
| « Unité invalide : \"degré\" attendu, \"degres\" saisi. » | « Erreur dans le formulaire. » |
| « Règle appliquée. sensor.tempureau est maintenant en °C. » | « Succès ! » |
| « 3 versions conservées. La plus ancienne est purgée à la prochaine sauvegarde. » | « Historique limité. » |
| « Aucun périphérique ne correspond à \"temp\". » | « Recherche infructueuse. » |
| « Restaurer la version du 26/09 21:04 ? Le mapping actuel sera archivé. » | « Restaurer ? » |

Une règle invalide n'est jamais acceptée silencieusement : chaque erreur de validation nomme le champ et la correction attendue.

## Component Patterns

Comportement. Les specs visuelles vivent dans `DESIGN.md.Components` — mêmes noms de composants que cette table.

| Component | Utilisation | Règles comportementales |
|---|---|---|
| Ligne de périphérique (`periph-row`) | Onglet Périphériques | Ligne = nom, `usage_id`, mapping courant. Recherche filtre en temps réel sur nom et `usage_id`. Badge (`badge-modified`) si le périphérique est touché par la dernière modification en vigueur : point + icône, `aria-label` obligatoire « modifié par la règle {nom}, {date} » — jamais un signal uniquement chromatique. Action « Créer une règle pour ce périphérique » sur chaque ligne : bascule sur l'onglet Règles avec le `usage_id` pré-rempli. Sur mobile : la ligne se replie en deux niveaux (identité / mapping), le badge reste visible. |
| Champ de formulaire de règle (`rule-form-field`) | Onglet Règles | Un formulaire par règle (condition `usage_id`/regex + mapping : entité HA, `device_class`, unité, `state_class`, priorité). Autocomplete temps réel (`eedomus/get_suggestions`) ; validation à la frappe via `eedomus/validate_config`. Sauvegarde unique en bas de formulaire, désactivée tant que la validation ne passe pas. |
| Éditeur YAML (`yaml-editor`) | Onglet Règles | Coloration syntaxique YAML complète + validation temps réel. Bascule formulaire ↔ YAML sans perte (le YAML reflète l'état du formulaire et réciproquement). Une règle invalide est signalée avant sauvegarde — jamais acceptée silencieusement. Lib légère vendorisée minifiée dans `www/`, à trancher à l'implémentation (CodeMirror complet exclu : trop lourd). **Critère de sélection avant vendorisation** : la lib doit être opérable au clavier complet et accessible aux lecteurs d'écran (texte exposé à l'AT, erreurs annoncées `aria-live` avec numéro de ligne — sinon repli `<textarea>`). La bascule formulaire ↔ YAML préserve le focus et annonce le changement de mode. |
| Lignes de diff (`diff-line-added` / `diff-line-removed` / `diff-line-modified`) | Onglet Historique | Diff entre la version sélectionnée et la précédente. Le texte est en couleur de texte primaire du thème ; la sémantique est portée par le fond teinté, les préfixes `+` / `-` / `~` (vrai nœud texte) et la barre gauche (specs visuelles dans DESIGN.md). Critère d'acceptation : texte ≥ 4.5:1 sur son fond teinté, vérifié en thème clair et sombre. |
| Carte de version (`version-card`) | Onglet Historique | 3 cartes maximum, horodatées, de la plus récente à la plus ancienne. Chaque carte : horodatage, résumé du changement, bouton « Restaurer ». La version active porte l'état « actuelle » et n'offre pas de restauration sur elle-même. Restaurer = deux gestes : clic, puis confirmation « Restaurer la version du {date} ? Le mapping actuel sera archivé. » ; l'application suit le chemin CAP-4 avec le même feedback nominatif que le save, et la version remplacée est archivée. La 4e sauvegarde purge la plus ancienne. |

## State Patterns

| État | Surface | Traitement |
|---|---|---|
| Vide — aucun périphérique | Périphériques | « Aucun périphérique détecté. Vérifiez que l'intégration eedomus est configurée. » Aucune action locale (la donnée vient du coordinator). |
| Vide — aucune règle | Règles | « Aucune règle de mapping. Le mapping par défaut s'applique. » + action primaire « Créer une règle ». |
| Vide — aucune version | Historique | « Aucune sauvegarde encore. La première sauvegarde archivera la version courante. » |
| Une seule version | Historique | Première sauvegarde : pas de version précédente, pas de diff. La carte affiche horodatage et résumé seuls, avec « Première version — le diff apparaîtra à la prochaine sauvegarde. » |
| Chargement | Tous | Squelettes (skeletons) au format du contenu attendu — lignes de liste, champs de formulaire, cartes de version. Résout à l'arrivée des données. |
| Erreur de validation | Règles (formulaire + YAML) | Temps réel, dans le champ : message en `{colors.error}` nommant le champ et la correction attendue. Bouton de sauvegarde désactivé. Jamais d'acceptation silencieuse. |
| Sauvegarde en cours | Règles | Bouton en état occupé (spinner), champs verrouillés. Message court : « Sauvegarde… » |
| Rechargement après save | Règles | Après persistance dans `custom_mapping.yaml`, l'intégration se recharge automatiquement : message « Application… » puis confirmation nominative — « Règle appliquée. {entité} est maintenant {unité}. » Le feedback est le contrat : le changement est visible immédiatement, sans redémarrage ni action manuelle. |
| Erreur de sauvegarde | Règles | Toast d'erreur : le contenu édité est conservé dans le formulaire, rien n'est perdu, bouton de nouvelle tentative. L'erreur nomme la cause quand le backend la donne. |
| Erreur de commande websocket | Tous | Message d'état dans la zone concernée, bouton « Réessayer ». Jamais de spinner infini. |

## Interaction Primitives

- **Recherche** — champ de filtrage en tête de l'onglet Périphériques ; filtre temps réel sur nom et `usage_id` ; insensible à la casse ; résultat compté (« 12 périphériques »). Filtre « Périphériques touchés » : son activation et son compte de résultats sont annoncés en `aria-live`.
- **Autocomplete** — dans le formulaire de règle sur `usage_id`, `device_class` et unité : suggestions issues de `eedomus/get_suggestions` et du schéma (`eedomus/get_schema`) ; navigation clavier (flèches + Entrée), suggestion sélectionnable au toucher.
- **Onglets** — trois surfaces persistantes, état réfléchi dans l'URL, conservées sur mobile.
- **Save + auto-apply** — un seul geste persiste ET applique : save → persistance `config_manager` → rechargement auto de l'intégration → feedback nominatif sur l'entité concernée (voir « Rechargement après save »). Pas de bouton « recharger » séparé à demander à l'utilisateur.
- **Restauration** — deux gestes depuis une carte de version : « Restaurer », puis confirmation (« Le mapping actuel sera archivé. ») ; même chemin d'application que le save, même feedback.
- **Clavier** — `Tab` suit l'ordre de lecture, `Échap` referme/annule, Entrée soumet depuis l'autocomplete. Le panneau est entièrement opérable au clavier.

Interdit partout : accepter une entrée invalide en silence, éditer sans désactiver le save, spinner sans issue (toujours un état d'erreur avec reprise).

## Responsive & Platform

Parité desktop + mobile engagée : tout ce qui est éditable sur desktop l'est sur mobile — rien n'est différé en lecture seule. Le panneau vit dans la zone de contenu HA et suit son reflow ; pas de breakpoints propriétaires.

- **Onglets** — conservés sur mobile (jamais masqués ni repliés en menu), hauteur ≥ 44 px, cibles espacées de 8 px.
- **Périphériques** — la ligne se replie en deux niveaux (identité / mapping), le badge reste visible ; l'action de ligne couvre la pleine hauteur de zone tactile.
- **Formulaire de règle** — mono-colonne sur mobile ; colonne unique largeur max ~760 px sur desktop ; cibles ≥ 44 px, autocomplete et restauration confortables au pouce.
- **Éditeur YAML** — sur petits viewports, le scroll horizontal est admis (mono non retouché), avec focus visible en débordement ; jamais de troncature silencieuse du contenu.
- **Vue diff** — reflow avec la colonne ; les lignes longues défilent horizontalement comme l'éditeur YAML, préfixe et barre gauche toujours visibles.

## Accessibility Floor

Comportemental. Le contraste visuel vit dans `DESIGN.md` — il dérive du thème HA de l'utilisateur. Le panneau ne crie qu'une seule paire de contraste par lui-même : le texte du diff sur son fond teinté, et elle porte un critère explicite.

- Contraste : le texte du diff est en couleur de texte primaire du thème (contraste hérité) ; les couleurs sémantiques du thème portent uniquement teintes de fond et barres gauche — usage seuil 3:1 (icônes, fonds), jamais couleur de texte. **Critère d'acceptation** : texte du diff ≥ 4.5:1 sur son fond teinté, vérifié sur les thèmes clair et sombre par défaut de HA — c'est le calage de l'assumption des 12 % de `DESIGN.md`.
- Focus visible sur tout élément interactif (outline du thème), jamais supprimé ; ordre de `Tab` = ordre de lecture.
- Cibles tactiles ≥ 44 px sur mobile — parité d'édition oblige : le formulaire, l'autocomplete et la restauration sont confortables au pouce.
- Annonces `aria-live` sur : résultats de validation temps réel, fin de sauvegarde/application, erreurs, activation et compte du filtre « Périphériques touchés ».
- Le diff porte son sens par la couleur ET par les préfixes `+` / `-` / `~` (vrai nœud texte) et la barre gauche — chaque type de ligne porte un glyphe distinct ; jamais la couleur seule.
- Équivalent textuel partout où la couleur porte du sens : badge avec `aria-label` « modifié par la règle {nom}, {date} », filtre « Périphériques touchés » comme équivalent de liste.

## Key Flows

### Flow 1 — Corriger une unité erronée (l'utilisateur HACS type de la discussion #28, un soir, sur ordinateur)

1. Il constate qu'un capteur de température affiche une unité erronée dans HA. Il ne veut pas ouvrir un fichier YAML à la main.
2. Barre latérale → panneau « Eedomus Config ». L'onglet Périphériques se charge ; il tape le nom du capteur dans la recherche.
3. La liste se réduit à quelques lignes ; il voit le mapping courant du périphérique — l'entité HA, son `device_class`, l'unité fautive.
4. Il crée une règle depuis le formulaire : condition sur le `usage_id` (autocomplete), `device_class` température, unité corrigée. La validation temps réel passe ; le bouton de sauvegarde s'active.
5. Il sauvegarde. « Sauvegarde… » puis « Application… »
6. **Climax :** l'entité se corrige sous ses yeux — la confirmation nomme le capteur et sa nouvelle unité, et le mapping affiché sur la ligne du périphérique reflète le changement immédiatement. Pas de redémarrage, pas de rechargement manuel : le panneau a tenu sa promesse.
7. Le lendemain, il ouvre l'onglet Historique : la carte de version de la veille affiche son horodatage, et le diff montre sa ligne ajoutée — préfixe `+`, fond teinté, barre verte à gauche. Il réalise que l'unité corrigée casse une automatisation ; il clique « Restaurer », confirme (« Restaurer la version du 26/09 21:04 ? Le mapping actuel sera archivé. ») et la version précédente s'applique avec le même feedback nominatif que le save.

Échec : s'il tape une unité invalide à l'étape 4, la validation temps réel la signale dans le champ (« \"degré\" attendu, \"degres\" saisi ») et le save reste désactivé — l'erreur ne peut pas atteindre le mapping. Si le save échoue à l'étape 5, le formulaire conserve la règle et propose une nouvelle tentative.

### Flow 2 — Éditer en YAML brut (même utilisateur, depuis son téléphone)

1. Il ouvre l'onglet Règles et bascule l'éditeur en mode YAML brut ; le YAML reflète l'état du formulaire, le focus est préservé et le changement de mode est annoncé.
2. Il colle un bloc de mapping venu d'un ancien fichier ; la validation temps réel signale « ligne 12 : clé dupliquée » (annoncée `aria-live`), le save reste désactivé.
3. Il corrige la ligne ; la bascule retour au formulaire montre exactement la même règle — le roundtrip n'a rien perdu.
4. Il sauvegarde : même chemin que Flow 1 — « Sauvegarde… », « Application… », confirmation nominative.

Échec : un YAML qui ne peut pas round-tripper proprement (clés dupliquées, structure ambiguë) est refusé avant sauvegarde avec son numéro de ligne ; jamais d'acceptation silencieuse.
