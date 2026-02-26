#!/bin/bash

# Script to check if the history option is properly set
# This script should be run on the Raspberry Pi

set -e

echo "🔍 Checking history option status..."
echo "===================================="

# Check if we're on the Raspberry Pi
if [ ! -d "/config/.storage" ]; then
    echo "❌ This script must be run on the Raspberry Pi"
    echo "   Current directory: $(pwd)"
    exit 1
fi

# Find the eedomus storage file
STORAGE_FILE=$(find /config/.storage -name "*eedomus*" -type f 2>/dev/null | head -1)

if [ -z "$STORAGE_FILE" ]; then
    echo "❌ No eedomus storage file found"
    echo "   Available files in /config/.storage:"
    ls -la /config/.storage/ | head -20
    exit 1
fi

echo "✅ Found storage file: $STORAGE_FILE"
echo ""

# Check if the file contains history option
if grep -q '"history"' "$STORAGE_FILE"; then
    echo "✅ History option found in storage file"
    
    # Check if it's enabled
    if grep -q '"history": true' "$STORAGE_FILE"; then
        echo "✅ History option is ENABLED (true)"
    else
        echo "❌ History option is DISABLED (false)"
    fi
    
    # Show the relevant section
    echo ""
    echo "📄 Relevant section from storage file:"
    echo "--------------------------------------"
    python3 -c "
import json
with open('$STORAGE_FILE') as f:
    data = json.load(f)
    if 'options' in data:
        opts = data['options']
        print('Options found:')
        for key, value in opts.items():
            if 'history' in key.lower() or 'api' in key.lower():
                print(f'  {key}: {value}')
    elif 'data' in data:
        opts = data['data']
        print('Data found:')
        for key, value in opts.items():
            if 'history' in key.lower() or 'api' in key.lower():
                print(f'  {key}: {value}')
"
else
    echo "❌ History option NOT found in storage file"
    echo "   This means the option was never saved or was removed"
fi

echo ""
echo "💡 Next steps:"
echo "   1. If history is disabled, enable it in the UI"
echo "   2. Check if API Eedomus mode is enabled (required for history)"
echo "   3. Restart Home Assistant after making changes"
