---
name: Eedomus Config
description: Panneau de configuration du mapping custom eedomus dans Home Assistant — héritage pur du thème HA ; ce DESIGN.md ne définit que la sémantique de diff type git, le badge de modification, les signaux de cohérence et les surfaces de supervision (carte de graphique, file de backfill).
status: final
updated: 2026-10-04
colors:
  # Héritage UI-system : chaque valeur est une variable CSS du thème HA.
  # Aucun hex — le thème utilisateur (clair/sombre) rend les valeurs.
  text-primary: 'var(--primary-text-color)'
  text-secondary: 'var(--secondary-text-color)'
  accent: 'var(--accent-color)'
  accent-contrast: 'var(--text-accent-color)'
  app-background: 'var(--primary-background-color)'
  card-background: 'var(--card-background-color)'
  divider: 'var(--divider-color)'
  input-fill: 'var(--input-fill-color)'
  input-ink: 'var(--input-ink-color)'
  error: 'var(--error-color)'
  warning: 'var(--warning-color)'
  success: 'var(--success-color)'
  # Sémantique diff type git — dérivée des couleurs sémantiques HA.
  # Portées par teinte de fond + barre gauche, jamais comme couleur de texte.
  diff-added: 'var(--success-color)'
  diff-removed: 'var(--error-color)'
  diff-modified: 'var(--warning-color)'
  # Sémantique de cohérence (onglet Cohérence) — mêmes couleurs sémantiques HA,
  # portées par teinte de fond + icône, jamais comme couleur de texte.
  coherence-no-entity: 'var(--error-color)'
  coherence-questionable: 'var(--warning-color)'
  coherence-rule: 'var(--primary-color)'
  coherence-retry: 'var(--error-color)'
  coherence-ok: 'var(--success-color)'
typography:
  # Tout hérite du thème HA. Rôles nominaux ; le thème rend les valeurs.
  body:
    note: 'Police du thème HA (Roboto / Noto Sans selon la plateforme)'
  label:
    note: 'Police du thème HA, graisse medium'
  code:
    fontFamily: "'Roboto Mono', monospace"
    note: 'Convention éditeur de code HA — [ASSUMPTION] var(--code-font-family) non exposé au niveau thème'
rounded:
  # Hérite du rayon des cartes HA
  DEFAULT: 'var(--ha-card-border-radius)'
  full: 9999px
