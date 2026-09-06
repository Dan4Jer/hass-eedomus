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

**SSH Log Bridge:**
- Background process that maintains persistent SSH connection
- Streams Home Assistant logs in real-time
- Saves logs locally to ${LOG_FILE} (default: ~/mistral/rasp.log)
- Automatic log rotation at 100MB with 5 file retention
- PID file tracking for process management

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

### SSH Log Bridge (Persistent Background Process)

**New in this version**: The `get_rasp_logs.sh` script now supports running as a persistent background process that continuously streams logs from the Raspberry Pi and saves them locally.

**Features:**
- ✅ Background execution (runs as a daemon)
- ✅ Automatic log file management
- ✅ Log rotation at configurable size (default: 100MB)
- ✅ Retains multiple log files (default: 5)
- ✅ PID file tracking for process control
- ✅ Automatic HA command detection (ha vs sudo -i ha)

**Configuration:**
```bash
# Environment variables (can be set in .env)
LOG_DIR=${LOG_DIR:-$HOME/mistral}           # Log directory
LOG_FILE=${LOG_FILE:-$LOG_DIR/rasp.log}    # Main log file
PID_FILE=${PID_FILE:-$LOG_DIR/rasp_logs.pid}  # Process ID file
MAX_LOG_SIZE_MB=100                        # Rotate at 100MB
MAX_LOG_FILES=5                           # Keep 5 rotated files
```

**Usage:**
```bash
# Start the log bridge (background)
./get_rasp_logs.sh start

# Check bridge status
./get_rasp_logs.sh status

# View current logs
./get_rasp_logs.sh tail     # Last 50 lines
./get_rasp_logs.sh tail 100 # Last 100 lines
./get_rasp_logs.sh logs     # Last 100 lines (alias)

# Follow logs in real-time
./get_rasp_logs.sh follow

# Stop the log bridge
./get_rasp_logs.sh stop

# Restart the log bridge
./get_rasp_logs.sh restart

# Clean old log files
./get_rasp_logs.sh clean
```

**Example Status Output:**
```
📊 SSH Log Bridge Status
======================
✅ Status: RUNNING
   PID: 12345
   Log file: /Users/danjer/mistral/rasp.log
   Started: Sat Sep  5 14:51:30 2026
   Log size: 8MB
   Last modified: 2026-09-05 14:51:30

📝 To view logs: tail -f /Users/danjer/mistral/rasp.log
🛑 To stop: ./get_rasp_logs.sh stop
```

**Automatic Log Rotation:**
When the log file reaches MAX_LOG_SIZE_MB (default 100MB), it is automatically rotated:
- Current log → rasp.log.0.log
- Old logs are renamed (rasp.log.0.log → rasp.log.1.log, etc.)
- Logs older than MAX_LOG_FILES are compressed with gzip
- Compressed logs: rasp.log.1.log.gz, rasp.log.2.log.gz, etc.

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

The `get_rasp_logs.sh` script has been **completely rewritten** to support background operation as an SSH log bridge. See the **SSH Log Bridge** section above for full documentation.

**Legacy Mode:** The script still supports backward compatibility - any arguments passed will be forwarded to `ha core logs` on the remote server.

```bash
# Legacy usage (direct SSH streaming to terminal)
./get_rasp_logs.sh --follow
./get_rasp_logs.sh -n 50
./get_rasp_logs.sh | grep -i eedomus
```

