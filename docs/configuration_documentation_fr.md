# Guide de Configuration pour l'Intégration Eedomus

## Options de Configuration

### Configuration de Base

#### api_host
**Description** : Adresse IP locale de votre box Eedomus (ex: `xxx.XXX.xxx.XXX`)
**But** : Permet à Home Assistant de communiquer directement avec votre box Eedomus
**Obligatoire** : Oui
**Exemple** : `192.168.1.100`

#### api_user
**Description** : Nom d'utilisateur API de votre compte Eedomus
**But** : Authentifie les requêtes vers l'API Eedomus
**Obligatoire** : Seulement si le mode API Eedomus est activé
**Emplacement** : Interface web Eedomus > "Mon Compte" > "Identifiants pour l'API"

#### api_secret
**Description** : Mot de passe API de votre compte Eedomus
**But** : Authentifie les requêtes vers l'API Eedomus
**Obligatoire** : Seulement si le mode API Eedomus est activé
**Emplacement** : Interface web Eedomus > "Mon Compte" > "Identifiants pour l'API"
**Sécurité** : Ce champ est masqué et sécurisé

### Modes de Connexion

#### enable_api_eedomus (par défaut: True)
**Description** : Activer l'interrogation directe de l'API Eedomus
**But** : Récupérer les états des périphériques et envoyer des commandes
**Recommandé** : Oui (pour une fonctionnalité complète)
**Sans cela** : L'intégration a une fonctionnalité limitée

#### enable_api_proxy (par défaut: False)
**Description** : Activer la communication basée sur les webhooks
**But** : Permettre à Eedomus d'envoyer des mises à jour à Home Assistant
**Cas d'utilisation** :
- Déclencher des automatisations Home Assistant depuis des scénarios Eedomus
- Contrôler des entités HA directement depuis Eedomus
- Mises à jour en temps réel sans interrogation

### Récupération de Données

#### scan_interval (par défaut: 300 secondes)
**Description** : Temps entre chaque interrogation de l'API (en secondes)
**But** : Contrôler la fréquence de vérification des états des périphériques
**Recommandations** :
- **300s (5min)** : Bon compromis pour la plupart des utilisateurs
- **60s (1min)** : Pour un monitoring en temps réel (charge plus élevée)
- **900s (15min)** : Pour un mode économie d'énergie (moins réactif)

#### enable_history (par défaut: False)
**Description** : Activer la récupération des données historiques
**Statut** : Fully implemented ✅
**Fonctionnalités** :
- Suivre la progression de la récupération d'historique
- Voir les statistiques de téléchargement
- Accéder aux données historiques des capteurs
**Requirements** :
- Le mode API Eedomus doit être activé
- Le composant Recorder est recommandé (mais pas obligatoire)

### Options Avancées

#### enable_set_value_retry (par défaut: True)
**Description** : Réessayer automatiquement les mises à jour échouées
**But** : Gérer les cas où les valeurs sont initialement refusées
**Cas d'utilisation** :
- Corriger automatiquement les valeurs invalides
- Améliorer la fiabilité pour les périphériques instables

#### max_retries (par défaut: 3)
**Description** : Nombre maximal de tentatives pour les commandes échouées
**But** : Contrôler le comportement de réessai
**Cas d'utilisation** :
- Augmenter pour les réseaux instables
- Diminuer pour une détection plus rapide des échecs

### Webhook & Sécurité

#### enable_webhook (par défaut: True)
**Description** : Activer les endpoints webhook
**But** : Permettre à Eedomus de déclencher des actions Home Assistant
**Fonctionnalités** :
- Rafraîchir les états des périphériques
- Actions internes (futur)
- Intégrations personnalisées

#### api_proxy_disable_security (par défaut: False)
**⚠️ Avertissement de Sécurité** : Désactiver la validation IP pour l'API Proxy
**But** : Permettre l'accès depuis des IP non standard (débogage seulement)
**Risque de Sécurité** : Expose les endpoints webhook à un potentiel abus
**Recommandation** : Garder désactivé en environnement de production

### Fallback PHP

#### php_fallback_enabled (par défaut: False)
**Description** : Utiliser un script PHP pour contourner les limitations de l'API
**But** : Définir des valeurs non disponibles dans les options par défaut
**Requirements** : Un script PHP doit être configuré
**Cas d'utilisation** :
- Contrôle avancé des périphériques
- Plages de valeurs personnalisées
- Contourner les restrictions de l'API

#### php_fallback_script_name (par défaut: "fallback.php")
**Description** : Nom du script PHP de fallback
**But** : Spécifier l'emplacement du script personnalisé
**Exemple** : "custom_fallback.php"

