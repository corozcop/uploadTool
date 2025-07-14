#!/bin/bash

# Run trackandtrace service manually WITHOUT loading config.env
# This uses environment variables that are already set or system defaults

set -e

echo "=== Manual Production Run (No config.env) ==="
echo "This script runs trackandtrace without loading config.env"
echo "Make sure environment variables are set in your shell or system"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    echo "Usage: sudo ./run_production_no_config.sh"
    exit 1
fi

# Production paths
PROJECT_DIR="/opt/trackandtrace"
VENV_PATH="/opt/trackandtrace/venv"

echo "=== Environment Check ==="
echo "Current environment variables:"
env | grep -E '^(DB_|GMAIL_|LOG_|DATA_)' | sort || echo "No trackandtrace env vars found"
echo

echo "=== Starting service without config.env ==="
echo "Press Ctrl+C to stop the service"
echo

# Run as trackandtrace user WITHOUT loading config.env
sudo -u trackandtrace bash -c "
    cd $PROJECT_DIR
    source $VENV_PATH/bin/activate
    echo 'Current user: \$(whoami)'
    echo 'Working directory: \$(pwd)'
    echo 'Python path: \$(which python)'
    echo 'Environment variables available:'
    env | grep -E '^(DB_|GMAIL_|LOG_|DATA_)' | sort || echo 'No trackandtrace env vars found'
    echo 'Starting service...'
    python -m trackandtrace.main_service start
" 