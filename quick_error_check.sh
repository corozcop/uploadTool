#!/bin/bash

# Quick error check for trackandtrace service failures

echo "=== Quick Error Check ==="
echo "$(date)"
echo

# Must run as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    echo "Usage: sudo ./quick_error_check.sh"
    exit 1
fi

echo "=== IMMEDIATE SERVICE STATUS ==="
systemctl is-active trackandtrace.service
systemctl is-enabled trackandtrace.service
echo

echo "=== LAST 10 ERROR LOGS ==="
journalctl -u trackandtrace.service -n 10 --no-pager -p err
echo

echo "=== LAST FAILED ATTEMPT ==="
journalctl -u trackandtrace.service --since "5 minutes ago" --no-pager | tail -20
echo

echo "=== QUICK MANUAL TEST ==="
echo "Testing manual run (10 second timeout):"
sudo -u trackandtrace bash -c "
    cd /opt/trackandtrace 2>/dev/null || { echo 'Cannot access /opt/trackandtrace'; exit 1; }
    source /opt/trackandtrace/venv/bin/activate 2>/dev/null || { echo 'Cannot activate venv'; exit 1; }
    export \$(cat /etc/trackandtrace/config.env | grep -v '^#' | grep -v '^$' | xargs) 2>/dev/null || echo 'Warning: Could not load config.env'
    timeout 10s python -m trackandtrace.main_service start 2>&1
" || echo "Manual test failed"
echo

echo "=== QUICK FIXES ==="
echo "1. Check config permissions: sudo ./fix_config_permissions.sh"
echo "2. Run full diagnosis: sudo ./diagnose_service_failure.sh"
echo "3. Try manual run: sudo ./run_production_manual.sh"
echo "4. Check service file: sudo systemctl cat trackandtrace.service" 