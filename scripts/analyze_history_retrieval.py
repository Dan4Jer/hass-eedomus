#!/usr/bin/env python3
"""
Script pour analyser l'état de la récupération des données historiques.

Ce script analyse les logs pour générer un rapport complet:
- Périphériques qui ont récupéré des données
- Périphériques en cours de récupération
- Périphériques avec erreurs
- Statistiques globales
"""

import re
import sys
from collections import defaultdict
from datetime import datetime

def analyze_history_logs(log_file="~/mistral/rasp.log"):
    """Analyser les logs pour générer un rapport de récupération historique."""
    
    print("📊 Analyse de la récupération des données historiques")
    print("=" * 60)
    
    # Remplacer ~ par le chemin complet
    log_file = log_file.replace("~", "/Users/danjer")
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ Fichier de log introuvable: {log_file}")
        print(f"   Vérifiez que le fichier existe à: {log_file}")
        return False
    
    # Structures de données pour le suivi
    devices_fetched = set()  # Périphériques qui ont récupéré des données
    devices_with_errors = set()  # Périphériques avec erreurs
    devices_in_progress = set()  # Périphériques en cours de récupération
    fetch_attempts = defaultdict(list)  # Tentatives de récupération par périphérique
    error_messages = defaultdict(list)  # Messages d'erreur par périphérique
    
    # Expressions régulières pour analyser les logs
    fetch_pattern = re.compile(r'Fetching history for (\d+) \(from (.*?)\)')
    error_pattern = re.compile(r'No history data received for (\d+)')
    async_error_pattern = re.compile(r"'async_generator' object is not iterable")
    virtual_sensors_pattern = re.compile(r'Virtual history sensors created: (\d+) device sensors')
    
    # Analyser chaque ligne
    for line in lines:
        # Vérifier les tentatives de récupération
        fetch_match = fetch_pattern.search(line)
        if fetch_match:
            device_id = fetch_match.group(1)
            timestamp = fetch_match.group(2)
            devices_in_progress.add(device_id)
            fetch_attempts[device_id].append({
                'timestamp': timestamp,
                'datetime': line.split()[0:2],  # Date et heure
                'line': line.strip()
            })
            continue
        
        # Vérifier les erreurs de récupération
        error_match = error_pattern.search(line)
        if error_match:
            device_id = error_match.group(1)
            devices_with_errors.add(device_id)
            error_messages[device_id].append({
                'type': 'no_data',
                'message': 'No history data received',
                'datetime': line.split()[0:2],
                'line': line.strip()
            })
            continue
        
        # Vérifier les erreurs async_generator
        if async_error_pattern.search(line):
            error_messages['global'].append({
                'type': 'async_generator',
                'message': 'async_generator object is not iterable',
                'datetime': line.split()[0:2],
                'line': line.strip()
            })
            continue
        
        # Vérifier la création des capteurs virtuels
        sensors_match = virtual_sensors_pattern.search(line)
        if sensors_match:
            device_count = int(sensors_match.group(1))
            print(f"✅ Capteurs virtuels créés: {device_count} capteurs par périphérique")
    
    # Déterminer quels périphériques ont réussi à récupérer des données
    # (ceux qui ont des tentatives de récupération et pas d'erreurs)
    for device_id in devices_in_progress:
        if device_id not in devices_with_errors:
            devices_fetched.add(device_id)
    
    # Générer le rapport
    print(f"\n📈 Statistiques globales")
    print("-" * 60)
    print(f"Périphériques avec données récupérées: {len(devices_fetched)}")
    print(f"Périphériques avec erreurs: {len(devices_with_errors)}")
    print(f"Périphériques en cours: {len(devices_in_progress)}")
    print(f"Total périphériques uniques: {len(devices_fetched | devices_with_errors | devices_in_progress)}")
    
    # Détails par périphérique
    print(f"\n🔍 Détails par périphérique")
    print("-" * 60)
    
    all_devices = sorted(devices_fetched | devices_with_errors | devices_in_progress)
    
    for device_id in all_devices:
        status = "✅ Récupéré" if device_id in devices_fetched else \
                 "❌ Erreur" if device_id in devices_with_errors else \
                 "🔄 En cours"
        
        print(f"\n📋 Périphérique {device_id} {status}")
        
        if device_id in fetch_attempts:
            print(f"   Tentatives de récupération: {len(fetch_attempts[device_id])}")
            for attempt in fetch_attempts[device_id][-3:]:  # Montrer les 3 dernières tentatives
                print(f"     - {attempt['datetime'][0]} {attempt['datetime'][1]}: {attempt['timestamp']}")
        
        if device_id in error_messages:
            print(f"   Erreurs: {len(error_messages[device_id])}")
            for error in error_messages[device_id][:3]:  # Montrer les 3 premières erreurs
                print(f"     - {error['datetime'][0]} {error['datetime'][1]}: {error['message']}")
    
    # Résumé des erreurs globales
    if 'global' in error_messages:
        print(f"\n⚠️  Erreurs globales")
        print("-" * 60)
        for error in error_messages['global']:
            print(f"   {error['datetime'][0]} {error['datetime'][1]}: {error['message']}")
    
    # Recommandations
    print(f"\n💡 Recommandations")
    print("-" * 60)
    
    if devices_with_errors:
        print("⚠️  Certains périphériques ont des erreurs de récupération:")
        print(f"   - Vérifiez que ces périphériques ont bien des données historiques")
        print(f"   - Certains périphériques peuvent ne pas avoir d'historique disponible")
        print(f"   - Consultez la documentation pour les périphériques spécifiques")
    
    if 'global' in error_messages:
        print("⚠️  Erreurs globales détectées:")
        print(f"   - Les capteurs virtuels peuvent ne pas être créés correctement")
        print(f"   - Vérifiez que les fixes ont été déployés")
        print(f"   - Redémarrez Home Assistant si nécessaire")
    
    if devices_fetched:
        print("✅ Certains périphériques ont réussi à récupérer des données:")
        print(f"   - La récupération est en cours pour {len(devices_fetched)} périphériques")
        print(f"   - Continuez à surveiller les logs pour le suivi")
    
    print(f"\n📊 Résumé final")
    print("-" * 60)
    print(f"Périphériques avec données: {len(devices_fetched)}")
    print(f"Périphériques avec erreurs: {len(devices_with_errors)}")
    print(f"Périphériques totaux: {len(all_devices)}")
    
    if len(devices_fetched) > 0:
        percentage = (len(devices_fetched) / len(all_devices) * 100) if all_devices else 0
        print(f"Progression estimée: {percentage:.1f}%")
    
    return True

if __name__ == "__main__":
    success = analyze_history_logs()
    sys.exit(0 if success else 1)