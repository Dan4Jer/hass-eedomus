#!/usr/bin/env python3
"""Script pour analyser les issues en cours et proposer des corrections."""

import os
import re

def analyze_code_issues():
    """Analyser les issues potentielles dans le code."""
    print('🔍 ANALYSE DES ISSUES DANS LE CODE')
    print('=' * 60)
    
    issues = []
    
    # Analyser coordinator.py
    coordinator_file = 'hass-eedomus/custom_components/eedomus/coordinator.py'
    if os.path.exists(coordinator_file):
        with open(coordinator_file, 'r') as f:
            content = f.read()
        
        # Vérifier les problèmes potentiels
        
        # 1. Vérifier si la validation des données est complète
        if 'def _validate_history_data' in content:
            if 'timestamp' in content and 'value' in content:
                print('✅ Validation des données implémentée')
            else:
                issues.append('❌ Validation des données incomplète')
        else:
            issues.append('❌ Pas de validation des données')
        
        # 2. Vérifier si la queue de réessais est implémentée
        if '_retry_queue' in content and '_error_count' in content:
            print('✅ Queue de réessais implémentée')
        else:
            issues.append('❌ Queue de réessais non implémentée')
        
        # 3. Vérifier si la correction de progression est appliquée
        if 'min(100,' in content and 'global_progress' in content:
            print('✅ Correction de progression appliquée')
        else:
            issues.append('❌ Correction de progression non appliquée')
        
        # 4. Vérifier si les capteurs d'erreur sont créés
        if 'async def _create_error_sensors' in content:
            print('✅ Capteurs d\'erreur implémentés')
        else:
            issues.append('❌ Capteurs d\'erreur non implémentés')
    else:
        issues.append(f'❌ Fichier introuvable: {coordinator_file}')
    
    # Analyser options_flow.py
    options_file = 'hass-eedomus/custom_components/eedomus/options_flow.py'
    if os.path.exists(options_file):
        with open(options_file, 'r') as f:
            content = f.read()
        
        # Vérifier si l'option de configuration est présente
        if 'CONF_HISTORY_RETRY_DELAY' in content:
            print('✅ Option de configuration implémentée')
        else:
            issues.append('❌ Option de configuration non implémentée')
    else:
        issues.append(f'❌ Fichier introuvable: {options_file}')
    
    return issues

