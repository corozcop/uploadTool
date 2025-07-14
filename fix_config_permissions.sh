#!/bin/bash

# Fix permissions for config.env file so trackandtrace user can read it

set -e

echo "=== Fixing config.env Permissions ==="
echo

# Must run as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    echo "Usage: sudo ./fix_config_permissions.sh"
    exit 1
fi

CONFIG_FILE="/etc/trackandtrace/config.env"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file $CONFIG_FILE does not exist"
    exit 1
fi

echo "Current permissions:"
ls -la "$CONFIG_FILE"

echo
echo "Current owner and group:"
stat -c "Owner: %U, Group: %G" "$CONFIG_FILE"

echo
echo "Fixing permissions..."

# Option 1: Make readable by trackandtrace user specifically
echo "1. Making file readable by trackandtrace user..."
chown root:trackandtrace "$CONFIG_FILE"
chmod 640 "$CONFIG_FILE"

echo
echo "New permissions:"
ls -la "$CONFIG_FILE"

echo
echo "Testing if trackandtrace user can read it..."
if sudo -u trackandtrace test -r "$CONFIG_FILE"; then
    echo "✅ SUCCESS: trackandtrace user can now read config.env"
    
    # Test loading environment variables
    echo
    echo "Testing environment variable loading..."
    sudo -u trackandtrace bash -c "
        export \$(cat $CONFIG_FILE | grep -v '^#' | grep -v '^$' | xargs)
        echo 'Environment variables loaded successfully:'
        env | grep -E '^(DB_|GMAIL_|LOG_|DATA_)' | sort || echo 'No trackandtrace env vars found'
    "
else
    echo "❌ FAILED: trackandtrace user still cannot read config.env"
    echo "You may need to adjust permissions manually"
fi

echo
echo "=== Permission Fix Complete ===" 