# Validation Report — hass-eedomus

- **DESIGN.md:** `_bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/DESIGN.md`
- **EXPERIENCE.md:** `_bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md`
- **Run at:** 2026-09-27

## Overall verdict

La paire `DESIGN.md` + `EXPERIENCE.md` est proche d'un contrat consommable (« near-consumable ») selon le rubric walker : la discipline des tokens est excellente (toute référence `{path.to.token}` des deux fichiers résout vers un token du frontmatter de DESIGN.md, y compris les références croisées d'EXPERIENCE.md), et la posture delta-only « le thème HA est le design system » est tenue de bout en bout. Elle n'est toutefois pas complète : EXPERIENCE.md manque sa section **Responsive & Platform** alors que la parité desktop + mobile est une décision engagée et porteuse, les tables de composants des deux fichiers ne partagent pas leurs noms, et le mode d'édition YAML — la moitié de CAP-3 — n'a aucun key flow. Une addition structurelle plus un alignement de nommage avant de passer à l'architecture / story-dev.

La lens accessibilité décale ce verdict vers le bas : le floor d'accessibilité déclaré dans EXPERIENCE.md repose sur une hypothèse fausse (« les couleurs sémantiques standard [du thème HA] sont assumées conformes ») — HA n'utilise ces couleurs que pour icônes et badges graphiques, jamais comme couleur de texte courant. Utilisées comme couleur de texte de diff, elles échouent AA 4.5:1 en thème clair par défaut. Par ailleurs, les lignes « modifiées » n'ont aucun signal redondant (exigence produit violée pour les daltoniens), le badge de modification n'a aucun équivalent textuel pour lecteurs d'écran, et aucun pattern ARIA (tabs, combobox, diff) n'est spécifié.

**Verdict global : ne pas implémenter tel quel.** Le critical **C1** (contraste du texte de diff) doit être résolu **avant l'implémentation**, avec H2 (préfixe `~` sur les lignes modifiées), H3 (nom accessible du badge) et H4 (plan de contraste du badge). Les findings medium sont spécifiables dans les deux spines en une passe ; les low peuvent attendre le floor d'implémentation, sauf M9 (critère de sélection de la lib YAML) à trancher avant vendorisation. Comptes : rubric — 0 critical, 1 high, 5 medium, 7 low (8 findings de niveau low listés, tous repris ici) ; accessibilité — 1 critical, 3 high, 10 medium, 3 low.

## Category verdicts

- Flow coverage — **adequate**
- Token completeness — **strong**
- Component coverage — **adequate**
- State coverage — **adequate**
- Visual reference coverage — **strong** (vacuously clean — aucun mockup, aucune référence pendante)
- Bloat & overspecification — **strong**
- Inheritance discipline — **adequate**
- Shape fit — **thin**
- Accessibilité — **ne pas implémenter tel quel** (1 critical, 3 high ; bloquer le passage à l'implémentation jusqu'à C1 + H2 + H3 + H4)

## Findings by severity

### Critical (1)

**[Accessibilité — contraste diff]** — C1 : le texte de diff en couleur sémantique n'est pas lisible AA, en clair surtout ; le fond teinté aggrave le delta
Localisation : `DESIGN.md › components.diff-line-*` + `Colors › Sémantique diff` ; `EXPERIENCE.md › Accessibility Floor`.
Le texte des lignes de diff est rendu en `var(--success/error/warning-color)` sur un fond `color-mix(… 12%, var(--card-background-color))`. Ces couleurs sémantiques HA ne sont pas calibrées pour du texte (warning ≈ 2:1, success ≈ 3:1, error ≈ 4:1 sur le thème clair par défaut — tous sous le 4.5:1 AA), et teinter le fond avec la même teinte que le texte *réduit* le contraste en rapprochant leurs luminances. La construction « lisibles en clair et en sombre par construction » est fausse dans les deux sens ; c'est le contenu principal de l'onglet Historique.
Fix : option A recommandée — texte du diff en `var(--primary-text-color)` (contraste hérité garanti), sémantique portée par fond teinté + préfixe + barre gauche 3 px. Option B si le texte coloré est non négociable : garde à l'exécution éclaircissant/assombrissant jusqu'à ≥ 4.5:1 mesuré contre le fond rendu. Dans tous les cas, remplacer « assumées conformes » par un critère testable : « contraste mesuré ≥ 4.5:1 sur les thèmes clair et sombre par défaut de HA ≥ 2026, plus 2 thèmes tiers populaires ».

