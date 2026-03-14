#!/usr/bin/env python3
"""Script to check eedomus history sensors using credentials from credentials-ha."""

import os
import json
import requests
import sys

def get_api_token(username, password):
    """Get Home Assistant API token using username and password."""
    try:
        # First, get the login flow
        login_flow_url = 'http://localhost:8123/api/auth/login_flow'
        
        response = requests.post(login_flow_url, json={
            "type": "auth",
            "username": username,
            "password": password
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('result') == 'ok':
                return data.get('data', {}).get('refresh_token')
        
        print(f"❌ Erreur lors de l'obtention du token: {response.status_code}")
        print(f"Réponse: {response.text}")
        return None
        
    except Exception as e:
        print(f"❌ Erreur lors de l'obtention du token: {e}")
        return None

def check_history_sensors(api_token):
    """Check eedomus history sensors using API token."""
    try:
        # Get all states
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get('http://localhost:8123/api/states', headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Erreur lors de la récupération des états: {response.status_code}")
            print(f"Réponse: {response.text}")
            return None
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification des capteurs: {e}")
        return None

def main():
    """Main function."""
    print('🔍 Vérification des capteurs eedomus dans Home Assistant')
    print('=' * 60)
    
    # Read credentials from credentials-ha
    credentials_file = '/Users/danjer/mistral/credentials-ha/credentials.txt'
    
    if not os.path.exists(credentials_file):
        print(f'❌ Fichier de credentials introuvable: {credentials_file}')
        return
    
    try:
        with open(credentials_file, 'r') as f:
            lines = f.readlines()
            
        username = None
        password = None
        
        for line in lines:
            if line.startswith('user:'):
                username = line.split(':', 1)[1].strip()
            elif line.startswith('password:'):
                password = line.split(':', 1)[1].strip()
        
        if not username or not password:
            print('❌ Informations de connexion incomplètes dans credentials.txt')
            return
        
        print(f'✅ Informations de connexion lues: user={username}')
        
    except Exception as e:
        print(f'❌ Erreur lors de la lecture des credentials: {e}')
        return
    
    # Get API token
    print('🔗 Obtention du token API...')
    api_token = get_api_token(username, password)
    
    if not api_token:
        print('❌ Impossible d\'obtenir le token API')
        print('   Vérifiez:')
        print('   - Home Assistant est en cours d\'exécution')
        print('   - Les informations de connexion sont correctes')
        print('   - Le port 8123 est accessible')
        return
    
    print('✅ Token API obtenu')
    print()
    
    # Check history sensors
    print('📊 Vérification des capteurs d\'historique...')
    states = check_history_sensors(api_token)
    
    if not states:
        print('❌ Impossible de récupérer les états')
        return
    
    # Filter eedomus sensors
    eedomus_sensors = [s for s in states if 'eedomus' in s.get('entity_id', '')]
    
    if not eedomus_sensors:
        print('❌ Aucun capteur eedomus trouvé')
        print('   Vérifiez que l\'intégration eedomus est bien installée')
        return
    
    print(f'✅ Trouvé {len(eedomus_sensors)} capteurs eedomus')
    print()
    
    # Filter history sensors
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
        print()
        print('📋 Comportement attendu:')
        print('   - sensor.eedomus_history_progress: Progression globale (0-100%)')
        print('   - sensor.eedomus_history_progress_{device_id}: Progression par appareil')
        print('   - sensor.eedomus_history_stats: Statistiques de téléchargement')
        print()
        print('💡 Pour vérifier manuellement:')
        print('   1. Allez dans Developer Tools → States')
        print('   2. Cherchez les entités eedomus_history')
        print('   3. Vérifiez que les valeurs changent à chaque rafraîchissement')
        
    else:
        print('❌ Aucun capteur d\'historique trouvé')
        print('   Cela peut signifier:')
        print('   - L\'option history n\'est pas activée')
        print('   - Les capteurs virtuels n\'ont pas été créés')
        print('   - L\'intégration n\'a pas encore démarré')
        print()
        print('💡 Pour activer l\'historique:')
        print('   1. Allez dans Settings → Devices & Services')
        print('   2. Sélectionnez votre intégration eedomus')
        print('   3. Cliquez sur Configure/Options')
        print('   4. Activez l\'option "Enable History"')
        print('   5. Redémarrez Home Assistant')
        print()
        print('   Ou utilisez le script:')
        print('   ./activate_history_feature.sh')
    
    # Show all eedomus sensors for reference
    print()
    print('📋 Tous les capteurs eedomus (premiers 10):')
    print('-' * 40)
    for sensor in eedomus_sensors[:10]:
        print(f'{sensor.get("entity_id", "Unknown")}: {sensor.get("state", "Unknown")}')
    if len(eedomus_sensors) > 10:
        print(f'... et {len(eedomus_sensors) - 10} autres capteurs')

if __name__ == '__main__':
    main()