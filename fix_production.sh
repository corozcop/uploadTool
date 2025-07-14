#!/bin/bash

# Script to diagnose and fix production configuration issues

echo "🔍 DIAGNOSING PRODUCTION CONFIGURATION ISSUES..."
echo "================================================="

# Check if config file exists
CONFIG_FILE="/etc/trackandtrace/config.env"
echo "1. Checking configuration file..."
if [ -f "$CONFIG_FILE" ]; then
    echo "   ✅ Config file exists: $CONFIG_FILE"
    echo "   📄 Config file permissions:"
    ls -la "$CONFIG_FILE"
else
    echo "   ❌ Config file NOT found: $CONFIG_FILE"
    echo "   📋 You need to create the config file first"
    exit 1
fi

# Check systemd service file
SERVICE_FILE="/etc/systemd/system/trackandtrace.service"
echo ""
echo "2. Checking systemd service file..."
if [ -f "$SERVICE_FILE" ]; then
    echo "   ✅ Service file exists: $SERVICE_FILE"
    if grep -q "EnvironmentFile" "$SERVICE_FILE"; then
        echo "   ✅ Service file has EnvironmentFile directive"
    else
        echo "   ❌ Service file MISSING EnvironmentFile directive"
        echo "   🔧 This is likely the problem!"
    fi
else
    echo "   ❌ Service file NOT found: $SERVICE_FILE"
fi

# Check service status
echo ""
echo "3. Checking service status..."
systemctl is-active trackandtrace || echo "   ⚠️  Service is not running"
systemctl is-enabled trackandtrace || echo "   ⚠️  Service is not enabled"

# Check logs
echo ""
echo "4. Recent service logs (last 10 lines):"
journalctl -u trackandtrace -n 10 --no-pager || echo "   ⚠️  No logs found"

echo ""
echo "🔧 RECOMMENDED FIX:"
echo "==================="
echo "1. Update the systemd service file to include EnvironmentFile"
echo "2. Reload systemd and restart the service"
echo ""
echo "Run the following commands:"
echo "  sudo systemctl edit trackandtrace --full"
echo "  # Add this line after the Environment lines:"
echo "  # EnvironmentFile=/etc/trackandtrace/config.env"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl restart trackandtrace"
echo "  sudo systemctl status trackandtrace" 