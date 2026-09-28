---
title: "P.1.5 Éditeur Règles — mode YAML avec coloration"
type: 'feature'
ticket: 5
created: '2026-09-28'
status: done
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'auto'
lenses_ran: ['quick']
review_loop_iteration: 0
baseline_revision: '5ef4ed9'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Le mapping custom n'est éditable qu'en mode formulaire — impossible de coller un bloc YAML venu d'un ancien fichier ou de manipuler la grammaire brute.

**Approach:** Mode YAML brut conforme à EXPERIENCE.md : coloration syntaxique, validation temps réel ligne par ligne (aria-live), bascule Formulaire↔YAML sans perte (le YAML reflète l'état du formulaire et réciproquement), focus préservé, jamais d'acceptation silencieuse d'un YAML invalide.

</frozen-after-approval>

## Implementation Notes

- **Décision M9 (lib vs repli)** : aucune candidate vendorisée ne passe le critère — CodeMirror exclu (trop lourd), CodeJar et al. reposent sur contenteditable (texte mal exposé au lecteur d'écran). Implémentation retenue : **textarea natif + calque de coloration** (`<pre>` sous un textarea transparent) — clavier complet et AT natifs (le champ EST un textarea), zéro dépendance, ~2 Ko. Critère rempli au-delà du repli.
- Le dump complet du mapping est sérialisé côté client par `_yamlDumpFull` (dicts/listes/scalaires, JSON-escaping des scalaires = YAML double-quoté valide) — round-trip vérifié contre le parseur PyYAML (sections, floats, règles imbriquées).
- Validation : debounce 400 ms → `eedomus/validate_config` sur le texte ENTIER ; erreur affichée `ligne N : message` (numéro extrait du `line N` PyYAML ou localisation de la clé fautive nommée par voluptuous), save désactivé tant qu'invalide. Le save YAML passe par `save_mapping` avec le `validated_config` (document complet revalidé côté serveur).
- Bascule form→YAML : dump du mapping courant. YAML→form : **refusée tant que le texte ne valide pas** (annonce aria-live de la cause — jamais de perte silencieuse) ; validée → le config validé devient le mapping du formulaire.
- Focus préservé : à l'entrée en YAML, focus sur l'éditeur ; Tab insère deux espaces (éditable au clavier complet) ; Échap blur ; gouttière de numéros de ligne synchronisée au scroll ; scroll horizontal admis (mono non retouché).

## Review Triage Log

Review quick (self), itération 1 :

- [checked] `_yamlDumpFull` : round-trip testé hors navigateur contre PyYAML (listes de scalars et de dicts, floats, clés numériques quotées, {} / [] vides).
- [checked] La bascule YAML→form avec texte non validé ne perd RIEN : reste en YAML avec le message en aria-live.
- [low] Les erreurs de schéma voluptuous ne portent pas de numéro de ligne natif : le panneau localise la clé fautive dans le texte (heuristique du dernier segment du path) — le message complet reste affiché quoi qu'il arrive.
- [low, defer→P.1.7] La coloration est une heuristique regex (clés/strings/nombres/booléens/commentaires) — suffisante pour la grammaire du mapping, pas un parser YAML.
- [checked] Le mode toggle (Formulaire/YAML) porte `aria-pressed` et un `role="group"` étiqueté.

## Verification

**Commands:**

- `node --check custom_components/eedomus/www/eedomus-panel.js` -- expected: OK
- Round-trip du dumper vérifié contre PyYAML (test jet hors navigateur, consigné au-dessus)
- `python3 -m pytest tests/unit -q` -- expected: 153 verts (backend inchangé pour P.1.5)

**Manual checks (déploiement requis) :**

- Bascule Formulaire↔YAML sans perte, focus conservé, changement de mode annoncé
- Coloration (clés/strings/commentaires), gouttière de numéros, Tab = 2 espaces
- YAML cassé collé → erreur `ligne N : …` en aria-live, Enregistrer désactivé
- Save YAML → « Sauvegarde… / Application… / Configuration appliquée. »
