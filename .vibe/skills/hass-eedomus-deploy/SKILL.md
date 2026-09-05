---
name: hass-eedomus-deploy
description: Load when deploying hass-eedomus integration to Raspberry Pi or managing remote logs. This skill standardizes deployment via git and provides SSH log streaming for Home Assistant custom component development.
user-invocable: true
license: MIT
metadata:
  display-name: "Hass-Eedomus Deployment Manager"
  short-description: "Standardized git-based deployment with SSH log streaming for Raspberry Pi"
---

# Hass-Eedomus Deployment Manager

## When to Load

Load this skill when you need to:
- Deploy the hass-eedomus integration to a Raspberry Pi running Home Assistant
- Follow deployment best practices (git-based only)
- Stream Home Assistant logs from remote Raspberry Pi to local terminal
- Validate deployment success and troubleshoot issues
- Manage version rollbacks and branch switching

## Overview

This skill provides **standardized deployment procedures** for the hass-eedomus Home Assistant custom component, enforcing:

1. **Git-Only Deployments**: All deployments MUST use git (no manual file copies)
2. **SSH Log Streaming**: Real-time log following via SSH pipe
3. **Version Control**: Proper branch management and version tracking
4. **Safety Checks**: Pre-deployment validation and post-deployment verification

## Architecture Context

**Target Environment:**
- Remote: Raspberry Pi running Home Assistant (IP: ${REMOTE_IP})
- Local: Development machine at ${LOCAL_REPO_PATH}
- Deployment path on Raspberry Pi: ${REMOTE_PATH}/

**Repository:**
- Main repository: https://github.com/Dan4Jer/hass-eedomus
- Branches: main (stable), unstable (development)
- Current version: 0.14.3 (from pyproject.toml)

## Quick Start

### Standard Deployment to Raspberry Pi

**Prerequisites:**
- SSH access configured with `.env` containing connection parameters
- Git repository cloned on both local and remote machines
- Home Assistant installed on Raspberry Pi

**Deployment Command (Git-Based Only):**
```bash
# 1. Ensure you're on the correct branch locally
cd ${LOCAL_REPO_PATH}
git checkout unstable

# 2. Push changes to remote (if needed)
git push origin unstable

# 3. Connect to Raspberry Pi and deploy
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && \
    git fetch && \
    git checkout unstable && \
    git pull origin unstable"

# 4. Restart Home Assistant (background)
ssh ${REMOTE_IP} "nohup ha core restart > /dev/null 2>&1 &"
```

### SSH Log Streaming

**Method 1: Direct SSH (basique)**
```bash
# Stream all Home Assistant logs
ssh ${REMOTE_IP} "ha core logs --follow"

# Stream with filter
ssh ${REMOTE_IP} "ha core logs --follow | grep -i eedomus"

# Save to file
ssh ${REMOTE_IP} "ha core logs --follow" | tee hass-eedomus.log
```

**Method 2: Using `get_rasp_logs.sh` (simple)**
```bash
# Stream all logs
./get_rasp_logs.sh

# With arguments passed to ha core logs
./get_rasp_logs.sh --follow
./get_rasp_logs.sh --last 50
```

**Method 3: Using `watch_logs.sh` (recommandé - avec couleurs et filtres)**
```bash
# Suivre tous les logs avec coloration syntaxique
./watch_logs.sh

# Suivre uniquement les logs eedomus
./watch_logs.sh -e

# Suivre uniquement les erreurs
./watch_logs.sh -E

# Suivre uniquement les erreurs eedomus
./watch_logs.sh -E -e

# Suivre uniquement les warnings
./watch_logs.sh -W

# Afficher les dernières 100 lignes (sans follow)
./watch_logs.sh --tail 100

# Sauvegarder dans un fichier tout en affichant
./watch_logs.sh --save ~/hass-logs.txt

# Désactiver les couleurs
./watch_logs.sh --no-color -e
```

**Options du script `watch_logs.sh` :**
| Option | Description |
|--------|-------------|
| `-e, --eedomus` | Filtrer pour eedomus seulement |
| `-E, --errors` | Afficher uniquement les erreurs |
| `-W, --warnings` | Afficher uniquement les warnings |
| `-d, --debug` | Afficher uniquement les debug |
| `-i, --info` | Afficher uniquement les infos |
| `--no-color` | Désactiver la coloration |
| `--save FILE` | Sauvegarder dans un fichier |
| `--tail N` | Afficher les N dernières lignes |
| `-h, --help` | Afficher l'aide |

