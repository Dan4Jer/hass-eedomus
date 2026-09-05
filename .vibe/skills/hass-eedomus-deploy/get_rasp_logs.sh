#!/bin/bash
# Standardized log retrieval for hass-eedomus
# Provides SSH log streaming with local display
# Part of the hass-eedomus-deploy skill

# Configuration
REMOTE_IP="${REMOTE_IP}"
LOG_FILE="~/mistral/rasp.log"

# Source environment configuration
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
