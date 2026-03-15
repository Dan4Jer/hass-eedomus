# Guide d'Utilisation du Support Multi-Langue

## Introduction
Ce guide explique comment activer et utiliser le support multi-langue dans l'intégration `hass-eedomus`. Actuellement, l'intégration supporte le français et l'anglais.

## Activation du Support Français

### Étape 1 : Changer la Langue de Home Assistant
1. **Accédez aux paramètres de Home Assistant** :
   - Allez dans **Paramètres** > **Système** > **Général**.
   - Faites défiler jusqu'à la section **Langue**.
   - Sélectionnez **Français** dans la liste des langues disponibles.

2. **Redémarrez Home Assistant** :
   - Après avoir changé la langue, redémarrez Home Assistant pour appliquer les changements.

### Étape 2 : Vérifier les Traductions
1. **Accédez à l'intégration `hass-eedomus`** :
   - Allez dans **Paramètres** > **Appareils et Services**.
   - Sélectionnez l'intégration `hass-eedomus`.

2. **Vérifiez les traductions** :
   - Les noms des champs et les descriptions doivent maintenant s'afficher en français.
   - Par exemple, "Eedomus box IP address" devrait s'afficher comme "Adresse IP de la box eedomus".

## Structure des Fichiers de Traduction

Les fichiers de traduction sont situés dans le dossier `custom_components/eedomus/translations/` :
- `en.json` : Traductions en anglais (par défaut).
- `fr.json` : Traductions en français.

### Exemple de Contenu

Voici un exemple du contenu du fichier `fr.json` :

```json
{
  "title": "Eedomus",
  "description": "Intégration pour la box domotique eedomus.",
  "config": {
    "host": "Adresse IP de la box eedomus",
    "api_user": "Utilisateur API",
    "api_secret": "Clé secrète API",
    "scan_interval": "Intervalle de scan (secondes)",
    "enable_history": "Activer l'historique",
    "enable_webhook": "Activer le webhook",
    "enable_api_proxy": "Activer l'API proxy",
    "api_proxy_disable_security": "Désactiver la sécurité de l'API proxy (debug uniquement)"
  },
  "errors": {
    "connection_failed": "Échec de la connexion à eedomus",
    "invalid_credentials": "Identifiants API invalides",
    "timeout": "Délai de connexion dépassé",
    "api_error": "Erreur de l'API"
  },
  "success": {
    "connected": "Connecté à eedomus",
    "updated": "Configuration mise à jour",
    "saved": "Paramètres enregistrés"
  },
  "warnings": {
    "no_devices": "Aucun périphérique trouvé",
    "partial_refresh": "Rafraîchissement partiel en cours",
    "full_refresh": "Rafraîchissement complet en cours"
  }
}
```

## Ajout de Nouvelles Traductions

Si vous souhaitez ajouter une nouvelle langue, suivez ces étapes :

1. **Créez un nouveau fichier de traduction** :
   - Créez un nouveau fichier dans le dossier `translations/` avec le code de la langue (par exemple, `es.json` pour l'espagnol).

2. **Traduisez les chaînes** :
   - Utilisez le fichier `en.json` comme référence pour traduire toutes les chaînes.

3. **Mettez à jour le manifest** :
   - Ajoutez la nouvelle langue dans le fichier `manifest.json` :
     ```json
     "language": ["fr", "es"]
     ```

4. **Redémarrez Home Assistant** :
   - Après avoir ajouté la nouvelle langue, redémarrez Home Assistant pour appliquer les changements.

## Dépannage

### Problème : Les traductions ne s'affichent pas
- **Solution** : Vérifiez que la langue de Home Assistant est bien définie sur français.
- **Solution** : Vérifiez que les fichiers de traduction sont bien présents dans le dossier `translations/`.
- **Solution** : Redémarrez Home Assistant pour appliquer les changements.

### Problème : Certaines chaînes ne sont pas traduites
- **Solution** : Vérifiez que toutes les chaînes sont bien traduites dans le fichier `fr.json`.
- **Solution** : Ajoutez les chaînes manquantes et redémarrez Home Assistant.

## Conclusion

Le support multi-langue dans l'intégration `hass-eedomus` permet aux utilisateurs de configurer et d'utiliser l'intégration dans leur langue préférée. Ce guide vous aide à activer et à utiliser le support français, ainsi qu'à ajouter de nouvelles langues si nécessaire.

Pour plus d'informations, consultez la [documentation officielle de Home Assistant sur les traductions](https://developers.home-assistant.io/docs/internationalization/).

---

**Date** : 2026-03-15
**Version** : 0.14.3
**Auteur** : Mistral Vibe