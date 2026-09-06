#!/usr/bin/env python3
"""
Script de suivi des capteurs d'historique via API Home Assistant.

Ce script permet de :
1. Lister tous les capteurs d'historique créés
2. Suivre leur état et progression en temps réel
3. Vérifier que les capteurs par périphérique sont bien créés
4. Confirmer le fonctionnement de l'option history

Usage:
    # Mode interactif (suivi en temps réel)
    python3 scripts/monitor_history_sensors.py --host http://localhost:8123 --token YOUR_TOKEN
    
    # Mode unique (liste des capteurs)
    python3 scripts/monitor_history_sensors.py --host http://localhost:8123 --token YOUR_TOKEN --once
    
    # Vérification spécifique d'un périphérique
    python3 scripts/monitor_history_sensors.py --host http://localhost:8123 --token YOUR_TOKEN --peripheral 1061603
"""

import argparse
import asyncio
import aiohttp
from datetime import datetime
import json
import sys
from typing import Dict, List, Optional, Any


class HistorySensorMonitor:
    """Moniteur des capteurs d'historique."""
    
    def __init__(self, host: str, token: str, session: Optional[aiohttp.ClientSession] = None):
        self.host = host.rstrip('/')
        self.token = token
        self.session = session
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    
    async def get_states(self) -> List[Dict[str, Any]]:
        """Récupère tous les états des entités eedomus."""
        url = f"{self.host}/api/states"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [state for state in data if state.get('entity_id', '').startswith('sensor.eedomus')]
                    else:
                        raise Exception(f"Erreur {response.status}: {await response.text()}")
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des états: {e}")
            return []
    
    async def get_history_sensors(self) -> Dict[str, Dict[str, Any]]:
        """Récupère tous les capteurs d'historique et les organise par type."""
        states = await self.get_states()
        
        sensors = {
            "global_progress": [],
            "global_stats": [],
            "device_progress": [],
            "device_history": [],
            "other": []
        }
        
        for state in states:
            entity_id = state.get('entity_id', '')
            
            if 'history_progress' in entity_id and 'global' in entity_id:
                sensors['global_progress'].append(state)
            elif 'history_progress' in entity_id:
                sensors['device_progress'].append(state)
            elif 'history_stats' in entity_id:
                sensors['global_stats'].append(state)
            elif 'history' in entity_id and 'progress' not in entity_id and 'stats' not in entity_id:
                sensors['device_history'].append(state)
            elif 'eedomus' in entity_id:
                sensors['other'].append(state)
        
        return sensors
    
    async def get_sensor_details(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les détails d'un capteur spécifique."""
        url = f"{self.host}/api/states/{entity_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
        except Exception as e:
            print(f"❌ Erreur lors de la récupération de {entity_id}: {e}")
            return None
    
    async def check_history_option(self) -> Dict[str, Any]:
        """Vérifie l'état de l'option history dans la configuration."""
        # Récupérer les config entries
        url = f"{self.host}/api/config/config_entry"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        entries = await response.json()
                        for entry in entries:
                            if entry.get('domain') == 'eedomus':
                                return {
                                    'entry_id': entry.get('entry_id'),
                                    'title': entry.get('title'),
                                    'data': entry.get('data', {}),
                                    'options': entry.get('options', {})
                                }
        except Exception as e:
            print(f"❌ Erreur lors de la vérification de l'option history: {e}")
        
        return {}
    
    def format_sensor_info(self, state: Dict[str, Any]) -> str:
        """Formate les informations d'un capteur pour l'affichage."""
        entity_id = state.get('entity_id', 'N/A')
        state_value = state.get('state', 'N/A')
        attributes = state.get('attributes', {})
        
        # Formatage des attributs importants
        important_attrs = {}
        for key in ['device_id', 'periph_id', 'periph_name', 'history_completed', 
                   'last_timestamp', 'data_points_retrieved', 'data_points_estimated',
                   'completed', 'devices_total', 'devices_completed']:
            if key in attributes:
                important_attrs[key] = attributes[key]
        
        return f"""
    Entity: {entity_id}
    State: {state_value}
    Attributes: {json.dumps(important_attrs, indent=2, ensure_ascii=False)}
"""
    
    def print_header(self, title: str):
        """Affiche un en-tête."""
        print("\n" + "="*80)
        print(f" 📊 {title}")
        print("="*80)
    
    def print_section(self, title: str):
        """Affiche une section."""
        print(f"\n📋 {title}")
        print("-"*60)
    
    async def display_history_sensors(self):
        """Affiche tous les capteurs d'historique."""
        self.print_header("MONITORING DES CAPTEURS D'HISTORIQUE EEDOMUS")
        
        # Vérifier l'option history
        self.print_section("1. État de l'option History")
        config = await self.check_history_option()
        if config:
            history_enabled = config.get('options', {}).get('history', 
                           config.get('data', {}).get('history', 'Inconnu'))
            print(f"   Option history: {history_enabled}")
            print(f"   Entry ID: {config.get('entry_id', 'N/A')}")
        else:
            print("   ❌ Impossible de récupérer la configuration")
        
        # Récupérer les capteurs
        self.print_section("2. Capteurs d'historique détectés")
        sensors = await self.get_history_sensors()
        
        total_sensors = sum(len(v) for v in sensors.values())
        print(f"   Total capteurs eedomus: {len(sensors['other'])}")
        print(f"   Total capteurs d'historique: {total_sensors}")
        
        # Détails par catégorie
        print(f"\n   📈 Capteurs globaux:")
        print(f"      - Progression globale: {len(sensors['global_progress'])}")
        print(f"      - Statistiques: {len(sensors['global_stats'])}")
        
        print(f"\n   📱 Capteurs par périphérique:")
        print(f"      - Progression par périphérique: {len(sensors['device_progress'])}")
        print(f"      - Historique par périphérique: {len(sensors['device_history'])}")
        
        # Afficher les détails des capteurs globaux
        if sensors['global_progress']:
            self.print_section("3. Détails - Progression Globale")
            for state in sensors['global_progress']:
                print(self.format_sensor_info(state))
        
        if sensors['global_stats']:
            self.print_section("4. Détails - Statistiques Globales")
            for state in sensors['global_stats']:
                print(self.format_sensor_info(state))
        
        # Afficher un échantillon des capteurs par périphérique
        if sensors['device_progress']:
            self.print_section("5. Échantillon - Progression par Périphérique")
            # Afficher les 5 premiers
            for state in sensors['device_progress'][:5]:
                print(self.format_sensor_info(state))
            if len(sensors['device_progress']) > 5:
                print(f"   ... et {len(sensors['device_progress']) - 5} autres")
        
        if sensors['device_history']:
            self.print_section("6. Échantillon - Historique par Périphérique")
            # Afficher les 5 premiers
            for state in sensors['device_history'][:5]:
                print(self.format_sensor_info(state))
            if len(sensors['device_history']) > 5:
                print(f"   ... et {len(sensors['device_history']) - 5} autres")
        
        # Résumé
        self.print_section("7. Résumé et Diagnostics")
        
        # Vérifications
        checks = []
        
        # Check 1: Capteurs globaux existent
        if len(sensors['global_progress']) > 0 or len(sensors['global_stats']) > 0:
            checks.append("✅ Capteurs globaux d'historique créés")
        else:
            checks.append("❌ Aucun capteur global d'historique trouvé")
        
        # Check 2: Capteurs par périphérique existent
        if len(sensors['device_progress']) > 0 or len(sensors['device_history']) > 0:
            checks.append(f"✅ {len(sensors['device_progress'] + sensors['device_history'])} capteurs par périphérique créés")
        else:
            checks.append("⚠️ Aucun capteur par périphérique trouvé (problème identifié)")
        
        # Check 3: Option history activée
        if config and (config.get('options', {}).get('history') or config.get('data', {}).get('history')):
            checks.append("✅ Option history est activée")
        elif config:
            checks.append("⚠️ Option history est désactivée")
        
        for check in checks:
            print(f"   {check}")
        
        # Recommandations
        self.print_section("8. Recommandations")
        if len(sensors['device_progress']) == 0 and len(sensors['device_history']) == 0:
            print("   🎯 Solution: Redémarrer Home Assistant après avoir activé l'option history")
            print("   🎯 Solution: Vérifier que l'option history est bien sauvegardée")
        else:
            print("   ✅ Les capteurs d'historique semblent fonctionner correctement")
        
        print()
    
    async def monitor_realtime(self, interval: int = 10):
        """Surveille les capteurs en temps réel."""
        self.print_header("MONITORING EN TEMPS RÉEL")
        print(f"   Intervalle de rafraîchissement: {interval} secondes")
        print(f"   Appuyez sur Ctrl+C pour arrêter\n")
        
        try:
            while True:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.print_section(f"Mise à jour à {timestamp}")
                
                sensors = await self.get_history_sensors()
                
                # Afficher les capteurs globaux
                if sensors['global_progress']:
                    for state in sensors['global_progress']:
                        entity_id = state.get('entity_id')
                        state_value = state.get('state')
                        print(f"   📈 {entity_id}: {state_value}%")
                
                if sensors['global_stats']:
                    for state in sensors['global_stats']:
                        entity_id = state.get('entity_id')
                        state_value = state.get('state')
                        print(f"   📊 {entity_id}: {state_value} MB")
                
                # Compter les capteurs par périphérique
                device_count = len(sensors['device_progress']) + len(sensors['device_history'])
                print(f"   📱 Capteurs par périphérique: {device_count}")
                
                # Vérifier la progression moyenne
                if sensors['global_progress']:
                    global_state = sensors['global_progress'][0]
                    attributes = global_state.get('attributes', {})
                    completed = attributes.get('devices_completed', 0)
                    total = attributes.get('devices_total', 1)
                    if total > 0:
                        progress = (completed / total) * 100
                        print(f"   🎯 Progression globale: {progress:.1f}%")
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n✅ Monitoring arrêté par l'utilisateur")
    
    async def check_specific_peripheral(self, peripheral_id: str):
        """Vérifie les capteurs pour un périphérique spécifique."""
        self.print_header(f"VÉRIFICATION DU PÉRIPHÉRIQUE {peripheral_id}")
        
        sensors = await self.get_history_sensors()
        
        # Chercher les capteurs pour ce périphérique
        found_sensors = []
        for state in sensors['device_progress'] + sensors['device_history']:
            entity_id = state.get('entity_id', '')
            if str(peripheral_id) in entity_id:
                found_sensors.append(state)
        
        if found_sensors:
            print(f"\n✅ Capteurs trouvés pour le périphérique {peripheral_id}:")
            for state in found_sensors:
                print(self.format_sensor_info(state))
        else:
            print(f"\n❌ Aucun capteur trouvé pour le périphérique {peripheral_id}")
            print(f"\n💡 Vérifications:")
            print(f"   1. Le périphérique {peripheral_id} existe-t-il dans le coordinator ?")
            print(f"   2. L'option history est-elle activée ?")
            print(f"   3. Home Assistant a-t-il été redémarré après activation ?")


async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(
        description="Script de suivi des capteurs d'historique eedomus"
    )
    parser.add_argument(
        "--host", 
        required=True,
        help="URL de Home Assistant (ex: http://localhost:8123)"
    )
    parser.add_argument(
        "--token", 
        required=True,
        help="Token d'accès API de Home Assistant"
    )
    parser.add_argument(
        "--once", 
        action="store_true",
        help="Mode unique (une seule vérification)"
    )
    parser.add_argument(
        "--peripheral", 
        type=str,
        default=None,
        help="Vérifier un périphérique spécifique"
    )
    parser.add_argument(
        "--interval", 
        type=int,
        default=10,
        help="Intervalle de rafraîchissement en secondes (par défaut: 10)"
    )
    
    args = parser.parse_args()
    
    monitor = HistorySensorMonitor(args.host, args.token)
    
    try:
        if args.peripheral:
            await monitor.check_specific_peripheral(args.peripheral)
        elif args.once:
            await monitor.display_history_sensors()
        else:
            await monitor.monitor_realtime(args.interval)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
