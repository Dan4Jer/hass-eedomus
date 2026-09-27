# Review Accessibilité — panneaux eedomus

- **Sources** : `DESIGN.md` et `EXPERIENCE.md` (`ux-hass-eedomus-2026-09-27/`), status draft.
- **Méthode** : revue adverse des spines de design (documents, pas du code). Référentiels : WCAG 2.2 niveau AA (contraste 1.4.3/1.4.11, clavier 2.1.1, cibles 2.5.8, statuts 4.1.3), WAI-ARIA Authoring Practices (tabs, combobox), cible tactile 44 px (Apple HIG / Android Material).
- **Postulat produit** : intégration HACS grand public — le floor d'accessibilité n'est pas négociable ; ~165 périphériques, parité desktop + mobile exigée, historique diff coloré = exigence forte.
- **Prérequis honorable** : l'héritage du thème HA est le bon choix architectural (pas de hex, pas de palette locale). Le problème n'est pas l'héritage — c'est ce que les spines demandent *au* thème.

## Verdict global

**Ne pas implémenter tel quel.** Le floor déclaré dans `EXPERIENCE.md › Accessibility Floor` repose sur une hypothèse fausse (« les couleurs sémantiques standard [du thème HA] sont assumées conformes ») : HA n'utilise `--success-color` / `--error-color` / `--warning-color` que pour icônes et badges graphiques (seuil 3:1), jamais comme couleur de texte courant. Utilisées comme couleur de texte de diff, elles échouent AA dans le thème clair par défaut de HA. Trois autres trous majeurs : les lignes « modifiées » n'ont **aucun signal redondant** (exigence produit violée pour les daltoniens), le badge n'a **aucun équivalent textuel** pour lecteurs d'écran, et aucun pattern ARIA (tabs, combobox, diff) n'est spécifié.

## Findings

### [critical] C1 — Le texte de diff en couleur sémantique n'est pas lisible AA, en clair surtout ; le fond teinté aggrave le delta

**Localisation** : `DESIGN.md` › frontmatter `components.diff-line-added/removed/modified` + `Colors › Sémantique diff` ; `EXPERIENCE.md` › `Accessibility Floor` (ligne « les couleurs de diff … sont des couleurs sémantiques du thème HA »).

**Finding** : le texte des lignes de diff est rendu en `var(--success/error/warning-color)` sur un fond `color-mix(… 12%, var(--card-background-color))`. Deux défaillances se combinent :

1. Les couleurs sémantiques HA ne sont pas calibrées pour du texte. À titre d'illustration sur le thème clair par défaut (fond blanc) : le warning orange (`#ff9800`) tombe à ≈ 2:1, le success vert (`#43a047`) à ≈ 3:1, l'error rouge (`#db4437`) à ≈ 4:1 — tous sous le 4.5:1 AA exigé pour du texte courant en police mono de corps normal. En thème sombre par défaut, le vert/orange passé sur fond sombre est meilleur, mais rien ne le garantit pour les milliers de thèmes tiers.
2. Teinter le fond avec **la même teinte** que le texte *réduit* le contraste par rapport à un fond de carte brut : mélanger 12 % de la couleur du texte dans le fond rapproche leurs luminances. La construction « lisibles en clair et en sombre par construction » est fausse dans les deux sens.

C'est le contenu principal de l'onglet Historique — l'exigence produit « historique VISIBLE en couleurs » échoue à la fois pour l'œil standard en thème clair et pour l'exigence AA.

**Fix suggéré** (option A recommandée) : inverser le portage — texte du diff en `var(--primary-text-color)` (contraste hérité du thème, garanti), sémantique portée par **fond teinté + préfixe + éventuelle barre gauche 3 px** en couleur sémantique. Option B si le texte coloré est non négociable : fonction de garde à l'exécution qui éclaircit/assombrit la couleur (color-mix avec blanc/noir) jusqu'à ≥ 4.5:1 mesuré contre le fond rendu. Dans tous les cas, supprimer l'affirmation « assumées conformes » de l'`Accessibility Floor` et la remplacer par un critère testable : « contraste mesuré ≥ 4.5:1 sur les thèmes clair et sombre par défaut de HA ≥ 2026, plus 2 thèmes tiers populaires ».

### [high] H2 — Lignes « modifiées » : la couleur est le SEUL signal (préfixe `~` absent)

