# Hass-Eedomus Deployment Skill

## Overview

This skill provides standardized deployment procedures for the hass-eedomus Home Assistant custom component.

## Quick Start

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

## Best Practices

### ❌ NEVER
- Manual file copying (`scp`, `rsync`)
- Direct file editing on Raspberry Pi
- Hard git resets without backup

### ✅ ALWAYS
- Use git for all deployments
- Create backup branches before major changes
- Test locally before deploying
- Monitor logs after deployment

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
