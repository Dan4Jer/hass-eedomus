#!/bin/bash
# Standardized deployment script for hass-eedomus
# Enforces git-based deployment with log streaming
# Part of the hass-eedomus-deploy skill

set -e

echo "🚀 Hass-Eedomus Deployment"
echo "=========================="
echo ""

# Configuration
REMOTE_IP="${REMOTE_IP}"
REMOTE_PATH="${REMOTE_PATH}"
BRANCH="unstable"
LOG_FILE="~/mistral/rasp.log"

# Validate environment configuration
if [ ! -f .env ]; then
    echo "❌ Error: Environment file not found at .env"
    echo "   Please create it from .env.example with your configuration"
    exit 1
fi

source .env

# Pre-deployment checks
echo "🔍 Running pre-deployment checks..."

# Check local git status
cd ${LOCAL_REPO_PATH}
echo "  - Local git status:"
git status --short 2>/dev/null || true

# 🚨 MANDATORY: Check for uncommitted changes
echo ""
echo "🔒 Git-Only Deployment Check:"
UNCOMMITTED=$(git status --porcelain 2>/dev/null | grep -v "^??" | wc -l)
if [ "$UNCOMMITTED" -gt 0 ]; then
    echo "❌ ERROR: You have uncommitted changes!"
    echo ""
    echo "   All modifications MUST be committed to git before deployment."
    echo "   This is a MANDATORY requirement - direct file modifications are FORBIDDEN."
    echo ""
    echo "   To fix:"
    echo "     1. git add ."
    echo "     2. git commit -m 'Your message'"
    echo "     3. git push origin unstable"
    echo "     4. Then run this deployment script again"
    echo ""
    echo "   Current uncommitted changes:"
    git status --short 2>/dev/null | grep -v "^??"
    exit 1
fi

# Check for untracked files (warning only, not blocking)
UNTRACTED=$(git status --porcelain 2>/dev/null | grep "^??" | wc -l)
if [ "$UNTRACTED" -gt 0 ]; then
    echo "⚠️  Warning: You have $UNTRACTED untracked files."
    echo "   These will not be deployed. Add them to git if they should be included."
    git status --short 2>/dev/null | grep "^??"
fi

# Check current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo "⚠️  Warning: Current branch is $CURRENT_BRANCH, expected $BRANCH"
    read -p "Continue with current branch? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get version from pyproject.toml
VERSION=$(grep "version" ${LOCAL_REPO_PATH}/pyproject.toml | head -1 | cut -d'"' -f2)
echo "  - Deploying version: $VERSION"

# Deployment
echo ""
echo "📦 Deploying to Raspberry Pi..."
start_time=$(date +%s)

# Git operations on remote (using sudo as the directory is owned by root)
ssh $REMOTE_IP "
    sudo git config --global --add safe.directory $REMOTE_PATH && \
    cd $REMOTE_PATH && \
    sudo git fetch && \
    sudo git checkout $BRANCH && \
    sudo git pull origin $BRANCH && \
    echo \"✅ Git operations completed\"
"

# Restart Home Assistant in background
ssh $REMOTE_IP "nohup sudo -i ha core restart > /dev/null 2>&1 &"

end_time=$(date +%s)
duration=$((end_time - start_time))

echo ""
echo "✅ Deployment completed in ${duration}s"
echo ""
echo "📋 Post-Deployment Actions:"
echo "  1. Wait 30-60s for Home Assistant to restart"
echo "  2. Check logs: tail -n 50 $LOG_FILE"
echo "  3. Verify: ssh $REMOTE_IP 'ha core info'"
echo ""
echo "🔄 To stream logs: ./get_rasp_logs.sh"
