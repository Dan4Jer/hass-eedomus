#!/bin/bash
# Deployment script with automatic validation
# Part of the hass-eedomus-deploy skill

# Source the deployment script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/deploy_hass_eedomus.sh"

# Wait for restart (adjust as needed)
echo ""
echo "⏳ Waiting for Home Assistant to restart..."
for i in {1..12}; do
    sleep 5
    STATUS=$(ssh ${REMOTE_IP} "ha core info" 2>&1 | grep -i "home assistant" | head -1 || echo "")
    if echo "$STATUS" | grep -qi "running\|started\|2026"; then
        echo "✅ Home Assistant is running"
        break
    fi
    echo "  Waiting... ($i/12)"
done

# Validate deployment
echo ""
echo "🔍 Validating deployment..."
VALID=$(ssh ${REMOTE_IP} "ha core logs | grep -i 'eedomus integration loaded\|Setup of eedomus integration' | tail -1" || echo "")

if [ -z "$VALID" ]; then
    echo "❌ Deployment validation failed"
    echo "   Check logs for errors:"
    ssh ${REMOTE_IP} "ha core logs | grep -i eedomus | tail -20" || true
    exit 1
else
    echo "✅ Deployment validated successfully"
    echo "   $VALID"
    exit 0
fi
