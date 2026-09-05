# Hass-Eedomus Log Pipe Guide

## Quick Access

From your project root (`/Users/danjer/mistral/hass-eedomus`):

```bash
# Method 1: Simple streaming
./.vibe/skills/hass-eedomus-deploy/get_rasp_logs.sh

# Method 2: Advanced streaming with colors and filters (RECOMMENDED)
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh

# Method 3: Direct SSH
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -e  # eedomus only
```

---

## 🎯 Log Pipe Setup Complete

### What Was Implemented

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| **Basic Log Streaming** | `get_rasp_logs.sh` | Simple SSH log streaming | ✅ Ready |
| **Advanced Log Watcher** | `watch_logs.sh` | Colorized, filtered log streaming | ✅ Ready |
| **Deploy Script** | `deploy_hass_eedomus.sh` | Git-based deployment | ✅ Ready |
| **Validate Script** | `deploy_and_validate.sh` | Deployment + validation | ✅ Ready |

---

## 🚀 Using the Log Pipe

### 1. Prerequisites

Make sure you have:
- `.env` file in your project root with `REMOTE_IP` configured
- SSH access to your Raspberry Pi
- Home Assistant running on the remote

```bash
# If you haven't already:
cp .env.example .env
nano .env  # Set REMOTE_IP, REMOTE_USER, etc.
chmod 600 .env
```

### 2. Basic Log Streaming

```bash
# Stream all Home Assistant logs
./.vibe/skills/hass-eedomus-deploy/get_rasp_logs.sh

# Stream with follow (continuous)
./.vibe/skills/hass-eedomus-deploy/get_rasp_logs.sh --follow

# Get last 50 lines
./.vibe/skills/hass-eedomus-deploy/get_rasp_logs.sh --last 50
```

### 3. Advanced Log Watching (RECOMMENDED)

The `watch_logs.sh` script provides:
- **Color coding** for different log levels
- **Filtering** by component, log level, etc.
- **Saving** to files
- **Tail** specific number of lines

#### Basic Usage

```bash
# Follow all logs with colors
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh

# Stop with: Ctrl+C
```

#### Filtering Options

```bash
# Eedomus logs only
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -e

# Errors only
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -E

# Eedomus errors only
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -E -e

# Warnings only
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -W

# Debug messages only
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -d

# Info messages only
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -i
```

#### Output Options

```bash
# Disable colors
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh --no-color

# Save to file while displaying
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh --save ~/hass-eedomus.log

# Save eedomus errors to file
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -E -e --save ~/eedomus-errors.log
```

#### Historical Logs

```bash
# Last 100 lines (no follow)
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh --tail 100

# Last 50 eedomus lines
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh --tail 50 -e

# Last 200 lines saved to file
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh --tail 200 --save last-200-lines.log
```

### 4. Combined Operations

```bash
# Deploy and watch logs in separate terminals:

# Terminal 1: Deploy
./.vibe/skills/hass-eedomus-deploy/deploy_hass_eedomus.sh

# Terminal 2: Watch eedomus logs
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -e
```

---

## 🎨 Color Coding

The `watch_logs.sh` script automatically colorizes output:

| Log Level | Color | Example |
|-----------|-------|---------|
| ERROR | 🔴 Red | `ERROR: Connection failed` |
| WARNING | 🟡 Yellow | `WARNING: Deprecated API` |
| Info | 🔵 Blue | `Info: Integration loaded` |
| Debug | 🟣 Magenta | `Debug: Fetching data` |
| eedomus | 🟢 Green | `eedomus: Device updated` |

**Note:** Colors are disabled when outputting to a file or pipe.

---

## 📋 Command Reference

### `get_rasp_logs.sh`

Simple wrapper for `ha core logs`:
```bash
./get_rasp_logs.sh [ha_core_logs_arguments...]
```