### High (4)

**[Shape fit — rubric]** — Responsive & Platform manquant d'EXPERIENCE.md
La parité desktop + mobile est une décision engagée et porteuse (« l'édition de mapping doit être confortable sur téléphone aussi »). Ce qui existe est dispersé et partiel : reflow mobile de periph-row, onglets conservés sur mobile, cibles 44 px. Pas de contrat de breakpoints, pas de comportement mobile par surface, et surtout aucun traitement mobile des deux surfaces les plus dures : l'éditeur YAML et le popup d'autocomplete au clavier tactile. Ce gap avale aussi le parcours témoin mobile (aucun flow n'édite sur téléphone).
Fix : ajouter la section Responsive & Platform : breakpoints (ou comportement de largeur de panneau HA), layout mobile par onglet, éditeur YAML sur petits viewports, autocomplete au toucher, et ce qui est explicitement différé en lecture seule mobile le cas échéant.

**[Accessibilité — diff]** — H2 : lignes « modifiées », la couleur est le SEUL signal (préfixe `~` absent)
Localisation : `EXPERIENCE.md › Vue diff type git` + `Accessibility Floor` ; `DESIGN.md › Lignes de diff`.
Les spines spécifient des préfixes `+`/`-` mais rien pour les modifications : `{colors.diff-modified}` ne reçoit ni préfixe, ni icône, ni soulignement. Une ligne modifiée est indistinguable d'une ligne de contexte au balayage rapide, la seule différenciation est chromatique, et le floor affirme « jamais la couleur seule » alors que sa propre spec ne le garantit que pour 2 types sur 3. Pour les ~8 % d'hommes daltoniens, « modifié » reste invisible.
Fix : préfixe `~` (ou `↻`) sur les lignes modifiées, rendu visuellement et dans l'arbre accessible (vrai nœud texte, pas un pseudo-élément `::before` muet). Compléter le floor : « chaque type de ligne porte un glyphe distinct : `+`, `-`, `~` ».

**[Accessibilité — badge]** — H3 : badge de modification sans nom accessible — lecteur d'écran = zéro information
Localisation : `DESIGN.md › Badge de modification` ; `EXPERIENCE.md › IA › Périphériques` + `Component Patterns › Liste de périphériques`.
Le badge est spécifié comme pur signal visuel — forme, couleur, position — sans aucun équivalent textuel. Un utilisateur lecteur d'écran ne saura jamais quels périphériques sont touchés par la dernière règle, alors que c'est un des deux signaux originaux du produit. « Se remarque au balayage visuel » exclut de fait les non-voyants du balayage.
Fix : contenu accessible obligatoire : `role="img"` ou `role="status"` + `aria-label="Touché par la dernière modification"` (texte visible court ou `sr-only` + icône). Plus un équivalent de liste : filtre « Périphériques touchés par la dernière règle » et/ou phrase résumée en tête d'onglet (« 4 périphériques modifiés par la dernière règle »), annoncée `aria-live`.