**Coloration automatique :**
- **Rouge** : ERROR, exceptions
- **Jaune** : WARNING
- **Bleu** : Info
- **Magenta** : Debug
- **Vert** : eedomus

**Stop Log Streaming:** Press `Ctrl+C`

### One-Command Deployment Script (Replaces deploy_on_rasp.sh)

Create a new deployment script at `${LOCAL_BASE_PATH}deploy_hass_eedomus.sh`:

```bash
#!/bin/bash
# Standardized deployment script for hass-eedomus
# Enforces git-based deployment with log streaming

set -e

echo "🚀 Hass-Eedomus Deployment"
echo "=========================="
echo ""

# Configuration
REMOTE_IP="${REMOTE_IP}"
REMOTE_PATH="${REMOTE_PATH}"
BRANCH="unstable"
LOG_FILE="~/mistral/rasp.log"

# Validate SSH environment
if [ ! -f .env ]; then
    echo "❌ Error: environment file not found at .env"
    echo "   Please create it with your SSH connection parameters"
    exit 1
fi

source .env

# Pre-deployment checks
echo "🔍 Running pre-deployment checks..."

# Check local git status
echo "  - Local git status:"
cd ${LOCAL_REPO_PATH}
git status --short

# Check current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
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

# Git operations on remote
ssh $REMOTE_IP "
    cd $REMOTE_PATH && \
    git fetch && \
    git checkout $BRANCH && \
    git pull origin $BRANCH && \
    echo "✅ Git operations completed"
"

# Restart Home Assistant in background
ssh $REMOTE_IP "nohup ha core restart > /dev/null 2>&1 &"

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
echo "🔄 To stream logs: ssh $REMOTE_IP 'ha core logs --follow'"
echo "   Or use: ./get_rasp_logs.sh"
```

Make it executable:
```bash
chmod +x ${LOCAL_BASE_PATH}deploy_hass_eedomus.sh
```

### Log Retrieval Script (Replaces get_rasp_log.sh)

Create a new log retrieval script at `${LOCAL_BASE_PATH}get_rasp_logs.sh`:

```bash
#!/bin/bash
# Standardized log retrieval for hass-eedomus
# Provides SSH log streaming with local display

# Configuration
REMOTE_IP="${REMOTE_IP}"
LOG_FILE="~/mistral/rasp.log"

# Source SSH environment
if [ -f .env ]; then
    source .env
fi

# Check if arguments provided
if [ $# -gt 0 ]; then
    # Pass all arguments to ha core logs
    ssh $REMOTE_IP "ha core logs $@"
else
    # Default: follow logs
    ssh $REMOTE_IP "ha core logs --follow"
fi
```

Make it executable:
```bash
chmod +x ${LOCAL_BASE_PATH}get_rasp_logs.sh
```

## Deployment Procedures

### 1. Standard Deployment Workflow

**Step 1: Local Development**
```bash
cd ${LOCAL_REPO_PATH}
# Make your changes, commit them
.git commit -am "Fix: description of changes"
```

**Step 2: Push to Remote Repository**
```bash
git push origin unstable
```

**Step 3: Deploy to Raspberry Pi**
```bash
./deploy_hass_eedomus.sh
```

**Step 4: Monitor Logs**
```bash
# In a new terminal
./get_rasp_logs.sh

# Or with filters
./get_rasp_logs.sh | grep -i eedomus
```

**Step 5: Verify Deployment**
```bash
# Check Home Assistant status
ssh ${REMOTE_IP} "ha core info"

# Check integration status
ssh ${REMOTE_IP} "ha core logs | grep -i eedomus | tail -20"

# Check version in logs
ssh ${REMOTE_IP} "ha core logs | grep 'eedomus integration' | tail -5"
```

### 2. Branch Switching Deployment

**Deploy a Specific Branch:**
```bash
# Update the BRANCH variable in deploy_hass_eedomus.sh
# Or override in command line
BRANCH="main" ./deploy_hass_eedomus.sh
```

**Switch Branch on Raspberry Pi:**
```bash
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && \
    git fetch && \
    git checkout main && \
    git pull origin main"
```

### 3. Version Rollback

**Check Available Versions:**
```bash
# On Raspberry Pi
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && \
    git tag -l | sort -V | tail -10"
```

**Deploy Specific Version:**
```bash
VERSION="v0.14.2"
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && \
    git fetch --tags && \
    git checkout $VERSION && \
    nohup ha core restart > /dev/null 2>&1 &"
```

### 4. Emergency Rollback

If deployment fails and Home Assistant doesn't restart properly:

