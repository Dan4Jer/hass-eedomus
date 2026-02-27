# 📖 Documentation des Options de Configuration

Ce document explique chaque paramètre disponible dans l'interface de configuration de l'intégration eedomus.

## 🔧 Paramètres Principaux

### api_host
**Type**: String (Adresse IP)
**Exemple**: `192.168.1.100`

L'adresse IP locale de votre box eedomus. Cette adresse permet à Home Assistant de communiquer directement avec votre box pour récupérer les états des périphériques et envoyer des commandes.

**Où le trouver** :
- Dans l'interface web de votre box eedomus
- Section "Réseau" ou "Informations système"

**Exemple de valeur**: `192.168.1.100`

---

### api_user
**Type**: String (Identifiant)
**Exemple**: `votre_email@example.com`

L'identifiant API de votre compte eedomus. Cet identifiant est nécessaire pour authentifier les requêtes envoyées à la box eedomus.

**Où le trouver** :
1. Connectez-vous à l'interface web de votre box eedomus
2. Allez dans "Mon compte" > "Identifiants pour l'API"
3. Copiez l'identifiant API

**Important**: Cet identifiant est différent de votre email de connexion habituel.

---

### api_secret
**Type**: String (Mot de passe)
**Exemple**: `votre_mot_de_passe_api`

Le mot de passe API associé à votre compte eedomus. Ce champ est sécurisé et masqué dans l'interface.

**Où le trouver** :
- Dans la même section que l'identifiant API ("Mon compte" > "Identifiants pour l'API")

**Important**: Ce mot de passe est différent de votre mot de passe de connexion habituel.

---

### enable_api_eedomus
**Type**: Boolean
**Valeur par défaut**: `True`

Active ou désactive l'interrogation des API locales de votre box eedomus. Lorsque cette option est activée, Home Assistant peut:
- Récupérer les états des périphériques (capteurs, actionneurs, etc.)
- Envoyer des commandes aux périphériques
- Synchroniser les états entre eedomus et Home Assistant

**Recommandation**: Laissez cette option activée pour un fonctionnement normal de l'intégration.

---

### enable_api_proxy
**Type**: Boolean
**Valeur par défaut**: `False`

Active le proxy API qui permet à votre box eedomus d'interroger Home Assistant et de manipuler directement des objets Home Assistant. Cette option permet:
- De déclencher des automatisations Home Assistant depuis des scénarios eedomus
- D'agir sur des entités Home Assistant depuis votre box eedomus
- D'intégrer des devices Home Assistant dans des scénarios eedomus

**Cas d'usage**:
- Créer un scénario eedomus qui active une lumière Home Assistant
- Déclencher une automatisation Home Assistant depuis un détecteur eedomus

---

### scan_interval
**Type**: Integer (secondes)
**Valeur par défaut**: `300` (5 minutes)
**Plage recommandée**: `60-600`

Détermine la fréquence à laquelle Home Assistant interroge votre box eedomus pour mettre à jour les états des périphériques.

**Optimisation**:
- **Intervalle court** (60-120s): Meilleure réactivité, mais charge plus la box
- **Intervalle long** (300-600s): Moins de charge, mais mise à jour moins fréquente
- **Équilibre recommandé**: 300 secondes (5 minutes) pour la plupart des installations

**Note**: Certains périphériques (lumières, interrupteurs) utilisent des webhooks pour des mises à jour instantanées et ne dépendent pas de cet intervalle.

---

### http_request_timeout
**Type**: Integer (secondes)
**Valeur par défaut**: `10`
**Plage recommandée**: `5-30`

Détermine le temps maximum d'attente pour une réponse de l'API eedomus avant de considérer la requête comme échouée.

**Quand l'ajuster**:
- **Augmenter** (15-30s): Si votre réseau est lent ou instable
- **Diminuer** (5-10s): Si vous voulez une détection plus rapide des échecs

**Positionnement**: Ce paramètre est maintenant placé juste en dessous de `scan_interval` pour une meilleure organisation logique, car les deux sont liés aux requêtes API.

---

### enable_set_value_retry
**Type**: Boolean
**Valeur par défaut**: `True`

Active la fonctionnalité de nouvelle tentative automatique lorsque l'envoi d'une valeur à un périphérique échoue (par exemple, valeur non autorisée).

**Fonctionnement**:
1. Première tentative avec la valeur demandée
2. Si échoue, utilise la valeur la plus proche autorisée
3. Nombre maximal de tentatives défini par `max_retries`