**New Bridge Mode (Recommended):**
```bash
# Start background bridge
./get_rasp_logs.sh start

# Then use bridge commands
./get_rasp_logs.sh status
./get_rasp_logs.sh tail 50
./get_rasp_logs.sh follow
./get_rasp_logs.sh stop
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

## 🚨 MANDATORY: Git-Only Deployment Policy

**⚠️ IMPERATIVE: ALL MODIFICATIONS MUST GO THROUGH GIT**

This is a **non-negotiable requirement** for this project. Direct file modifications on the Raspberry Pi will cause:
- ❌ Version control loss
- ❌ Inability to rollback
- ❌ Conflicts during deployments
- ❌ Unrecoverable errors
- ❌ **VOIDED SUPPORT**

---

## Best Practices

### ❌❌❌ STRICTLY FORBIDDEN ❌❌❌

1. **❌ Manual File Copying**: NEVER use `scp` or `rsync` to copy files directly
   ```bash
   # ❌❌❌ FORBIDDEN: Manual file copying
   scp -r custom_components/eedomus/* ${REMOTE_IP}:${REMOTE_COMPONENTS_PATH}eedomus/
   ```

2. **❌ Direct File Editing on Raspberry Pi**: NEVER edit files directly on the Pi
   ```bash
   # ❌❌❌ FORBIDDEN: Editing files directly on Pi
   ssh ${REMOTE_IP} "nano ${REMOTE_COMPONENTS_PATH}eedomus/some_file.py"
   ssh ${REMOTE_IP} "vim ${REMOTE_COMPONENTS_PATH}eedomus/some_file.py"
   ssh ${REMOTE_IP} "sed -i 's/.../.../' ${REMOTE_COMPONENTS_PATH}eedomus/some_file.py"
   ```

3. **❌ Manual Git Operations on Raspberry Pi**: NEVER run git commands manually on Pi
   ```bash
   # ❌❌❌ FORBIDDEN: Manual git operations on Raspberry Pi
   ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && git pull"
   ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && git commit"
   ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && git reset --hard"
   ```

### ✅✅✅ ONLY ALLOWED METHOD ✅✅✅

**Use the standardized deployment scripts ONLY:**

```bash
# ✅✅✅ CORRECT: Use deployment scripts
cd ${LOCAL_REPO_PATH}

# 1. Make your changes locally
# ... edit files ...

# 2. Commit to git
git add .
git commit -m "Fix: description of changes"
git push origin unstable

# 3. Deploy using the script (ONLY method)
cd .vibe/skills/hass-eedomus-deploy
./deploy_hass_eedomus.sh

# 4. Monitor logs
./get_rasp_logs.sh status
./get_rasp_logs.sh tail 20
```

---

### 🔒 Enforcement Rules

1. **All code changes** MUST be committed to git before deployment
2. **All deployments** MUST use `deploy_hass_eedomus.sh` script
3. **No exceptions** - Direct file modifications will be rejected in support requests
4. **Automated checks** - Deployment script verifies git status before deploying

---

### 🛡️ Why This Policy?

| Reason | Benefit |
|--------|---------|
| Version Control | Track all changes, rollback capability |
| Consistency | Same process for all developers |
| Reproducibility | Deployments are traceable and repeatable |
| Collaboration | Team can review and validate changes |
| Disaster Recovery | Always able to restore previous versions |

---

### 🚨 Violation Consequences

- ❌ **Support will be refused** for issues caused by direct modifications
- ❌ **Changes will be lost** on next deployment
- ❌ **Merge conflicts** will occur
- ❌ **Integration may break** unpredictably

---

### 📋 Deployment Workflow (MANDATORY)

```
Local Machine                    Raspberry Pi
    │                                │
    ▼                                ▼
┌─────────────┐          ┌───────────────────────┐
│  1. Edit     │          │                       │
│     files    │          │                       │
└─────────────┘          │                       │
    │                    │                       │
    ▼                    │                       │
┌─────────────┐          │                       │
│  2. git add  │          │                       │
│     .       │          │                       │
└─────────────┘          │                       │
    │                    │                       │
    ▼                    │                       │
┌─────────────┐          │                       │
│  3. git     │          │                       │
│  commit    │          │                       │
└─────────────┘          │                       │
    │                    │                       │
    ▼                    │                       │
┌─────────────┐          │                       │
│  4. git     │──────┬───►                       │
│  push      │      │    │                       │
└─────────────┘      │    │                       │
                     │    ▼
                     ├──────────────────────────┐
                     │                          │
                     ▼                          ▼
              ┌─────────────────┐       ┌───────────────┐
              │ deploy_hass_    │       │  Git pull    │
              │ eedomus.sh      │───────►│ + restart    │
              │ (ONLY method)   │       │ (automatic)  │
              └─────────────────┘       └───────────────┘
```

---

### 🔧 Backup and Recovery

If you MUST modify files directly on Raspberry Pi (emergency only):

```bash
# 1. Create a backup branch FIRST
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && git checkout -b emergency-fix-$(date +%Y%m%d-%H%M%S)"

# 2. Make your emergency changes
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && nano some_file.py"

# 3. Commit the changes to the backup branch
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && \
    git add . && \
    git commit -m 'Emergency fix: description' && \
    git push origin emergency-fix-$(date +%Y%m%d-%H%M%S)"

# 4. Then create a PR to merge into unstable
# 5. Use the normal deployment process

# ⚠️ WARNING: This is for EMERGENCY ONLY. Normal development MUST use local git.
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