#### php_fallback_timeout (par défaut: 5 secondes)
**Description** : Timeout pour les requêtes PHP de fallback
**But** : Contrôler le temps de réponse
**Recommandations** :
- Augmenter pour les serveurs lents (10-30s)
- Diminuer pour une réponse plus rapide (2-5s)

### Options de Désinstallation

#### remove_entities_on_uninstall (par défaut: False)
**Description** : Supprimer toutes les entités lors de la désinstallation
**But** : Nettoyer complètement
**Cas d'utilisation** :
- Suppression complète avant réinstallation
- Tests de nouvelles configurations
- Dépannage

## Modes de Connexion Expliqués

### Mode API Eedomus (Pull)
```
Home Assistant → (Pull) → Box Eedomus
```
**Avantages** :
- Accès complet aux périphériques
- Récupération d'historique
- Interrogation fiable

**Inconvénients** :
- Nécessite des identifiants
- Dépendance réseau

### Mode API Proxy (Push)
```
Box Eedomus → (Push via Webhook) → Home Assistant
```
**Avantages** :
- Mises à jour en temps réel
- Pas d'interrogation nécessaire
- Léger

**Inconvénients** :
- Pas d'accès à l'historique
- Nécessite une configuration webhook

## Bonnes Pratiques

### Pour une Meilleure Performance
1. Utilisez les deux modes (API Eedomus + API Proxy) pour la redondance
2. Réglez scan_interval à 300s (5 minutes) pour un bon équilibre
3. Gardez enable_set_value_retry activé pour la fiabilité
4. Désactivez api_proxy_disable_security sauf pour le débogage

### Pour le Dépannage
1. Vérifiez les logs : `journalctl -u home-assistant@homeassistant -f`
2. Vérifiez la connectivité : `ping 192.168.1.100`
3. Testez les identifiants API dans l'interface Eedomus
4. Désactivez les options une par une pour isoler les problèmes

### Pour la Sécurité
1. Ne jamais exposer la box Eedomus à Internet
2. Gardez api_proxy_disable_security désactivé
3. Utilisez des identifiants API robustes
4. Mettez à jour régulièrement Home Assistant

## Dépannage

### Problèmes Courants

**Problème** : Échec de la connexion
- Vérifiez l'adresse IP de l'API
- Vérifiez les identifiants API
- Assurez-vous que la box Eedomus est en ligne

**Problème** : Périphériques non mis à jour
- Augmentez scan_interval
- Vérifiez la connectivité réseau
- Vérifiez les permissions des périphériques dans Eedomus

**Problème** : Commandes ne fonctionnent pas
- Activez enable_set_value_retry
- Vérifiez la compatibilité des périphériques
- Vérifiez les plages de valeurs

### Messages des Logs

**"Missing or empty value"** : Normal pour certains périphériques, peut être ignoré
**"API request failed"** : Vérifiez le réseau et les identifiants
**"Cannot connect to eedomus API"** : Vérifiez l'hôte et les identifiants
**"History retrieval failed"** : Vérifiez que le mode API Eedomus est activé

## Support

Pour les problèmes ou questions :
1. Vérifiez cette documentation en premier
2. Consultez les logs pour les messages d'erreur
3. Créez un issue sur GitHub avec :
   - Version de Home Assistant
   - Version de l'intégration Eedomus
   - Extraits de logs pertinents
   - Étapes pour reproduire

## Historique des Versions

### Version Actuelle : 0.13.10-unstable
- ✅ Fonctionnalité historique entièrement implémentée
- ✅ Capteurs correctement attachés aux devices
- ✅ Organisation de l'UI améliorée
- ✅ Meilleure gestion des erreurs

### Versions Précédentes
- 0.13.9 : Correction des problèmes de mapping RGBW
- 0.13.8 : Ajout du support des périphériques dynamiques
- 0.13.7 : Amélioration de la récupération d'erreur

## Détails Techniques

### Mapping des Périphériques
- Lampes RGBW : Détectées automatiquement en ayant 4+ enfants
- Canaux de luminosité : Mappés comme light:brightness
- Capteurs : Mappés par usage_id
- Capteurs binaires : Détection de mouvement et fumée

### Endpoints API
- `/periph/list` : Obtenir tous les périphériques
- `/periph/value/list` : Obtenir les valeurs
- `/periph/caract` : Obtenir les caractéristiques
- `/periph/set/value` : Définir les valeurs

### Flux de Données
1. Chargement initial : Liste complète des périphériques et valeurs
2. Interrogation régulière : Seulement les caractéristiques (scan_interval)
3. Webhooks : Mises à jour en temps réel (si activé)
4. Historique : Récupération en arrière-plan (si activé)

---

**Dernière mise à jour** : 2026-02-14
**Intégration** : Eedomus
**Auteur** : Dan4Jer
**Licence** : MIT