**Recommandation**: Laissez activé pour une meilleure compatibilité avec les périphériques ayant des contraintes de valeurs.

---

### max_retries
**Type**: Integer
**Valeur par défaut**: `3`
**Plage recommandée**: `1-5`

Nombre maximal de tentatives pour envoyer une valeur à un périphérique en cas d'échec initial.

**Exemple**: Si vous essayez de setter une luminosité à 45% mais que le périphérique n'accepte que 0%, 25%, 50%, 75%, 100%, l'intégration essaiera:
1. 45% (échoue)
2. 50% (valeur la plus proche autorisée)

---

### enable_webhook
**Type**: Boolean
**Valeur par défaut**: `True`

Active les webhooks pour une communication bidirectionnelle entre eedomus et Home Assistant. Permet:
- Rafraîchissement instantané des états
- Déclenchement d'actions Home Assistant depuis eedomus
- Intégration plus réactive

---

### api_proxy_disable_security
**Type**: Boolean
**Valeur par défaut**: `False`

**⚠️ À utiliser avec prudence**

Désactive la vérification de l'adresse IP source pour les requêtes API Proxy. Peut être utile pour:
- Tests locaux
- Autoriser d'autres machines du réseau local

**Risque**: Désactiver cette sécurité peut exposer votre installation à des requêtes non autorisées.

---

### php_fallback_enabled
**Type**: Boolean
**Valeur par défaut**: `False`

Active l'utilisation d'un script PHP pour contourner certaines limitations de l'API eedomus, notamment pour setter des valeurs non listées dans les options par défaut.

**Requiert**: Un serveur web PHP fonctionnel sur le même hôte que Home Assistant.

---

### php_fallback_script_name
**Type**: String
**Valeur par défaut**: `"fallback.php"`

Nom du script PHP utilisé pour le fallback. Doit être placé dans un répertoire accessible par votre serveur web.

---

### php_fallback_timeout
**Type**: Integer (secondes)
**Valeur par défaut**: `5`

Temps maximum d'attente pour la réponse du script PHP de fallback.

---

## 🧹 Fonctionnalité de Nettoyage (Nouveau)

**Service**: `eedomus.cleanup_unused_entities`

La fonctionnalité de nettoyage permet de supprimer automatiquement les entités eedomus inutilisées pour maintenir votre installation propre et performante.

### 🎯 Ce que fait le nettoyage

- **Supprime les entités désactivées**: Entités que vous avez manuellement désactivées dans Home Assistant
- **Supprime les entités obsolètes**: Entités dont l'`unique_id` contient "deprecated" (insensible à la casse)
- **Journalisation complète**: Suivi détaillé de toutes les actions de nettoyage
- **Sécurité**: N'affecte que les entités eedomus, sans risque pour les autres intégrations

### 🔧 Comment utiliser le nettoyage

#### Méthode 1: Via l'interface utilisateur
1. Allez dans **Paramètres** > **Outils de développement** > **Services**
2. Sélectionnez le service `eedomus.cleanup_unused_entities`
3. Cliquez sur **Appeler le service**

#### Méthode 2: Via la ligne de commande
```bash
ha services call eedomus.cleanup_unused_entities
```

#### Méthode 3: Via une automatisation
```yaml
automation:
  - alias: "Nettoyage mensuel Eedomus"
    trigger:
      - platform: time
        at: "03:00:00"
    action:
      - service: eedomus.cleanup_unused_entities
```

#### Méthode 4: Via un bouton dans le tableau de bord
```yaml
type: button
name: Nettoyer les entités Eedomus
tap_action:
  action: call-service
  service: eedomus.cleanup_unused_entities
```

### 📊 Que faire après le nettoyage

1. **Vérifiez les logs**: Consultez les logs Home Assistant pour voir le résumé du nettoyage
2. **Testez votre installation**: Assurez-vous que toutes vos automatisations fonctionnent encore
3. **Surveillez les performances**: Observez si le nettoyage a amélioré les performances
4. **Planifiez des nettoyages réguliers**: Configurez une automatisation pour un nettoyage périodique

### ⚠️ Précautions

- **Faites une sauvegarde** avant un nettoyage majeur
- **Évitez les heures de pointe** pour exécuter le nettoyage
- **Vérifiez les entités** avant de nettoyer (liste des entités désactivées/obsolètes)
- **Testez d'abord** sur un petit ensemble si vous êtes incertain