**[Accessibilité — badge]** — H4 : badge — contraste accent/texte et accent/fond de carte non garantis, signal uniquement chromatique
Localisation : `DESIGN.md › components.badge-modified` (`accent`/`accent-contrast`), `Colors › Accent`, `Ligne de périphérique`.
(a) Le couple `--accent-color`/`--text-accent-color` dépend entièrement du thème : le cœur HA ne force aucun ratio, et de nombreux thèmes tiers populaires définissent un accent décoratif sans lisibilité du texte posé dessus (texte < 4.5:1 possible). (b) Contraste non textuel (WCAG 1.4.11) : un accent pastel peut être < 3:1 contre `--card-background-color` — badge quasi invisible pour la basse vision. (c) Point de teinte unique, sans icône ni texte : pas de redondance de forme.
Fix : critère mesurable au floor (« badge ≥ 4.5:1 texte/fond et ≥ 3:1 fond/carte sur les thèmes par défaut + 2 thèmes tiers ») avec garde à l'exécution si requis ; icône adaptée dans la pill (redondance de forme) ; repli sur filet `--divider` + icône `--primary-text-color` si le thème rend le badge illisible.

### Medium (15)

**[Flow coverage]** — Aucun key flow n'exerce le mode d'édition YAML brut ni l'aller-retour formulaire ↔ YAML
« Bascule formulaire ↔ YAML sans perte » (Component Patterns, Éditeur YAML) est la moitié de CAP-3 et une garantie comportementale engagée ; un story-dev n'a aucun parcours témoin montrant le roundtrip préservant l'état ou gérant un YAML qui ne round-trip pas proprement.
Fix : ajouter un Flow 2 compact (édition YAML → validation → sauvegarde), ou une annexe de chemin d'échec à Flow 1.

**[Token completeness]** — La combinaison critique pour le contraste créée par le panneau — texte de diff en `{colors.diff-*}` sur fond teinté 12 % — n'a aucune cible de contraste
L'héritage du thème ne peut pas se porter garant de cette paire car la teinte est inventée par le panneau. Le ratio 12 % est marqué `[ASSUMPTION]` mais aucun seuil d'acceptance (ex. WCAG AA 4.5:1) n'est énoncé, donc un story-dev ne peut pas écrire de test.
Fix : ajouter une cible de contraste à la spec du composant diff-line et la nommer comme vérification à l'implémentation de l'hypothèse 12 %.

**[Component coverage]** — Les noms de composants ne sont pas identiques entre les deux fichiers, et la granularité diffère
`periph-row` (« Ligne de périphérique ») vs « Liste de périphériques » ; `rule-form-field` (« Champ de formulaire de règle ») vs « Formulaire de règle » ; `diff-line-*` vs « Vue diff type git ». Un consommateur partant de la table EXPERIENCE doit deviner l'appariement vers les specs visuelles DESIGN. Seuls `yaml-editor` ↔ « Éditeur YAML » et `version-card` ↔ « Carte de version » sont quasi verbatim.
Fix : ajouter le nom de token DESIGN entre parenthèses à chaque ligne EXPERIENCE (ou aligner les noms outright).

**[State coverage]** — L'état à une version de l'Historique n'est pas spécifié
Le diff est défini « entre la version sélectionnée et la précédente » ; avec exactement une version archivée il n'y a pas de précédent, et State Patterns ne couvre que zéro version (« Aucune sauvegarde encore »). Un story-dev rencontrera ce cas dès la première vraie sauvegarde.
Fix : ajouter une ligne d'état : 1 version → pas de diff disponible, carte en résumé seul (ou diff désactivé avec explication).

**[Shape fit]** — Inspiration & Anti-patterns manquant
Sa moitié anti-patterns est partiellement couverte par « Interdit partout » et le Do/Don't de Voice, mais les inspirations/précédents qui ancrent les jugements (précédents diff-view, conventions de panneau HA suivies) sont absents.
Fix : courte section — même trois puces (conventions de panneau HA reprises ; convention git-diff ; alternatives rejetées) — ou plier « Interdit partout » dedans explicitement.

