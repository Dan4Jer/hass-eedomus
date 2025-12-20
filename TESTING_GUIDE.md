# 🧪 Guide de Test pour les Modes de Connexion Duales

Ce guide vous aidera à tester les nouvelles fonctionnalités des modes de connexion duales de l'intégration eedomus.

## 📋 Prérequis

- Home Assistant installé et fonctionnel
- Intégration eedomus installée (version avec les modes duales)
- Accès à votre box Eedomus
- Identifiants API Eedomus (pour tester le mode API Eedomus)

## ⚠️ Avertissements de Sécurité Importants

### Communications Non Chiffrées

⚠️ **CRITIQUE**: La box Eedomus **ne supporte pas HTTPS** pour les communications locales. Cela signifie:

- Toutes les communications entre Eedomus et Home Assistant se font en **HTTP (non chiffré)**
- Les webhooks et requêtes API sont envoyés en **texte clair** sur votre réseau
- Les identifiants et données sont **visibles** sur votre réseau local

### Recommandations de Test

1. **Testez uniquement sur un réseau local sécurisé**
2. **Ne testez pas sur des réseaux publics** (cafés, hôtels, etc.)
3. **Désactivez temporairement les autres appareils** sur votre réseau pendant les tests
4. **Utilisez un réseau dédié** pour les tests de sécurité si possible
5. **Ne jamais exposer** votre environnement de test sur Internet

### Configuration de Production

Pour une utilisation en production:
- **Isolez** votre box Eedomus et Home Assistant sur un VLAN dédié
- **Utilisez un VPN** pour l'accès distant (WireGuard, OpenVPN)
- **Activez les pare-feux** pour limiter l'accès
- **Gardez la validation IP activée** (ne désactivez jamais en production)
- **Surveillez les logs** régulièrement pour détecter les activités suspectes

## 🔧 Scénarios de Test

### Test 1: Mode API Eedomus uniquement

**Objectif**: Vérifier que le mode API Eedomus fonctionne correctement.

**Étapes**:
1. Accédez à l'intégration eedomus via l'UI Home Assistant
2. Configurez avec:
   - Mode API Eedomus: ✅ Activé
   - Mode API Proxy: ❌ Désactivé
   - Hôte API: [votre_hôte_eedomus]
   - Utilisateur API: [votre_utilisateur]
   - Clé secrète API: [votre_clé]
   - Activer l'historique: ✅ Activé
   - Intervalle de scan: 300 (5 minutes)

**Vérifications**:
- ✅ L'intégration devrait se configurer sans erreur
- ✅ Les entités devraient apparaître dans Home Assistant
- ✅ Les données devraient se rafraîchir toutes les 5 minutes
- ✅ L'historique devrait être disponible
- ✅ Les logs devraient montrer: "API Eedomus mode initialized successfully"

**Logs attendus**:
```
INFO: Starting eedomus integration - API Eedomus: True, API Proxy: False
INFO: API Eedomus mode initialized successfully
```

### Test 2: Mode API Proxy uniquement

**Objectif**: Vérifier que le mode API Proxy fonctionne correctement.

**Étapes**:
1. Accédez à l'intégration eedomus via l'UI Home Assistant
2. Configurez avec:
   - Mode API Eedomus: ❌ Désactivé
   - Mode API Proxy: ✅ Activé
   - Hôte API: [votre_hôte_eedomus]
   - Utilisateur API: (laisser vide)
   - Clé secrète API: (laisser vide)
   - Activer l'historique: ❌ Désactivé (devrait être désactivé automatiquement)

**Vérifications**:
- ✅ L'intégration devrait se configurer sans erreur
- ✅ Les webhooks devraient être enregistrés
- ✅ Les mises à jour devraient arriver en temps réel via webhooks
- ✅ Les logs devraient montrer: "API Proxy mode enabled - setting up webhook endpoints"

**Logs attendus**:
```
INFO: Starting eedomus integration - API Eedomus: False, API Proxy: True
INFO: API Proxy mode enabled - setting up webhook endpoints
INFO: Proxy mode client created successfully
```