### 💡 Cas d'utilisation recommandés

- Après une mise à jour majeure de l'intégration
- Lors de la résolution de problèmes de performance
- Comme maintenance régulière (mensuelle/trimestrielle)
- Avant de faire une sauvegarde complète

---

## 🛠️ Services Eedomus Disponibles

L'intégration eedomus fournit plusieurs services puissants pour interagir avec votre box eedomus directement depuis Home Assistant.

### 🔄 Service: `eedomus.refresh`

**Description**: Force un rafraîchissement manuel de tous les périphériques eedomus.

**Utilisation**:
```bash
# Via Developer Tools
ha services call eedomus.refresh

# Via automatisation
service: eedomus.refresh
```

**Cas d'utilisation**:
- Après des changements manuels sur la box eedomus
- Pour synchroniser immédiatement les états
- Lors du débogage de problèmes de synchronisation

**Précautions**:
- Peut charger temporairement la box eedomus
- Les rafraîchissements trop fréquents peuvent être bloqués

---

### 📤 Service: `eedomus.set_value`

**Description**: Permet de définir la valeur d'un périphérique eedomus.

**Paramètres requis**:
- `device_id`: ID du périphérique eedomus
- `value`: Valeur à définir

**Exemple**:
```bash
ha services call eedomus.set_value \
  --device_id 12345 \
  --value 100

# Via automatisation
action:
  service: eedomus.set_value
  data:
    device_id: "12345"
    value: "100"
```

**Cas d'utilisation**:
- Contrôler des périphériques spécifiques
- Intégrer avec des scripts personnalisés
- Automatisations avancées

**Précautions**:
- Vérifiez que le device_id existe
- Utilisez des valeurs valides pour le type de périphérique
- Gérez les erreurs dans les automatisations

---

### 🔄 Service: `eedomus.reload`

**Description**: Recharge la configuration de l'intégration sans redémarrer Home Assistant.

**Utilisation**:
```bash
ha services call eedomus.reload
```

**Cas d'utilisation**:
- Après des changements dans les fichiers de configuration
- Pour appliquer des modifications sans redémarrage complet
- Lors du développement ou du débogage

**Précautions**:
- Peut interrompre brièvement la communication
- Les changements majeurs peuvent nécessiter un redémarrage

---

### 🌡️ Service: `eedomus.set_climate_temperature`

**Description**: Définit la température d'un périphérique climatisation eedomus.

**Paramètres requis**:
- `device_id`: ID du périphérique climatisation
- `temperature`: Température cible (7.0°C - 30.0°C)

**Exemple**:
```bash
ha services call eedomus.set_climate_temperature \
  --device_id 67890 \
  --temperature 21.5
```

**Cas d'utilisation**:
- Contrôle précis de la température
- Intégration avec des thermostats intelligents
- Automatisations basées sur la température

**Précautions**:
- Le périphérique doit être un device climatisation valide
- Température doit être entre 7.0°C et 30.0°C
- Arrondie au 0.5°C près

---

### 🧹 Service: `eedomus.cleanup_unused_entities`

**Description**: Nettoie les entités eedomus inutilisées (désactivées ou obsolètes).

**Utilisation**:
```bash
ha services call eedomus.cleanup_unused_entities
```

**Cas d'utilisation**:
- Maintenance régulière du système
- Après des mises à jour majeures
- Résolution de problèmes de performance

**Précautions**:
- Faites une sauvegarde avant un nettoyage majeur
- Vérifiez les logs après exécution
- Évitez les heures de pointe

---

## 🎯 Bonnes Pratiques

1. **Commencez avec les valeurs par défaut** pour la plupart des paramètres
2. **Ajustez scan_interval** en fonction de vos besoins de réactivité et de la charge de votre box
3. **Activez les options avancées** (webhook, API proxy) seulement si vous en avez besoin
4. **Surveillez les logs** après des changements pour détecter des problèmes
5. **Testez les changements** un par un pour identifier les impacts

## 📚 Documentation Complémentaire

Pour plus d'informations sur l'intégration eedomus:
- [Documentation officielle](https://github.com/Dan4Jer/hass-eedomus)
- [Forum Home Assistant](https://community.home-assistant.io/)
- [Issues GitHub](https://github.com/Dan4Jer/hass-eedomus/issues)

---

*Documentation générée automatiquement - Dernière mise à jour: 2026*
