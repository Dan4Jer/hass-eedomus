#!/usr/bin/env python3
"""Script pour analyser les capteurs d'historique eedomus avec débogage détaillé."""

import os
import json
import urllib.request
import urllib.error
import sys
from datetime import datetime

# Adresses IP possibles du Raspberry Pi
RASPBERRY_PI_IPS = ['192.168.1.4', '192.168.1.5']

def test_connection(ip):
    """Tester la connexion de base à une adresse IP."""
    try:
        test_url = f'http://{ip}:8123/'
        req = urllib.request.Request(test_url, method='GET')
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"  URL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"  Other Error: {e}")
        return False

def get_api_token(username, password, base_url):
    """Obtenir un token API depuis Home Assistant."""
    try:
        login_url = f'{base_url}/api/auth/login_flow'
        data = json.dumps({
            "type": "auth",
            "username": username,
            "password": password
        }).encode('utf-8')
        
        print(f"  Tentative de connexion à {login_url}")
        print(f"  Username: {username}")
        
        req = urllib.request.Request(
            login_url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"  Réponse: {json.dumps(data, indent=2)}")
            
            if data.get('result') == 'ok':
                token = data.get('data', {}).get('refresh_token')
                if token:
                    print(f"  ✅ Token obtenu: {token[:20]}...")
                    return token
                else:
                    print("  ❌ Aucun token dans la réponse")
            else:
                print(f"  ❌ Résultat: {data.get('result')}")
                if 'message' in data:
                    print(f"  Message: {data['message']}")
        
        return None
        
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code}: {e.reason}")
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            print(f"  Error details: {json.dumps(error_data, indent=2)}")
        except:
            pass
        return None
    except Exception as e:
        print(f"  Erreur lors de l'obtention du token: {e}")
        return None

def main():
    """Fonction principale."""
    print('🔍 ANALYSE DES CAPTEURS D\'HISTORIQUE EEDOMUS')
    print('=' * 60)
    
    # Lire les credentials
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
            print('❌ Informations de connexion incomplètes')
            return
        
        print(f'✅ Credentials lus: user={username}')
        
    except Exception as e:
        print(f'❌ Erreur lors de la lecture des credentials: {e}')
        return
    
    # Tester les différentes adresses IP
    successful_connection = False
    base_url = None
    
    for ip in RASPBERRY_PI_IPS:
        print(f'🔗 Test de connexion à {ip}...')
        
        # Tester la connexion de base
        if test_connection(ip):
            base_url = f'http://{ip}:8123'
            successful_connection = True
            print(f'✅ Connexion de base réussie à {ip}')
            break
        else:
            print(f'❌ Connexion échouée à {ip}')
    
    if not successful_connection:
        print('❌ Impossible de se connecter à aucune des adresses IP')
        print('   Vérifiez:')
        print('   - Le Raspberry Pi est allumé')
        print('   - Home Assistant est en cours d\'exécution')
        print('   - Les adresses IP sont correctes')
        print('   - Le port 8123 est ouvert')
        print('   - Essayez de vous connecter manuellement à http://192.168.1.4:8123')
        return
    
    # Obtenir le token API
    print(f'🔗 Obtention du token API sur {base_url}...')
    api_token = get_api_token(username, password, base_url)
    
    if not api_token:
        print('❌ Impossible d\'obtenir le token API')
        print()
        print('💡 Dépannage:')
        print('   1. Vérifiez que le nom d\'utilisateur et le mot de passe sont corrects')
        print('   2. Essayez de vous connecter manuellement à l\'interface web')
        print('   3. Vérifiez que l\'utilisateur a les permissions API')
        print('   4. Vérifiez que le compte n\'est pas verrouillé')
        return
    
    print('✅ Token API obtenu')
    print()
    print('📋 Prochaine étape:')
    print('   Le script peut maintenant accéder à Home Assistant')
    print('   Pour une analyse complète des capteurs d\'historique,')
    print('   exécutez le script sur le Raspberry Pi directement.')

if __name__ == '__main__':
    main()