spacing:
  # [ASSUMPTION] Le thème HA n'expose pas d'échelle d'espacement publique ;
  # échelle 4 px standard du frontend HA.
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 24px
components:
  badge-modified:
    background: '{colors.accent}'
    foreground: '{colors.accent-contrast}'
    radius: '{rounded.full}'
  periph-row:
    background: '{colors.card-background}'
    border-color: '{colors.divider}'
  diff-line-added:
    color: '{colors.text-primary}'
    background: 'color-mix(in srgb, var(--success-color) 12%, var(--card-background-color))'
    bar: '{colors.diff-added}'
    prefix: '+'
  diff-line-removed:
    color: '{colors.text-primary}'
    background: 'color-mix(in srgb, var(--error-color) 12%, var(--card-background-color))'
    bar: '{colors.diff-removed}'
    prefix: '-'
  diff-line-modified:
    color: '{colors.text-primary}'
    background: 'color-mix(in srgb, var(--warning-color) 12%, var(--card-background-color))'
    bar: '{colors.diff-modified}'
    prefix: '~'
  rule-form-field:
    background: '{colors.input-fill}'
    color: '{colors.input-ink}'
    border-color: '{colors.divider}'
  yaml-editor:
    fontFamily: '{typography.code.fontFamily}'
    background: '{colors.card-background}'
    foreground: '{colors.text-primary}'
  version-card:
    background: '{colors.card-background}'
    border-color: '{colors.divider}'
    radius: '{rounded.DEFAULT}'
  coherence-chip-no-entity:
    color: '{colors.text-primary}'
    background: 'color-mix(in srgb, var(--error-color) 12%, var(--card-background-color))'
    signal: '{colors.coherence-no-entity}'
    radius: '{rounded.full}'
  coherence-chip-questionable:
    color: '{colors.text-primary}'
    background: 'color-mix(in srgb, var(--warning-color) 12%, var(--card-background-color))'
    signal: '{colors.coherence-questionable}'
    radius: '{rounded.full}'
  coherence-chip-rule:
    color: '{colors.text-primary}'
    background: 'color-mix(in srgb, var(--primary-color) 12%, var(--card-background-color))'
    signal: '{colors.coherence-rule}'
    radius: '{rounded.full}'
  coherence-chip-retry:
    color: '{colors.text-primary}'
    background: 'color-mix(in srgb, var(--error-color) 12%, var(--card-background-color))'
    signal: '{colors.coherence-retry}'
    radius: '{rounded.full}'
  coherence-chip-ok:
    color: '{colors.text-primary}'
    background: 'color-mix(in srgb, var(--success-color) 12%, var(--card-background-color))'
    signal: '{colors.coherence-ok}'
    radius: '{rounded.full}'
  periph-popover:
    background: '{colors.card-background}'
    border-color: '{colors.divider}'
    radius: '{rounded.DEFAULT}'
  sort-header:
    color: '{colors.text-secondary}'
    indicator: '{colors.text-secondary}'
  coherence-table:
    background: '{colors.card-background}'
    border-color: '{colors.divider}'
  entity-link:
    color: '{colors.accent}'
  metric-chart-card:
    background: '{colors.card-background}'
    border-color: '{colors.divider}'
    radius: '{rounded.DEFAULT}'
  backfill-queue:
    background: '{colors.card-background}'
    border-color: '{colors.divider}'
---

# DESIGN.md — Eedomus Config

## Références visuelles

Les mocks des trois écrans clés vivent dans `mockups/` (bascule clair/sombre incluse pour la vérification du contraste) :

- `mockups/mock-01-peripheriques.html` — onglet Périphériques : liste, filtre, badge « modifié », raccourci vers les règles
- `mockups/mock-02-regles.html` — onglet Règles : bascule Formulaire/YAML, validation temps réel
- `mockups/mock-03-historique.html` — onglet Historique config : cartes de version, restauration confirmée, diff type git

Les spines priment sur tout mock en cas de conflit.

Les onglets Cohérence et Supervision sont spine-only à ce stade : pas de mock — le tableau, les puces, le popover, les cartes de graphique et la file de backfill se construisent depuis les spines seules ; à rendre en mock si le besoin s'en fait sentir.

## Brand & Style

Eedomus Config est un panneau d'administration Home Assistant : un outil de configuration, pas une application grand public. Sa posture visuelle est l'**effacement** — il se fond dans l'installation HA de l'utilisateur au point de sembler natif. Aucune identité propre : pas de logo, pas de palette propriétaire, pas de police dédiée. Le thème HA (clair ou sombre) est le design system ; ce document ne spécifie que la couche sémantique que HA ne fournit pas — le langage de diff type git de l'historique, le badge de modification des périphériques et les signaux de cohérence du mapping. Ce DESIGN.md ne porte que l'identité visuelle ; le comportement vit dans EXPERIENCE.md, qui référence ses tokens.

La seule expression visuelle originale du panneau est fonctionnelle : la couleur y porte toujours un sens (ajout, suppression, modification, périphérique touché par la dernière règle, état de cohérence), jamais décorative.

## Colors

Toutes les couleurs sont des variables CSS du thème HA. Le panneau fonctionne en clair et en sombre sans code spécifique : les valeurs viennent du thème, point final.

