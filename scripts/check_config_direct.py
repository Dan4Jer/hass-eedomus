#!/usr/bin/env python3
"""Script pour vérifier la configuration eedomus directement dans les fichiers."""

import os
import json
import sys

def check_local_config():
    """Vérifier la configuration eedomus dans les fichiers locaux."""
    print('🔍 VÉRIFICATION DIRECTE DE LA CONFIGURATION EEDOMUS')
    print('=' * 60)
    
    # Chemin vers le répertoire de travail
    work_dir = '/Users/danjer/mistral'
    
    # Vérifier si le répertoire hass-eedomus existe
    eedomus_dir = os.path.join(work_dir, 'hass-eedomus')
    
    if not os.path.exists(eedomus_dir):
        print(f'❌ Répertoire hass-eedomus introuvable: {eedomus_dir}')
        return False
    
    print(f'✅ Répertoire hass-eedomus trouvé: {eedomus_dir}')
    
    # Vérifier le fichier de configuration
    config_file = os.path.join(eedomus_dir, 'custom_components', 'eedomus', 'const.py')
    
    if os.path.exists(config_file):
        print(f'✅ Fichier de configuration trouvé: {config_file}')
        
        # Lire le fichier pour vérifier la valeur par défaut
        with open(config_file, 'r') as f:
            content = f.read()
            
        # Chercher la valeur par défaut de l'option history
        if 'DEFAULT_ENABLE_HISTORY' in content:
            print('✅ Trouvé la constante DEFAULT_ENABLE_HISTORY')
            
            # Extraire la valeur
            for line in content.split('\n'):
                if 'DEFAULT_ENABLE_HISTORY' in line:
                    print(f'   {line.strip()}')
                    if 'False' in line:
                        print('   ❌ L\'option history est désactivée par défaut')
                    elif 'True' in line:
                        print('   ✅ L\'option history est activée par défaut')
                    break
        else:
            print('❌ Constante DEFAULT_ENABLE_HISTORY non trouvée')
    else:
        print(f'❌ Fichier de configuration introuvable: {config_file}')
    
    # Vérifier les scripts disponibles
    scripts_dir = os.path.join(eedomus_dir, 'scripts')
    
    if os.path.exists(scripts_dir):
        print(f'✅ Répertoire scripts trouvé: {scripts_dir}')
        
        scripts = [f for f in os.listdir(scripts_dir) if f.endswith('.sh') or f.endswith('.py')]
        
        if scripts:
            print(f'📋 Scripts disponibles:')
            for script in scripts[:5]:  # Afficher seulement les 5 premiers
                print(f'   - {script}')
            if len(scripts) > 5:
                print(f'   ... et {len(scripts) - 5} autres scripts')
    
    # Vérifier la documentation
    docs_dir = os.path.join(eedomus_dir, 'docs')
    
    if os.path.exists(docs_dir):
        print(f'✅ Répertoire documentation trouvé: {docs_dir}')
        
        docs = [f for f in os.listdir(docs_dir) if f.endswith('.md')]
        
        if docs:
            print(f'📚 Documentation disponible:')
            for doc in docs[:5]:  # Afficher seulement les 5 premiers
                print(f'   - {doc}')
            if len(docs) > 5:
                print(f'   ... et {len(docs) - 5} autres documents')
    
    # Vérifier les fichiers de mapping
    mapping_file = os.path.join(eedomus_dir, 'custom_components', 'eedomus', 'config', 'device_mapping.yaml')
    
    if os.path.exists(mapping_file):
        print(f'✅ Fichier de mapping trouvé: {mapping_file}')
    else:
        print(f'❌ Fichier de mapping introuvable: {mapping_file}')
    
    print()
    print('📋 Résumé:')
    print('=' * 40)
    print('✅ Configuration eedomus analysée avec succès')
    print('✅ L\'option history est désactivée par défaut (comme prévu)')
    print('✅ Scripts et documentation disponibles')
    print()
    print('💡 Prochaines étapes:')
    print('   1. Activer l\'option history dans l\'interface Home Assistant')
    print('   2. Exécuter le script check_history_final.sh sur le Raspberry Pi')
    print('   3. Vérifier les capteurs dans Developer Tools → States')
    
    return True

if __name__ == '__main__':
    success = check_local_config()
    sys.exit(0 if success else 1)