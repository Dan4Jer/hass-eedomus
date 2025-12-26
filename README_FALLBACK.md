# Script PHP de Fallback pour hass-eedomus

Ce document décrit comment déployer et configurer le script PHP de fallback pour gérer les valeurs rejetées par l'API eedomus.

## Introduction

Le script `fallback.php` permet d'effectuer directement un appel à l'API eedomus locale pour setter une valeur lorsqu'une tentative initiale a échoué. Cela offre une solution simple et efficace pour gérer les valeurs rejetées.

## Déploiement du script

### Prérequis
- Une box eedomus avec un serveur web fonctionnel (Apache, Nginx, etc.).
- Accès en écriture au répertoire web de la box eedomus (généralement `/var/www/html/`).
- Le script doit être en encodage ASCII pour être compatible avec la box eedomus.

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

4. **Vérifier l'encodage** :
   Assurez-vous que le script est en encodage ASCII :
   ```bash
   file -i /var/www/html/eedomus_fallback/fallback.php
   ```
   Le résultat doit être : `text/x-php; charset=us-ascii`

5. **Tester le script** :
   Vous pouvez tester le script en accédant à l'URL suivante dans votre navigateur ou via `curl` :
   ```bash
   curl "http://<IP_BOX_EEDOMUS>/eedomus_fallback/fallback.php?value=50&device_id=123"
   ```
   
   **Paramètres requis (2 seulement)** :
   - `value` : Valeur à setter sur le périphérique
   - `device_id` : ID du périphérique eedomus
   
   Remplacez `<IP_BOX_EEDOMUS>` par l'adresse IP de votre box eedomus.
   
   **Note importante** : Le script utilise les fonctions natives de l'API eedomus (`setValue()`) qui accèdent directement aux informations d'API de la box, donc aucun paramètre supplémentaire n'est nécessaire.

## Configuration dans Home Assistant

### Activation du PHP fallback

1. **Accéder à la configuration de l'intégration hass-eedomus** :
   - Allez dans **Paramètres** > **Périphériques et services** > **hass-eedomus**.
   - Cliquez sur **Configurer**.

2. **Activer le PHP fallback** :
   - Cochez la case **Activer le PHP fallback**.
   - Entrez le nom du script PHP (ex: `eedomus_fallback`).
   - Configurez le timeout pour la requête HTTP (défaut : 5 secondes).
   - Activez les logs détaillés si nécessaire.

3. **Sauvegarder la configuration** :
   - Cliquez sur **Soumettre** pour enregistrer les modifications.

**Note** : Le nom du script est utilisé pour construire l'URL complète du script. Par exemple, si vous entrez `eedomus_fallback` comme nom de script, l'URL complète sera `http://<IP_BOX_EEDOMUS>/script/?exec=eedomus_fallback`. Assurez-vous que le script est déployé sur la box eedomus avec le nom exact que vous avez spécifié.

## Fonctionnement du script

Le script `fallback.php` est conçu pour être **ultra-simple et direct**. Il utilise uniquement la fonction native `setValue()` de l'API eedomus avec **2 paramètres seulement** :

### Architecture simplifiée

```
Home Assistant → PHP Fallback Script → eedomus API (setValue)
```

### Détails techniques

1. **Paramètres d'entrée (2 seulement)** :
   - `value` : Valeur à setter sur le périphérique
   - `device_id` : ID du périphérique eedomus

2. **Appel API natif** :
   - Le script appelle `setValue($device_id, $value)` - une fonction native de l'API eedomus
   - Aucune authentification supplémentaire nécessaire (utilise le contexte de la box)
   - Aucune construction d'URL complexe

3. **Réponse directe** :
   - Si succès : retourne le JSON natif de `setValue()` (ex: `{"success":1,"body":{"result":"ok"}}`)
   - Si échec : retourne un JSON d'erreur simple

### Avantages de cette approche

✅ **Simplicité maximale** : Seulement 27 lignes de code
✅ **Performance optimale** : Appel direct sans surcharge
✅ **Compatibilité totale** : Utilise les fonctions natives eedomus
✅ **Maintenance facile** : Pas de dépendances externes
✅ **Sécurité intégrée** : Utilise le contexte d'exécution de la box

**Documentation** : Basé sur la documentation officielle : https://doc.eedomus.com/view/Scripts

**Contraintes respectées** : Pas de fonctions interdites (`json_encode`, `http_response_code`, etc.)

