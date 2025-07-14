#!/bin/bash

# Comprehensive diagnostic script for trackandtrace service failures

set -e

echo "=== TrackAndTrace Service Failure Diagnosis ==="
echo "$(date)"
echo

# Must run as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    echo "Usage: sudo ./diagnose_service_failure.sh"
    exit 1
fi

echo "=== 1. SERVICE STATUS ==="
systemctl status trackandtrace.service --no-pager -l
echo

echo "=== 2. RECENT JOURNAL LOGS (last 50 lines) ==="
journalctl -u trackandtrace.service -n 50 --no-pager
echo

echo "=== 3. DETAILED ERROR LOGS ==="
journalctl -u trackandtrace.service --since "10 minutes ago" --no-pager
echo

echo "=== 4. CONFIG FILE PERMISSIONS ==="
CONFIG_FILE="/etc/trackandtrace/config.env"
if [ -f "$CONFIG_FILE" ]; then
    echo "Config file exists:"
    ls -la "$CONFIG_FILE"
    echo
    echo "Testing trackandtrace user access:"
    if sudo -u trackandtrace test -r "$CONFIG_FILE"; then
        echo "✅ trackandtrace user CAN read config.env"
    else
        echo "❌ trackandtrace user CANNOT read config.env"
        echo "Run: sudo ./fix_config_permissions.sh"
    fi
else
    echo "❌ Config file $CONFIG_FILE does not exist"
fi
echo

echo "=== 5. DIRECTORY PERMISSIONS ==="
for dir in "/opt/trackandtrace" "/var/lib/trackandtrace" "/var/log/trackandtrace" "/etc/trackandtrace"; do
    if [ -d "$dir" ]; then
        echo "$dir:"
        ls -la "$dir"
        echo
    else
        echo "❌ Missing: $dir"
    fi
done

echo "=== 6. VIRTUAL ENVIRONMENT TEST ==="
VENV_PATH="/opt/trackandtrace/venv"
if [ -f "$VENV_PATH/bin/python" ]; then
    echo "✅ Virtual environment exists"
    echo "Python version:"
    sudo -u trackandtrace "$VENV_PATH/bin/python" --version
    echo
    echo "Testing trackandtrace module import:"
    sudo -u trackandtrace bash -c "
        cd /opt/trackandtrace
        source $VENV_PATH/bin/activate
        python -c 'import trackandtrace; print(\"✅ Module import successful\")'
    " 2>&1 || echo "❌ Module import failed"
else
    echo "❌ Virtual environment not found at $VENV_PATH"
fi
echo

echo "=== 7. MANUAL SERVICE RUN TEST ==="
echo "Testing manual service run to see actual error:"
sudo -u trackandtrace bash -c "
    cd /opt/trackandtrace
    source /opt/trackandtrace/venv/bin/activate
    export \$(cat /etc/trackandtrace/config.env | grep -v '^#' | grep -v '^$' | xargs) 2>/dev/null || echo 'Could not load config.env'
    echo 'Running service manually...'
    timeout 10s python -m trackandtrace.main_service start 2>&1 || echo 'Service failed or timed out'
"
echo

echo "=== 8. SYSTEMD SERVICE FILE CHECK ==="
SERVICE_FILE="/etc/systemd/system/trackandtrace.service"
if [ -f "$SERVICE_FILE" ]; then
    echo "Service file content:"
    cat "$SERVICE_FILE"
    echo
    echo "Checking for EnvironmentFile directive:"
    if grep -q "EnvironmentFile" "$SERVICE_FILE"; then
        echo "✅ EnvironmentFile directive found"
    else
        echo "❌ EnvironmentFile directive missing"
        echo "This could be the issue!"
    fi
else
    echo "❌ Service file not found at $SERVICE_FILE"
fi
echo

echo "=== 9. ENVIRONMENT VARIABLES TEST ==="
echo "Testing environment variable loading:"
if sudo -u trackandtrace test -r "$CONFIG_FILE"; then
    sudo -u trackandtrace bash -c "
        export \$(cat $CONFIG_FILE | grep -v '^#' | grep -v '^$' | xargs)
        echo 'Environment variables loaded:'
        env | grep -E '^(DB_|GMAIL_|LOG_|DATA_)' | sort
    " 2>&1 || echo "Failed to load environment variables"
else
    echo "Cannot test - trackandtrace user cannot read config file"
fi
echo

echo "=== DIAGNOSIS COMPLETE ==="
echo "Review the output above to identify the issue."
echo "Common fixes:"
echo "1. Fix config.env permissions: sudo ./fix_config_permissions.sh"
echo "2. Fix service file: ensure EnvironmentFile directive is present"
echo "3. Check database connectivity and Gmail credentials"
echo "4. Run manually: sudo ./run_production_manual.sh" 