#!/bin/bash

# Eedomus Dynamic Configuration Panel - Git Commit Script
# 
# This script commits the dynamic device configuration panel implementation
# with proper commit message and structure.

echo "🚀 Starting Eedomus Dynamic Configuration Panel commit process..."

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository. Please run this script from the root of your git repository."
    exit 1
fi

# Check current branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD)
echo "📋 Current branch: $CURRENT_BRANCH"

# Check for uncommitted changes
if [[ -z $(git status --porcelain) ]]; then
    echo "⚠️  No changes to commit. All files are up to date."
    exit 0
fi

# Show what will be committed
echo "📝 Changes to be committed:"
git status --short

echo ""
echo "📋 Preparing commit..."

# Create a detailed commit message
COMMIT_MESSAGE="Add dynamic device configuration panel with modern Lovelace card

This commit implements a comprehensive system for configuring which
eedomus devices should be treated as dynamic (requiring frequent updates)
and includes a modern Lovelace card for user-friendly configuration.

Key Features:
- Configurable dynamic properties by entity type (light, switch, sensor, etc.)
- Specific device overrides by periph_id for fine-grained control
- Modern Lovelace card compatible with Home Assistant 2026.1+
- Opportunistic refresh mechanisms for optimized API usage
- Comprehensive documentation with best practices and FAQ

Dynamic devices are defined as those whose state can change
unpredictably due to user actions (e.g., buttons, switches, motion
detectors) and are included in optimized refresh cycles.

Files Changed:
- Backend: config_panel.py, device_mapping.py, coordinator.py
- Frontend: lovelace/config_panel_card.py, lovelace/config_panel.js
- Configuration: device_mapping.yaml, custom_mapping.yaml
- Documentation: lovelace/README.md with complete usage guide
- Tools: scripts/copy_static_files.py for static file management

The implementation uses a priority system:
1. Specific device overrides (highest priority)
2. Explicit is_dynamic properties
3. Entity type properties
4. Fallback to default behavior

This provides users with full control over device refresh behavior
while maintaining optimal performance through opportunistic refresh
mechanisms that minimize API calls while ensuring responsive updates
for critical devices.