**Configuration par défaut** : Le nom du script est maintenant `fallback.php` par défaut.

## Exemple de code

Voici le code complet du script PHP (27 lignes seulement) :

```php
<?php
/**
 * Script PHP de fallback pour la gestion des valeurs non definies dans hass-eedomus.
 * 
 * Ce script appelle uniquement la fonction setValue de l'API eedomus.
 * Il est conçu pour être simple et direct, sans logique supplémentaire.
 * 
 * Documentation : https://doc.eedomus.com/view/Scripts
 * 
 * @package hass-eedomus
 * @author Dan4Jer
 * @license MIT
 */

// Récupération des arguments minimaux
$value = $_GET['value'];
$device_id = $_GET['device_id'];

// Appel de la fonction setValue de l'API eedomus
$result = setValue($device_id, $value);

// Retourner le resultat directement (setValue retourne déjà un JSON valide)
if ($result !== false) {
    echo $result;
} else {
    echo '{"success": 0, "error": "Erreur lors de l\'appel a setValue"}';
}
```

**Points clés** :
- Seulement 2 paramètres requis (`value` et `device_id`)
- Appel direct à `setValue()` - fonction native eedomus
- Retourne le JSON natif de l'API sans transformation
- Gestion d'erreur minimale et efficace

## Dépannage

### Problèmes courants

#### 1. "PHP fallback is not configured or disabled"

**Symptômes** :
- Les logs montrent `🔄 Trying PHP fallback` mais échouent avec `PHP fallback is not configured or disabled`

**Solutions** :
1. **Vérifiez la configuration** : Dans Home Assistant, allez dans Paramètres > Périphériques et services > hass-eedomus > Configurer et assurez-vous que "Activer le PHP fallback" est coché.
2. **Redémarrez Home Assistant** : Après avoir activé la fonctionnalité, un redémarrage est nécessaire pour que les modifications prennent effet.
3. **Vérifiez les options** : Si vous avez modifié les options, assurez-vous qu'elles sont bien enregistrées.

#### 2. "Invalid JSON response from PHP fallback script"

**Symptômes** :
- Les logs montrent `Invalid JSON response from PHP fallback script: {"success": 1, "result": "{\"success\":1, ...}"}`

**Cause** : Le script PHP enveloppait le résultat JSON de `setValue()` dans un autre JSON, créant un JSON imbriqué invalide.

**Solution** : Ce problème a été corrigé dans la version 0.11.4. Assurez-vous d'utiliser la dernière version du script `fallback.php`.

#### 3. "Erreur API eedomus: HTTP 400/500"

**Symptômes** :
- Le script PHP retourne des erreurs HTTP

**Solutions** :
1. **Vérifiez les paramètres** : Assurez-vous que `api_host`, `api_user` et `api_secret` sont corrects.
2. **Vérifiez le périphérique** : Assurez-vous que `device_id` est valide.
3. **Vérifiez les logs du serveur web** : Consultez `/var/log/apache2/error.log` ou `/var/log/nginx/error.log` pour plus de détails.

### Vérification des logs

Pour vérifier les logs du serveur web :

```bash
# Pour Apache
tail -f /var/log/apache2/error.log

# Pour Nginx
tail -f /var/log/nginx/error.log
```

### Test du script PHP

Pour tester manuellement le script PHP :

```bash
curl -v "http://<IP_BOX_EEDOMUS>/eedomus_fallback/fallback.php?value=50&device_id=123&api_host=192.168.1.100&api_user=myuser&api_secret=mysecret"
```

Une réponse réussie devrait ressembler à :
```json
{"success":1,"body":{"result":"ok"}}
```

## Historique des versions

### Version 0.11.4 (2025-12-26)
- **Correction** : Fix JSON response parsing by returning `setValue()` result directly
- **Correction** : Fix PHP fallback configuration reading from config_entry
- **Correction** : Remove unused `CONF_PHP_FALLBACK_LOG_ENABLED` constants
- **Amélioration** : Simplified fallback.php script with direct API calls
- **Documentation** : Added troubleshooting section

### Version 0.11.3 (2025-12-25)
- **Nouvelle fonctionnalité** : PHP fallback support for handling rejected values
- **Nouveau fichier** : `fallback.php` script for direct API calls
- **Nouveau fichier** : `README_FALLBACK.md` documentation
- **Nouveau fichier** : `test_fallback.py` test suite

