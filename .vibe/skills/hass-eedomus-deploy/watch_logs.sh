#!/bin/bash
# Advanced log watching script for hass-eedomus
# Provides real-time SSH log streaming with filtering and coloring
# Part of the hass-eedomus-deploy skill

# Load environment configuration
if [ -f .env ]; then
    source .env
else
    echo "❌ Error: .env file not found. Please create it from .env.example"
    exit 1
fi

# Check if REMOTE_IP is set
if [ -z "$REMOTE_IP" ]; then
    echo "❌ Error: REMOTE_IP not configured in .env"
    exit 1
fi

# Check if REMOTE_USER is set, default to current user
if [ -z "$REMOTE_USER" ]; then
    REMOTE_USER=$(whoami)
fi

# Check if REMOTE_PORT is set, default to 22
if [ -z "$REMOTE_PORT" ]; then
    REMOTE_PORT=22
fi

# Build SSH connection string with optional SSH_OPTS
SSH_CONNECT="ssh -p ${REMOTE_PORT}"
if [ -n "$SSH_OPTS" ]; then
    SSH_CONNECT="ssh -p ${REMOTE_PORT} ${SSH_OPTS}"
fi

# Determine the correct ha command (some systems require sudo)
# Try direct ha first, fall back to sudo -i ha if needed
TEST_HA=$(${SSH_CONNECT} ${REMOTE_USER}@${REMOTE_IP} "ha core logs -n 1 2>/dev/null" | grep -v "401: Unauthorized" | grep -v "Unaauthorized" | head -1)
if [ -n "$TEST_HA" ]; then
    HA_CMD="ha"
else
    HA_CMD="sudo -i ha"
fi

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    cat << EOF
🔍 Hass-Eedomus Log Watcher - Usage
====================================

$(echo -e "${GREEN}Basic Usage:${NC}")
  $(echo -e "${CYAN}./watch_logs.sh${NC}")                  # Follow all logs
  $(echo -e "${CYAN}./watch_logs.sh eedomus${NC}")         # Follow only eedomus logs
  $(echo -e "${CYAN}./watch_logs.sh --errors${NC}")        # Show only errors

$(echo -e "${GREEN}Filter Options:${NC}")
  $(echo -e "${CYAN}--eedomus, -e${NC}")         # Filter for eedomus only
  $(echo -e "${CYAN}--errors, -E${NC}")         # Show only errors
  $(echo -e "${CYAN}--warnings, -W${NC}")       # Show only warnings
  $(echo -e "${CYAN}--debug, -d${NC}")           # Show debug messages
  $(echo -e "${CYAN}--info, -i${NC}")            # Show info messages

$(echo -e "${GREEN}Output Options:${NC}")
  $(echo -e "${CYAN}--no-color${NC}")           # Disable colors
  $(echo -e "${CYAN}--save FILE${NC}")           # Save logs to file
  $(echo -e "${CYAN}--tail N${NC}")             # Show last N lines (no follow)

$(echo -e "${GREEN}Examples:${NC}")
  $(echo -e "${CYAN}./watch_logs.sh${NC}")                    # Follow all logs
  $(echo -e "${CYAN}./watch_logs.sh -e${NC}")                  # Follow eedomus logs
  $(echo -e "${CYAN}./watch_logs.sh -E -e${NC}")               # Follow eedomus errors
  $(echo -e "${CYAN}./watch_logs.sh --save /tmp/hass.log${NC}")  # Save all logs
  $(echo -e "${CYAN}./watch_logs.sh --tail 100 -e${NC}")         # Last 100 eedomus lines

EOF
    exit 0
}

# Parse arguments
FILTER=""
SAVE_FILE=""
TAIL_LINES=""
NO_COLOR=false
FOLLOW=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --eedomus|-e)
            FILTER="grep -i eedomus"
            shift
            ;;
        --errors|-E)
            FILTER="grep -i 'error\\|exception\\|traceback\\|failed'"
            shift
            ;;
        --warnings|-W)
            FILTER="grep -i 'warning\\|warn'"
            shift
            ;;
        --debug|-d)
            FILTER="grep -i 'debug'"
            shift
            ;;
        --info|-i)
            FILTER="grep -i 'info'"
            shift
            ;;
        --no-color)
            NO_COLOR=true
            shift
            ;;
        --save)
            SAVE_FILE="$2"
            shift 2
            ;;
        --tail)
            TAIL_LINES="$2"
            FOLLOW=false
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "❌ Unknown option: $1"
            usage
            ;;
    esac
done

# Build the base SSH command
SSH_BASE="${SSH_CONNECT} ${REMOTE_USER}@${REMOTE_IP} \"${HA_CMD} core logs"

# Add options to the remote command (inside the quotes)
if [ -n "$TAIL_LINES" ]; then
    SSH_BASE="${SSH_BASE} -n ${TAIL_LINES}"
    FOLLOW=false
fi

# Add follow if needed
if [ "$FOLLOW" = true ]; then
    SSH_BASE="${SSH_BASE} --follow"
fi

# Close the SSH command
SSH_CMD="${SSH_BASE}\""

# Apply filter if specified
if [ -n "$FILTER" ]; then
    SSH_CMD="${SSH_CMD} | ${FILTER}"
fi

# Colorize output if colors are enabled
if [ "$NO_COLOR" = false ]; then
    # Skip colorization for now - will fix later
    echo "Note: Colorization disabled temporarily for compatibility"
fi

# Save to file if specified
if [ -n "$SAVE_FILE" ]; then
    SSH_CMD="${SSH_CMD} | tee ${SAVE_FILE}"
else
    # Display to console
    SSH_CMD="${SSH_CMD}"
fi

# Execute the command
echo -e "${GREEN}🔍 Starting log stream from ${REMOTE_IP}...${NC}"
if [ -n "$FILTER" ]; then
    echo -e "   Filter: ${FILTER}"
fi
if [ -n "$SAVE_FILE" ]; then
    echo -e "   Saving to: ${SAVE_FILE}"
fi
echo ""

eval "${SSH_CMD}"
