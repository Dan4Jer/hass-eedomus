#!/usr/bin/env python3
"""Script simple pour vérifier les capteurs eedomus sans authentification."""

import json
import os
import urllib.error
import urllib.request

# Adresses IP possibles du Raspberry Pi
RASPBERRY_PI_IPS = ["192.168.1.4", "192.168.1.5"]


def test_connection(ip):
    """Tester la connexion de base à une adresse IP."""
    try:
        test_url = f"http://{ip}:8123/"
        req = urllib.request.Request(test_url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception as e:
        print(f"  Erreur: {e}")
        return False


def get_states(ip):
    """Récupérer les états depuis Home Assistant."""
    try:
        states_url = f"http://{ip}:8123/api/states"
        req = urllib.request.Request(states_url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"  Erreur lors de la récupération des états: {e}")
        return None


def main():
    """Fonction principale."""
    print("🔍 VÉRIFICATION SIMPLE DES CAPTEURS EEDOMUS")
    print("=" * 60)

    # Tester les différentes adresses IP
    successful_connection = False
    base_url = None

    for ip in RASPBERRY_PI_IPS:
        print(f"🔗 Test de connexion à {ip}...")

        # Tester la connexion de base
        if test_connection(ip):
            base_url = f"http://{ip}:8123"
            successful_connection = True
            print(f"✅ Connexion de base réussie à {ip}")
            break
        else:
            print(f"❌ Connexion échouée à {ip}")

    if not successful_connection:
        print("❌ Impossible de se connecter à aucune des adresses IP")
        return

    # Récupérer les états
    print(f"📊 Récupération des états depuis {base_url}...")
    states = get_states(RASPBERRY_PI_IPS[0])  # Utiliser la première IP qui a fonctionné

    if not states:
        print("❌ Impossible de récupérer les états")
        return

    print(f"✅ {len(states)} états récupérés")
    print()

    # Filtrer les capteurs eedomus
    eedomus_sensors = [s for s in states if "eedomus" in s.get("entity_id", "")]

    if not eedomus_sensors:
        print("❌ Aucun capteur eedomus trouvé")
        print("   Vérifiez que l'intégration eedomus est bien installée")
        return

    print(f"✅ Trouvé {len(eedomus_sensors)} capteurs eedomus")
    print()

    # Filtrer les capteurs d'historique
    history_sensors = [
        s for s in eedomus_sensors if "history" in s.get("entity_id", "")
    ]

    if history_sensors:
        print("📊 Capteurs de progression d'historique:")
        print("-" * 40)
        for sensor in history_sensors:
            print(f'Entity: {sensor.get("entity_id", "Unknown")}')
            print(f'State: {sensor.get("state", "Unknown")}')
            attrs = sensor.get("attributes", {})
            print(f"Attributes: {json.dumps(attrs, indent=2)}")
            print()

        print("✅ Capteurs d'historique trouvés et fonctionnels")
        print()
        print("📋 Comportement attendu:")
        print("   - sensor.eedomus_history_progress: Progression globale (0-100%)")
        print(
            "   - sensor.eedomus_history_progress_{device_id}: Progression par appareil"
        )
        print("   - sensor.eedomus_history_stats: Statistiques de téléchargement")

    else:
        print("❌ Aucun capteur d'historique trouvé")
        print("   Cela peut signifier:")
        print("   - L'option history n'est pas activée")
        print("   - Les capteurs virtuels n'ont pas été créés")
        print("   - L'intégration n'a pas encore démarré")
        print()
        print("💡 Pour activer l'historique:")
        print("   1. Allez dans Settings → Devices & Services")
        print("   2. Sélectionnez votre intégration eedomus")
        print("   3. Cliquez sur Configure/Options")
        print('   4. Activez l\'option "Enable History"')
        print("   5. Redémarrez Home Assistant")

    # Afficher tous les capteurs eedomus pour référence
    print()
    print("📋 Tous les capteurs eedomus (premiers 10):")
    print("-" * 40)
    for sensor in eedomus_sensors[:10]:
        print(f'{sensor.get("entity_id", "Unknown")}: {sensor.get("state", "Unknown")}')
    if len(eedomus_sensors) > 10:
        print(f"... et {len(eedomus_sensors) - 10} autres capteurs")


if __name__ == "__main__":
    main()