**[Accessibilité — diff]** — M5 : diff sans équivalent structuré pour lecteurs d'écran
Le diff est spécifié comme rendu visuel uniquement : préfixes lus caractère par caractère sans sémantique de ligne, aucun résumé (« 2 ajouts, 1 suppression, 3 modifications »), pas de structure de liste, pas de lien ligne ↔ périphérique concerné.
Fix : résumé `sr-only` en tête de diff (`role="status"`), libellé accessible par ligne (« ligne ajoutée : … »), `list` sémantique ou tableau avec en-têtes `sr-only` (type de changement / contenu).

**[Accessibilité — tabs]** — M6 : onglets — pattern ARIA APG non spécifié
« Trois onglets, état reflété dans l'URL, opérable au clavier » — mais rien sur `tablist`/`tab`/`tabpanel`, `aria-selected`, `aria-controls`, ni la navigation par flèches du pattern APG. Si les onglets sont des liens d'URL stylés, `Tab` seul ne révèle pas la surface active à un lecteur d'écran.
Fix : spécifier le pattern APG tabs complet (flèches gauche/droite, `aria-selected`, `tabpanel` associé, focus déplacé sur le panneau) ou l'usage d'un composant natif HA équivalent ; URL synchronisée sans piéger le focus.

**[Accessibilité — autocomplete]** — M7 : autocomplete — pattern combobox non spécifié, et `Échap` ambigu
Pas d'`aria-expanded`, pas de `role="listbox"`/`option`, pas d'`aria-activedescendant`, pas de restitution du focus. « `Échap` referme/annule » est dangereusement vague : annule quoi ? Un `Échap` mal scopé pendant l'autocomplete peut vider le champ ou fermer le panneau.
Fix : pattern APG combobox avec listbox (`aria-expanded`, `aria-controls`, `aria-activedescendant`, `role="option"` + `aria-selected`) ; `Échap` referme la liste uniquement, focus et saisie conservés ; `Home`/`End` sur la liste. Documenter dans Interaction Primitives.

**[Accessibilité — formulaire]** — M8 : validation de formulaire — câblage ARIA non spécifié
L'erreur temps réel est annoncée `aria-live` (bon point), mais rien sur l'association `<label for>`/`aria-label` par champ, `aria-invalid="true"` sur le champ en erreur, `aria-describedby` liant le message au champ, ni la gestion du focus à l'apparition d'erreur / à la soumission. Un message en `aria-live` global sans association reste désynchronisé pour NVDA/VoiceOver naviguant champ par champ.
Fix : compléter State Patterns — label persistant par champ ; à l'erreur : `aria-invalid` + `aria-describedby` → message ; à la soumission bloquée : focus sur le premier champ en erreur ; le message ne repose jamais sur la couleur seule.

**[Accessibilité — YAML]** — M9 : éditeur YAML — accessibilité non garantie par la lib vendorisée
Les éditeurs de code légers (CodeMirror-like, contenteditable) sont notoirement inaccessibles aux lecteurs d'écran : curseur non annoncé, navigation caractière impossible, erreurs muettes. La spine rejette CodeMirror pour son poids sans poser de critère d'accessibilité pour la lib de remplacement, ni de repli. Le mode YAML est l'échappatoire fonctionnel au formulaire — s'il est SR-hostile, l'édition complète l'est aussi.
Fix : ajouter au critère de sélection de la lib : opérable au clavier complet, texte accessible à l'AT (ou repli `<textarea>`), erreurs annoncées via `aria-live` avec numéro de ligne ; le toggle formulaire ↔ YAML préserve le focus et annonce le changement de mode.

**[Accessibilité — recherche]** — M10 : recherche — le compteur et le refiltrage temps réel ne sont pas annoncés
Pendant la frappe, la liste se réécrit à chaque touche. Sans `role="status"`/`aria-live` sur le compteur ni `aria-busy` sur la liste, un lecteur d'écran ne sait ni que la liste a changé, ni combien de résultats il y a.
Fix : compteur en `role="status"` (polite) annoncé à l'arrivée des résultats ; liste filtrée `aria-label="Périphériques filtrés"` ; ne pas déplacer le focus pendant la frappe.