- **Texte et surfaces** — `{colors.text-primary}`, `{colors.text-secondary}`, `{colors.app-background}`, `{colors.card-background}`, `{colors.divider}` : piliers du chrome, tels que HA les rend. Les cartes du panneau (lignes de périphériques, cartes de version) vivent sur `{colors.app-background}` avec un filet `{colors.divider}`.
- **Accent (`{colors.accent}`)** — utilisé exclusivement pour le badge de modification sur les périphériques touchés par la dernière règle en vigueur (`{components.badge-modified}`) et pour le lien d'entité HA de l'onglet Cohérence (`{components.entity-link}`). Jamais pour le chrome, jamais pour un état d'erreur.
- **Sémantique diff (héritage HA)** — les trois couleurs sémantiques du thème portent le langage git de l'historique, comme teinte de fond et barre gauche — **jamais comme couleur de texte** : HA ne les utilise qu'au seuil 3:1, pour icônes et fonds graphiques.
  - `{colors.diff-added}` = `var(--success-color)` — lignes ajoutées entre deux versions.
  - `{colors.diff-removed}` = `var(--error-color)` — lignes supprimées.
  - `{colors.diff-modified}` = `var(--warning-color)` — lignes modifiées.
  - Le texte des lignes de diff est toujours `{colors.text-primary}` (contraste hérité du thème). La sémantique est portée par trois signaux redondants : fond teinté (`color-mix` 12 % sur `{colors.card-background}`), préfixe texte `+` / `-` / `~`, barre gauche 3 px en couleur sémantique.
  - **Critère d'acceptation** : texte du diff ≥ 4.5:1 sur son fond teinté, vérifié sur les thèmes clair et sombre par défaut de HA. `[ASSUMPTION]` : le ratio de teinte 12 % est un point de départ, à caler sur ce critère (monter à 16–20 % si la teinte reste sous 3:1 contre le fond de carte).
- **Sémantique de cohérence (onglet Cohérence)** — les puces de statut réutilisent les couleurs sémantiques du thème comme teintes de fond, texte toujours en `{colors.text-primary}` — même discipline que le diff, jamais la couleur comme couleur de texte :
  - `{colors.coherence-no-entity}` = `var(--error-color)` — aucun mapping vers une entité HA (`entity_id` null).
  - `{colors.coherence-questionable}` = `var(--warning-color)` — mapping douteux (pas d'état vivant ni d'unité, `device_class` discutable).
  - `{colors.coherence-rule}` = `var(--primary-color)` — règle custom active (`modified_by_rule`) : une information, pas une faute.
  - `{colors.coherence-retry}` = `var(--error-color)` — périphérique en file d'erreur/retry du coordinator.
  - `{colors.coherence-ok}` = `var(--success-color)` — aucun signal (vue « Tout afficher »).
  - Teinte `color-mix` 12 % sur fond carte (`{components.coherence-chip-*}`), calée sur le même critère : texte de puce ≥ 4.5:1 sur son fond teinté, vérifié sur les thèmes clair et sombre par défaut de HA.
- **Graphiques de Supervision (héritage HA)** — les séries des cartes de graphique (`{components.metric-chart-card}`) héritent de la palette de graphique du thème HA : aucune couleur de série locale, aucun hex. Les cartes vivent sur `{colors.card-background}` avec filet `{colors.divider}`, comme toute carte du panneau.
- **Validation** — les erreurs de validation temps réel des règles utilisent `{colors.error}` ; la correction sauvegardée avec succès est confirmée par les mécanismes standard HA (toast).

## Typography

Héritage complet du thème HA — hiérarchie, corps et graisses de texte suivent les conventions des panneaux HA (titre du panneau, libellés de champs, texte de corps). Deux rôles seulement sont nommés ici :

- **`{typography.body}` / `{typography.label}`** — texte courant et libellés de formulaire, rendus par le thème.
- **`{typography.code}`** — l'éditeur YAML brut et la vue diff de l'historique sont en police mono (`{components.yaml-editor}`), convention des éditeurs de code HA. `[ASSUMPTION]` : Roboto Mono en repli, la police mono exacte dépend de la plateforme/du thème.

