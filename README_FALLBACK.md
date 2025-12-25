# Script PHP de Fallback pour hass-eedomus

Ce document décrit comment déployer et configurer le script PHP de fallback pour gérer les valeurs rejetées par l'API eedomus.

## Introduction

Le script `fallback.php` permet de transformer ou mapper une valeur rejetée par l'API eedomus avant une nouvelle tentative d'envoi. Cela offre une solution flexible et configurable pour gérer les valeurs non autorisées ou invalides.

## Déploiement du script

### Prérequis
- Une box eedomus avec un serveur web fonctionnel (Apache, Nginx, etc.).
- Accès en écriture au répertoire web de la box eedomus (généralement `/var/www/html/`).

### Étapes de déploiement

1. **Créer un répertoire dédié** :
   ```bash
   mkdir -p /var/www/html/eedomus_fallback/
   ```

2. **Copier le script PHP** :
   ```bash
   cp fallback.php /var/www/html/eedomus_fallback/
   ```

3. **Vérifier les permissions** :
   Assurez-vous que le script est accessible par le serveur web :
   ```bash
   chmod 644 /var/www/html/eedomus_fallback/fallback.php
   chown www-data:www-data /var/www/html/eedomus_fallback/fallback.php
   ```

4. **Tester le script** :
   Vous pouvez tester le script en accédant à l'URL suivante dans votre navigateur ou via `curl` :
   ```bash
   curl "http://<IP_BOX_EEDOMUS>/eedomus_fallback/fallback.php?value=haut&device_id=123&cmd_name=set_value&log=true"
   ```
   Remplacez `<IP_BOX_EEDOMUS>` par l'adresse IP de votre box eedomus.

## Configuration dans Home Assistant

### Activation du fallback PHP

1. **Accéder à la configuration de l'intégration hass-eedomus** :
   - Allez dans **Paramètres** > **Périphériques et services** > **hass-eedomus**.
   - Cliquez sur **Configurer**.

2. **Activer le fallback PHP** :
   - Cochez la case **Activer le fallback PHP**.
   - Entrez l'URL du script PHP (ex: `http://<IP_BOX_EEDOMUS>/eedomus_fallback/fallback.php`).
   - Configurez le timeout pour la requête HTTP (défaut : 5 secondes).
   - Activez les logs détaillés si nécessaire.

3. **Sauvegarder la configuration** :
   - Cliquez sur **Soumettre** pour enregistrer les modifications.

## Personnalisation du script

### Mapping des valeurs

Le script inclut un exemple de mapping des valeurs. Vous pouvez personnaliser ce mapping en modifiant la section suivante dans `fallback.php` :

```php
$mapping = [
    'haut' => '100',
    'bas' => '0',
    'on' => '1',
    'off' => '0',
    'open' => '1',
    'close' => '0',
];
```

### Traitement conditionnel

Le script inclut également un exemple de traitement conditionnel pour les valeurs numériques. Vous pouvez ajuster les valeurs minimales et maximales selon vos besoins :

```php
$min_value = 0;
$max_value = 100;
$new_value = max($min_value, min($max_value, $numeric_value));
```

## Journalisation

Le script peut journaliser les appels et les transformations si le paramètre `log` est défini à `true`. Les logs sont écrits dans le journal du serveur web (généralement `/var/log/apache2/error.log` ou `/var/log/nginx/error.log`).

## Sécurité

- **Validation des entrées** : Le script valide et sanitize toutes les entrées pour éviter les injections.
- **Accès restreint** : Assurez-vous que le script est accessible uniquement depuis votre réseau local ou depuis l'adresse IP de votre instance Home Assistant.

## Exemples d'utilisation

### Exemple 1 : Mapping de valeurs textuelles

Si l'API eedomus rejette la valeur "haut", le script peut la mapper à "100" :

```bash
curl "http://<IP_BOX_EEDOMUS>/eedomus_fallback/fallback.php?value=haut&device_id=123&cmd_name=set_value"
```

Réponse :
```
100
```

### Exemple 2 : Traitement conditionnel

Si l'API eedomus rejette une valeur numérique en dehors d'une plage autorisée, le script peut ajuster la valeur :

```bash
curl "http://<IP_BOX_EEDOMUS>/eedomus_fallback/fallback.php?value=150&device_id=123&cmd_name=set_value"
```

Réponse :
```
100
```

### Exemple 3 : Journalisation activée

Pour activer la journalisation, ajoutez le paramètre `log=true` :

```bash
curl "http://<IP_BOX_EEDOMUS>/eedomus_fallback/fallback.php?value=haut&device_id=123&cmd_name=set_value&log=true"
```

## Dépannage

### Problèmes courants

1. **Script inaccessible** :
   - Vérifiez que le script est bien copié dans le répertoire web.
   - Vérifiez les permissions du fichier.
   - Assurez-vous que le serveur web est en cours d'exécution.

2. **Erreur 400** :
   - Vérifiez que tous les paramètres requis (`value`, `device_id`, `cmd_name`) sont fournis.
   - Assurez-vous que les valeurs des paramètres sont valides.

3. **Erreur 500** :
   - Consultez les logs du serveur web pour plus de détails.
   - Vérifiez la syntaxe du script PHP.

### Vérification des logs

Pour vérifier les logs du serveur web :

```bash
# Pour Apache
tail -f /var/log/apache2/error.log

# Pour Nginx
tail -f /var/log/nginx/error.log
```

## Conclusion

Le script PHP de fallback offre une solution flexible pour gérer les valeurs rejetées par l'API eedomus. En le personnalisant, vous pouvez adapter le comportement de votre intégration hass-eedomus à vos besoins spécifiques.

Pour plus d'informations, consultez la [documentation principale de hass-eedomus](README.md).
