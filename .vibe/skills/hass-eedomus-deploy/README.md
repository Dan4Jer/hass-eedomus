# Hass-Eedomus Deployment Skill

## 🚨 MANDATORY POLICY: Git-Only Deployment

**⚠️ ALL MODIFICATIONS MUST GO THROUGH GIT - NO EXCEPTIONS**

Direct file modifications on the Raspberry Pi are **STRICTLY FORBIDDEN** and will:
- ❌ Cause version control loss
- ❌ Prevent rollback capability  
- ❌ Create merge conflicts
- ❌ **VOID ALL SUPPORT**

**Only use the provided deployment scripts.**

---

## Overview

This skill provides **standardized, git-based** deployment procedures for the hass-eedomus Home Assistant custom component. All deployments must follow the mandatory workflow described below.

## 📋 Quick Start (MANDATORY PROCESS)

### 1. Deploy to Raspberry Pi

```bash
# Navigate to the project root
cd ${LOCAL_REPO_PATH}

# Make sure you have a .env file
cp .env.example .env
nano .env  # Edit with your configuration

# Run deployment from project root
./.vibe/skills/hass-eedomus-deploy/deploy_hass_eedomus.sh
```

### 2. Stream Logs

**Option A: Basique**
```bash
# In a new terminal, from project root
./.vibe/skills/hass-eedomus-deploy/get_rasp_logs.sh

# With filters
./.vibe/skills/hass-eedomus-deploy/get_rasp_logs.sh | grep -i eedomus
```

**Option B: Avancé (recommandé)**
```bash
# Suivre tous les logs avec couleurs
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh

# Suivre uniquement eedomus
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -e

# Suivre uniquement les erreurs eedomus
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -E -e

# Afficher les 100 dernières lignes
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh --tail 100 -e

# Sauvegarder dans un fichier
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh --save ~/hass-eedomus.log -e
```

### 3. Deploy and Validate

```bash
# From project root
./.vibe/skills/hass-eedomus-deploy/deploy_and_validate.sh
```

## Scripts Included

| Script | Purpose | Usage |
|--------|---------|-------|
| `deploy_hass_eedomus.sh` | Standard deployment with git | `./deploy_hass_eedomus.sh` |
| `get_rasp_logs.sh` | Basic log streaming | `./get_rasp_logs.sh [options]` |
| `watch_logs.sh` | Advanced log watching with colors and filters | `./watch_logs.sh [options]` |
| `deploy_and_validate.sh` | Deploy + auto-validation | `./deploy_and_validate.sh` |

## Configuration

### Environment File

Create `.env` in your project root from the provided example:

```bash
# Copy the example file
cp .env.example .env

# Edit with your configuration
nano .env

# Set restrictive permissions (recommended)
chmod 600 .env
```

**Required variables in .env:**
- `REMOTE_IP` - IP address of your Home Assistant server
- `REMOTE_USER` - SSH username
- `REMOTE_PATH` - Path to hass-eedomus on remote
- `LOCAL_REPO_PATH` - Path to your local hass-eedomus repository

### Remote Setup

Ensure the hass-eedomus repository is cloned at the location specified in `REMOTE_PATH`:
```
${REMOTE_PATH}/
```

## 🚨 Best Practices (MANDATORY)

### ❌❌❌ STRICTLY FORBIDDEN ❌❌❌

**Violating these rules will VOID all support:**

- ❌ **Manual file copying** (`scp`, `rsync`) - Direct copies bypass version control
- ❌ **Direct file editing on Raspberry Pi** - Any editor (nano, vim, sed, etc.)
- ❌ **Manual git operations on Raspberry Pi** - All git must be done locally
- ❌ **Hard resets without backup** - Data loss risk

### ✅✅✅ ONLY ALLOWED METHOD ✅✅✅

**The ONLY acceptable deployment process:**

```bash
# 1. Edit files LOCALLY (never on Raspberry Pi)
# ... make your changes ...

# 2. Commit to git LOCALLY
git add .
git commit -m "Your descriptive message"

# 3. Push to remote repository
git push origin unstable

# 4. Deploy using the script (ONLY method)
./.vibe/skills/hass-eedomus-deploy/deploy_hass_eedomus.sh
```

**Remember:** The deployment script will **BLOCK** deployment if uncommitted changes exist.

### 📋 Pre-Deployment Checklist

- [ ] All changes are in local files (not on Raspberry Pi)
- [ ] `git status` shows no uncommitted changes (except untracked files)
- [ ] All changes are committed with descriptive messages
- [ ] Changes are pushed to GitHub (`git push`)
- [ ] You are on the correct branch (`unstable` for development)
- [ ] You have tested changes locally when possible

### 🛡️ Why This Matters

| Problem | Solution |
|---------|----------|
| Version conflicts | Git tracks all changes |
| Deployment failures | Script validates git status |
| Lost changes | Git provides history |
| Team collaboration | Everyone uses same process |
| Disaster recovery | Easy rollback to previous commits |

## Troubleshooting

### Common Issues

**SSH Connection Failed:**
```bash
# Test connection
ssh ${REMOTE_IP} echo "SSH working"

# Check if Pi is powered on
ping ${REMOTE_IP}
```

**Git Operations Failed:**
```bash
# Check git status on remote
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && git status"

# Reset and pull
ssh ${REMOTE_IP} "cd ${REMOTE_PATH} && git reset --hard origin/unstable"
```

## Related Files

- **Replaces**: `deploy_on_rasp.sh`, `get_rasp_log.sh` (from project root)
- **Skill File**: `SKILL.md` (detailed documentation)
- **Project**: [Dan4Jer/hass-eedomus](https://github.com/Dan4Jer/hass-eedomus)

## License

MIT License - See SKILL.md for details
