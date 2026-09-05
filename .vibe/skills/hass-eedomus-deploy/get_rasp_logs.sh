#!/bin/bash
# Hass-Eedomus SSH Log Bridge
# Creates a persistent SSH tunnel to stream and save Raspberry Pi logs locally
# Runs as a background process with automatic log file management
# Part of the hass-eedomus-deploy skill

set -o pipefail

# Default configuration
REMOTE_IP="${REMOTE_IP:-192.168.1.5}"
LOG_DIR="${LOG_DIR:-$HOME/mistral}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/rasp.log}"
PID_FILE="${PID_FILE:-$LOG_DIR/rasp_logs.pid}"
MAX_LOG_SIZE_MB="${MAX_LOG_SIZE_MB:-100}"  # Rotation at 100MB
MAX_LOG_FILES="${MAX_LOG_FILES:-5}"       # Keep last 5 rotated files

# Source environment configuration
if [ -f .env ]; then
    source .env
fi

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to rotate logs if they get too large
rotate_logs() {
    local log_path="$LOG_FILE"
    local base_path="${LOG_FILE%.*}"
    local ext="${LOG_FILE##*.}"
    
    if [ -f "$log_path" ]; then
        local current_size=$(stat -f%z "$log_path" 2>/dev/null || stat -c%s "$log_path" 2>/dev/null)
        local max_size_bytes=$((MAX_LOG_SIZE_MB * 1024 * 1024))
        
        if [ "$current_size" -ge "$max_size_bytes" ]; then
            # Rotate existing logs
            for i in $(seq $((MAX_LOG_FILES-1)) -1 1); do
                local prev=$((i-1))
                if [ $prev -ge 0 ]; then
                    if [ -f "${base_path}.${prev}.${ext}" ]; then
                        mv "${base_path}.${prev}.${ext}" "${base_path}.${i}.${ext}" 2>/dev/null
                    fi
                fi
            done
            
            # Move current log to .0
            mv "$log_path" "${base_path}.0.${ext}" 2>/dev/null
            
            # Compress old logs
            for i in $(seq 1 $((MAX_LOG_FILES-1))); do
                if [ -f "${base_path}.${i}.${ext}" ]; then
                    gzip "${base_path}.${i}.${ext}" 2>/dev/null || true
                fi
            done
        fi
    fi
}

# Function to start the log bridge
do_start() {
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        local running_pid=$(cat "$PID_FILE")
        if ps -p "$running_pid" > /dev/null 2>&1; then
            echo "⚠️  Log bridge is already running (PID: $running_pid)"
            echo "   Use: ./get_rasp_logs.sh stop"
            return 1
        else
            # Clean up stale PID file
            rm -f "$PID_FILE"
        fi
    fi
    
    # Rotate logs before starting
    rotate_logs
    
    # Remove stale PID file
    rm -f "$PID_FILE"
    
    # Set up SSH command with proper HA command detection
    TEST_HA=$(ssh -p ${REMOTE_PORT:-22} ${REMOTE_USER:-$USER}@${REMOTE_IP} "ha core logs -n 1 2>/dev/null" | grep -v "401: Unauthorized" | grep -v "Unauthorized" | head -1)
    if [ -n "$TEST_HA" ]; then
        HA_CMD="ha"
    else
        HA_CMD="sudo -i ha"
    fi
    
    # Start the bridge in background
    echo "🔄 Starting SSH log bridge to $REMOTE_IP..."
    echo "📁 Logs will be saved to: $LOG_FILE"
    echo "📋 PID file: $PID_FILE"
    
    # Run the SSH command directly in background, redirecting output to log file
    nohup ssh -p ${REMOTE_PORT:-22} ${REMOTE_USER:-$USER}@${REMOTE_IP} "${HA_CMD} core logs -f" >> "$LOG_FILE" 2>&1 &
    local bridge_pid=$!
    
    # Save PID
    echo "$bridge_pid" > "$PID_FILE"
    
    echo "✅ Log bridge started successfully (PID: $bridge_pid)"
    echo "   Logs: tail -f $LOG_FILE"
    echo "   Stop: ./get_rasp_logs.sh stop"
    echo "   Status: ./get_rasp_logs.sh status"
    
    # Tail the log file to show it's working
    sleep 2
    if [ -f "$LOG_FILE" ]; then
        echo ""
        echo "📊 Last 5 lines of current logs:"
        tail -n 5 "$LOG_FILE"
    fi
}

# Function to stop the log bridge
do_stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "ℹ️  No running log bridge found (no PID file)"
        return 0
    fi
    
    local running_pid=$(cat "$PID_FILE")
    
    if ps -p "$running_pid" > /dev/null 2>&1; then
        echo "🛑 Stopping log bridge (PID: $running_pid)..."
        kill "$running_pid" 2>/dev/null
        
        # Wait for process to stop
        local count=0
        while ps -p "$running_pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 1
            count=$((count+1))
        done
        
        if ps -p "$running_pid" > /dev/null 2>&1; then
            echo "⚠️  Process did not stop gracefully, killing forcefully..."
            kill -9 "$running_pid" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        echo "✅ Log bridge stopped"
    else
        echo "ℹ️  Process already stopped (stale PID file)"
        rm -f "$PID_FILE"
    fi
}

