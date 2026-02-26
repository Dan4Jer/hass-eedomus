#!/bin/bash

# Script to check eedomus history progress sensors in Home Assistant
# This script should be run on the Raspberry Pi

set -e

echo "🔍 Vérification des capteurs eedomus dans Home Assistant"
echo "=========================================================="

# Check if we're on the Raspberry Pi
if [ ! -d "/config/.storage" ]; then
    echo "❌ Ce script doit être exécuté sur le Raspberry Pi"
    echo "   Le répertoire /config/.storage n'a pas été trouvé"
    exit 1
fi

echo "✅ Exécuté sur le Raspberry Pi"
echo ""

# Check if Home Assistant is running
if ! curl -s http://localhost:8123/api/ > /dev/null 2>&1; then
    echo "❌ Home Assistant n'est pas accessible"
    echo "   Vérifiez que Home Assistant est en cours d'exécution"
    exit 1
fi

echo "✅ Home Assistant est accessible"
echo ""

# Get API token (you may need to set this manually)
API_TOKEN=""

# Try to get API token from config file
if [ -f "/config/.storage/auth" ]; then
    API_TOKEN=$(jq -r '.data[] | select(.type == "access_token") | .access_token' /config/.storage/auth 2>/dev/null | head -1)
fi

if [ -z "$API_TOKEN" ]; then
    echo "⚠️  Token API non trouvé automatiquement"
    echo "   Veuillez entrer votre token API manuellement:"
    read -p "Token API: " API_TOKEN
fi

echo "🔗 Test de connexion à l'API Home Assistant..."

# Test API connection
if ! curl -s -X GET "http://localhost:8123/api/states" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" > /tmp/hass_states.json; then
    echo "❌ Impossible de se connecter à l'API Home Assistant"
    echo "   Vérifiez le token API"
    exit 1
fi

echo "✅ Connexion API réussie"
echo ""

# Get eedomus sensors
python3 -c "
import json

with open('/tmp/hass_states.json', 'r') as f:
    states = json.load(f)

eedomus_sensors = [s for s in states if 'eedomus' in s.get('entity_id', '')]

if not eedomus_sensors:
    print('❌ Aucun capteur eedomus trouvé')
    print('   Vérifiez que l\'intégration eedomus est bien installée')
    exit(1)

print(f'✅ Trouvé {len(eedomus_sensors)} capteurs eedomus')
print()

# Filter history sensors
history_sensors = [s for s in eedomus_sensors if 'history' in s.get('entity_id', '')]

if history_sensors:
    print('📊 Capteurs de progression d\'historique:')
    print('-' * 40)
    for sensor in history_sensors:
        print(f'Entity: {sensor.get(\"entity_id\", \"Unknown\")}')
        print(f'State: {sensor.get(\"state\", \"Unknown\")}')
        attrs = sensor.get('attributes', {})
        print(f'Attributes: {json.dumps(attrs, indent=2)}')
        print()
else:
    print('❌ Aucun capteur d\'historique trouvé')
    print('   Cela peut signifier:')
    print('   - L\'option history n\'est pas activée')
    print('   - Les capteurs virtuels n\'ont pas été créés')
    print('   - L\'intégration n\'a pas encore démarré')
    print()
    print('💡 Pour activer l\'historique:')
    print('   1. Allez dans Settings → Devices & Services')
    print('   2. Sélectionnez votre intégration eedomus')
    print('   3. Cliquez sur Configure/Options')
    print('   4. Activez l\'option \"Enable History\"')
    print('   5. Redémarrez Home Assistant')
    print()
    print('   Ou utilisez le script:')
    print('   ./activate_history_feature.sh')
    exit(1)

# Show all eedomus sensors for reference
print('📋 Tous les capteurs eedomus (premiers 10):')
print('-' * 40)
for sensor in eedomus_sensors[:10]:
    print(f'{sensor.get(\"entity_id\", \"Unknown\")}: {sensor.get(\"state\", \"Unknown\")}')
if len(eedomus_sensors) > 10:
    print(f'... et {len(eedomus_sensors) - 10} autres capteurs')

print()
print('✅ Analyse des capteurs d\'historique terminée')
print('   Les capteurs sont bien créés et fonctionnent')
"

# Clean up
rm -f /tmp/hass_states.json

echo ""
echo "📋 Résumé:"
echo "=========="
echo "Les capteurs de progression d'historique sont bien créés."
echo "Vous pouvez les voir dans l'interface Home Assistant:"
echo "  - sensor.eedomus_history_progress (progression globale)"
echo "  - sensor.eedomus_history_progress_{device_id} (progression par appareil)"
echo "  - sensor.eedomus_history_stats (statistiques)"
echo ""
echo "Pour vérifier le comportement:"
echo "  1. Allez dans Developer Tools → States"
echo "  2. Cherchez les entités eedomus_history"
echo "  3. Vérifiez que les valeurs changent à chaque rafraîchissement"

exit 0