**Localisation** : `EXPERIENCE.md` › `Component Patterns › Vue diff type git` et `EXPERIENCE.md` › `Accessibility Floor` (« le diff porte son sens par la couleur ET par les préfixes `+`/`-` ») ; `DESIGN.md` › `Components › Lignes de diff`.

**Finding** : les spines spécifient des préfixes `+` / `-` (ajout/suppression) mais **rien pour les modifications** — `{colors.diff-modified}` (warning) ne reçoit ni préfixe, ni icône, ni soulignement. Conséquences : (a) une ligne modifiée est indistinguable d'une ligne de contexte pour tout le monde au balayage rapide ; (b) la seule differentiation est chromatique ; (c) le floor d'accessibilité affirme « jamais la couleur seule » alors que sa propre spec ne le garantit que pour 2 types sur 3. Pour les ~8 % d'hommes daltoniens (deutéranopes surtout), ajouts/suppressions sont sauvés par `+`/`-`, mais « modifié » reste invisible.

**Fix suggéré** : préfixe `~` (ou `↻`) sur les lignes modifiées, rendu visuellement **et** dans l'arbre accessible ; vérifier que le préfixe est bien un vrai nœud texte (pas un pseudo-élément `::before` invisible aux lecteurs d'écran). Compléter le floor : « chaque type de ligne porte un glyphe distinct : `+`, `-`, `~` ».

### [high] H3 — Badge de modification sans nom accessible : lecteur d'écran = zéro information

