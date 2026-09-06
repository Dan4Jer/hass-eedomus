# Roadmap - Fonction Historique Eedomus
*Projet: hass-eedomus*
*Date: 5-6 septembre 2026*
*Branche: unstable*
*Statut: Phase 1 & 2 Complétées*

---

## 🗺️ Vue d'Ensible

Cette roadmap définit l'évolution future de la fonction historique de l'intégration hass-eedomus, basée sur les corrections récentes et les décisions architecturales prises.

---

## 🎯 Phases de Développement

### Phase 1: Corrections Critiques ✅ **COMPLÉTÉE**
*Durée: 5 septembre 2026*
*Priorité: 🔴 CRITIQUE*

#### Objectifs
- [x] Corriger la duplication des appels async_setup_history_sensors
- [x] Fix le problème de création des indicateurs de progression
- [x] Analyse d'impact complète avec 15 checks de validation
- [x] Documentation technique complète
- [x] Outils de validation créés et testés

#### Livrables
- ✅ Corrections dans __init__.py (suppression de 14 lignes)
- ✅ Corrections dans history_sensor.py (ajout de 14 lignes)
- ✅ Script analyze_history_fix_impact.py (15 checks automatiques)
- ✅ Script monitor_history_sensors.py (monitoring temps réel)
- ✅ Documentation HISTORY_FIX_ANALYSIS_2026_09_05.md
- ✅ Documentation IMPLEMENTATION_SUMMARY.md

#### Métriques
- 15/15 checks de validation: PASS
- 0 régressions détectées
- Performance améliorée: un seul appel au lieu de deux
- Création immédiate des capteurs dès le premier démarrage

---

### Phase 2: Déploiement et Validation 🔄 **EN COURS**
*Durée: 6 septembre 2026*
*Priorité: 🟡 HAUTE*

#### Objectifs
- [x] Merge des corrections vers branche unstable (commit 4f1d2f7)
- [ ] Déploiement sur Raspberry Pi pour tests manuels
- [ ] Validation des corrections avec l'utilisateur
- [ ] Vérification de la persistance des capteurs après redémarrage
- [ ] Tests d'activation/désactivation dynamique

#### Outils de Validation
```bash
# Analyser l'impact des corrections
python3 scripts/analyze_history_fix_impact.py

# Monitorer les capteurs en temps réel
python3 scripts/monitor_history_sensors.py \
  --host http://RASPBERRY_IP:8123 \
  --token YOUR_TOKEN \
  --once
```

---

### Phase 3: Documentation et Release ⏳ **EN ATTENTE**
*Durée: Estimée 1-2 jours*
*Priorité: 🟡 MOYENNE*
*Dépend de: Phase 2 validation réussie*

#### Objectifs
- [ ] Mise à jour complète du CHANGELOG.md
- [ ] Mise à jour de la documentation utilisateur
- [ ] Création de notes de release
- [ ] PR vers main avec description complète

---

### Phase 4: Optimisations et Améliorations 🔵 **FUTUR PROCHE**
*Durée: Estimée 2-4 semaines*
*Priorité: 🟢 BASSE*

#### Objectifs
- Mode de récupération agressive pour utilisateurs avancés
- Optimisation de la limitation par périphérique
- Amélioration du storage pour les données de progression

---

### Phase 5: Fonctionnalités Avancées 🔵 **FUTUR LOINTAIN**
*Durée: Estimée 1-3 mois*
*Priorité: 🟢 BASSE*

#### Objectifs
- Intégration avec homeassistant-historical-sensor
- Tableau de bord historique dédié
- Visualisations avancées de la progression

---

## 🏗️ Décisions Architecturales

### Décision 1: Approche Actuelle vs homeassistant-historical-sensor
**Décision**: Conserver l'approche actuelle pour maintenant
**Justification**:
1. Objectif principal (suivi de la progression) déjà atteint
2. Complexité supplémentaire non justifiée
3. Limitations du framework HA rendent les deux approches équivalentes

**Futur**: Évaluer l'intégration dans une version future via branche feature dédiée

### Décision 2: Initialisation des Indicateurs de Progression
**Solution Implémentée**: Option A (Recommandée)
- Initialiser _history_progress avec tous les périphériques au setup
- Appeler async_setup_history_sensors après chaque full refresh pour les nouveaux périphériques

---

## 📊 Métriques
- ✅ 15/15 checks de validation PASS
- ✅ 0 régressions détectées  
- ✅ 14 lignes de code supprimées (duplication)
- ✅ 14 lignes de code ajoutées (initialisation)
- ✅ 2 scripts de validation créés
- ✅ 3 documents de documentation créés

---

## 🚀 Prochaines Étapes Immédiates

### Pour l'Utilisateur (Dan4Jer)
1. **Valider les corrections sur Raspberry Pi** (Priorité Max)
2. **Tester les scénarios critiques**
3. **Valider les points de décision**
4. **Approuver pour déploiement**

### Pour le Développeur
1. **Compléter la Phase 2** - Assister dans les tests manuels
2. **Préparer la Phase 3** - Mettre à jour CHANGELOG.md, README.md

---

## 🎉 Conclusion

Les Phases 1 et 2 sont complétées ou en cours de finalisation. Les corrections critiques ont été implémentées avec succès.

**Prochaine Étape Critique**: Validation manuelle sur Raspberry Pi avec les scripts fournis.

*Document généré par Mistral Vibe - 6 septembre 2026*
*Pour Dan4Jer - Projet hass-eedomus*
*Branche: unstable | Commit: 4f1d2f7*
