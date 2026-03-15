# Guide de Migration pour l'Intégration hass-eedomus

## Aperçu

Ce guide explique comment fonctionne le système de migration dans l'intégration hass-eedomus pour préserver les personnalisations des utilisateurs lors des mises à jour de version.

## Système de Migration

### Fonctionnement

1. **Suivi des Versions** : L'intégration suit les versions des entrées de configuration
2. **Migration Automatique** : Lorsqu'une nouvelle version est détectée, la fonction `async_migrate_entry` est exécutée
3. **Préservation des Sauvegardes** : Les fichiers personnalisés comme `custom_mapping.yaml` sont sauvegardés avant la migration
4. **Intégrité des Données** : Les personnalisations utilisateur sont préservées lors des mises à jour

### Chemins de Migration Actuels

- **Version 1 → 2** : Ajout des options d'historique et de suppression d'entités
- **Version 2 → 3** : Ajout des paramètres de proxy API
- **Version 3 → 4** : Préserve le fichier `custom_mapping.yaml`

## Pour les Utilisateurs comme Fabrice (Issue #27)

### Ce qui se Passe Pendant la Mise à Jour

1. **Avant la Mise à Jour** : Votre fichier `custom_mapping.yaml` contient vos mappages personnalisés
2. **Pendant la Mise à Jour** : Le système de migration crée une sauvegarde : `custom_mapping.yaml.backup_v3`
3. **Après la Mise à Jour** : Vos mappages personnalisés restent intacts et fonctionnels

### Comment Vérifier que vos Personnalisations sont Préservées

1. **Vérifier les Fichiers de Sauvegarde** :
   ```bash
   ls -la custom_components/eedomus/config/custom_mapping.yaml* 
   ```

2. **Vérifier les Mappages Actuels** :
   ```bash
   grep -c "custom_usage_id_mappings" custom_components/eedomus/config/custom_mapping.yaml
   ```

3. **Vérifier les Logs pour la Réussite de la Migration** :
   ```bash
   grep "Migration to version 4 completed" home-assistant.log
   ```

## Migration Manuelle (Si Nécessaire)

### Si la Migration ne s'est pas Exécutée Automatiquement

1. **Déclencher la Migration Manuelle** :
   ```yaml
   # Appeler le service de rechargement pour déclencher la migration
   service: eedomus.reload
   ```

2. **Vérifier le Statut de la Migration** :
   ```bash
   # Vérifier la version de votre entrée de configuration
   grep "version" ~/.homeassistant/.storage/core.config_entries
   ```

## Dépannage

### Problèmes Courants

1. **Échec de l'Exécution de la Migration** :
   - Vérifier les logs pour les erreurs : `grep "Migration failed" home-assistant.log`
   - Assurez-vous d'être en version 0.14.2 ou ultérieure

2. **Mappages Personnalisés Perdus** :
   - Restaurer à partir de la sauvegarde : `cp custom_mapping.yaml.backup_v3 custom_mapping.yaml`
   - Redémarrer Home Assistant

3. **Entités ne se Mettant pas à Jour** :
   - Appeler le service de nettoyage : `service: eedomus.cleanup_unused_entities`
   - Recharger l'intégration : `service: eedomus.reload`

### Commandes de Vérification

```bash
# Vérifier la version actuelle de l'intégration
cat custom_components/eedomus/manifest.json | grep version

# Vérifier que la sauvegarde de migration existe
ls -la custom_components/eedomus/config/*.backup*

# Vérifier la réussite de la migration dans les logs
grep "custom_mapping.yaml preserved" home-assistant.log
```

## Bonnes Pratiques

1. **Toujours Sauvegarder** : Avant les mises à jour majeures, sauvegardez manuellement votre `custom_mapping.yaml`
2. **Vérifier les Logs** : Après les mises à jour, vérifiez que la migration s'est terminée avec succès
3. **Tester la Fonctionnalité** : Assurez-vous que tous les appareils personnalisés fonctionnent toujours comme prévu
4. **Signaler les Problèmes** : Si la migration échoue, ouvrez une issue avec les logs joints

## Détails Techniques

### Emplacement de la Fonction de Migration
- Fichier : `custom_components/eedomus/__init__.py`
- Fonction : `async_migrate_entry(hass, config_entry)`
- Déclencheur : Automatique lors du changement de version pendant la configuration

### Stratégie de Sauvegarde
- Fichier original : `custom_mapping.yaml`
- Fichier de sauvegarde : `custom_mapping.yaml.backup_v{version}`
- Méthode : Utilise `hass.async_add_executor_job()` pour les opérations de fichiers non bloquantes

### Progression des Versions
```
v1 (initiale) → v2 (options d'historique) → v3 (proxy API) → v4 (préservation des mappages personnalisés)
```

## Support

Si vous rencontrez des problèmes avec la migration :
1. Consultez le [suivi des problèmes](https://github.com/Dan4Jer/hass-eedomus/issues)
2. Examinez les problèmes existants comme #27 pour des problèmes similaires
3. Fournissez les logs lors de l'ouverture de nouvelles issues

## Journal des Changements

### Version 0.14.2
- Ajout de la version de migration 4 pour la préservation des mappages personnalisés
- Correction des avertissements d'appels bloquants dans la migration
- Ajout du service de nettoyage dans services.yaml

### Version 0.14.1
- Implémentation initiale du système de migration
- Ajout des migrations des versions 1-3
- Suivi de base des versions des entrées de configuration