```bash
# Stop Home Assistant
ssh ${REMOTE_IP} "sudo systemctl stop home-assistant@homeassistant"

# Restore from backup or switch to stable branch
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && \
    git checkout main && \
    git pull origin main"

# Restart Home Assistant
ssh ${REMOTE_IP} "sudo systemctl start home-assistant@homeassistant"
```

## Monitoring and Verification

### Check Deployment Status

**Home Assistant Info:**
```bash
ssh ${REMOTE_IP} "ha core info"
```

**Integration Logs:**
```bash
# Last 100 lines of logs
ssh ${REMOTE_IP} "ha core logs | tail -100"

# Filter for eedomus only
ssh ${REMOTE_IP} "ha core logs | grep -i eedomus"
```

**Eedomus Integration Status:**
```bash
# Check if integration is loaded
ssh ${REMOTE_IP} "ha core logs | grep 'Setup of eedomus integration'"

# Check for errors
ssh ${REMOTE_IP} "ha core logs | grep -i 'error.*eedomus'"
```

### Continuous Log Monitoring

**Start Log Streaming in Background:**
```bash
# In terminal 1
./get_rasp_logs.sh > ~/mistral/rasp_stream.log &

# In terminal 2 (to watch)
tail -f ~/mistral/rasp_stream.log
```

**Stop Background Streaming:**
```bash
# Find and kill the process
ps aux | grep "get_rasp_logs.sh"
pkill -f "get_rasp_logs.sh"
```

### Health Checks

**Check Home Assistant Health:**
```bash
ssh ${REMOTE_IP} "ha core info"
```

**Check Eedomus Integration Health:**
```bash
# Count eedomus entities
ssh ${REMOTE_IP} "ha core logs | grep 'Eedomus' | grep 'entity' | wc -l"

# Check for errors in last hour
ssh ${REMOTE_IP} "ha core logs --since 1h | grep -i error | grep -i eedomus"
```

## Troubleshooting

### Common Deployment Issues

**Issue 1: SSH Connection Failed**
```bash
# Test SSH connection
ssh ${REMOTE_IP} echo "SSH working"

# If failed, check:
# 1. Is Raspberry Pi powered on?
# 2. Is network connection working?
# 3. Are SSH credentials correct in .env?
```

**Issue 2: Git Operations Failed**
```bash
# Check git status on remote
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && git status"

# Common fixes:
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && \
    git fetch --all && \
    git reset --hard origin/unstable"
```

**Issue 3: Home Assistant Won't Restart**
```bash
# Check Home Assistant service status
ssh ${REMOTE_IP} "sudo systemctl status home-assistant@homeassistant"

# Common fixes:
# Check logs for errors
ssh ${REMOTE_IP} "journalctl -u home-assistant@homeassistant -n 50"

# Restart manually
ssh ${REMOTE_IP} "sudo systemctl restart home-assistant@homeassistant"
```

**Issue 4: Integration Not Loading**
```bash
# Check for Python errors
ssh ${REMOTE_IP} "ha core logs | grep -i 'error.*import'"

# Check if custom_components directory exists
ssh ${REMOTE_IP} "ls -la ${REMOTE_COMPONENTS_PATH}"

# Check eedomus directory specifically
ssh ${REMOTE_IP} "ls -la ${REMOTE_COMPONENTS_PATH}eedomus/"
```

**Issue 5: Version Mismatch**
```bash
# Check current version on Raspberry Pi
ssh ${REMOTE_IP} "cat ${REMOTE_COMPONENTS_PATH}eedomus/pyproject.toml | grep version"

# Compare with local version
grep version ${LOCAL_REPO_PATH}/pyproject.toml
```

### Debug Mode

**Enable Debug Logging:**
```bash
# On Raspberry Pi, temporarily enable debug logging
ssh ${REMOTE_IP} "
    cd ${REMOTE_PATH} && \
    # Edit __init__.py to set logging level to DEBUG
    # Or use logger configuration
    ha core logs --level debug | grep -i eedomus
"
```

**Collect Debug Information:**
```bash
# Save comprehensive debug info
deploy_hass_eedomus.sh 2>&1 | tee deployment_debug_$(date +%Y%m%d_%H%M%S).log

# Collect system info
ssh ${REMOTE_IP} "
    echo '=== System Info ===' && \
    uname -a && \
    echo '=== Home Assistant Info ===' && \
    ha core info && \
    echo '=== Git Status ===' && \
    cd ${REMOTE_PATH} && git status && \
    echo '=== Recent Logs ===' && \
    ha core logs | tail -50
" > system_debug_$(date +%Y%m%d_%H%M%S).txt
```

