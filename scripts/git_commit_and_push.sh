#!/bin/bash

# Eedomus Dynamic Configuration Panel - Complete Git Workflow
# 
# This script performs the complete git workflow: commit + push

echo "🚀 Starting Eedomus Dynamic Configuration Panel git workflow..."
echo "=============================================================="

# Run the commit script
if [[ -f "$(dirname "$0")/git_commit_dynamic_config.sh" ]]; then
    echo "📝 Step 1: Running commit script..."
    if bash "$(dirname "$0")/git_commit_dynamic_config.sh"; then
        echo "✅ Commit completed successfully!"
        echo ""
        
        # Run the push script
        echo "📤 Step 2: Running push script..."
        if bash "$(dirname "$0")/git_push_changes.sh"; then
            echo "✅ Push completed successfully!"
            echo ""
            echo "🎉 Complete! Your changes have been committed and pushed."
            exit 0
        else
            echo "❌ Push failed. Please check the error messages above."
            exit 1
        fi
    else
        echo "❌ Commit failed. Please check the error messages above."
        exit 1
    fi
else
    echo "❌ Commit script not found. Please run from the correct directory."
    exit 1
fi