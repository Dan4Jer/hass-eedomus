#!/usr/bin/env python3
"""Script pour vérifier les capteurs eedomus en utilisant le token API."""

import json
import os
import sys
import urllib.error
import urllib.request

# Adresses IP possibles du Raspberry Pi
RASPBERRY_PI_IPS = ["192.168.1.4", "192.168.1.5"]


def get_token_from_file():
    """Lire le token API depuis le fichier."""
    token_file = "/Users/danjer/mistral/credentials-ha/token"

    if not os.path.exists(token_file):
        print(f"❌ Fichier token introuvable: {token_file}")
        return None

    try:
        with open(token_file, "r") as f:
            token = f.read().strip()

        if token:
            print(f"✅ Token API lu: {token[:30]}...")
            return token
        else:
            print("❌ Token vide dans le fichier")
            return None
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du token: {e}")
        return None


def get_all_states(api_token, base_url):
    """Récupérer tous les états depuis Home Assistant."""
    try:
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(
            f"{base_url}/api/states", headers=headers, method="GET"
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        try:
            error_data = json.loads(e.read().decode("utf-8"))
            print(f"Error details: {json.dumps(error_data, indent=2)}")
        except:
            pass
        return None
    except Exception as e:
        print(f"Erreur lors de la récupération des états: {e}")
        return None


def analyze_history_sensors(states):
    """Analyser les capteurs d'historique."""
    if not states:
        return None

    # Filtrer les capteurs eedomus
    eedomus_sensors = [s for s in states if "eedomus" in s.get("entity_id", "")]

    # Filtrer les capteurs d'historique
    history_sensors = [
        s for s in eedomus_sensors if "history" in s.get("entity_id", "")
    ]

    return {
        "all_sensors": eedomus_sensors,
        "history_sensors": history_sensors,
        "total_eedomus_sensors": len(eedomus_sensors),
        "total_history_sensors": len(history_sensors),
    }


def display_results(analysis):
    """Afficher les résultats de l'analyse."""
    if not analysis:
        print("❌ Analyse échouée")
        return

    print()
    print("📊 Résultats de l'analyse:")
    print("=" * 40)

    print(f'Total capteurs eedomus: {analysis["total_eedomus_sensors"]}')
    print(f'Capteurs d\'historique: {analysis["total_history_sensors"]}')
    print()

    if analysis["history_sensors"]:
        print("✅ Capteurs de progression d'historique trouvés:")
        print("-" * 40)

        for sensor in analysis["history_sensors"]:
            print(f'Entity: {sensor.get("entity_id", "Unknown")}')
            print(f'State: {sensor.get("state", "Unknown")}')

            attrs = sensor.get("attributes", {})
            if "device_class" in attrs and attrs["device_class"] == "progress":
                try:
                    progress = float(sensor.get("state", 0))
                    print(f"Progress: {progress}%")

                    if progress == 0:
                        print("Status: ⚠️  Non démarré")
                    elif progress < 100:
                        print("Status: ℹ️  En cours")
                    else:
                        print("Status: ✅ Complété")
                except ValueError:
                    print("Status: ❌ État invalide")

            if "periph_name" in attrs:
                print(f'Device: {attrs["periph_name"]}')

            print()

        print("✅ Capteurs d'historique fonctionnels")
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

    # Afficher quelques capteurs eedomus pour référence
    print("📋 Exemple de capteurs eedomus (premiers 5):")
    print("-" * 40)
    for sensor in analysis["all_sensors"][:5]:
        print(f'{sensor.get("entity_id", "Unknown")}: {sensor.get("state", "Unknown")}')
    if len(analysis["all_sensors"]) > 5:
        print(f'... et {len(analysis["all_sensors"]) - 5} autres capteurs')


def main():
    """Fonction principale."""
    print("🔍 VÉRIFICATION DES CAPTEURS EEDOMUS AVEC TOKEN API")
    print("=" * 60)

    # Lire le token API
    api_token = get_token_from_file()

    if not api_token:
        return

    # Tester les adresses IP
    successful_connection = False
    base_url = None

    for ip in RASPBERRY_PI_IPS:
        print(f"🔗 Test de connexion à {ip}...")

        # Tester la connexion avec le token
        try:
            test_url = f"http://{ip}:8123/api/states"
            req = urllib.request.Request(
                test_url, headers={"Authorization": f"Bearer {api_token}"}, method="GET"
            )

            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    base_url = f"http://{ip}:8123"
                    successful_connection = True
                    print(f"✅ Connexion réussie à {ip} avec le token")
                    break
        except urllib.error.HTTPError as e:
            print(f"❌ Connexion échouée à {ip}: HTTP {e.code}")
        except Exception as e:
            print(f"❌ Connexion échouée à {ip}: {e}")

    if not successful_connection:
        print("❌ Impossible de se connecter à aucune des adresses IP")
        print("   Vérifiez:")
        print("   - Le Raspberry Pi est allumé")
        print("   - Home Assistant est en cours d'exécution")
        print("   - Le token API est valide")
        print("   - Les adresses IP sont correctes")
        return

    # Récupérer les états
    print(f"📊 Récupération des états depuis {base_url}...")
    states = get_all_states(api_token, base_url)

    if not states:
        print("❌ Impossible de récupérer les états")
        return

    print(f"✅ {len(states)} états récupérés")
    print()

    # Analyser les capteurs
    print("🔍 Analyse des capteurs d'historique...")
    analysis = analyze_history_sensors(states)

    if not analysis:
        print("❌ Analyse échouée")
        return

    print(f"✅ Analyse terminée")
    print()

    # Afficher les résultats
    display_results(analysis)

    print()
    print("📋 Résumé:")
    print("=" * 40)

    if analysis["history_sensors"]:
        print("✅ Les capteurs d'historique sont fonctionnels")
        print(
            f'   - {analysis["total_history_sensors"]} capteurs d\'historique trouvés'
        )
    else:
        print("❌ Aucun capteur d'historique trouvé")
        print("   L'option history doit être activée")


if __name__ == "__main__":
    main()