### Test 3: Mode Combiné (API Eedomus + API Proxy)

**Objectif**: Vérifier que les deux modes fonctionnent ensemble.

**Étapes**:
1. Accédez à l'intégration eedomus via l'UI Home Assistant
2. Configurez avec:
   - Mode API Eedomus: ✅ Activé
   - Mode API Proxy: ✅ Activé
   - Hôte API: [votre_hôte_eedomus]
   - Utilisateur API: [votre_utilisateur]
   - Clé secrète API: [votre_clé]
   - Activer l'historique: ✅ Activé
   - Intervalle de scan: 600 (10 minutes)

**Vérifications**:
- ✅ L'intégration devrait se configurer sans erreur
- ✅ Les deux modes devraient être actifs
- ✅ Les données devraient se rafraîchir toutes les 10 minutes (API Eedomus)
- ✅ Les mises à jour devraient aussi arriver en temps réel (API Proxy)
- ✅ Les logs devraient montrer les deux modes actifs

**Logs attendus**:
```
INFO: Starting eedomus integration - API Eedomus: True, API Proxy: True
INFO: API Eedomus mode initialized successfully
INFO: API Proxy mode enabled - setting up webhook endpoints
```

### Test 4: Validation des Erreurs

**Objectif**: Vérifier que la validation des erreurs fonctionne correctement.

**Test 4a: Aucun mode activé**
1. Essayez de configurer avec les deux modes désactivés
2. **Résultat attendu**: Erreur "At least one connection mode must be enabled"

**Test 4b: API Eedomus sans identifiants**
1. Activez le mode API Eedomus mais laissez les champs identifiants vides
2. **Résultat attendu**: Erreur "API user is required when API Eedomus mode is enabled"

**Test 4c: Historique sans API Eedomus**
1. Désactivez le mode API Eedomus mais activez l'historique
2. **Résultat attendu**: Erreur "History can only be enabled with API Eedomus mode"

**Test 4d: Intervalle de scan trop court**
1. Configurez un intervalle de scan < 30 secondes
2. **Résultat attendu**: Erreur "Scan interval must be at least 30 seconds"

### Test 5: Sécurité des Webhooks

**Objectif**: Vérifier que la sécurité des webhooks fonctionne correctement.

**Test 5a: Validation IP par défaut**
1. Activez le mode API Proxy avec la sécurité activée (par défaut)
2. Essayez d'envoyer une requête webhook depuis une IP non autorisée
3. **Résultat attendu**: Réponse 403 Unauthorized
4. **Logs attendus**: "Unauthorized IP: [IP_NON_AUTORISÉE]"

**Test 5b: Désactivation de la sécurité (debug)**
1. Activez le mode API Proxy et l'option "Désactiver la validation IP du proxy"
2. **Résultat attendu**: Avertissements de sécurité dans les logs
3. **Logs attendus**:
   ```
   WARNING: ⚠️ SECURITY WARNING: API Proxy IP validation has been disabled for debugging purposes.
   WARNING:   This exposes your webhook endpoints to potential abuse from any IP address.
   ```
4. Essayez d'envoyer une requête webhook depuis une IP non autorisée
5. **Résultat attendu**: Requête acceptée (mais avec avertissement de sécurité)
6. **Logs attendus**: "SECURITY WARNING: IP validation disabled for debugging. Request from [IP_NON_AUTORISÉE]"

**Test 5c: Réactivation de la sécurité**
1. Désactivez l'option "Désactiver la validation IP du proxy"
2. **Résultat attendu**: Plus d'avertissements de sécurité
3. Essayez à nouveau d'envoyer une requête depuis une IP non autorisée
4. **Résultat attendu**: Réponse 403 Unauthorized (comportement normal restauré)

## 🔍 Vérifications Techniques

### Vérification des Entités