def propose_corrections():
    """Proposer des corrections pour les issues identifiées."""
    print('\n💡 CORRECTIONS PROPOSÉES')
    print('=' * 60)
    
    corrections = []
    
    # 1. Correction pour la validation des données
    corrections.append({
        'issue': 'Validation des données incomplète',
        'correction': """Ajouter une validation complète dans _validate_history_data():

    def _validate_history_data(self, chunk: list) -> bool:
        \"\"\"Valider les données historiques reçues.\"\"\"
        if not isinstance(chunk, list):
            return False

        for entry in chunk:
            if not isinstance(entry, dict):
                return False
            if "timestamp" not in entry or "value" not in entry:
                return False
            # Vérifier que le timestamp est valide
            try:
                datetime.fromisoformat(entry["timestamp"])
            except ValueError:
                return False
            # Vérifier que la valeur est valide
            try:
                float(entry["value"])
            except ValueError:
                return False

        return True
""",
        'fichier': 'coordinator.py'
    })
    
    # 2. Correction pour la queue de réessais
    corrections.append({
        'issue': 'Queue de réessais non implémentée',
        'correction': """Ajouter la gestion des erreurs et la queue de réessais:

    def _handle_fetch_error(self, periph_id, error_message):
        \"\"\"Gérer les erreurs de récupération d'historique.\"\"\"
        now = datetime.now().timestamp()

        # Initialiser si première erreur
        if periph_id not in self._error_count:
            self._error_count[periph_id] = 0

        self._error_count[periph_id] += 1

        # Si première erreur, mettre en pause pour la durée configurée
        if self._error_count[periph_id] == 1:
            retry_delay_hours = self.config_entry.options.get(
                CONF_HISTORY_RETRY_DELAY,
                DEFAULT_HISTORY_RETRY_DELAY
            )
            retry_delay = retry_delay_hours * 3600
            retry_after = now + retry_delay
            self._retry_queue[periph_id] = {
                "error_time": now,
                "retry_after": retry_after,
                "error_message": error_message,
                "attempts": 1
            }
            _LOGGER.error(f"❌ Erreur lors de la récupération de l'historique pour {periph_id}: {error_message}")
            _LOGGER.error(f"   Réessai dans {retry_delay_hours} heures")
        else:
            # Mettre à jour le compteur d'erreurs
            if periph_id in self._retry_queue:
                self._retry_queue[periph_id]["attempts"] += 1
""",
        'fichier': 'coordinator.py'
    })
    
    # 3. Correction pour la progression
    corrections.append({
        'issue': 'Correction de progression non appliquée',
        'correction': """Corriger le calcul de progression globale:

            # Corriger le calcul pour éviter de dépasser 100%
            if total_estimated > 0:
                global_progress = min(100, (total_retrieved / total_estimated) * 100)
            else:
                global_progress = 0
""",
        'fichier': 'coordinator.py'
    })
    
    # 4. Correction pour les capteurs d'erreur
    corrections.append({
        'issue': 'Capteurs d\'erreur non implémentés',
        'correction': """Ajouter la création des capteurs d'erreur:

    async def _create_error_sensors(self):
        \"\"\"Créer des capteurs pour visualiser les erreurs et la queue de réessais.\"\"\"
        if not self.hass:
            return
        
        try:
            # Capteur pour le nombre total de périphériques en erreur
            self.hass.states.async_set(
                "sensor.eedomus_history_errors_total",
                str(len(self._retry_queue)),
                {
                    "device_class": "problem",
                    "state_class": "measurement",
                    "unit_of_measurement": "devices",
                    "friendly_name": "Eedomus History Errors Total",
                    "icon": "mdi:alert-circle",
                    "last_updated": datetime.now().isoformat(),
                },
            )

            # Capteur pour chaque périphérique en erreur
            for periph_id, error_info in self._retry_queue.items():
                periph_name = self.data.get(periph_id, {}).get("name", "Unknown")
                retry_in_hours = max(0, (error_info["retry_after"] - datetime.now().timestamp()) / 3600)

                self.hass.states.async_set(
                    f"sensor.eedomus_history_error_{periph_id}",
                    str(retry_in_hours),
                    {
                        "device_class": "duration",
                        "state_class": "measurement",
                        "unit_of_measurement": "hours",
                        "friendly_name": f"History Error: {periph_name}",
                        "icon": "mdi:clock-alert",
                        "periph_id": periph_id,
                        "periph_name": periph_name,
                        "error_message": error_info["error_message"],
                        "attempts": error_info["attempts"],
                        "last_updated": datetime.now().isoformat(),
                    },
                )

        except Exception as e:
            _LOGGER.error("Error creating error sensors: %s", e)
""",
        'fichier': 'coordinator.py'
    })
    
    # 5. Correction pour l'option de configuration
    corrections.append({
        'issue': 'Option de configuration non implémentée',
        'correction': """Ajouter l'option de configuration dans const.py:

CONF_HISTORY_RETRY_DELAY = "history_retry_delay"
DEFAULT_HISTORY_RETRY_DELAY = 24  # 24 heures par défaut

Et dans options_flow.py:

vol.Optional(CONF_HISTORY_RETRY_DELAY, default=DEFAULT_HISTORY_RETRY_DELAY): int,
""",
        'fichier': 'const.py et options_flow.py'
    })
    
    return corrections

def main():
    """Fonction principale."""
    print('🔍 ANALYSE DES ISSUES ET CORRECTIONS PROPOSÉES')
    print('=' * 60)
    
    # Analyser les issues
    issues = analyze_code_issues()
    
    if issues:
        print('\n❌ Issues identifiées:')
        for issue in issues:
            print(f'   - {issue}')
    else:
        print('\n✅ Aucun problème critique identifié')
    
    # Proposer des corrections
    corrections = propose_corrections()
    
    print('\n📋 Corrections proposées:')
    print('=' * 40)
    
    for i, correction in enumerate(corrections, 1):
        print(f'\n{i}. {correction["issue"]}')
        print(f'   Fichier: {correction["fichier"]}')
        print('   Correction:')
        print(correction["correction"])
    
    print('\n📝 Documentation:')
    print('=' * 40)
    print('Pour plus d\'informations, consultez:')
    print('   - HISTORY_FEATURE_STATUS.md')
    print('   - ENABLE_HISTORY_FEATURE.md')
    print('   - DEPLOYMENT_GUIDE.md')

if __name__ == '__main__':
    main()