Aucune taille ni graisse surchargée : le panneau respecte la rampe typographique du thème.

## Layout & Spacing

Panneau web plein-cadre dans la zone de contenu HA, séparateurs en `{colors.divider}` entre zones fonctionnelles. Contenu en colonne unique avec largeur maximale de lisibilité (~760 px) pour les formulaires ; la liste des périphériques et le tableau de cohérence s'étirent sur la largeur disponible. Échelle d'espacement `{spacing.1}`–`{spacing.5}` en base 4 px, appliquée uniformément (gouttières de cartes, marges de formulaire, densité de liste). `[ASSUMPTION]` : HA n'expose pas d'échelle publique ; la base 4 px est la convention du frontend HA.

## Elevation & Depth

Héritage HA : les cartes suivent `{rounded.DEFAULT}` et l'ombre `--ha-card-box-shadow` du thème s'il en définit une. Aucune élévation supplémentaire — pas de modale flottante décorative, pas d'ombre portée locale. La hiérarchie se fait par filets (`{colors.divider}`) et par position, pas par la profondeur.

Une seule surface flottante, fonctionnelle : le popover de périphérique (`{components.periph-popover}`) se détache du contenu par un filet `{colors.divider}` et l'ombre de carte du thème (`--ha-card-box-shadow`) — une élévation de lisibilité, jamais décorative. Si le thème ne définit pas d'ombre de carte, le filet suffit ; pas d'ombre locale inventée. Sur mobile, cette surface n'existe pas : c'est la ligne étendue, plate comme le reste.

## Shapes

Un seul rayon de surface : `{rounded.DEFAULT}` = `var(--ha-card-border-radius)` — le panneau est indiscernable des cartes HA. Les puces (`{rounded.full}`) sont réservées aux badges (`{components.badge-modified}`) et aux états sémantiques (puces de cohérence, `{components.coherence-chip-*}`). Aucun coin arrondi inventé, aucune forme brandée.

## Components

