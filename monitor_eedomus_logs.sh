#!/bin/bash

echo "🔍 Surveillance des logs eedomus en temps réel..."
echo "Appuyez sur Ctrl+C pour arrêter"
echo ""

# Surveiller les logs et filtrer les messages eedomus
tail -f /Users/danjer/rasp.log | while read line; do
    if echo "$line" | grep -qiE "(history|eedomus|virtual sensor|Performing partial refresh|Eedomus integration|Starting eedomus)"; then
        echo "$line"
    fi
done