**Localisation** : `DESIGN.md` › `Components › Badge de modification` (« un point discret plutôt qu'un pavé ») ; `EXPERIENCE.md` › `Information Architecture › Périphériques` et `Component Patterns › Liste de périphériques`.

**Finding** : le badge est spécifié comme pur signal visuel — forme, couleur, position (« à droite ») — sans aucun équivalent textuel. Rien ne dit s'il contient du texte, une icône, ou n'est qu'un point coloré. Un utilisateur lecteur d'écran ne saura jamais quels périphériques sont touchés par la dernière règle, alors que c'est un des deux signaux originaux du produit et une exigence forte (« badge sur les périphériques touchés »). « Se remarque au balayage visuel » exclut de fait les non-voyants du balayage.

**Fix suggéré** : spécifier un contenu accessible obligatoire : `role="img"` ou `role="status"` + `aria-label="Touché par la dernière modification"` (texte visible court ou texte `sr-only` + icône crayon dans la pill). Fournir de plus un équivalent de liste : filtre « Périphériques touchés par la dernière règle » et/ou phrase résumée en tête d'onglet (« 4 périphériques modifiés par la dernière règle »), annoncée `aria-live` à l'arrivée des données.

### [high] H4 — Badge : contraste accent/texte et accent/fond de carte non garantis, signal uniquement chromatique

**Localisation** : `DESIGN.md` › frontmatter `components.badge-modified` (`accent` / `accent-contrast`) et `Colors › Accent` ; `DESIGN.md` › `Components › Ligne de périphérique`.

**Finding** : (a) le couple `--accent-color` / `--text-accent-color` dépend entièrement du thème : le cœur HA ne force aucun ratio, et de nombreux thèmes tiers très populaires définissent un accent décoratif sans vérifier la lisibilité du texte posé dessus — le texte du badge peut tomber sous 4.5:1. (b) Contraste non textuel (WCAG 1.4.11) : un accent pastel d'un thème clair doux peut être < 3:1 contre `--card-background-color` — le badge devient quasi invisible pour la basse vision, précisément ceux qui en ont besoin. (c) Le signal est un point de teinte unique, sans icône ni texte : pas de redondance de forme.

**Fix suggéré** : ajouter au floor un critère mesurable (« badge ≥ 4.5:1 texte/fond et ≥ 3:1 fond/carte sur les thèmes par défaut + 2 thèmes tiers ») avec garde à l'exécution si requis ; mettre une icône blanche/noire adaptée dans la pill (redondance de forme) ; si le thème rend le badge illisible, prévoir un repli sur filet `--divider` + icône `--primary-text-color`.

### [medium] M5 — Diff sans équivalent structuré pour lecteurs d'écran

**Localisation** : `EXPERIENCE.md` › `Information Architecture › Historique`, `Component Patterns › Vue diff type git`.

**Finding** : le diff est spécifié comme rendu visuel uniquement. Les préfixes `+`/`-` seront lus caractère par caractère (« plus… ») sans sémantique de ligne ; aucun résumé (« 2 ajouts, 1 suppression, 3 modifications ») n'est spécifié ; pas de structure de liste annoncée ; pas de lien entre la ligne de diff et le périphérique concerné.

**Fix suggéré** : spécifier : résumé `sr-only` en tête de diff (`role="status"`), chaque ligne portant un libellé accessible (« ligne ajoutée : … » / « ligne modifiée : … »), le tout dans une `list` sémantique ou un tableau avec en-têtes `sr-only` (type de changement / contenu). Prévoir le reflow de ce résumé visible en option (bénéficie aussi à la vue défaillante).

### [medium] M6 — Onglets : pattern ARIA APG non spécifié

**Localisation** : `EXPERIENCE.md` › `Information Architecture › Onglets`, `Interaction Primitives › Onglets` et `Clavier`.

**Finding** : « trois onglets, état reflété dans l'URL, opérable au clavier » — mais rien sur les rôles (`tablist`/`tab`/`tabpanel`, `aria-selected`, `aria-controls`), ni la navigation par flèches du pattern APG, ni l'annonce de l'état actif. Si les onglets sont des liens d'URL stylés, `Tab` seul ne révèle pas la surface active à un lecteur d'écran. Le focus visible est bien exigé globalement, mais l'onglet actif doit aussi être *annoncé*.

**Fix suggéré** : spécifier le pattern APG tabs complet (flèches gauche/droite, `aria-selected`, `tabpanel` associé) ou l'usage d'un composant natif HA équivalent ; focus déplacé sur le panneau au changement d'onglet, URL synchronisée sans pièger le focus.

### [medium] M7 — Autocomplete : pattern combobox non spécifié (et `Échap` ambigu)

**Localisation** : `EXPERIENCE.md` › `Interaction Primitives › Autocomplete` et `Clavier` (« `Échap` referme/annule ») ; `DESIGN.md` › `Components › Champ de formulaire de règle`.

**Finding** : « navigation clavier (flèches + Entrée), suggestion sélectionnable au toucher » ne suffit pas : pas de `aria-expanded`, pas de `role="listbox"/"option"`, pas d'`aria-activedescendant`, pas de restitution du focus. « `Échap` referme/annule » est dangereusement vague : annule quoi ? le formulaire entier ? Un `Échap` mal scópé pendant l'autocomplete peut vider le champ ou fermer le panneau.

**Fix suggéré** : spécifier le pattern APG combobox avec listbox : `aria-expanded`, `aria-controls`, `aria-activedescendant`, `role="option"` + `aria-selected` par suggestion ; `Échap` referme **la liste uniquement**, focus et saisie conservés dans le champ ; `Home`/`End` sur la liste. Documenter ce comportement dans `Interaction Primitives`.

### [medium] M8 — Validation de formulaire : câblage ARIA non spécifié

**Localisation** : `EXPERIENCE.md` › `Component Patterns › Formulaire de règle`, `State Patterns › Erreur de validation` ; `DESIGN.md` › `Components › Champ de formulaire de règle`.

**Finding** : l'erreur temps réel est « dans le champ, en `{colors.error}`, nommant le champ et la correction » et annoncée `aria-live` — bon point. Mais rien sur : association `<label for>` / `aria-label` par champ, `aria-invalid="true"` sur le champ en erreur, `aria-describedby` liant le message au champ, gestion du focus (où va le focus quand une erreur apparaît / quand on soumet). Un message d'erreur en `aria-live` global sans association au champ reste désynchronisé pour un utilisateur NVDA/VoiceOver qui navigue champ par champ. Le bouton de sauvegarde désactivé comme seul garde-fou est acceptable mais ne dispense pas de l'association.

**Fix suggéré** : compléter `State Patterns › Erreur de validation` : chaque champ a un `label` persistant ; à l'erreur : `aria-invalid` + `aria-describedby` → message ; à la soumission bloquée : focus sur le premier champ en erreur ; le message d'erreur ne repose jamais sur la couleur seule (il porte déjà du texte — le garantir dans le floor).

### [medium] M9 — Éditeur YAML : accessibilité lecteur d'écran non garantie par la lib vendorisée

**Localisation** : `EXPERIENCE.md` › `Component Patterns › Éditeur YAML` (« lib légère vendorisée minifiée… à trancher à l'implémentation »).

**Finding** : les éditeurs de code légers (CodeMirror-like, contenteditable/`div`) sont notoirement inaccessibles aux lecteurs d'écran : pas de curseur annoncé, navigation caractière impossible, erreurs de validation muettes si mal câblées. La spine rejette CodeMirror pour son poids sans poser de critère d'accessibilité pour la lib de remplacement, et ne spécifie aucun repli. Le mode YAML est un échappatoire fonctionnel au formulaire — s'il est SR-hostile, l'édition complète l'est aussi.

**Fix suggéré** : ajouter au critère de sélection de la lib : opérable au clavier complet, texte accessible à l'AT (ou repli `<textarea>` + validation diff apply), erreurs de validation annoncées via `aria-live` avec numéro de ligne ; le toggle formulaire ↔ YAML doit préserver le focus et annoncer le changement de mode.

### [medium] M10 — Recherche : le compteur et le refiltrage temps réel ne sont pas annoncés

**Localisation** : `EXPERIENCE.md` › `Interaction Primitives › Recherche` (« filtre temps réel… résultat compté ("12 périphériques") »).

**Finding** : pendant la frappe, la liste se réécrit à chaque touche. Sans `role="status"`/`aria-live` sur le compteur ni `aria-busy` sur la liste, un utilisateur lecteur d'écran ne sait ni que la liste a changé, ni combien de résultats il y a — il tape dans le vide.

**Fix suggéré** : compteur en `role="status"` (polite), annoncé à l'arrivée des résultats ; la liste filtrée portée `aria-label="Périphériques filtrés"` ; ne pas déplacer le focus pendant la frappe.

### [medium] M11 — Skeletons de chargement : silence pour lecteurs d'écran

**Localisation** : `EXPERIENCE.md` › `State Patterns › Chargement`.

**Finding** : les skeletons sont purement visuels. Sans `aria-busy="true"` sur la zone ni annonce textuelle, un lecteur d'écran présente un panneau vide sans explication — indistinguable de l'état « Vide — aucun périphérique ».

**Fix suggéré** : `aria-busy` + texte `sr-only` « Chargement des périphériques… » en `role="status"` sur chaque zone ; skeletons décoratifs (`aria-hidden`). Distinguer explicitement l'état chargé-vide du chargement-en-cours dans le DOM.

### [medium] M12 — Restauration en un clic : ni confirmation ni annulation, activation accidentelle non couverte

**Localisation** : `EXPERIENCE.md` › `Information Architecture › Historique`, `Component Patterns › Carte de version avec restauration` (« Restauration en un clic »), `Interaction Primitives › Restauration`.

**Finding** : restaurer remplace le mapping en vigueur et archive — c'est une action à fort impact sur un système domestique, exécutée sans confirmation ni annulation, sur mobile, sur un bouton voisin d'autres cibles. Pour les utilisateurs à motricité réduite ou tremblements (et simplement en mobilité), une activation accidentelle écrase l'état courant. La seule protection est l'archive — qui purge la 4e version : deux erreurs successives détruisent l'historique.

**Fix suggéré** : confirmation explicite (« Restaurer la version du 26/09 21:04 ? Le mapping actuel sera archivé. ») avec gestion du focus (dialog ARIA, focus piégé, retour au bouton à la fermeture), **ou** pattern undo : toast `role="status"` « Version restaurée — Annuler » avec fenêtre d'annulation. Bouton ≥ 44 px avec espacement des cibles voisines.

### [medium] M13 — Cibles tactiles : le floor dit ≥ 44 px mais les specs composants ne le garantissent pas

**Localisation** : `EXPERIENCE.md` › `Accessibility Floor` (« cibles ≥ 44 px ») vs `DESIGN.md` › `Components › Badge de modification` (« point discret ») ; `EXPERIENCE.md` › `Component Patterns › Liste de périphériques` (action par ligne, repli mobile en deux niveaux) ; `Interaction Primitives › Autocomplete`, `Onglets`.

**Finding** : le floor est déclaratif, aucune spec de composant ne l'applique, et certaines le contredisent : (a) le badge « point discret » — s'il devient interactif (ex. filtrer les touchés), il fera bien moins de 44 px ; (b) les suggestions d'autocomplete doivent être des lignes ≥ 44 px — non spécifié ; (c) sur mobile, l'action « Créer une règle pour ce périphérique » du repli en deux niveaux n'a ni taille ni position spécifiée ; (d) la barre d'onglets conservée sur mobile : hauteur non spécifiée.

**Fix suggéré** : épingler par composant : badge non interactif **ou** zone d'impact ≥ 44 px via padding transparent ; suggestions autocomplete ≥ 44 px de haut ; action de ligne = pleine hauteur de zone tactile avec `aria-label` nominatif (« Créer une règle pour Salon Température ») ; onglets ≥ 44 px ; bouton « Restaurer » ≥ 44 px + 8 px d'espacement des voisins.

### [medium] M14 — Fond de ligne teinté à 12 % : possiblement imperceptible (contraste non textuel)

**Localisation** : `DESIGN.md` › `Components › diff-line-*` et `Colors › Sémantique diff` (« le ratio de teinte 12 % est un point de départ »).

**Finding** : 12 % d'une couleur sémantique dans un fond de carte peut passer sous le seuil 3:1 de contraste non textuel (WCAG 1.4.11) — surtout en thème sombre, où success vert teinté dans un fond sombre reste très discret. Le surlignage du bloc modifié devient alors invisible pour la basse vision ; il ne resterait que le préfixe et la couleur du texte (déjà en échec, voir C1). Le « [ASSUMPTION] point de départ » n'est suivi d'aucun critère de vérification.

**Fix suggéré** : doubler le teintage d'une barre gauche 3 px en couleur sémantique (signal de forme + position, insensible au thème) ; remplacer l'assumption par un critère : teinte ≥ 3:1 contre le fond de carte sur les thèmes par défaut clair et sombre, sinon monter à 16–20 %.

### [low] L15 — `prefers-reduced-motion` non spécifié

**Localisation** : `EXPERIENCE.md` › `State Patterns › Chargement` (skeletons), `Sauvegarde en cours` (spinner), toasts.

**Finding** : skeletons animés (pulse), spinner, apparition des toasts : aucune mention de `prefers-reduced-motion`. Le vertige vestibulaire (WCAG 2.3.3, grand public inclus) n'est pas couvert par le floor.

**Fix suggéré** : une ligne au floor : toute animation décorative (pulse de skeleton, transitions de toast) se désactive sous `prefers-reduced-motion: reduce` ; les skeletons deviennent des blocs statiques, le spinner un texte d'état.

### [low] L16 — Zoom 200 % / reflow mobile non testés

**Localisation** : `DESIGN.md` › `Layout & Spacing` (colonne ~760 px) ; `EXPERIENCE.md` › `Foundation` (parité desktop + mobile), `Éditeur YAML`.

**Finding** : WCAG 1.4.4 (zoom 200 %) et 1.4.10 (reflow 320 px sans scroll bidimensionnel) ne figurent nulle part, ni dans le floor ni comme critère de test. L'éditeur YAML sur mobile pose un scroll horizontal par nature (mono non-retchou), acceptable *si* spécifié.

**Fix suggéré** : ajouter au floor : utilisable à 200 % de zoom ; contenu reflow à 320 px sauf l'éditeur YAML/diff, où le scroll horizontal est explicitement admis avec focus visible en débordement.

### [low] L17 — Mécanisme de sélection de version du diff non spécifié

**Localisation** : `EXPERIENCE.md` › `Information Architecture › Historique` (« la version sélectionnée »).

**Finding** : « la version sélectionnée » suppose un sélecteur non décrit. Un widget custom mal balisé serait inopérable au clavier et muet pour l'AT.

**Fix suggéré** : spécifier un contrôle natif (`<select>`, ou radio group ARIA) reliant version ↔ diff affiché, avec annonce du changement.

## Ce que les spines ont déjà de correct (à conserver)

- Héritage total du thème HA, interdiction des hex et des palettes locales — la bonne architecture.
- Préfixes `+`/`-` sur ajouts/suppressions (redondance chromatique partielle).
- Focus visible jamais supprimé, `Tab` = ordre de lecture, panneaux opérables au clavier.
- `aria-live` prévu sur validation, fin de save/application, erreurs.
- Floor ≥ 44 px déclaré, erreurs toujours textuelles et nominatives, aucun spinner sans issue.
- Compteur de résultats de recherche prévu (il ne manque que l'annonce — M10).

## Recommandation de sortie

Bloquer le passage à l'implémentation jusqu'à : correction de C1 (stratégie de contraste du diff), ajout du préfixe `~` (H2), spécification du nom accessible du badge (H3) et du plan de contraste du badge (H4). Les findings medium sont spécifiables dans les deux spines en une passe ; les low peuvent être traités au moment du floor d'implémentation, sauf M9 (critère de sélection de la lib YAML) qui doit être tranché avant vendorisation.
