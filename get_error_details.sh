#!/bin/bash

# Script to get detailed error information from the failed service

echo "🔍 GETTING DETAILED ERROR INFORMATION..."
echo "======================================="

echo "1. 📋 RECENT JOURNAL LOGS FOR TRACKANDTRACE:"
echo "-------------------------------------------"
journalctl -u trackandtrace -n 100 --no-pager

echo ""
echo "2. 📋 SYSTEMD LOGS WITH TIMESTAMPS:"
echo "----------------------------------"
journalctl -u trackandtrace --since "1 hour ago" --no-pager

echo ""
echo "3. 📋 ALL JOURNAL ENTRIES (including boot):"
echo "-------------------------------------------"
journalctl -u trackandtrace --no-pager

echo ""
echo "4. 🧪 MANUAL TEST TO REPRODUCE ERROR:"
echo "------------------------------------"
echo "Testing manual execution to see the actual error..."

# Try to run the service manually to catch the error
echo "Running: sudo -u trackandtrace /opt/trackandtrace/venv/bin/python -m trackandtrace.main_service start"

# Change to the correct directory and run
cd /opt/trackandtrace
sudo -u trackandtrace /opt/trackandtrace/venv/bin/python -m trackandtrace.main_service start

echo ""
echo "5. 📋 ENVIRONMENT TEST:"
echo "----------------------"
echo "Testing environment variable loading..."

# Test if config file can be sourced
if [ -f "/etc/trackandtrace/config.env" ]; then
    echo "Config file exists, testing..."
    source /etc/trackandtrace/config.env
    echo "EMAIL_HOST: $EMAIL_HOST"
    echo "DB_HOST: $DB_HOST"
    echo "APP_BASE_DIR: $APP_BASE_DIR"
else
    echo "❌ Config file not found!"
fi 