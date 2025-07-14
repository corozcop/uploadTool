#!/bin/bash

# Different methods to run trackandtrace service manually on production

echo "=== Methods to Run TrackAndTrace Manually on Production ==="
echo

# Production paths
PROJECT_DIR="/opt/trackandtrace"
VENV_PATH="/opt/trackandtrace/venv"
CONFIG_FILE="/etc/trackandtrace/config.env"

echo "Choose a method:"
echo "1. Quick run (as trackandtrace user)"
echo "2. Debug run (as root, more verbose)"
echo "3. Test configuration only"
echo "4. Show manual commands"
echo

read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo "=== Method 1: Quick Run as trackandtrace user ==="
        sudo -u trackandtrace bash -c "
            cd $PROJECT_DIR
            source $VENV_PATH/bin/activate
            export \$(cat $CONFIG_FILE | grep -v '^#' | grep -v '^$' | xargs)
            python -m trackandtrace.main_service start
        "
        ;;
    
    2)
        echo "=== Method 2: Debug Run (verbose) ==="
        sudo -u trackandtrace bash -c "
            cd $PROJECT_DIR
            source $VENV_PATH/bin/activate
            export \$(cat $CONFIG_FILE | grep -v '^#' | grep -v '^$' | xargs)
            echo 'Current user: \$(whoami)'
            echo 'Working directory: \$(pwd)'
            echo 'Python path: \$(which python)'
            echo 'Environment variables loaded:'
            env | grep -E '^(DB_|GMAIL_|LOG_|DATA_)' | sort
            echo 'Starting service with debug...'
            python -m trackandtrace.main_service start --debug
        "
        ;;
    
    3)
        echo "=== Method 3: Test Configuration Only ==="
        sudo -u trackandtrace bash -c "
            cd $PROJECT_DIR
            source $VENV_PATH/bin/activate
            export \$(cat $CONFIG_FILE | grep -v '^#' | grep -v '^$' | xargs)
            python -c '
import os
from trackandtrace.config import Config
print(\"Testing configuration...\")
config = Config()
print(f\"Database URL: {config.database_url[:50]}...\")
print(f\"Gmail user: {config.gmail_user}\")
print(f\"Data directory: {config.data_dir}\")
print(f\"Log directory: {config.log_dir}\")
print(\"Configuration test completed successfully!\")
'
        "
        ;;
    
    4)
        echo "=== Method 4: Manual Commands ==="
        echo "Run these commands manually:"
        echo
        echo "# Switch to trackandtrace user"
        echo "sudo -u trackandtrace bash"
        echo
        echo "# Navigate to project directory"
        echo "cd $PROJECT_DIR"
        echo
        echo "# Activate virtual environment"
        echo "source $VENV_PATH/bin/activate"
        echo
        echo "# Load environment variables"
        echo "export \$(cat $CONFIG_FILE | grep -v '^#' | grep -v '^$' | xargs)"
        echo
        echo "# Run the service"
        echo "python -m trackandtrace.main_service start"
        echo
        echo "# Or run with debug"
        echo "python -m trackandtrace.main_service start --debug"
        echo
        echo "# To stop: Press Ctrl+C"
        ;;
    
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac 