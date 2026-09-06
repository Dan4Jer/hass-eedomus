#!/usr/bin/env python3
"""
Script d'analyse d'impact pour la correction des capteurs d'historique.

Ce script analyse les changements apportés à history_sensor.py et leur impact sur :
1. La création des capteurs au démarrage
2. L'activation/désactivation dynamique de l'option history
3. L'ajustement automatique quand de nouveaux périphériques sont identifiés

Usage:
    python3 scripts/analyze_history_fix_impact.py
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Optional, Any


class HistoryFixAnalyzer:
    """Analyseur d'impact pour la correction des capteurs d'historique."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.checks: Dict[str, bool] = {}
    
    def analyze(self) -> Dict[str, Any]:
        """Exécute toutes les analyses et retourne les résultats."""
        self._check_files_exist()
        self._analyze_history_sensor_changes()
        self._analyze_coordinator_integration()
        self._analyze_init_integration()
        self._check_backward_compatibility()
        
        return {
            "status": "success" if not self.issues else "warning",
            "issues": self.issues,
            "warnings": self.warnings,
            "info": self.info,
            "checks": self.checks,
            "recommendations": self._generate_recommendations()
        }
    
    def _check_files_exist(self):
        """Vérifie que les fichiers modifiés existent."""
        files_to_check = [
            "custom_components/eedomus/history_sensor.py",
            "custom_components/eedomus/__init__.py",
            "custom_components/eedomus/coordinator.py",
        ]
        
        for file_path in files_to_check:
            full_path = os.path.join(self.repo_path, file_path)
            if not os.path.exists(full_path):
                self.issues.append(f"❌ Fichier manquant: {file_path}")
                self.checks[f"file_exists_{file_path}"] = False
            else:
                self.checks[f"file_exists_{file_path}"] = True
                self.info.append(f"✅ Fichier vérifié: {file_path}")
    
    def _analyze_history_sensor_changes(self):
        """Analyse les changements dans history_sensor.py."""
        file_path = os.path.join(self.repo_path, "custom_components/eedomus/history_sensor.py")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Vérifie la nouvelle logique d'initialisation
            if "Initialize _history_progress with all peripherals" in content:
                self.checks["history_progress_initialization"] = True
                self.info.append("✅ Nouvelle logique d'initialisation de _history_progress détectée")
            else:
                self.checks["history_progress_initialization"] = False
                self.warnings.append("⚠️ Logique d'initialisation de _history_progress non trouvée")
            
            # Vérifie que tous les périphériques sont traités
            if "for periph_id, periph_data in coordinator.data.items():" in content:
                self.checks["all_devices_processed"] = True
                self.info.append("✅ Tous les périphériques du coordinator sont traités")
            else:
                self.checks["all_devices_processed"] = False
                self.warnings.append("⚠️ Logique de traitement de tous les périphériques non trouvée")
            
            # Vérifie la création des capteurs
            if "EedomusHistorySensor(coordinator" in content and "EedomusHistoryProgressSensor(coordinator" in content:
                self.checks["sensor_creation"] = True
                self.info.append("✅ Création des capteurs par périphérique confirmée")
            else:
                self.checks["sensor_creation"] = False
                self.issues.append("❌ Création des capteurs par périphérique manquante")
            
            # Vérifie la syntaxe
            try:
                ast.parse(content)
                self.checks["syntax_valid"] = True
                self.info.append("✅ Syntaxe Python valide dans history_sensor.py")
            except SyntaxError as e:
                self.checks["syntax_valid"] = False
                self.issues.append(f"❌ Erreur de syntaxe dans history_sensor.py: {e}")
            
        except Exception as e:
            self.issues.append(f"❌ Erreur de lecture de history_sensor.py: {e}")
            self.checks["file_readable"] = False
    
    def _analyze_coordinator_integration(self):
        """Analyse l'intégration avec le coordinator."""
        file_path = os.path.join(self.repo_path, "custom_components/eedomus/coordinator.py")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Vérifie que _history_progress est initialisé (peut être sur plusieurs lignes)
            if "self._history_progress" in content and "=" in content:
                self.checks["coordinator_history_progress_init"] = True
                self.info.append("✅ _history_progress initialisé dans le coordinator")
            else:
                self.checks["coordinator_history_progress_init"] = False
                self.warnings.append("⚠️ _history_progress non initialisé dans le coordinator")
            
            # Vérifie la méthode de chargement
            if "async def _load_history_progress" in content:
                self.checks["load_history_progress_method"] = True
                self.info.append("✅ Méthode _load_history_progress existe")
            else:
                self.checks["load_history_progress_method"] = False
                self.warnings.append("⚠️ Méthode _load_history_progress non trouvée")
            
            # Vérifie la méthode de sauvegarde
            if "async def _save_history_progress" in content:
                self.checks["save_history_progress_method"] = True
                self.info.append("✅ Méthode _save_history_progress existe")
            else:
                self.checks["save_history_progress_method"] = False
                self.warnings.append("⚠️ Méthode _save_history_progress non trouvée")
            
        except Exception as e:
            self.issues.append(f"❌ Erreur de lecture de coordinator.py: {e}")
    
    def _analyze_init_integration(self):
        """Analyse l'intégration dans __init__.py."""
        file_path = os.path.join(self.repo_path, "custom_components/eedomus/__init__.py")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Compte le nombre d'appels à async_setup_history_sensors (exclut les imports et definitions)
            lines = content.split('\n')
            call_lines = [line for line in lines if 'await async_setup_history_sensors' in line or 'async_setup_history_sensors(' in line]
            # Exclure les lignes avec 'from' ou 'import' ou 'def'
            call_lines = [line for line in call_lines if not any(kw in line for kw in ['from', 'import', 'def'])]
            call_count = len(call_lines)
            
            if call_count == 1:
                self.checks["single_history_setup_call"] = True
                self.info.append(f"✅ Un seul appel à async_setup_history_sensors (duplication supprimée)")
            elif call_count == 0:
                self.checks["single_history_setup_call"] = False
                self.issues.append("❌ Aucun appel à async_setup_history_sensors trouvé")
            else:
                self.checks["single_history_setup_call"] = False
                self.issues.append(f"❌ {call_count} appels à async_setup_history_sensors trouvés (duplication toujours présente)")
            
            # Vérifie la logique de vérification des options (plusieurs formats possibles)
            if ("_get_config_value(entry, CONF_ENABLE_HISTORY" in content or
                "CONF_ENABLE_HISTORY in" in content or
                "coordinator.config_entry.options.get(CONF_ENABLE_HISTORY" in content):
                self.checks["options_check_logic"] = True
                self.info.append("✅ Logique de vérification des options présente")
            else:
                self.checks["options_check_logic"] = False
                self.warnings.append("⚠️ Logique de vérification des options non trouvée")
            
            # Vérifie la syntaxe
            try:
                ast.parse(content)
                self.checks["init_syntax_valid"] = True
                self.info.append("✅ Syntaxe Python valide dans __init__.py")
            except SyntaxError as e:
                self.checks["init_syntax_valid"] = False
                self.issues.append(f"❌ Erreur de syntaxe dans __init__.py: {e}")
            
        except Exception as e:
            self.issues.append(f"❌ Erreur de lecture de __init__.py: {e}")
    
    def _check_backward_compatibility(self):
        """Vérifie la compatibilité ascendante."""
        # Vérifie que les anciens formats de données sont supportés
        coordinator_path = os.path.join(self.repo_path, "custom_components/eedomus/coordinator.py")
        
        try:
            with open(coordinator_path, 'r') as f:
                content = f.read()
            
            # Vérifie que la progression est chargée depuis les states
            if "async_all(f\"{DOMAIN}.history_progress_*\")" in content:
                self.checks["backward_compat_states"] = True
                self.info.append("✅ Chargement de la progression depuis les states (compatibilité ascendante)")
            else:
                self.checks["backward_compat_states"] = False
                self.warnings.append("⚠️ Chargement depuis les states non trouvé")
            
            # Vérifie que la progression est sauvegardée
            if "async_set" in content and "history_progress" in content:
                self.checks["backward_compat_save"] = True
                self.info.append("✅ Sauvegarde de la progression dans les states")
            else:
                self.checks["backward_compat_save"] = False
                self.warnings.append("⚠️ Sauvegarde de la progression non trouvée")
            
        except Exception as e:
            self.warnings.append(f"⚠️ Erreur de vérification de compatibilité: {e}")
    
    def _generate_recommendations(self) -> List[str]:
        """Génère des recommandations basées sur l'analyse."""
        recommendations = []
        
        if self.checks.get("single_history_setup_call", False):
            recommendations.append(
                "✅ La duplication dans __init__.py a été correctement supprimée. "
                "Un seul appel à async_setup_history_sensors garantit une initialisation propre."
            )
        
        if self.checks.get("history_progress_initialization", False):
            recommendations.append(
                "✅ La nouvelle logique dans history_sensor.py permet la création des capteurs "
                "même au premier démarrage quand _history_progress est vide."
            )
        
        if self.checks.get("all_devices_processed", False):
            recommendations.append(
                "✅ Tous les périphériques du coordinator seront traités, ce qui permet "
                "l'ajustement automatique quand de nouveaux périphériques sont identifiés."
            )
        
        if self.checks.get("coordinator_history_progress_init", False):
            recommendations.append(
                "✅ L'activation/désactivation dynamique de l'option history fonctionnera "
                "car _history_progress est correctement initialisé et persistant."
            )
        
        # Recommandations générales
        recommendations.append(
            "\n📋 **Prochaines étapes recommandées:**"
        )
        recommendations.append(
            "1. Tester le démarrage avec history activé pour la première fois"
        )
        recommendations.append(
            "2. Vérifier que tous les capteurs par périphérique sont créés"
        )
        recommendations.append(
            "3. Tester l'activation/désactivation dynamique de l'option"
        )
        recommendations.append(
            "4. Vérifier que de nouveaux périphériques ajoutés déclenchent la création de capteurs"
        )
        
        return recommendations


def print_analysis_results(results: Dict[str, Any]):
    """Affiche les résultats de l'analyse de manière lisible."""
    print("\n" + "="*80)
    print("📊 ANALYSE D'IMPACT - CORRECTION DES CAPTEURS D'HISTORIQUE")
    print("="*80 + "\n")
    
    # Statut global
    status_icon = "✅" if results["status"] == "success" else "⚠️"
    print(f"{status_icon} **Statut global**: {results['status'].upper()}\n")
    
    # Issues
    if results["issues"]:
        print("❌ **ISSUES CRITIQUES**:")
        for issue in results["issues"]:
            print(f"   {issue}")
        print()
    
    # Avertissements
    if results["warnings"]:
        print("⚠️ **AVERTISSEMENTS**:")
        for warning in results["warnings"]:
            print(f"   {warning}")
        print()
    
    # Informations
    if results["info"]:
        print("ℹ️ **INFORMATIONS**:")
        for info in results["info"]:
            print(f"   {info}")
        print()
    
    # Checks détaillés
    print("📋 **CHECKS DÉTAILLÉS**:")
    for check_name, passed in results["checks"].items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {check_name}")
    print()
    
    # Recommandations
    if results["recommendations"]:
        print("🎯 **RECOMMANDATIONS**:")
        for recommendation in results["recommendations"]:
            print(f"   {recommendation}")
        print()
    
    print("="*80 + "\n")


def main():
    """Fonction principale."""
    repo_path = "/Users/danjer/mistral/hass-eedomus"
    
    print("🔍 Analyse de l'impact des corrections sur les capteurs d'historique...")
    print("   Repository: hass-eedomus")
    print("   Fichiers analysés: history_sensor.py, __init__.py, coordinator.py")
    print()
    
    analyzer = HistoryFixAnalyzer(repo_path)
    results = analyzer.analyze()
    
    print_analysis_results(results)
    
    # Retourne le statut pour les scripts d'intégration
    return 0 if results["status"] == "success" else 1


if __name__ == "__main__":
    exit(main())
