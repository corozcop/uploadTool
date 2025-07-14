#!/bin/bash

# Script to update the systemd service file with the configuration fix

set -e

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

echo "🔄 UPDATING TRACKANDTRACE SERVICE WITH CONFIGURATION FIX..."
echo "========================================================="

# Backup existing service file
SERVICE_FILE="/etc/systemd/system/trackandtrace.service"
if [ -f "$SERVICE_FILE" ]; then
    echo "📋 Backing up existing service file..."
    cp "$SERVICE_FILE" "${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "   ✅ Backup created: ${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Stop the service
echo ""
echo "🛑 Stopping trackandtrace service..."
systemctl stop trackandtrace || echo "   ⚠️  Service was not running"

# Copy the updated service file
echo ""
echo "📝 Installing updated service file..."
cp systemd/trackandtrace.service /etc/systemd/system/
echo "   ✅ Service file updated"

# Reload systemd
echo ""
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload
echo "   ✅ Systemd daemon reloaded"

# Start the service
echo ""
echo "🚀 Starting trackandtrace service..."
systemctl start trackandtrace

# Check status
echo ""
echo "📊 Service status:"
systemctl status trackandtrace --no-pager -l

# Verify configuration is loaded
echo ""
echo "🧪 Testing configuration..."
if command -v trackandtrace-test &> /dev/null; then
    trackandtrace-test
else
    echo "   ⚠️  trackandtrace-test command not found"
fi

echo ""
echo "✅ SERVICE UPDATE COMPLETED!"
echo "=========================="
echo "The service has been updated with the configuration fix."
echo "Monitor logs with: sudo journalctl -u trackandtrace -f" 