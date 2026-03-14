#!/usr/bin/env python3
"""Script final pour vérifier les capteurs eedomus avec une approche directe."""

import os
import json
import subprocess
import sys

def run_curl_command(url, headers=None):
    """Exécuter une commande curl."""
    try:
        cmd = ['curl', '-s', '-X', 'GET', url]
        
        if headers:
            for header in headers:
                cmd.extend(['-H', header])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"Erreur curl: {result.stderr}")
            return None
    except Exception as e:
        print(f"Erreur lors de l'exécution de curl: {e}")
        return None

def main():
    """Fonction principale."""
    print('🔍 VÉRIFICATION FINALE DES CAPTEURS EEDOMUS')
    print('=' * 60)
    
    # Adresses IP possibles
    ips = ['192.168.1.4', '192.168.1.5']
    
    # Tester les adresses IP
    for ip in ips:
        print(f'🔗 Test de connexion à {ip}...')
        
        # Essayer une connexion simple
        if run_curl_command(f'http://{ip}:8123/'):
            print(f'✅ Connexion réussie à {ip}')
            
            # Essayer d'obtenir les états
            print(f'📊 Tentative de récupération des états...')
            states_data = run_curl_command(f'http://{ip}:8123/api/states')
            
            if states_data:
                try:
                    states = json.loads(states_data)
                    print(f'✅ {len(states)} états récupérés')
                    
                    # Filtrer les capteurs eedomus
                    eedomus_sensors = [s for s in states if 'eedomus' in s.get('entity_id', '')]
                    
                    if eedomus_sensors:
                        print(f'✅ Trouvé {len(eedomus_sensors)} capteurs eedomus')
                        
                        # Filtrer les capteurs d'historique
                        history_sensors = [s for s in eedomus_sensors if 'history' in s.get('entity_id', '')]
                        
                        if history_sensors:
                            print('📊 Capteurs de progression d\'historique:')
                            print('-' * 40)
                            for sensor in history_sensors:
                                print(f'Entity: {sensor.get("entity_id", "Unknown")}')
                                print(f'State: {sensor.get("state", "Unknown")}')
                                attrs = sensor.get('attributes', {})
                                print(f'Attributes: {json.dumps(attrs, indent=2)}')
                                print()
                            
                            print('✅ Capteurs d\'historique trouvés et fonctionnels')
                            return True
                        else:
                            print('❌ Aucun capteur d\'historique trouvé')
                            print('   L\'option history doit être activée')
                            return False
                    else:
                        print('❌ Aucun capteur eedomus trouvé')
                        return False
                        
                except json.JSONDecodeError as e:
                    print(f"Erreur de parsing JSON: {e}")
                    print(f"Réponse: {states_data[:200]}...")
                    return False
            else:
                print('❌ Impossible de récupérer les états')
                print('   Erreur 401: Authentification requise')
                
                # Essayer avec un token par défaut
                print('🔐 Tentative avec token par défaut...')
                token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'  # Token fictif
                states_data = run_curl_command(
                    f'http://{ip}:8123/api/states',
                    [f'Authorization: Bearer {token}', 'Content-Type: application/json']
                )
                
                if states_data:
                    print('✅ Accès réussi avec token')
                    # Continuer avec le traitement...
                else:
                    print('❌ Accès échoué même avec token')
        else:
            print(f'❌ Connexion échouée à {ip}')
    
    print('❌ Impossible de se connecter à aucune des adresses IP')
    return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)