# Politique de sécurité

## Versions supportées

Seule la dernière release (installée via HACS) reçoit des correctifs de sécurité. Mets à jour d'abord, puis signale.

| Version        | Supportée |
| -------------- | --------- |
| dernière (0.15+) | oui     |
| plus ancienne  | non       |

## Signaler une vulnérabilité

**N'ouvre pas d'issue publique, de discussion ou de PR pour un problème de sécurité.**

- Méthode préférée : le signalement privé GitHub — onglet **Security** → **« Report a vulnerability »** (visible seulement par toi et les mainteneurs).
- Ou par email : **jdanoffre@gmail.com** avec `[security]` dans l'objet.

Indique : version de l'intégration, version de Home Assistant, étapes de reproduction, impact, et une PoC si tu en as une. Accusé de réception sous **72 heures**.

## Déroulement

1. Triage et confirmation (des détails peuvent être demandés).
2. Correctif développé sur une branche privée, revu, mergé sur `unstable`.
3. Coupe de release ; les notes de version créditent le rapporteur (s'il préfère rester anonyme, aucun crédit).
4. Un advisory de sécurité est publié une fois le correctif disponible pour tous.

## Périmètre

- Dans le périmètre : ce dépôt — l'intégration (`custom_components/eedomus/`), le JS du panneau, les scripts de déploiement.
- Hors périmètre : le core Home Assistant, HACS, la box eedomus et le cloud eedomus — signale-les à leurs projets respectifs.