```bash
# Vérifiez que les entités sont créées correctement
hass --state

# Filtrez pour les entités eedomus
hass --state | grep eedomus
```

### Vérification des Logs

```bash
# Affichez les logs de l'intégration eedomus
tail -f /config/home-assistant.log | grep eedomus

# Filtrez pour les erreurs
tail -f /config/home-assistant.log | grep -i error | grep eedomus
```

### Vérification des Webhooks (Mode Proxy)

```bash
# Vérifiez que les endpoints webhook sont enregistrés
curl -X GET "http://localhost:8123/api/webhook/eedomus_[votre_entry_id]"

# Testez un webhook manuel (remplacez les données)
curl -X POST "http://localhost:8123/api/webhook/eedomus_[votre_entry_id]" \
  -H "Content-Type: application/json" \
  -d '{"periph_id": "123", "value": "ON"}'
```

## 📊 Métriques de Performance

### Mode API Eedomus

- **Consommation CPU**: Moyenne (rafraîchissements périodiques)
- **Bande passante**: Moyenne (requêtes API régulières)
- **Latence**: 30 secondes à X minutes (selon l'intervalle de scan)
- **Fiabilité**: Élevée (connexion directe)

### Mode API Proxy

- **Consommation CPU**: Faible (webhooks passifs)
- **Bande passante**: Faible (uniquement les mises à jour)
- **Latence**: Temps réel (dès que l'événement se produit)
- **Fiabilité**: Moyenne (dépend des webhooks)

### Mode Combiné

- **Consommation CPU**: Moyenne à élevée
- **Bande passante**: Moyenne
- **Latence**: Temps réel (webhooks) + périodique (API)
- **Fiabilité**: Très élevée (redondance)

## 🎯 Checklist de Validation

- [ ] Mode API Eedomus fonctionne seul
- [ ] Mode API Proxy fonctionne seul
- [ ] Mode combiné fonctionne
- [ ] Validation des erreurs fonctionne correctement
- [ ] Les entités sont créées correctement
- [ ] Les données sont mises à jour correctement
- [ ] Les logs sont clairs et informatifs
- [ ] La documentation est à jour
- [ ] La compatibilité ascendante est maintenue
- [ ] La sécurité des webhooks fonctionne correctement (validation IP)
- [ ] L'option de désactivation de la sécurité fonctionne (avec avertissements)
- [ ] Les avertissements de sécurité sont clairs et visibles

## 🐛 Rapport de Bugs

Si vous rencontrez des problèmes, veuillez fournir:

1. **Version de Home Assistant**
2. **Version de l'intégration eedomus**
3. **Configuration utilisée** (mode(s) activé(s))
4. **Logs pertinents**
5. **Étapes pour reproduire**
6. **Comportement attendu vs. comportement réel**

## 🚀 Recommandations pour les Tests

1. **Commencez par tester chaque mode séparément** avant de tester le mode combiné
2. **Surveillez les logs** pour détecter les problèmes rapidement
3. **Testez avec différents intervalles de scan** pour voir l'impact sur les performances
4. **Testez la résilience** en simulant des échecs de connexion
5. **Vérifiez la compatibilité** avec vos périphériques eedomus existants

## 📝 Notes de Version

**Version**: 0.9.0 (Dual API Modes with Security Options)
**Date**: [Date du test]
**Testeur**: [Votre nom]
**Résultats**: [Succès/Échec/Partiel]
**Commentaires**: [Notes supplémentaires]

### Nouveautés dans cette version:
- ✅ Deux modes de connexion indépendants (API Eedomus + API Proxy)
- ✅ Validation IP stricte par défaut pour la sécurité
- ✅ Option de désactivation de la sécurité pour le débogage (avec avertissements)
- ✅ Documentation complète et guide de test
- ✅ Avertissements de sécurité clairs dans les logs
- ✅ Compatibilité ascendante maintenue

---

*Ce guide de test fait partie de l'intégration eedomus pour Home Assistant.*
*© 2023 - Communauté eedomus/Home Assistant*