- **Ligne de périphérique (`{components.periph-row}`)** — fond `{colors.card-background}`, filet `{colors.divider}`. Nom, `usage_id`, mapping courant (entité HA, `device_class`, unité). Le badge de modification apparaît à droite quand la dernière règle en vigueur touche ce périphérique.
- **Badge de modification (`{components.badge-modified}`)** — pill `{colors.accent}` / `{colors.accent-contrast}`, taille contenue : un point de teinte et une icône (redondance de forme — jamais un point chromatique seul). `aria-label` obligatoire : « modifié par la règle {nom}, {date} » — un lecteur d'écran reçoit la même information que l'œil. Un point discret plutôt qu'un pavé : le signal se remarque au balayage visuel sans crier.
- **Champ de formulaire de règle (`{components.rule-form-field}`)** — remplissage `{colors.input-fill}` / texte `{colors.input-ink}`, conformes aux champs HA. Autocomplete et messages de validation temps réel dans le champ même.
- **Éditeur YAML (`{components.yaml-editor}`)** — mono, fond carte, coloration syntaxique YAML complète. Palette de coloration dérivée des variables du thème (texte, accents, commentaires) — jamais de couleurs codées. `[ASSUMPTION]` : le mappage exact variable→token syntaxique sera tranché à l'implémentation avec la lib vendorisée minifiée.
- **Lignes de diff (`{components.diff-line-added}`, `{components.diff-line-removed}`, `{components.diff-line-modified}`)** — vue type git entre deux versions. Texte en `{colors.text-primary}` ; sémantique portée par le fond teinté dérivé de la couleur sémantique, le préfixe texte `+` / `-` / `~` (vrai nœud texte, pas un pseudo-élément muet) et la barre gauche 3 px en couleur sémantique. Critère de contraste : voir §Colors.
- **Carte de version (`{components.version-card}`)** — une des 3 dernières versions : horodatage, résumé, action de restauration. Restaure = bouton d'action standard HA, la carte de la version courante porte l'état « actuelle ».
- **Puces de cohérence (`{components.coherence-chip-no-entity}` / `-questionable` / `-rule` / `-retry` / `-ok`)** — une puce par signal, cumulables sur une même ligne du tableau de cohérence : icône + texte, jamais la couleur seule. Teinte et critère de contraste : voir §Colors (sémantique de cohérence). `[ASSUMPTION]` : les glyphes exacts (jeu d'icônes HA) seront tranchés à l'implémentation — un glyphe distinct par signal, redondant avec le libellé.
- **Popover de périphérique (`{components.periph-popover}`)** — surface flottante fonctionnelle de l'onglet Cohérence : fond `{colors.card-background}`, filet `{colors.divider}`, rayon `{rounded.DEFAULT}`, élévation selon Elevation & Depth. Une seule ouverte à la fois ; les champs bruts de l'API eedomus y vivent en section secondaire repliable.
- **En-tête de tri (`{components.sort-header}`)** — bouton focusable dans chaque cellule d'en-tête du tableau de cohérence, outline du thème jamais supprimé ; `aria-sort` porte l'état de tri ; l'indicateur de direction (glyphe flèche) en `{colors.text-secondary}`.
- **Tableau de cohérence (`{components.coherence-table}`)** — pleine largeur de la zone de contenu, fond `{colors.card-background}`. Séparation de lignes par filet `{colors.divider}` (pas de zébrage) ; l'en-tête collant garde fond `{colors.card-background}` et filet bas `{colors.divider}` pour rester lisible au défilement ; cellules en `{typography.body}`, `periph_id` en `{typography.code}`. Densité compacte mais respirée : hauteur de ligne ≥ 44 px (cible tactile), padding vertical `{spacing.3}` — un tableau de ~165 lignes se balaye sans fatigue visuelle.
- **Lien d'entité HA (`{components.entity-link}`)** — lien texte inline en `{colors.accent}`, souligné ; pas de fond, pas de bordure, pas de chrome de bouton. Il navigue vers la page de réglages standard de l'entité HA — un lien, pas un contrôle d'édition.
- **Carte de graphique de métrique (`{components.metric-chart-card}`)** — surface = motif de carte existant : fond `{colors.card-background}`, filet `{colors.divider}`, rayon `{rounded.DEFAULT}`. Les couleurs de séries héritent de la palette de graphique du thème HA (voir §Colors) — aucune palette locale. Priorité aux composants de graphique du frontend HA exposés dans le contexte du panneau ; repli SVG inline thémé (variables CSS HA uniquement). `[ASSUMPTION]` : la disponibilité des composants de graphique HA dans le contexte du panneau est vérifiée à l'implémentation.
- **File de backfill (`{components.backfill-queue}`)** — lignes sur `{colors.card-background}`, filets `{colors.divider}`. Les boutons d'action sont les boutons standard HA — aucun pattern visuel nouveau ; les statuts sont portés par texte, jamais la couleur seule (comportement dans EXPERIENCE.md). Ce composant n'introduit aucun token de couleur.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Toute couleur via une variable CSS HA | Hex codé en dur, même « assorti au thème » |
| Diff : success/ajout, error/suppression, warning/modification — portés par teinte + préfixe + barre gauche | Réassigner les sémantiques ou inventer une quatrième couleur de diff |
| Texte du diff en `{colors.text-primary}` | Couleur sémantique comme couleur de texte de diff |
| Accent réservé au badge de périphérique touché et au lien d'entité | Accent pour boutons, chrome ou décor |
| Puces de cohérence : icône + texte, teinte de fond sémantique | Porter le sens d'une puce par la seule couleur, ou fusionner plusieurs signaux en un seul |
| Rayons et ombres hérités du thème HA | Coins ou ombres locaux, modales flottantes décoratives |
| Mono pour YAML et diff uniquement | Mono pour le texte courant |
| Tester clair ET sombre via le thème utilisateur | Supposer les valeurs d'un seul mode |
