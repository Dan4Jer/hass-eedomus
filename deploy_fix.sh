#!/bin/bash

# Deployment script for device mapping fix
# This script deploys the YAML merging improvement to the Raspberry Pi

set -e

echo "🚀 Deploying Device Mapping Fix to Raspberry Pi"
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
    
    echo "✅ Files copied successfully"
    
    # Execute remote commands
    echo "🔧 Running deployment commands on Raspberry Pi..."
    sshpass -p "$SSH_PASSWORD" ssh "$SSH_ADDRESS" << 'EOF'
        cd ~/hass-eedomus
        
        # Check current status
        echo "🔍 Checking current deployment status..."
        if [ -f "custom_components/eedomus/__init__.py" ]; then
            echo "✅ eedomus component found"
            
            # Check if our fix is present
            if grep -q "merge_yaml_mappings" "custom_components/eedomus/__init__.py"; then
                echo "✅ Device mapping fix is already deployed"
            else
                echo "❌ Device mapping fix not found - deploying now"
            fi
        else
            echo "❌ eedomus component not found"
        fi
        
        # Restart Home Assistant
        echo "🔄 Restarting Home Assistant to apply changes..."
        ha core restart
        
        echo "✅ Deployment complete!"
        echo "   Monitor logs with: tail -f ~/mistral/rasp.log | grep -E '(mapping|YAML|merge)'"
EOF
    
    exit 0
fi

# If we're on the Raspberry Pi
echo "✅ Running on Raspberry Pi - executing local commands"

# Check current status
echo "🔍 Checking current deployment status..."
if [ -f "custom_components/eedomus/__init__.py" ]; then
    echo "✅ eedomus component found"
    
    # Check if our fix is present
    if grep -q "merge_yaml_mappings" "custom_components/eedomus/__init__.py"; then
        echo "✅ Device mapping fix is already deployed"
    else
        echo "❌ Device mapping fix not found - deploying now"
    fi
else
    echo "❌ eedomus component not found"
fi

# Restart Home Assistant
echo "🔄 Restarting Home Assistant to apply changes..."
ha core restart

echo "✅ Deployment complete!"
echo "   Monitor logs with: tail -f ~/mistral/rasp.log | grep -E '(mapping|YAML|merge)'"