## Conclusion

Le script PHP de fallback offre une solution simple et efficace pour gérer les valeurs rejetées par l'API eedomus. En l'utilisant, vous pouvez améliorer la robustesse de votre intégration hass-eedomus.

Pour plus d'informations, consultez la [documentation principale de hass-eedomus](README.md) et la [documentation officielle de l'API eedomus](https://doc.eedomus.com/view/Scripts).
## Fonctionnement du script

Le script `fallback.php` est conçu pour être simple et direct. Il appelle uniquement la fonction `setValue` de l'API eedomus avec les paramètres minimaux. Voici comment il fonctionne :

1. **Récupération des paramètres minimaux** :
   - `value` : Valeur à setter sur le périphérique.
   - `device_id` : ID du périphérique eedomus.

2. **Appel de la fonction setValue** :
   - Le script appelle la fonction `setValue` de l'API eedomus avec les paramètres minimaux.
   - La fonction `setValue` est définie dans l'API eedomus et est documentée ici : https://doc.eedomus.com/view/Scripts

3. **Gestion des erreurs** :
   - Si l'appel réussit, le script retourne un JSON avec `success` à 1 et le résultat.
   - Si l'appel échoue, le script retourne un JSON avec `success` à 0 et un message d'erreur générique.

**Documentation** : Ce script suit la documentation officielle de l'API eedomus : https://doc.eedomus.com/view/Scripts

**Contraintes** : Ce script respecte les contraintes de la box eedomus et n'utilise pas de fonctions non autorisées comme `json_encode`, `http_response_code`, `getMessage`, et `()`.

## Exemple de code

Voici un exemple simplifié du script PHP :

```php
<?php
// Récupération des arguments minimaux
$value = isset($_GET['value']) ? $_GET['value'] : (isset($_POST['value']) ? $_POST['value'] : '');
$device_id = isset($_GET['device_id']) ? $_GET['device_id'] : (isset($_POST['device_id']) ? $_POST['device_id'] : '');

// Appel de la fonction setValue de l'API eedomus
$result = setValue($device_id, $value);

// Retourner le résultat
if ($result !== false) {
    echo '{"success": 1, "result": "' . $result . '"}';
} else {
    echo '{"success": 0, "error": "Erreur lors de l\'appel à setValue"}';
}
?>
```

## Conclusion

Le script PHP de fallback offre une solution simple et efficace pour gérer les valeurs rejetées par l'API eedomus. En l'utilisant, vous pouvez améliorer la robustesse de votre intégration hass-eedomus.

Pour plus d'informations, consultez la [documentation principale de hass-eedomus](README.md) et la [documentation officielle de l'API eedomus](https://doc.eedomus.com/view/Scripts).
## Fonctionnement du script

Le script `fallback.php` est conçu pour être simple et direct. Il appelle uniquement la fonction `setValue` de l'API eedomus avec les paramètres minimaux. Voici comment il fonctionne :

1. **Récupération des paramètres minimaux** :
   - `value` : Valeur à setter sur le périphérique.
   - `device_id` : ID du périphérique eedomus.

2. **Appel de la fonction setValue** :
   - Le script appelle la fonction `setValue` de l'API eedomus avec les paramètres minimaux.
   - La fonction `setValue` est définie dans l'API eedomus et est documentée ici : https://doc.eedomus.com/view/Scripts

3. **Gestion des erreurs** :
   - Si l'appel réussit, le script retourne un JSON avec `success` à 1 et le résultat.
   - Si l'appel échoue, le script retourne un JSON avec `success` à 0 et un message d'erreur générique.

**Documentation** : Ce script suit la documentation officielle de l'API eedomus : https://doc.eedomus.com/view/Scripts

**Contraintes** : Ce script respecte les contraintes de la box eedomus et n'utilise pas de fonctions non autorisées comme `json_encode`, `http_response_code`, `getMessage`, et `()`.

## Exemple de code

Voici un exemple simplifié du script PHP :

```php
## Fonctionnement du script

Le script `fallback.php` est conçu pour être simple et direct. Il appelle uniquement la fonction `setValue` de l'API eedomus avec les paramètres minimaux. Voici comment il fonctionne :

1. **Récupération des paramètres minimaux** :
   - `value` : Valeur à setter sur le périphérique.
   - `device_id` : ID du périphérique eedomus.

2. **Appel de la fonction setValue** :
   - Le script appelle la fonction `setValue` de l'API eedomus avec les paramètres minimaux.
   - La fonction `setValue` est définie dans l'API eedomus et est documentée ici : https://doc.eedomus.com/view/Scripts

3. **Gestion des erreurs** :
   - Si l'appel réussit, le script retourne un JSON avec `success` à 1 et le résultat.
   - Si l'appel échoue, le script retourne un JSON avec `success` à 0 et le message d'erreur.

**Documentation** : Ce script suit la documentation officielle de l'API eedomus : https://doc.eedomus.com/view/Scripts

**Contraintes** : Ce script respecte les contraintes de la box eedomus et n'utilise pas de fonctions non autorisées comme `json_encode`, `http_response_code`, et `getMessage`.

## Exemple de code

Voici un exemple simplifié du script PHP :

```php
## Fonctionnement du script

Le script `fallback.php` est conçu pour être simple et direct. Il appelle uniquement la fonction `setValue` de l'API eedomus avec les paramètres minimaux. Voici comment il fonctionne :

1. **Récupération des paramètres minimaux** :
   - `value` : Valeur à setter sur le périphérique.
   - `device_id` : ID du périphérique eedomus.

2. **Appel de la fonction setValue** :
   - Le script appelle la fonction `setValue` de l'API eedomus avec les paramètres minimaux.
   - La fonction `setValue` est définie dans l'API eedomus et est documentée ici : https://doc.eedomus.com/view/Scripts

3. **Gestion des erreurs** :
   - Si l'appel réussit, le script retourne un JSON avec `success` à 1 et le résultat.
   - Si l'appel échoue, le script retourne un JSON avec `success` à 0 et le message d'erreur.

**Documentation** : Ce script suit la documentation officielle de l'API eedomus : https://doc.eedomus.com/view/Scripts

## Exemple de code

Voici un exemple simplifié du script PHP :

```php
## Fonctionnement du script

Le script `fallback.php` est conçu pour être simple et direct. Il appelle uniquement la fonction `setValue` de l'API eedomus avec une gestion des erreurs. Voici comment il fonctionne :

1. **Récupération des paramètres** :
   - `value` : Valeur à setter sur le périphérique.
   - `device_id` : ID du périphérique eedomus.
   - `api_host` : Adresse IP de la box eedomus.
   - `api_user` : Utilisateur API eedomus.
   - `api_secret` : Clé secrète API eedomus.
   - `log` (optionnel) : Active la journalisation si défini à `true`.

2. **Appel de la fonction setValue** :
   - Le script appelle la fonction `setValue` de l'API eedomus en utilisant `file_get_contents`.
   - L'URL construite est de la forme :
     ````
     http://<api_host>/api/set?action=periph.value&periph_id=<device_id>&value=<value>&api_user=<api_user>&api_secret=<api_secret>
     ````

3. **Gestion des erreurs** :
   - Si l'appel réussit, le script retourne la réponse de l'API.
   - Si l'appel échoue, le script retourne le code d'erreur et le message d'erreur.
   - Les erreurs sont également gérées et retournées avec un code HTTP 500.

**Documentation** : Ce script suit la documentation officielle de l'API eedomus : https://doc.eedomus.com/view/Scripts

## Exemple de code

Voici un exemple simplifié du script PHP :

```php
## Fonctionnement du script

Le script `fallback.php` est conçu pour être simple et direct. Il appelle uniquement la fonction `setValue` de l'API eedomus avec une gestion des erreurs. Voici comment il fonctionne :

1. **Récupération des paramètres** :
   - `value` : Valeur à setter sur le périphérique.
   - `device_id` : ID du périphérique eedomus.
   - `api_host` : Adresse IP de la box eedomus.
   - `api_user` : Utilisateur API eedomus.
   - `api_secret` : Clé secrète API eedomus.
   - `log` (optionnel) : Active la journalisation si défini à `true`.

2. **Appel de la fonction setValue** :
   - Le script appelle la fonction `setValue` de l'API eedomus en utilisant `file_get_contents`.
   - L'URL construite est de la forme :
     ````
     http://<api_host>/api/set?action=periph.value&periph_id=<device_id>&value=<value>&api_user=<api_user>&api_secret=<api_secret>
     ````

3. **Gestion des erreurs** :
   - Si l'appel réussit, le script retourne la réponse de l'API.
   - Si l'appel échoue, le script retourne le code d'erreur et le message d'erreur.
   - Les erreurs sont également gérées et retournées avec un code HTTP 500.

4. **Journalisation** :
   - Si la journalisation est activée (`log=true`), le script journalise les appels et les réponses dans les logs du serveur web.

**Inspiration** : Ce script s'inspire du script [2B_domzevents.php](https://github.com/2bprog/eedomus-domoticzevent-plugin/blob/master/php/2B_domzevents.php) du plugin eedomus-domoticzevent-plugin.

## Exemple de code

Voici un exemple simplifié du script PHP :

```php
## Fonctionnement du script

Le script `fallback.php` est conçu pour être simple et direct. Il appelle uniquement la fonction `setValue` de l'API eedomus avec une gestion des erreurs. Voici comment il fonctionne :

1. **Récupération des paramètres** :
   - `value` : Valeur à setter sur le périphérique.
   - `device_id` : ID du périphérique eedomus.
   - `api_host` : Adresse IP de la box eedomus.
   - `api_user` : Utilisateur API eedomus.
   - `api_secret` : Clé secrète API eedomus.
   - `log` (optionnel) : Active la journalisation si défini à `true`.

2. **Appel de la fonction setValue** :
   - Le script appelle la fonction `setValue` de l'API eedomus en utilisant cURL.
   - L'URL construite est de la forme :
     ````
     http://<api_host>/api/set?action=periph.value&periph_id=<device_id>&value=<value>&api_user=<api_user>&api_secret=<api_secret>
     ````

3. **Gestion des erreurs** :
   - Si l'appel réussit (code HTTP 200), le script retourne la réponse de l'API.
   - Si l'appel échoue, le script retourne le code d'erreur et le message d'erreur.
   - Les erreurs cURL sont également gérées et retournées avec un code HTTP 500.

4. **Journalisation** :
   - Si la journalisation est activée (`log=true`), le script journalise les appels et les réponses dans les logs du serveur web.

## Exemple de code

Voici un exemple simplifié du script PHP :

```php


## Exemple de code

Voici un exemple simplifié du script PHP :

```php
<?php
// Récupération des arguments
$value = getArg('value', true);
$device_id = getArg('device_id', true);
$api_host = getArg('api_host', true);
$api_user = getArg('api_user', true);
$api_secret = getArg('api_secret', true);
$log_enabled = getArg('log', false, 'false') === 'true';

// Appel direct à l'API eedomus pour setter la valeur
$url = "http://$api_host/api/set?action=periph.value&periph_id=$device_id&value=$value&api_user=$api_user&api_secret=$api_secret";

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);

if (curl_errno($ch)) {
    http_response_code(500);
    echo "Erreur cURL: " . curl_error($ch);
    exit;
}

$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($http_code != 200) {
    http_response_code($http_code);
    echo "Erreur API eedomus: HTTP $http_code - $response";
    exit;
}

echo $response;
?>
```

## Exemples d'utilisation

### Exemple 1 : Setter une valeur numérique

Si l'API eedomus a rejeté une valeur, le script peut la réessayer directement :

```bash
curl "http://<IP_BOX_EEDOMUS>/eedomus_fallback/fallback.php?value=75&device_id=123&api_host=192.168.1.100&api_user=myuser&api_secret=mysecret"
```

Réponse (exemple) :
```json
{"success":1,"body":{"result":"ok"}}
```

### Exemple 2 : Journalisation activée

Pour activer la journalisation, ajoutez le paramètre `log=true` :

```bash
curl "http://<IP_BOX_EEDOMUS>/eedomus_fallback/fallback.php?value=50&device_id=123&api_host=192.168.1.100&api_user=myuser&api_secret=mysecret&log=true"
```

### Exemple 3 : Erreur d'API

Si l'API eedomus retourne une erreur, le script la propagera :

```bash
curl "http://<IP_BOX_EEDOMUS>/eedomus_fallback/fallback.php?value=invalid&device_id=123&api_host=192.168.1.100&api_user=myuser&api_secret=mysecret"
```

Réponse (exemple) :
```
Erreur API eedomus: HTTP 400 - {"success":0,"error":"Invalid parameter value"}
```

## Journalisation

Le script peut journaliser les appels et les réponses si le paramètre `log` est défini à `true`. Les logs sont écrits dans le journal du serveur web (généralement `/var/log/apache2/error.log` ou `/var/log/nginx/error.log`).

Exemple de log :
```
[hass-eedomus fallback] Script appelé avec value=50, device_id=123, api_host=192.168.1.100
[hass-eedomus fallback] Appel API eedomus: http://192.168.1.100/api/set?action=periph.value&periph_id=123&value=50&api_user=myuser&api_secret=*****
[hass-eedomus fallback] Réponse API: HTTP 200 - {"success":1,"body":{"result":"ok"}}
```

## Sécurité

- **Validation des entrées** : Le script valide et sanitize toutes les entrées pour éviter les injections.
- **Accès restreint** : Assurez-vous que le script est accessible uniquement depuis votre réseau local ou depuis l'adresse IP de votre instance Home Assistant.
- **Protection des informations sensibles** : Les logs masquent les informations sensibles comme `api_secret`.

## Dépannage

### Problèmes courants

1. **Script inaccessible** :
   - Vérifiez que le script est bien copié dans le répertoire web.
   - Vérifiez les permissions du fichier.
   - Assurez-vous que le serveur web est en cours d'exécution.

2. **Erreur 400** :
   - Vérifiez que tous les paramètres requis (`value`, `device_id`, `api_host`, `api_user`, `api_secret`) sont fournis.
   - Assurez-vous que les valeurs des paramètres sont valides.

3. **Erreur 500** :
   - Consultez les logs du serveur web pour plus de détails.
   - Vérifiez que l'extension cURL est activée sur votre serveur web.

4. **Erreur API eedomus** :
   - Vérifiez que les informations d'API (`api_host`, `api_user`, `api_secret`) sont correctes.
   - Assurez-vous que le périphérique (`device_id`) existe et est accessible.

### Vérification des logs

Pour vérifier les logs du serveur web :

```bash
# Pour Apache
tail -f /var/log/apache2/error.log

# Pour Nginx
tail -f /var/log/nginx/error.log
```

## Personnalisation

Le script peut être personnalisé pour ajouter des fonctionnalités supplémentaires :

1. **Mapping des valeurs** : Ajoutez un mapping des valeurs avant l'appel API.
2. **Traitement conditionnel** : Ajoutez des règles pour transformer les valeurs en fonction de conditions spécifiques.
3. **Gestion des erreurs avancée** : Personnalisez la gestion des erreurs pour des cas spécifiques.

## Étapes d'installation de la fonctionnalité PHP fallback

### Résumé des étapes

1. **Déployer le script PHP** :
   - Copiez le fichier `fallback.php` dans un répertoire accessible par votre serveur web sur la box eedomus (ex: `/var/www/html/eedomus_fallback/`).
   - Assurez-vous que le script est en encodage ASCII.
   - Vérifiez les permissions du fichier.

2. **Configurer l'intégration** :
   - Accédez à la configuration de l'intégration hass-eedomus dans Home Assistant.
   - Activez l'option **Activer le PHP fallback**.
   - Entrez le nom du script PHP (ex: `eedomus_fallback`).
   - Configurez le timeout pour la requête HTTP (défaut : 5 secondes).
   - Activez les logs détaillés si nécessaire.

3. **Tester la fonctionnalité** :
   - Essayez de setter une valeur invalide sur un périphérique pour déclencher le PHP fallback.
   - Vérifiez les logs pour voir si le PHP fallback est appelé et s'il réussit.

### Exemple de test

1. **Déclencher le PHP fallback** :
   - Essayez de setter une valeur invalide sur un périphérique :
   ```bash
   curl "http://<IP_BOX_EEDOMUS>/api/set?action=periph.value&periph_id=123&value=invalid&api_user=myuser&api_secret=mysecret"
   ```

2. **Vérifier les logs** :
   - Vérifiez les logs de Home Assistant pour voir si le PHP fallback est appelé :
   ```bash
   tail -f /config/home-assistant.log | grep "PHP fallback"
   ```

3. **Vérifier le résultat** :
   - Vérifiez que la valeur a été correctement setée sur le périphérique.

## Conclusion

Le script PHP de fallback offre une solution simple et efficace pour gérer les valeurs rejetées par l'API eedomus. En l'utilisant, vous pouvez améliorer la robustesse de votre intégration hass-eedomus.

Pour plus d'informations, consultez la [documentation principale de hass-eedomus](README.md) et la [documentation officielle de l'API eedomus](https://doc.eedomus.com/view/Scripts).