Examples:
```bash
./get_rasp_logs.sh                    # Follow all logs
./get_rasp_logs.sh --follow           # Explicit follow
./get_rasp_logs.sh --last 100         # Last 100 lines
./get_rasp_logs.sh | grep -i error   # Filter client-side
```

### `watch_logs.sh`

Advanced log watching with built-in filtering:

```
watch_logs.sh [OPTIONS]

Options:
  -e, --eedomus      Filter for eedomus only
  -E, --errors       Show only errors
  -W, --warnings     Show only warnings
  -d, --debug        Show only debug messages
  -i, --info         Show only info messages
  --no-color         Disable color output
  --save FILE        Save output to file
  --tail N           Show last N lines (no follow)
  -h, --help         Show this help message
```

---

## 💡 Tips & Best Practices

### 1. Recommended Workflow

```bash
# Terminal 1: Deployment
cd /Users/danjer/mistral/hass-eedomus
./.vibe/skills/hass-eedomus-deploy/deploy_hass_eedomus.sh

# Terminal 2: Log monitoring (immediately after deployment)
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -e
```

### 2. Debugging Specific Issues

```bash
# Check for eedomus errors in last hour
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -E -e --tail 1000 | grep "$(date +%Y-%m-%d)"

# Monitor startup issues
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -E | grep -i "eedomus\|setup\|integration"

# Save debug session for later analysis
./.vibe/skills/hass-eedomus-deploy/watch_logs.sh -d --save ~/debug-$(date +%Y%m%d-%H%M%S).log
```

### 3. Continuous Monitoring

```bash
# Run in background and save to file
nohup ./watch_logs.sh --save ~/hass-continuous.log &

# Check background process
ps aux | grep watch_logs

# Stop background monitoring
pkill -f watch_logs

# View saved logs
tail -f ~/hass-continuous.log
```

### 4. Remote Log Analysis

```bash
# Analyze logs from saved file
cat ~/hass-continuous.log | grep -i error | sort | uniq -c | sort -nr

# Count eedomus entries
cat ~/hass-continuous.log | grep -c "eedomus"

# Find specific device issues
cat ~/hass-continuous.log | grep "periph_id:12345"
```

---

## ⚠️ Troubleshooting

### "Permission denied" when running scripts

```bash
# Make all scripts executable
chmod +x .vibe/skills/hass-eedomus-deploy/*.sh
```

### ".env: No such file or directory"

```bash
# Create .env from example
cp .env.example .env
nano .env
```

### "Connection refused" or SSH errors

```bash
# Test SSH connection
ssh ${REMOTE_IP} echo "Connection OK"

# Check if Home Assistant is running
ssh ${REMOTE_IP} "ha core info"

# Check if the correct path exists
ssh ${REMOTE_IP} "ls -la ${REMOTE_PATH}"
```

### "ha: command not found"

The remote server doesn't have Home Assistant CLI installed or the user doesn't have the correct environment:

```bash
# Check Home Assistant installation
ssh ${REMOTE_IP} "which ha || echo 'ha command not found'"

# Try using full path
ssh ${REMOTE_IP} "/usr/local/bin/ha core logs --follow"
```

### Colors not displaying properly

```bash
# Force colors (if terminal supports it)
export FORCE_COLOR=1

# Or disable colors
./watch_logs.sh --no-color
```

---

## 📚 Related Files

- **Main Documentation**: `SKILL.md`
- **Quick Start**: `README.md`
- **Environment Template**: `.env.example` (in project root)
- **GitHub Workflow**: `.github/workflows/release.yml`

---

## 🎯 Next Steps

1. ✅ **Log pipe is set up** - Ready to use
2. ⏳ **Test the scripts** - Verify they work with your setup
3. ⏳ **Create aliases** (optional) - For easier access
4. ⏳ **Integrate with CI/CD** (optional) - For automated testing

---

**Last Updated**: 2026-09-05
**Maintained by**: Mistral Vibe for Dan4Jer/hass-eedomus
