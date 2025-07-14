#!/bin/bash

# Script to run trackandtrace service manually on production (without systemd)
# This is useful for debugging and testing

set -e

echo "=== Manual Production Run Script ==="
echo "This script will run trackandtrace service directly without systemd"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    echo "Usage: sudo ./run_production_manual.sh"
    exit 1
fi

# Production paths
PROJECT_DIR="/opt/trackandtrace"
VENV_PATH="/opt/trackandtrace/venv"
CONFIG_FILE="/etc/trackandtrace/config.env"
LOG_DIR="/var/log/trackandtrace"
DATA_DIR="/var/lib/trackandtrace"

# Check if directories exist
echo "Checking production directories..."
for dir in "$PROJECT_DIR" "$VENV_PATH" "$LOG_DIR" "$DATA_DIR"; do
    if [ ! -d "$dir" ]; then
        echo "Error: Directory $dir does not exist"
        exit 1
    fi
    echo "✓ $dir exists"
done

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file $CONFIG_FILE does not exist"
    exit 1
fi
echo "✓ Config file $CONFIG_FILE exists"

# Check if virtual environment exists
if [ ! -f "$VENV_PATH/bin/python" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi
echo "✓ Virtual environment found"

# Check if trackandtrace user exists
if ! id "trackandtrace" &>/dev/null; then
    echo "Error: trackandtrace user does not exist"
    exit 1
fi
echo "✓ trackandtrace user exists"

echo
echo "=== Starting trackandtrace service manually ==="
echo "Press Ctrl+C to stop the service"
echo

# Method 1: Run as trackandtrace user (recommended)
echo "Running as trackandtrace user..."
sudo -u trackandtrace bash -c "
    cd $PROJECT_DIR
    source $VENV_PATH/bin/activate
    export \$(cat $CONFIG_FILE | grep -v '^#' | grep -v '^$' | xargs)
    echo 'Environment loaded from $CONFIG_FILE'
    echo 'Python path: \$(which python)'
    echo 'Working directory: \$(pwd)'
    echo 'Starting service...'
    python -m trackandtrace.main_service start
" 