**[Accessibilité — loading]** — M11 : skeletons de chargement — silence pour lecteurs d'écran
Les skeletons sont purement visuels. Sans `aria-busy="true"` ni annonce textuelle, un lecteur d'écran présente un panneau vide — indistinguable de l'état « Vide — aucun périphérique ».
Fix : `aria-busy` + texte `sr-only` « Chargement des périphériques… » en `role="status"` par zone ; skeletons décoratifs (`aria-hidden`). Distinguer explicitement chargé-vide vs chargement-en-cours dans le DOM.

**[Accessibilité — restauration]** — M12 : restauration en un clic — ni confirmation ni annulation, activation accidentelle non couverte
Restaurer remplace le mapping en vigueur et archive — action à fort impact, sans confirmation ni annulation, sur mobile, sur un bouton voisin d'autres cibles. Pour les utilisateurs à motricité réduite, une activation accidentelle écrase l'état courant ; la seule protection (l'archive) purge la 4e version — deux erreurs successives détruisent l'historique.
Fix : confirmation explicite avec gestion du focus (dialog ARIA, focus piégé, retour au bouton), **ou** pattern undo : toast `role="status"` « Version restaurée — Annuler ». Bouton ≥ 44 px avec espacement des cibles voisines.

**[Accessibilité — cibles]** — M13 : cibles tactiles — le floor dit ≥ 44 px mais les specs composants ne le garantissent pas
Le floor est déclaratif et aucune spec de composant ne l'applique ; certaines le contredisent : badge « point discret » s'il devient interactif ; suggestions d'autocomplete sans hauteur spécifiée ; action « Créer une règle pour ce périphérique » du repli mobile sans taille ni position ; barre d'onglets mobile sans hauteur.
Fix : épingler par composant : badge non interactif **ou** zone d'impact ≥ 44 px (padding transparent) ; suggestions autocomplete ≥ 44 px ; action de ligne = pleine hauteur de zone tactile avec `aria-label` nominatif ; onglets et « Restaurer » ≥ 44 px + 8 px d'espacement.

**[Accessibilité — contraste]** — M14 : fond de ligne teinté à 12 % — possiblement imperceptible (contraste non textuel)
12 % d'une couleur sémantique dans un fond de carte peut passer sous le seuil 3:1 de WCAG 1.4.11 — surtout en thème sombre. Le surlignage du bloc modifié devient invisible pour la basse vision ; il ne resterait que le préfixe et la couleur du texte (déjà en échec, cf. C1). L'`[ASSUMPTION]` n'est suivie d'aucun critère de vérification.
Fix : doubler le teintage d'une barre gauche 3 px en couleur sémantique (signal de forme + position, insensible au thème) ; remplacer l'assumption par un critère : teinte ≥ 3:1 contre le fond de carte sur les thèmes clair et sombre par défaut, sinon monter à 16–20 %.

### Low (11)

**[Flow coverage]** — La restauration n'apparaît que conditionnellement (subjonctif) au Flow 1, étape 7
« S'il s'était trompé, un clic sur "Restaurer" remettrait la version précédente » — non démontré, alors que la restauration de CAP-5 est une action de premier plan avec sémantique d'archive.
Fix : faire de l'étape 7 une vraie action du flow, ou ajouter un flow de restauration en deux étapes.

**[Token completeness]** — `{colors.success}` et `{colors.warning}` sont définis mais jamais référencés ; ils dupliquent `{colors.diff-added}` / `{colors.diff-modified}`
Un consommateur ne peut pas dire quel token utiliser pour un signal succès/warning hors diff.
Fix : les supprimer, ou une ligne stating qu'ils sont les alias sémantiques panneau-wide, diff-* réservé à la vue historique.

**[Component coverage]** — `badge-modified` a une ligne visuelle dans DESIGN.md mais pas de ligne comportementale dédiée dans EXPERIENCE.md
Son comportement est plié dans « Liste de périphériques ». Le badge porte la sémantique porteuse « touché par la dernière règle » (décision memlog 1).
Fix : extraire une ligne badge avec règles d'apparition, de disparition et de survie au reload.

**[Component coverage]** — Le champ de recherche a un comportement spécifié mais aucun foyer visuel — absent de DESIGN.md.Components
Son héritage du style input HA (via `rule-form-field`) est impliqué mais non énoncé.
Fix : une ligne dans DESIGN.md — le champ de recherche hérite du style input HA (tokens `rule-form-field`).

**[State coverage]** — Permission-denied n'est pas couvert comme état
Le panneau est `require_admin` (Foundation) et HA masque vraisemblablement l'entrée, mais la spine ne le dit jamais — un consommateur ne peut distinguer « géré par HA » de « non considéré ».
Fix : une ligne dans State Patterns : les non-admins ne voient jamais le panneau ; `require_admin` gère l'accès ; pas d'écran de refus in-panel.

**[State coverage]** — Offline n'est jamais nommé comme état ; implicitement plié dans « Erreur de commande websocket »
Adéquat par construction, mais le mapping est laissé à l'inférence.
Fix : une clause nommant la perte réseau comme cas websocket-error.

**[State coverage]** — La suppression de règle n'a aucun comportement spécifié
Création couverte, modification implicite, suppression nommée seulement dans l'IA (« création, modification, suppression »). Pas de règle de confirmation ni d'annulation, pas de state pattern.
Fix : ajouter le comportement de suppression à la ligne Formulaire de règle (confirm ou trust-the-user, précédent Drift).

**[Inheritance discipline]** — Les noms de capacités du SPEC ne sont pas repris verbatim
Seul CAP-4 est nommé dans EXPERIENCE.md (« Restaurer applique le chemin CAP-4 ») ; CAP-1/2/3/5 sont couverts comportementalement mais un consommateur ne peut mapper capacité → surface/flow sans inférer.
Fix : note de traçabilité de quatre lignes (CAP-N → onglet/section) dans IA ou Foundation.

**[Accessibilité — motion]** — L15 : `prefers-reduced-motion` non spécifié
Skeletons animés (pulse), spinner, apparition des toasts : aucune mention. Le vertige vestibulaire (WCAG 2.3.3) n'est pas couvert par le floor.
Fix : une ligne au floor : toute animation décorative se désactive sous `prefers-reduced-motion: reduce` ; skeletons en blocs statiques, spinner en texte d'état.

**[Accessibilité — reflow]** — L16 : zoom 200 % / reflow mobile non testés
WCAG 1.4.4 (zoom 200 %) et 1.4.10 (reflow 320 px sans scroll bidimensionnel) ne figurent nulle part. L'éditeur YAML sur mobile pose un scroll horizontal par nature — acceptable *si* spécifié.
Fix : ajouter au floor : utilisable à 200 % de zoom ; reflow à 320 px sauf éditeur YAML/diff où le scroll horizontal est explicitement admis avec focus visible en débordement.

**[Accessibilité — historique]** — L17 : mécanisme de sélection de version du diff non spécifié
« La version sélectionnée » suppose un sélecteur non décrit ; un widget custom mal balisé serait inopérable au clavier et muet pour l'AT.
Fix : spécifier un contrôle natif (`<select>` ou radio group ARIA) reliant version ↔ diff affiché, avec annonce du changement.

## Reviewer files

- `review-rubric.md` — rubric walker (0 critical, 1 high, 5 medium, 7 low annoncés ; 8 findings low listés)
- `review-accessibility.md` — lens accessibilité WCAG 2.2 AA / ARIA APG (1 critical, 3 high, 10 medium, 3 low)
