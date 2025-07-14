#!/bin/bash

# Script for full redeployment with latest changes

set -e

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

echo "🔄 FULL REDEPLOYMENT WITH LATEST CHANGES..."
echo "=========================================="

# Stop the existing service
echo "🛑 Stopping existing service..."
systemctl stop trackandtrace || echo "   ⚠️  Service was not running"

# Backup configuration
CONFIG_FILE="/etc/trackandtrace/config.env"
if [ -f "$CONFIG_FILE" ]; then
    echo "📋 Backing up configuration..."
    cp "$CONFIG_FILE" "/tmp/config.env.backup.$(date +%Y%m%d_%H%M%S)"
    echo "   ✅ Configuration backed up"
fi

# Run the deployment script with update option
echo ""
echo "🚀 Running deployment script..."
if [ -f "deployment/deploy.sh" ]; then
    ./deployment/deploy.sh install
else
    echo "❌ deployment/deploy.sh not found!"
    echo "   Make sure you're in the project directory"
    exit 1
fi

# Restore configuration if it was backed up
if [ -f "/tmp/config.env.backup.*" ]; then
    echo ""
    echo "📋 Restoring configuration..."
    LATEST_BACKUP=$(ls -t /tmp/config.env.backup.* | head -1)
    cp "$LATEST_BACKUP" "$CONFIG_FILE"
    echo "   ✅ Configuration restored from $LATEST_BACKUP"
fi

# Start the service
echo ""
echo "🚀 Starting service..."
systemctl start trackandtrace

# Check status
echo ""
echo "📊 Service status:"
systemctl status trackandtrace --no-pager -l

# Test configuration
echo ""
echo "🧪 Testing configuration..."
trackandtrace-test

echo ""
echo "✅ FULL REDEPLOYMENT COMPLETED!"
echo "=============================="
echo "The service has been fully redeployed with all latest changes."
echo "Monitor logs with: sudo journalctl -u trackandtrace -f" 