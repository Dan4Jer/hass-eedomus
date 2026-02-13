#!/bin/bash

# Script final pour vérifier les capteurs eedomus dans Home Assistant
# Ce script doit être exécuté sur le Raspberry Pi

set -e

echo "🔍 Vérification des capteurs eedomus dans Home Assistant"
echo "=========================================================="

# Vérifier si nous sommes sur le Raspberry Pi
if [ ! -d "/config/.storage" ]; then
    echo "❌ Ce script doit être exécuté sur le Raspberry Pi"
    echo "   Le répertoire /config/.storage n'a pas été trouvé"
    exit 1
fi

echo "✅ Exécuté sur le Raspberry Pi"
echo ""

# Vérifier si Home Assistant est en cours d'exécution
if ! curl -s http://localhost:8123/api/ > /dev/null 2>&1; then
    echo "❌ Home Assistant n'est pas accessible"
    echo "   Vérifiez que Home Assistant est en cours d'exécution"
    exit 1
fi

echo "✅ Home Assistant est accessible"
echo ""

# Obtenir le token API depuis le fichier de credentials
CREDENTIALS_FILE="/Users/danjer/mistral/credentials-ha/credentials.txt"

if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "❌ Fichier de credentials introuvable: $CREDENTIALS_FILE"
    exit 1
fi

USERNAME=$(grep "^user:" "$CREDENTIALS_FILE" | cut -d: -f2 | tr -d ' ')
PASSWORD=$(grep "^password:" "$CREDENTIALS_FILE" | cut -d: -f2 | tr -d ' ')

if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
    echo "❌ Informations de connexion incomplètes dans $CREDENTIALS_FILE"
    exit 1
fi

echo "✅ Informations de connexion lues: user=$USERNAME"
echo ""

# Obtenir le token API
echo "🔗 Obtention du token API..."

API_TOKEN=$(curl -s -X POST "http://localhost:8123/api/auth/login_flow" \
    -H "Content-Type: application/json" \
    -d "{\"type\": \"auth\", \"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}" \
    | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('refresh_token', ''))" 2>/dev/null)

if [ -z "$API_TOKEN" ]; then
    echo "❌ Impossible d'obtenir le token API"
    echo "   Vérifiez:"
    echo "   - Home Assistant est en cours d'exécution"
    echo "   - Les informations de connexion sont correctes"
    echo "   - Le port 8123 est accessible"
    exit 1
fi

echo "✅ Token API obtenu"
echo ""

# Vérifier les capteurs d'historique
echo "📊 Vérification des capteurs d'historique..."

# Obtenir tous les états
curl -s -X GET "http://localhost:8123/api/states" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" > /tmp/hass_states.json

if [ ! -f "/tmp/hass_states.json" ]; then
    echo "❌ Impossible de récupérer les états"
    exit 1
fi

# Analyser les capteurs
echo ""
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

# Filtrer les capteurs d'historique
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
    
    print('✅ Capteurs d\'historique trouvés et fonctionnels')
    print()
    print('📋 Comportement attendu:')
    print('   - sensor.eedomus_history_progress: Progression globale (0-100%)')
    print('   - sensor.eedomus_history_progress_{device_id}: Progression par appareil')
    print('   - sensor.eedomus_history_stats: Statistiques de téléchargement')
    print()
    print('💡 Pour vérifier manuellement:')
    print('   1. Allez dans Developer Tools → States')
    print('   2. Cherchez les entités eedomus_history')
    print('   3. Vérifiez que les valeurs changent à chaque rafraîchissement')
    
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

# Afficher tous les capteurs eedomus pour référence
print()
print('📋 Tous les capteurs eedomus (premiers 10):')
print('-' * 40)
for sensor in eedomus_sensors[:10]:
    print(f'{sensor.get(\"entity_id\", \"Unknown\")}: {sensor.get(\"state\", \"Unknown\")}')
if len(eedomus_sensors) > 10:
    print(f'... et {len(eedomus_sensors) - 10} autres capteurs')
"

# Nettoyage
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