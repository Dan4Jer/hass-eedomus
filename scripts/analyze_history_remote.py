#!/usr/bin/env python3
"""Script pour analyser les capteurs d'historique eedomus sur le Raspberry Pi distant."""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime

# Adresses IP possibles du Raspberry Pi
RASPBERRY_PI_IPS = ["192.168.1.4", "192.168.1.5"]


def get_api_token(username, password, base_url):
    """Obtenir un token API depuis Home Assistant."""
    try:
        login_url = f"{base_url}/api/auth/login_flow"
        data = json.dumps(
            {"type": "auth", "username": username, "password": password}
        ).encode("utf-8")

        req = urllib.request.Request(
            login_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("result") == "ok":
                return data.get("data", {}).get("refresh_token")

        return None

    except Exception as e:
        print(f"Erreur lors de l'obtention du token: {e}")
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


def generate_report(analysis):
    """Générer un rapport détaillé."""
    if not analysis or not analysis["history_sensors"]:
        return {
            "status": "NO_HISTORY_SENSORS",
            "message": "Aucun capteur d'historique trouvé",
            "recommendations": [
                "Activer l'option history dans les paramètres de l'intégration eedomus",
                "Redémarrer Home Assistant après activation",
                "Vérifier les logs pour les erreurs potentielles",
            ],
        }

    report = {
        "status": "HISTORY_SENSORS_FOUND",
        "timestamp": datetime.now().isoformat(),
        "total_eedomus_sensors": analysis["total_eedomus_sensors"],
        "total_history_sensors": analysis["total_history_sensors"],
        "sensors": [],
    }

    # Analyser chaque capteur d'historique
    for sensor in analysis["history_sensors"]:
        sensor_data = {
            "entity_id": sensor.get("entity_id"),
            "state": sensor.get("state"),
            "attributes": sensor.get("attributes", {}),
        }

        # Analyser la progression
        if (
            "device_class" in sensor_data["attributes"]
            and sensor_data["attributes"]["device_class"] == "progress"
        ):
            try:
                progress = float(sensor_data["state"])
                sensor_data["progress"] = progress

                if progress == 0:
                    sensor_data["status"] = "NOT_STARTED"
                elif progress < 100:
                    sensor_data["status"] = "IN_PROGRESS"
                else:
                    sensor_data["status"] = "COMPLETED"

            except ValueError:
                sensor_data["status"] = "INVALID_STATE"

        report["sensors"].append(sensor_data)

    # Calculer les statistiques
    report["statistics"] = {
        "completed": sum(
            1 for s in report["sensors"] if s.get("status") == "COMPLETED"
        ),
        "in_progress": sum(
            1 for s in report["sensors"] if s.get("status") == "IN_PROGRESS"
        ),
        "not_started": sum(
            1 for s in report["sensors"] if s.get("status") == "NOT_STARTED"
        ),
        "invalid": sum(
            1 for s in report["sensors"] if s.get("status") == "INVALID_STATE"
        ),
    }

    # Générer des recommandations
    recommendations = []

    if report["statistics"]["completed"] > 0:
        recommendations.append(
            "✅ Certains devices ont leur historique complètement récupéré"
        )

    if report["statistics"]["in_progress"] > 0:
        recommendations.append("ℹ️  Certains devices sont en cours de récupération")

    if report["statistics"]["not_started"] > 0:
        recommendations.append(
            "⚠️  Certains devices n'ont pas encore commencé la récupération"
        )

    if report["statistics"]["invalid"] > 0:
        recommendations.append("❌ Certains capteurs ont un état invalide")

    if report["total_history_sensors"] == 0:
        recommendations.append(
            "⚠️  Aucun capteur d'historique trouvé - vérifier que l'option est activée"
        )

    report["recommendations"] = recommendations

    return report


def save_report(report, filename="history_analysis_report.json"):
    """Sauvegarder le rapport dans un fichier."""
    try:
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        print(f"✅ Rapport sauvegardé dans {filename}")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde du rapport: {e}")
        return False


def display_report(report):
    """Afficher le rapport de manière lisible."""
    print("\n" + "=" * 60)
    print("📊 RAPPORT D'ANALYSE DES CAPTEURS D'HISTORIQUE")
    print("=" * 60)

    if report["status"] == "NO_HISTORY_SENSORS":
        print("❌ AUCUN CAPTEUR D'HISTORIQUE TROUVÉ")
        print()
        print("Recommandations:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")
        return

    print(f'📅 Date: {report["timestamp"]}')
    print(f'📊 Total capteurs eedomus: {report["total_eedomus_sensors"]}')
    print(f'📈 Capteurs d\'historique: {report["total_history_sensors"]}')
    print()

    print("📊 Statistiques:")
    print(f'  ✅ Complétés: {report["statistics"]["completed"]}')
    print(f'  ℹ️  En cours: {report["statistics"]["in_progress"]}')
    print(f'  ⚠️  Non démarrés: {report["statistics"]["not_started"]}')
    print(f'  ❌ Invalides: {report["statistics"]["invalid"]}')
    print()

    print("📋 Détails des capteurs:")
    print("-" * 40)

    for sensor in report["sensors"]:
        print(f'Entity: {sensor["entity_id"]}')
        print(f'State: {sensor["state"]}')

        if "progress" in sensor:
            print(f'Progress: {sensor["progress"]}%')

        if "status" in sensor:
            status_emoji = {
                "COMPLETED": "✅",
                "IN_PROGRESS": "ℹ️",
                "NOT_STARTED": "⚠️",
                "INVALID_STATE": "❌",
            }
            print(
                f'Status: {status_emoji.get(sensor["status"], "?")} {sensor["status"]}'
            )

        # Afficher les attributs intéressants
        attrs = sensor.get("attributes", {})
        if "periph_name" in attrs:
            print(f'Device: {attrs["periph_name"]}')
        if "data_points_retrieved" in attrs:
            print(f'Points récupérés: {attrs["data_points_retrieved"]}')
        if "data_points_estimated" in attrs:
            print(f'Points estimés: {attrs["data_points_estimated"]}')

        print()

    print("💡 Recommandations:")
    for rec in report["recommendations"]:
        print(f"  {rec}")

    print("=" * 60)


def main():
    """Fonction principale."""
    print("🔍 ANALYSE DES CAPTEURS D'HISTORIQUE EEDOMUS")
    print("=" * 60)

    # Lire les credentials
    credentials_file = "/Users/danjer/mistral/credentials-ha/credentials.txt"

    if not os.path.exists(credentials_file):
        print(f"❌ Fichier de credentials introuvable: {credentials_file}")
        return

    try:
        with open(credentials_file, "r") as f:
            lines = f.readlines()

        username = None
        password = None

        for line in lines:
            if line.startswith("user:"):
                username = line.split(":", 1)[1].strip()
            elif line.startswith("password:"):
                password = line.split(":", 1)[1].strip()

        if not username or not password:
            print("❌ Informations de connexion incomplètes")
            return

        print(f"✅ Credentials lus: user={username}")

    except Exception as e:
        print(f"❌ Erreur lors de la lecture des credentials: {e}")
        return

    # Tester les différentes adresses IP
    successful_connection = False
    base_url = None

    for ip in RASPBERRY_PI_IPS:
        print(f"🔗 Test de connexion à {ip}...")

        # Tester la connexion
        try:
            test_url = f"http://{ip}:8123/api/"
            req = urllib.request.Request(test_url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    base_url = f"http://{ip}:8123"
                    successful_connection = True
                    print(f"✅ Connexion réussie à {ip}")
                    break
        except Exception as e:
            print(f"❌ Connexion échouée à {ip}: {e}")

    if not successful_connection:
        print("❌ Impossible de se connecter à aucune des adresses IP")
        print("   Vérifiez:")
        print("   - Le Raspberry Pi est allumé")
        print("   - Home Assistant est en cours d'exécution")
        print("   - Les adresses IP sont correctes")
        print("   - Le port 8123 est ouvert")
        return

    # Obtenir le token API
    print(f"🔗 Obtention du token API sur {base_url}...")
    api_token = get_api_token(username, password, base_url)

    if not api_token:
        print("❌ Impossible d'obtenir le token API")
        return

    print("✅ Token API obtenu")
    print()

    # Récupérer les états
    print("📊 Récupération des états...")
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

    # Générer le rapport
    report = generate_report(analysis)

    # Afficher le rapport
    display_report(report)

    # Sauvegarder le rapport
    save_report(report)

    print()
    print("📋 Résumé:")
    print("=" * 40)

    if report["status"] == "HISTORY_SENSORS_FOUND":
        print("✅ Les capteurs d'historique sont fonctionnels")
        print(f'   - {report["total_history_sensors"]} capteurs d\'historique trouvés')
        print(
            f'   - {report["statistics"]["completed"]} devices complètement récupérés'
        )
        print(
            f'   - {report["statistics"]["in_progress"]} devices en cours de récupération'
        )
    else:
        print("❌ Aucun capteur d'historique trouvé")
        print("   L'option history doit être activée")


if __name__ == "__main__":
    main()