## Best Practices

### ❌ NEVER Do This

1. **Manual File Copying**: Never use `scp` or `rsync` to copy files directly
   ```bash
   # BAD: Manual file copying
   scp -r custom_components/eedomus/* ${REMOTE_IP}:${REMOTE_COMPONENTS_PATH}eedomus/
   ```

2. **Direct File Editing on Raspberry Pi**: Never edit files directly on the Pi
   ```bash
   # BAD: Editing files directly on Pi
   ssh ${REMOTE_IP} "nano ${REMOTE_COMPONENTS_PATH}eedomus/some_file.py"
   ```

3. **Hard Resets**: Never reset git repository on Raspberry Pi without backup
   ```bash
   # BAD: Hard reset without backup
   ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && git reset --hard"
   ```

### ✅ ALWAYS Do This

1. **Use Git for All Changes**: All deployments must go through git
   ```bash
   # GOOD: Git-based deployment
   git add .
   git commit -m "Fix: description"
   git push
   ./deploy_hass_eedomus.sh
   ```

2. **Backup Before Major Changes**: Always create a backup branch
   ```bash
   # Create backup branch
   git checkout -b backup-$(date +%Y%m%d-%H%M%S)
   git push origin backup-$(date +%Y%m%d-%H%M%S)
   ```

3. **Test Locally First**: Test changes in development before deploying
   ```bash
   # Test syntax
   python3 -m py_compile custom_components/eedomus/*.py
   
   # Run local tests
   python3 -m pytest tests/ -v
   ```

4. **Monitor After Deployment**: Always check logs after deployment
   ```bash
   # Check deployment succeeded
   ./get_rasp_logs.sh | grep -i "setup.*eedomus"
   ```

## Security Considerations

### SSH Security
- Use SSH keys instead of passwords when possible
- Store SSH credentials in `.env` with restricted permissions:
  ```bash
  chmod 600 .env
  ```
- Use `sudo` sparingly; prefer running Home Assistant as a dedicated user

### Git Security
- Never commit sensitive information (API keys, passwords) to git
- Use `.gitignore` to exclude sensitive files:
  ```
  *.secret
  *.key
  !.gitignore
  ```

### Home Assistant Security
- Restart Home Assistant gracefully when possible
- Avoid killing processes directly
- Use `ha core restart` instead of `systemctl kill`

## Version Management

### Version Tracking

**Current Version Sources:**
- `pyproject.toml`: Primary version source (0.14.3)
- `manifest.json`: Integration version for Home Assistant
- Git tags: Release versions (v0.14.2, etc.)

**Version Update Procedure:**
1. Update version in `pyproject.toml`
2. Update version in `manifest.json`
3. Create git tag: `git tag -a v0.14.3 -m "Release v0.14.3"`
4. Push tag: `git push origin v0.14.3`
5. Create GitHub release

### Branch Management

**Branches:**
- `main`: Stable releases only
- `unstable`: Development branch
- `fix/*`: Hotfix branches
- `feat/*`: Feature branches

**Merge Strategy:**
- Feature branches → unstable
- Hotfix branches → main (and unstable)
- unstable → main (for releases)

## Automation (Optional)

### Automated Deployment with Validation

Create a deployment validation script:

```bash
#!/bin/bash
# deploy_and_validate.sh

./deploy_hass_eedomus.sh

# Wait for restart
sleep 60

# Validate deployment
VALID=$(ssh ${REMOTE_IP} "ha core logs | grep -i 'eedomus integration loaded' | tail -1")

if [ -z "$VALID" ]; then
    echo "❌ Deployment validation failed"
    echo "   Check logs for errors"
    exit 1
else
    echo "✅ Deployment validated successfully"
    exit 0
fi
```

## References

### Files Replaced
- **deploy_on_rasp.sh**: Replaced by `deploy_hass_eedomus.sh` (this skill)
- **get_rasp_log.sh**: Replaced by `get_rasp_logs.sh` (this skill)

### Related Documentation
- [Home Assistant Custom Component Development](https://developers.home-assistant.io/docs/development_components/)
- [Git Best Practices](https://git-scm.com/book/en/v2/Distributed-Git-Distributed-Workflows)
- [SSH Configuration](https://www.ssh.com/academy/ssh/sshd_config)

### Contacts
- Repository: https://github.com/Dan4Jer/hass-eedomus
- Issues: https://github.com/Dan4Jer/hass-eedomus/issues

---

**Last Updated**: 2026-09-05
**Version**: 1.0.0
**Skill Author**: Mistral Vibe (for Dan4Jer/hass-eedomus)
