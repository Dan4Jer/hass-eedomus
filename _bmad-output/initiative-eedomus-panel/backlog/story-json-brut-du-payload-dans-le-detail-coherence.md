---
id: 104
type: story
title: "Cohérence : JSON brut du payload sous « Champs bruts de l'API eedomus »"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: low
---

# Cohérence : JSON brut du payload sous « Champs bruts de l'API eedomus »

## Description

La section repliable « Champs bruts de l'API eedomus » du détail de périphérique (popover desktop et ligne étendue mobile, en parité) gagne un second niveau sous la liste triée clé→valeur existante : le document JSON brut du payload coordinator, à l'ordre des clés d'origine, sans tri ni transformation, avec un bouton « Copier le JSON ». La microcopie nouvelle passe par le catalogue websocket et l'inventaire i18n ; aucun changement backend (le payload brut est déjà servi sur chaque ligne de cohérence).

## Acceptance Criteria

1. **JSON brut affiché sous la liste**
   **Given** un périphérique dont le coordinator cache un payload
   **When** le détail est ouvert et la section « Champs bruts de l'API eedomus » dépliée
   **Then** la liste triée clé→valeur existante se rend en premier, et le JSON du payload s'affiche en dessous, formaté et lisible, avec les clés dans l'ordre d'origine du payload (pas triées) et les valeurs fidèles au cache
   **And** aucune valeur n'est modifiée ni reformulée — le document est celui mis en cache par le coordinator
2. **Bouton Copier le JSON**
   **Given** la section dépliée
   **When** « Copier le JSON » est activé
   **Then** le JSON du payload se retrouve dans le presse-papiers et la copie est confirmée par une annonce (pattern d'annonce existant du panneau)
3. **Parité mobile**
   **Given** la vue étroite (ligne étendue mobile)
   **When** la ligne d'un périphérique est étendue
   **Then** la section repliable rend exactement le même contenu que le popover desktop : liste triée, JSON brut, bouton copier
4. **Microcopie localisée via le catalogue**
   **Given** le panneau rendu sous une locale couverte
   **When** la section et ses nouveaux libellés s'affichent
   **Then** chaque nouvelle chaîne (bouton copier, retour de copie) vient du catalogue `eedomus/get_translations` via les clés `panel.*` ajoutées à l'inventaire et au catalogue (source EN, traduction FR), et la garde i18n reste verte

## Boundaries

- Must not change: la liste triée clé→valeur (premier niveau conservé), les contrats gelés des commandes `eedomus/get_coherence` et `eedomus/get_peripherals` (le payload `_raw` est déjà servi — aucun changement backend), les autres sections du détail (état vivant, identité, actions), les clés déjà livrées dans le catalogue.
- Le JSON affiché est celui du cache coordinator au moment du rendu — pas de re-fetch spécifique.

## References

- design — _bmad-output/planning-artifacts/ux-designs/ux-hass-eedomus-2026-09-27/EXPERIENCE.md, Component Patterns, `periph-popover` (règle des deux niveaux + copie) et section Responsive (parité)
- spec — _bmad-output/specs/spec-eedomus-i18n/SPEC.md, régime de localisation (toute chaîne user-facing passe par l'inventaire puis le catalogue websocket)
- inventaire — _bmad-output/specs/spec-eedomus-i18n/i18n-inventory.md (les clés nouvelles s'y ajoutent, sinon le test de parité inventaire/catalogue échoue)

## Notes

- Decision: rendu en deux niveaux (liste triée conservée + JSON brut en dessous), ordre des clés d'origine, bouton « Copier le JSON » — capture UX run 3 du 2026-10-04, entrées memlog 44-46 du workspace UX.
- Decision: prettifying côté panneau (`JSON.stringify(payload, null, 2)`, indentation 2 espaces) — le backend sert le payload tel quel (confirmé 2026-10-04).
- Decision: microcopie validée (2026-10-04) — bouton « Copier le JSON » / "Copy JSON", retour « JSON copié. » / "JSON copied." (source EN, traduction FR).
- Decision: le build démarre dès que le cycle 3.4 rend l'arbre libre ; la garde E2E 3.7 (postérieure) le couvrira (confirmé 2026-10-04).