# Function to check status
do_status() {
    echo "📊 SSH Log Bridge Status"
    echo "======================"
    
    if [ -f "$PID_FILE" ]; then
        local saved_pid=$(cat "$PID_FILE")
        if ps -p "$saved_pid" > /dev/null 2>&1; then
            echo "✅ Status: RUNNING"
            echo "   PID: $saved_pid"
            echo "   Log file: $LOG_FILE"
            echo "   Started: $(ps -p $saved_pid -o lstart= 2>/dev/null)"
            
            if [ -f "$LOG_FILE" ]; then
                local log_size=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
                local log_size_mb=$((log_size / 1024 / 1024))
                echo "   Log size: ${log_size_mb}MB"
                echo "   Last modified: $(stat -f%Sm -t "%Y-%m-%d %H:%M:%S" "$LOG_FILE" 2>/dev/null || stat -c %y "$LOG_FILE" 2>/dev/null | cut -d'.' -f1)"
            else
                echo "   Log file: NOT FOUND"
            fi
            
            echo ""
            echo "📝 To view logs: tail -f $LOG_FILE"
            echo "🛑 To stop: ./get_rasp_logs.sh stop"
            return 0
        else
            echo "❌ Status: STOPPED (stale PID file)"
            echo "   Clean up: ./get_rasp_logs.sh stop"
            return 1
        fi
    else
        echo "❌ Status: NOT RUNNING"
        echo "   No PID file found at $PID_FILE"
        echo "🔄 To start: ./get_rasp_logs.sh start"
        return 1
    fi
}

# Function to view current logs
do_tail() {
    local lines=${1:-50}
    if [ -f "$LOG_FILE" ]; then
        echo "📄 Showing last $lines lines from $LOG_FILE"
        echo "=========================================="
        tail -n "$lines" "$LOG_FILE"
    else
        echo "❌ Log file not found: $LOG_FILE"
        echo "   Start the log bridge first: ./get_rasp_logs.sh start"
    fi
}

# Function to follow current logs
do_follow() {
    if [ -f "$LOG_FILE" ]; then
        echo "📊 Following $LOG_FILE (Ctrl+C to stop)"
        echo "=========================================="
        tail -f "$LOG_FILE"
    else
        echo "❌ Log file not found: $LOG_FILE"
        echo "   Start the log bridge first: ./get_rasp_logs.sh start"
    fi
}

# Function to clean old log files
do_clean() {
    local base_path="${LOG_FILE%.*}"
    local ext="${LOG_FILE##*.}"
    
    echo "🧹 Cleaning old log files..."
    
    # Remove old compressed logs
    for i in $(seq 1 $((MAX_LOG_FILES))); do
        if [ -f "${base_path}.${i}.${ext}.gz" ]; then
            rm -f "${base_path}.${i}.${ext}.gz"
            echo "   Removed: ${base_path}.${i}.${ext}.gz"
        fi
        if [ -f "${base_path}.${i}.${ext}" ]; then
            rm -f "${base_path}.${i}.${ext}"
            echo "   Removed: ${base_path}.${i}.${ext}"
        fi
    done
    
    # Truncate current log file
    if [ -f "$LOG_FILE" ]; then
        > "$LOG_FILE"
        echo "   Truncated: $LOG_FILE"
    fi
    
    echo "✅ Log cleanup completed"
}

# Main command handling
case "$1" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_stop
        sleep 1
        do_start
        ;;
    status)
        do_status
        ;;
    tail)
        do_tail "${2:-50}"
        ;;
    follow)
        do_follow
        ;;
    clean)
        do_clean
        ;;
    logs)
        do_tail "${2:-100}"
        ;;
    "")
        # Default: show help
        echo "📡 Hass-Eedomus SSH Log Bridge"
        echo "=============================="
        echo ""
        echo "Usage: ./get_rasp_logs.sh [COMMAND] [OPTIONS]"
        echo ""
        echo "Commands:"
        echo "  start          Start the SSH log bridge in background"
        echo "  stop           Stop the running log bridge"
        echo "  restart        Restart the log bridge"
        echo "  status         Show bridge status"
        echo "  tail [N]       Show last N lines (default: 50)"
        echo "  follow         Follow the log file in real-time"
        echo "  logs [N]      Show last N lines (default: 100)"
        echo "  clean          Clean old log files"
        echo ""
        echo "Configuration:"
        echo "  REMOTE_IP=${REMOTE_IP}"
        echo "  LOG_FILE=${LOG_FILE}"
        echo "  LOG_DIR=${LOG_DIR}"
        echo "  PID_FILE=${PID_FILE}"
        echo ""
        echo "Environment:"
        if [ -f .env ]; then
            echo "  .env file: FOUND"
        else
            echo "  .env file: NOT FOUND (create from .env.example)"
        fi
        echo ""
        do_status
        ;;
    *)
        # Pass through to ha core logs for backward compatibility
        echo "⚠️  Passing through to direct SSH command (legacy mode)"
        echo "   For bridge mode, use: start, stop, status, tail, follow, logs"
        echo ""
        TEST_HA=$(ssh -p ${REMOTE_PORT:-22} ${REMOTE_USER:-$USER}@${REMOTE_IP} "ha core logs -n 1 2>/dev/null" | grep -v "401: Unauthorized" | grep -v "Unauthorized" | head -1)
        if [ -n "$TEST_HA" ]; then
            HA_CMD="ha"
        else
            HA_CMD="sudo -i ha"
        fi
        ssh -p ${REMOTE_PORT:-22} ${REMOTE_USER:-$USER}@${REMOTE_IP} "${HA_CMD} core logs $@"
        ;;
esac