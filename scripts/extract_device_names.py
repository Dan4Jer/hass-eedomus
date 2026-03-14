#!/usr/bin/env python3
"""
Script pour extraire les noms des périphériques à partir des logs.

Ce script analyse les logs pour trouver les noms des périphériques
qui ont récupéré des données historiques.
"""

import re
import sys
from collections import defaultdict

def extract_device_names(log_file="~/mistral/rasp.log"):
    """Extraire les noms des périphériques à partir des logs."""
    
    print("🔍 Extraction des noms des périphériques")
    print("=" * 60)
    
    # Remplacer ~ par le chemin complet
    log_file = log_file.replace("~", "/Users/danjer")
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ Fichier de log introuvable: {log_file}")
        return False
    
    # Structures de données
    device_info = defaultdict(dict)  # {device_id: {'name': '', 'attempts': []}}
    
    # Expressions régulières
    fetch_pattern = re.compile(r'Fetching history for (\d+) \(from (.*?)\)')
    name_pattern = re.compile(r'"name": "(.*?)"')
    periph_id_pattern = re.compile(r'periph_id": (\d+)')
    
    # Analyser chaque ligne pour trouver les noms
    for line in lines:
        # Chercher les noms de périphériques
        name_match = name_pattern.search(line)
        if name_match:
            device_name = name_match.group(1)
            # Chercher l'ID du périphérique dans la même ligne ou les lignes précédentes
            # (les logs peuvent avoir le nom et l'ID dans des lignes différentes)
            continue
        
        # Chercher les tentatives de récupération
        fetch_match = fetch_pattern.search(line)
        if fetch_match:
            device_id = fetch_match.group(1)
            if 'attempts' not in device_info[device_id]:
                device_info[device_id]['attempts'] = []
            device_info[device_id]['attempts'].append(fetch_match.group(2))
    
    # Maintenant, chercher les noms dans les lignes qui contiennent des IDs
    for line in lines:
        periph_match = periph_id_pattern.search(line)
        if periph_match:
            device_id = periph_match.group(1)
            # Chercher le nom dans les 5 lignes suivantes
            for i in range(1, 6):
                if len(lines) > lines.index(line) + i:
                    next_line = lines[lines.index(line) + i]
                    name_match = name_pattern.search(next_line)
                    if name_match:
                        device_info[device_id]['name'] = name_match.group(1)
                        break
    
    # Afficher les résultats
    print(f"\n📋 Périphériques avec noms extraits:")
    print("-" * 60)
    
    # Trier par ID
    sorted_devices = sorted(device_info.keys(), key=int)
    
    for device_id in sorted_devices:
        info = device_info[device_id]
        name = info.get('name', 'Nom inconnu')
        attempts = len(info.get('attempts', []))
        
        print(f"\n📋 Périphérique {device_id}")
        print(f"   Nom: {name}")
        print(f"   Tentatives: {attempts}")
        if 'attempts' in info and info['attempts']:
            print(f"   Dernière tentative: {info['attempts'][-1]}")
    
    # Résumé
    print(f"\n📊 Résumé")
    print("-" * 60)
    print(f"Périphériques trouvés: {len(sorted_devices)}")
    print(f"Périphériques avec noms: {sum(1 for d in device_info.values() if d.get('name'))}")
    print(f"Périphériques sans noms: {sum(1 for d in device_info.values() if not d.get('name'))}")
    
    return True

if __name__ == "__main__":
    success = extract_device_names()
    sys.exit(0 if success else 1)