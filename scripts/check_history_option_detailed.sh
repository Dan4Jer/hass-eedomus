#!/bin/bash

echo "=== Checking History Option State ==="
echo ""

# Find the config entry storage file
STORAGE_DIR="config/.storage"
CONFIG_ENTRY_FILE="core.config_entries"

if [ -d "$STORAGE_DIR" ]; then
    echo "📁 Storage directory found: $STORAGE_DIR"
    
    if [ -f "$STORAGE_DIR/$CONFIG_ENTRY_FILE" ]; then
        echo "📄 Config entries file found: $STORAGE_DIR/$CONFIG_ENTRY_FILE"
        
        # Extract eedomus config entry
        echo ""
        echo "🔍 Extracting eedomus config entry..."
        python3 -c "
import json
with open('$STORAGE_DIR/$CONFIG_ENTRY_FILE', 'r') as f:
    data = json.load(f)
    
# Find eedomus entries
eedomus_entries = [entry for entry in data.get('data', {}).get('entries', []) if entry.get('domain') == 'eedomus']

if eedomus_entries:
    for entry in eedomus_entries:
        print('Config Entry ID:', entry.get('entry_id'))
        print('Data:', json.dumps(entry.get('data', {}), indent=2))
        print('Options:', json.dumps(entry.get('options', {}), indent=2))
        print('')
else:
    print('No eedomus config entries found')
        "
    else
        echo "❌ Config entries file not found"
    fi
else
    echo "❌ Storage directory not found"
fi

echo ""
echo "=== Checking if history option is properly set ==="
echo ""

# Check if the activate_history_feature.sh script exists and run it
if [ -f "scripts/activate_history_feature.sh" ]; then
    echo "✅ Found activate_history_feature.sh script"
    echo "Running script to check current state..."
    bash scripts/activate_history_feature.sh check
else
    echo "❌ activate_history_feature.sh script not found"
fi

echo ""
echo "=== Done ==="