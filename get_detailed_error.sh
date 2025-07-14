#!/bin/bash

# Get detailed error information from trackandtrace service

echo "=== Getting Detailed Error Information ==="
echo

# Must run as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

echo "=== 1. MANUAL RUN WITH FULL ERROR OUTPUT ==="
echo "Running service manually to capture actual error:"
sudo -u trackandtrace bash -c "
    cd /opt/trackandtrace
    source /opt/trackandtrace/venv/bin/activate
    echo 'Loading environment...'
    export \$(cat /etc/trackandtrace/config.env | grep -v '^#' | grep -v '^$' | xargs) 2>/dev/null || echo 'Could not load config.env'
    echo 'Starting service...'
    python -m trackandtrace.main_service start
" 2>&1
echo

echo "=== 2. CHECK CONFIG FILE ACCESS ==="
if sudo -u trackandtrace test -r /etc/trackandtrace/config.env; then
    echo "✅ Config file is readable"
    echo "Environment variables available:"
    sudo -u trackandtrace bash -c "
        export \$(cat /etc/trackandtrace/config.env | grep -v '^#' | grep -v '^$' | xargs)
        env | grep -E '^(DB_|GMAIL_|LOG_|DATA_)' | sort
    " 2>/dev/null || echo "Could not load environment variables"
else
    echo "❌ Config file is NOT readable by trackandtrace user"
    echo "Fix with: sudo chown root:trackandtrace /etc/trackandtrace/config.env"
    echo "          sudo chmod 640 /etc/trackandtrace/config.env"
fi
echo

echo "=== 3. CHECK PYTHON IMPORT ==="
sudo -u trackandtrace bash -c "
    cd /opt/trackandtrace
    source /opt/trackandtrace/venv/bin/activate
    python -c 'import trackandtrace; print(\"Import successful\")'
" 2>&1
echo

echo "=== 4. CHECK SPECIFIC MODULE ==="
sudo -u trackandtrace bash -c "
    cd /opt/trackandtrace
    source /opt/trackandtrace/venv/bin/activate
    python -c 'from trackandtrace.main_service import main; print(\"Main service import successful\")'
" 2>&1
echo

echo "=== 5. VERBOSE SYSTEMD LOGS ==="
echo "Last 5 lines with all details:"
journalctl -u trackandtrace.service -n 5 --no-pager -o verbose
echo

echo "=== SUMMARY ==="
echo "The manual run above should show the exact error causing the failure." 