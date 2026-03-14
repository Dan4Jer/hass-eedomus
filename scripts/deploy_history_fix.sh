#!/bin/bash

# Deployment script for history option fix
# This script helps deploy the fix to the Raspberry Pi

set -e

echo "🚀 Deploying History Option Fix to Raspberry Pi"
echo "=============================================="

# Check if we're on the Raspberry Pi
if [ ! -d "/config/.storage" ]; then
    echo "ℹ️  Not on Raspberry Pi - copying files to remote"
    
    # Ask for SSH details
    read -p "Enter Raspberry Pi SSH address (e.g., pi@raspberrypi.local): " SSH_ADDRESS
    read -s -p "Enter SSH password: " SSH_PASSWORD
    echo ""
    
    # Copy files to Raspberry Pi
    echo "📤 Copying files to Raspberry Pi..."
    sshpass -p "$SSH_PASSWORD" scp -r custom_components/eedomus/ "$SSH_ADDRESS":~/hass-eedomus/
    sshpass -p "$SSH_PASSWORD" scp scripts/*.sh "$SSH_ADDRESS":~/hass-eedomus/scripts/
    
    echo "✅ Files copied successfully"
    
    # Execute remote commands
    echo "🔧 Running deployment commands on Raspberry Pi..."
    sshpass -p "$SSH_PASSWORD" ssh "$SSH_ADDRESS" << 'EOF'
        cd ~/hass-eedomus
        
        # Check if history option is set
        echo "🔍 Checking current history option status..."
        if [ -f "/config/.storage/core.config_entries" ]; then
            if grep -q '"history": true' "/config/.storage/core.config_entries"; then
                echo "✅ History option is already enabled in storage"
            else
                echo "❌ History option is not enabled in storage"
                echo "   You may need to enable it manually in the UI or use activate_history_feature.sh"
            fi
        else
            echo "⚠️  Cannot check storage - file not found"
        fi
        
        # Restart Home Assistant
        echo "🔄 Restarting Home Assistant to apply changes..."
        ha core restart
        
        echo "✅ Deployment complete!"
        echo "   Monitor logs with: tail -f ~/mistral/rasp.log | grep -E '(history|Virtual|Fetching)'"
EOF
    
    exit 0
fi

# If we're on the Raspberry Pi
echo "✅ Running on Raspberry Pi - executing local commands"

# Check if history option is set
echo "🔍 Checking current history option status..."
if [ -f "/config/.storage/core.config_entries" ]; then
    if grep -q '"history": true' "/config/.storage/core.config_entries"; then
        echo "✅ History option is already enabled in storage"
    else
        echo "❌ History option is not enabled in storage"
        echo "   You may need to enable it manually in the UI or use activate_history_feature.sh"
    fi
else
    echo "⚠️  Cannot check storage - file not found"
fi

# Restart Home Assistant
echo "🔄 Restarting Home Assistant to apply changes..."
ha core restart

echo "✅ Deployment complete!"
echo "   Monitor logs with: tail -f ~/mistral/rasp.log | grep -E '(history|Virtual|Fetching)'"