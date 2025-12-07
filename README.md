# Intégration eedomus pour Home Assistant

Cette intégration permet de connecter votre box domotique **eedomus** à **Home Assistant**.

Ce module récupère et découvre, via l'API eedomus (https://doc.eedomus.com/view/API_eedomus), les informations et pilotes les périphériques eedomus.
L'objectif est de faire communiquer HA et eedomus de manière efficace, il y a trois étapes :
 - L'initialisation, démarrage ou setup, qui collecte toutes les informations sur les périphériques eedomus pour faire un mapping dans avec les entitées eedomus.
 - Un refresh périodique (5 minutes, c'est bien), pour raffaichir les états des périphériques dont la valeur évolue.
 - Un refresh partiel sur évènement, une action dans HA ou bien un webhook depuis eedomus (avec un actionneur http)

---

## Configuration

### Prérequis
- Une box eedomus configurée et accessible sur votre réseau local.
- Les api_user et api_secret eedomus (dans eedomus Confguration > Mon compte > Parametres > Api eedomus : consulter vos identifiants)
- Home Assistant installé et opérationnel.

---

## Installation
1. Ajoutez ce dépôt en tant que [dépôt personnalisé](https://www.home-assistant.io/integrations/#installing-custom-integrations) dans Home Assistant.
2. Redémarrez Home Assistant.
3. Ajoutez l'intégration via **Paramètres > Appareils et services > Ajouter une intégration > eedomus**.

---

## Configuration de l'intégration
Lors de la configuration, vous devrez fournir les informations suivantes :

| Champ               | Description                                      | Exemple                     |
|---------------------|--------------------------------------------------|-----------------------------|
| `Adresse IP`        | Adresse IP de votre box eedomus                  | `192.168.1.2`               |
| `api_user`          | Nom d'utilisateur pour l'API eedomus             | `votre_utilisateur`         |
| `api_secret`        | Mot de passe pour l'API eedomus                  | `votre_mot_de_passe`        |

---

## Webhook
Cette intégration expose un webhook pour déclencher des rafraîchissements depuis eedomus.

### Configuration du webhook dans eedomus
1. Dans l'interface eedomus, allez dans **Automatismes > Actionneurs HTTP**.
2. Créez un nouvel actionneur HTTP avec les paramètres suivants :

| Paramètre           | Valeur                                                                       |
|---------------------|-----------------------------------------------------------------------------|
| **Nom**             | `Rafraîchir Home Assistant` (ou un nom de votre choix)                      |
| **URL**             | `http://<IP_HOME_ASSISTANT>:8123/api/eedomus/webhook`                        |
| **Méthode**         | `POST`                                                                       |
| **Headers**         | `Content-Type: application/json`                                             |
| **Corps (Body)**    | `{"action": "refresh"}` (pour un rafraîchissement complet)                  |
|                     | `{"action": "partial_refresh"}` (pour un rafraîchissement partiel)          |

> ⚠️ **Important** : Ne pas ajouter de `/` à la fin de l'URL (`/api/eedomus/webhook/` ne fonctionnera pas).

---

### Sécurité du webhook
Pour sécuriser le webhook, cette intégration vérifie que les requêtes proviennent bien de votre box eedomus en validant l'**IP source**. L'IP de votre box eedomus doit être configurée lors de l'ajout de l'intégration.

Si votre box eedomus a une **IP dynamique**, configurez une **IP statique** pour votre box eedomus dans votre routeur.

---

## Actions disponibles
| Action               | Description                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| `refresh`            | Déclenche un rafraîchissement complet de tous les périphériques eedomus.   |
| `partial_refresh`    | Déclenche un rafraîchissement partiel (périphériques dynamiques uniquement).|

---

## Exemples d'utilisation

### Rafraîchir les données depuis un scénario eedomus
1. Créez un scénario dans eedomus.
2. Ajoutez une action de type **Actionneur HTTP** avec les paramètres ci-dessus.
3. Déclenchez le scénario pour rafraîchir les données dans Home Assistant.

---

### Rafraîchir les données depuis Home Assistant
Vous pouvez également déclencher un rafraîchissement depuis Home Assistant :
1. Allez dans **Développement > Services**.
2. Sélectionnez le service `eedomus.refresh`.
3. Exécutez le service pour rafraîchir les données.

---

## Dépannage

### Problèmes courants
| Problème                          | Solution                                                                                     |
|-----------------------------------|----------------------------------------------------------------------------------------------|
| **Erreur 404**                    | Vérifiez que l'URL du webhook ne se termine pas par `/` (ex: `/api/eedomus/webhook/`).        |
| **Erreur "Unauthorized"**         | Vérifiez que l'IP de votre box eedomus est correctement configurée dans l'intégration.        |
| **Erreur "Invalid JSON payload"** | Vérifiez que le `Content-Type` est bien `application/json` dans l'actionneur HTTP eedomus.   |
| **Aucune réponse**                | Vérifiez que Home Assistant est accessible depuis votre box eedomus (pare-feu, réseau, etc.).|

---

### Logs
Pour diagnostiquer les problèmes, activez les logs en mode debug :
```yaml
# configuration.yaml
logger:
  default: warn
  logs:
    custom_components.eedomus: debug
