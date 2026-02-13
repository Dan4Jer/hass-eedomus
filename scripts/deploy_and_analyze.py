#!/usr/bin/env python3
"""Script de déploiement et analyse des erreurs sur le Raspberry Pi."""

import os
import subprocess
import sys
import json
import time
from datetime import datetime

# Configuration
RASPBERRY_PI_IPS = ['192.168.1.4', '192.168.1.5']
RASPBERRY_PI_USER = 'pi'
LOCAL_DIR = '/Users/danjer/mistral/hass-eedomus'
REMOTE_DIR = '/home/pi/hass-eedomus'
LOG_FILE = '/tmp/deployment_log.txt'

class DeploymentError(Exception):
    """Exception pour les erreurs de déploiement."""
    pass

def run_command(cmd, description="Command"):
    """Exécuter une commande et retourner le résultat."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ {description} réussie")
            return True, result.stdout
        else:
            print(f"❌ {description} échouée")
            print(f"   Erreur: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timeout")
        return False, "Timeout expired"
    except Exception as e:
        print(f"❌ {description} erreur: {e}")
        return False, str(e)

def deploy_files(ip):
    """Déployer les fichiers sur le Raspberry Pi."""
    print(f'\n📤 DÉPLOIEMENT DES FICHIERS SUR {ip}')
    print('=' * 60)
    
    # Créer le répertoire distant si nécessaire
    cmd = f'ssh {RASPBERRY_PI_USER}@{ip} "mkdir -p {REMOTE_DIR}"'
    success, output = run_command(cmd, "Création du répertoire distant")
    if not success:
        return False
    
    # Copier les fichiers modifiés
    files_to_copy = [
        'custom_components/eedomus/const.py',
        'custom_components/eedomus/coordinator.py',
        'custom_components/eedomus/options_flow.py',
    ]
    
    for file_path in files_to_copy:
        local_path = os.path.join(LOCAL_DIR, file_path)
        remote_path = os.path.join(REMOTE_DIR, file_path)
        
        if not os.path.exists(local_path):
            print(f'❌ Fichier introuvable: {local_path}')
            continue
        
        cmd = f'scp {local_path} {RASPBERRY_PI_USER}@{ip}:{remote_path}'
        success, output = run_command(cmd, f"Copie de {file_path}")
        if not success:
            return False
    
    # Copier les scripts
    scripts_to_copy = [
        'scripts/check_history_final.sh',
        'scripts/check_with_token.py',
    ]
    
    for script in scripts_to_copy:
        local_path = os.path.join(LOCAL_DIR, script)
        remote_path = os.path.join(REMOTE_DIR, script)
        
        if not os.path.exists(local_path):
            print(f'❌ Script introuvable: {local_path}')
            continue
        
        cmd = f'scp {local_path} {RASPBERRY_PI_USER}@{ip}:{remote_path}'
        success, output = run_command(cmd, f"Copie de {script}")
        if not success:
            return False
    
    # Rendre les scripts exécutables
    cmd = f'ssh {RASPBERRY_PI_USER}@{ip} "chmod +x {REMOTE_DIR}/scripts/*.sh {REMOTE_DIR}/scripts/*.py"'
    success, output = run_command(cmd, "Rendre les scripts exécutables")
    if not success:
        return False
    
    return True

def restart_home_assistant(ip):
    """Redémarrer Home Assistant."""
    print(f'\n🔄 REDÉMARRAGE DE HOME ASSISTANT SUR {ip}')
    print('=' * 60)
    
    # Vérifier si Home Assistant est en cours d'exécution
    cmd = f'ssh {RASPBERRY_PI_USER}@{ip} "systemctl is-active home-assistant@pi.service"'
    success, output = run_command(cmd, "Vérification de l'état de Home Assistant")
    
    if success and output.strip() == 'active':
        print("✅ Home Assistant est en cours d'exécution")
        
        # Redémarrer Home Assistant
        cmd = f'ssh {RASPBERRY_PI_USER}@{ip} "sudo systemctl restart home-assistant@pi.service"'
        success, output = run_command(cmd, "Redémarrage de Home Assistant")
        if not success:
            return False
        
        # Attendre que Home Assistant redémarre
        print("⏳ Attente du redémarrage de Home Assistant...")
        for i in range(30):
            cmd = f'ssh {RASPBERRY_PI_USER}@{ip} "systemctl is-active home-assistant@pi.service"'
            success, output = run_command(cmd, f"Vérification {i+1}/30")
            if success and output.strip() == 'active':
                print("✅ Home Assistant a redémarré")
                return True
            time.sleep(10)
        
        print("❌ Timeout: Home Assistant n'a pas redémarré")
        return False
    else:
        print("❌ Home Assistant n'est pas en cours d'exécution")
        return False

def analyze_logs(ip):
    """Analyser les logs pour identifier les erreurs."""
    print(f'\n📋 ANALYSE DES LOGS SUR {ip}')
    print('=' * 60)
    
    # Récupérer les logs récents
    cmd = f'ssh {RASPBERRY_PI_USER}@{ip} "tail -n 100 /config/rasp.log | grep -i \"eedomus\|history\|error\""'
    success, output = run_command(cmd, "Récupération des logs")
    
    if success and output:
        print("📝 Logs récents:")
        print('-' * 40)
        print(output)
        
        # Analyser les erreurs
        errors = []
        warnings = []
        
        for line in output.split('\n'):
            if 'ERROR' in line and 'eedomus' in line.lower():
                errors.append(line)
            elif 'WARNING' in line and 'eedomus' in line.lower():
                warnings.append(line)
        
        if errors:
            print(f"\n❌ {len(errors)} erreurs trouvées:")
            for i, error in enumerate(errors, 1):
                print(f"   {i}. {error}")
        
        if warnings:
            print(f"\n⚠️  {len(warnings)} avertissements trouvés:")
            for i, warning in enumerate(warnings, 1):
                print(f"   {i}. {warning}")
        
        if not errors and not warnings:
            print("\n✅ Aucun problème critique trouvé dans les logs")
    else:
        print("❌ Impossible de récupérer les logs")
    
    return True

def check_sensors(ip):
    """Vérifier les capteurs eedomus."""
    print(f'\n🔍 VÉRIFICATION DES CAPTEURS SUR {ip}')
    print('=' * 60)
    
    # Utiliser le script check_with_token.py
    cmd = f'ssh {RASPBERRY_PI_USER}@{ip} "cd {REMOTE_DIR} && python3 scripts/check_with_token.py"'
    success, output = run_command(cmd, "Vérification des capteurs")
    
    if success:
        print("📊 Résultats de la vérification:")
        print('-' * 40)
        print(output)
    else:
        print("❌ Impossible de vérifier les capteurs")
    
    return True

def main():
    """Fonction principale."""
    print('🚀 DÉPLOIEMENT ET ANALYSE DES ERREURS')
    print('=' * 60)
    
    # Tester les adresses IP
    successful_ip = None
    for ip in RASPBERRY_PI_IPS:
        print(f'🔗 Test de connexion à {ip}...')
        cmd = f'ssh {RASPBERRY_PI_USER}@{ip} "echo Connexion réussie"'
        success, output = run_command(cmd, f"Test de {ip}")
        if success:
            successful_ip = ip
            print(f'✅ Connexion réussie à {ip}')
            break
    
    if not successful_ip:
        print('❌ Impossible de se connecter à aucune des adresses IP')
        return 1
    
    # Déployer les fichiers
    if not deploy_files(successful_ip):
        print('❌ Déploiement échoué')
        return 1
    
    # Redémarrer Home Assistant
    if not restart_home_assistant(successful_ip):
        print('❌ Redémarrage échoué')
        return 1
    
    # Analyser les logs
    if not analyze_logs(successful_ip):
        print('❌ Analyse des logs échouée')
        return 1
    
    # Vérifier les capteurs
    if not check_sensors(successful_ip):
        print('❌ Vérification des capteurs échouée')
        return 1
    
    print('\n📋 RÉSUMÉ DU DÉPLOIEMENT')
    print('=' * 60)
    print('✅ Déploiement terminé avec succès')
    print(f'✅ Fichiers copiés sur {successful_ip}')
    print('✅ Home Assistant redémarré')
    print('✅ Logs analysés')
    print('✅ Capteurs vérifiés')
    
    print('\n💡 Prochaines étapes:')
    print('   1. Vérifier les nouveaux capteurs dans Developer Tools → States')
    print('   2. Configurer le délai de réessai dans les options')
    print('   3. Surveiller les logs pour les erreurs')
    
    return 0

if __name__ == '__main__':
    sys.exit(main())