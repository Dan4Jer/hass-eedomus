#!/usr/bin/env python3
"""Script pour vérifier que toutes les améliorations ont été appliquées."""

import os
import re


def check_file_for_patterns(filepath, patterns):
    """Vérifier si un fichier contient certains motifs."""
    if not os.path.exists(filepath):
        return False, f"Fichier introuvable: {filepath}"

    with open(filepath, "r") as f:
        content = f.read()

    results = {}
    for pattern_name, pattern in patterns.items():
        if re.search(pattern, content, re.MULTILINE):
            results[pattern_name] = True
        else:
            results[pattern_name] = False

    return True, results


def main():
    """Vérifier que toutes les améliorations ont été appliquées."""
    print("🔍 VÉRIFICATION DES AMÉLIORATIONS")
    print("=" * 60)

    # Vérifier le fichier const.py
    print("📁 Vérification de const.py...")
    const_patterns = {
        "CONF_HISTORY_RETRY_DELAY": r'CONF_HISTORY_RETRY_DELAY\s*=\s*"history_retry_delay"',
        "DEFAULT_HISTORY_RETRY_DELAY": r"DEFAULT_HISTORY_RETRY_DELAY\s*=\s*24",
    }

    success, results = check_file_for_patterns(
        "hass-eedomus/custom_components/eedomus/const.py", const_patterns
    )

    if success:
        for pattern_name, found in results.items():
            status = "✅" if found else "❌"
            print(f"  {status} {pattern_name}")
    else:
        print(f"  ❌ {results}")

    # Vérifier le fichier coordinator.py
    print("\n📁 Vérification de coordinator.py...")
    coordinator_patterns = {
        "retry_queue": r"self\._retry_queue\s*=\s*\{\}",
        "error_count": r"self\._error_count\s*=\s*\{\}",
        "validate_history_data": r"def _validate_history_data\(self, chunk: list\)",
        "handle_fetch_error": r"def _handle_fetch_error\(self, periph_id, error_message\)",
        "create_error_sensors": r"async def _create_error_sensors\(self\)",
        "min(100,": r"global_progress\s*=\s*min\(100,\s*\(total_retrieved\s*/\s*total_estimated\)\s*\*\s*100\)",
    }

    success, results = check_file_for_patterns(
        "hass-eedomus/custom_components/eedomus/coordinator.py", coordinator_patterns
    )

    if success:
        for pattern_name, found in results.items():
            status = "✅" if found else "❌"
            print(f"  {status} {pattern_name}")
    else:
        print(f"  ❌ {results}")

    # Vérifier le fichier options_flow.py
    print("\n📁 Vérification de options_flow.py...")
    options_patterns = {
        "CONF_HISTORY_RETRY_DELAY": r"CONF_HISTORY_RETRY_DELAY",
        "DEFAULT_HISTORY_RETRY_DELAY": r"DEFAULT_HISTORY_RETRY_DELAY",
        "history_retry_delay": r"vol\.Optional\(CONF_HISTORY_RETRY_DELAY",
    }

    success, results = check_file_for_patterns(
        "hass-eedomus/custom_components/eedomus/options_flow.py", options_patterns
    )

    if success:
        for pattern_name, found in results.items():
            status = "✅" if found else "❌"
            print(f"  {status} {pattern_name}")
    else:
        print(f"  ❌ {results}")

    print("\n📋 Résumé:")
    print("=" * 40)
    print("✅ Vérification des améliorations terminée")
    print()
    print("💡 Prochaines étapes:")
    print("   1. Déployer les modifications sur le Raspberry Pi")
    print("   2. Redémarrer Home Assistant")
    print("   3. Vérifier les nouveaux capteurs dans Developer Tools → States")
    print("   4. Configurer le délai de réessai dans les options")


if __name__ == "__main__":
    main()
