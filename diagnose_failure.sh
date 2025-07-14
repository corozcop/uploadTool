#!/bin/bash

# Comprehensive diagnostic script for trackandtrace service failure

echo "🔍 DIAGNOSING TRACKANDTRACE SERVICE FAILURE..."
echo "=============================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "❌ This script should be run as root for complete diagnosis"
    echo "   Run with: sudo ./diagnose_failure.sh"
    exit 1
fi

# 1. Check systemd journal logs
echo ""
echo "1. 📋 SYSTEMD JOURNAL LOGS (last 50 lines):"
echo "-------------------------------------------"
journalctl -u trackandtrace -n 50 --no-pager || echo "   ⚠️  No journal logs found"

# 2. Check service file
echo ""
echo "2. 📄 SERVICE FILE ANALYSIS:"
echo "----------------------------"
SERVICE_FILE="/etc/systemd/system/trackandtrace.service"
if [ -f "$SERVICE_FILE" ]; then
    echo "   ✅ Service file exists: $SERVICE_FILE"
    echo "   📋 Service file contents:"
    cat "$SERVICE_FILE"
else
    echo "   ❌ Service file NOT found: $SERVICE_FILE"
fi

# 3. Check configuration file
echo ""
echo "3. 📋 CONFIGURATION FILE ANALYSIS:"
echo "----------------------------------"
CONFIG_FILE="/etc/trackandtrace/config.env"
if [ -f "$CONFIG_FILE" ]; then
    echo "   ✅ Config file exists: $CONFIG_FILE"
    echo "   📄 Config file permissions:"
    ls -la "$CONFIG_FILE"
    echo "   📋 Config file contents (sensitive data hidden):"
    grep -v "PASSWORD\|password" "$CONFIG_FILE" | head -20
else
    echo "   ❌ Config file NOT found: $CONFIG_FILE"
fi

# 4. Check installation directory
echo ""
echo "4. 📁 INSTALLATION DIRECTORY ANALYSIS:"
echo "-------------------------------------"
INSTALL_DIR="/opt/trackandtrace"
if [ -d "$INSTALL_DIR" ]; then
    echo "   ✅ Installation directory exists: $INSTALL_DIR"
    echo "   📋 Directory permissions:"
    ls -la "$INSTALL_DIR"
    
    # Check Python virtual environment
    VENV_PYTHON="$INSTALL_DIR/venv/bin/python"
    if [ -f "$VENV_PYTHON" ]; then
        echo "   ✅ Virtual environment Python exists"
        echo "   📋 Python version:"
        "$VENV_PYTHON" --version
    else
        echo "   ❌ Virtual environment Python NOT found: $VENV_PYTHON"
    fi
    
    # Check main module
    MAIN_MODULE="$INSTALL_DIR/trackandtrace/main_service.py"
    if [ -f "$MAIN_MODULE" ]; then
        echo "   ✅ Main service module exists"
    else
        echo "   ❌ Main service module NOT found: $MAIN_MODULE"
    fi
else
    echo "   ❌ Installation directory NOT found: $INSTALL_DIR"
fi

# 5. Check data directories
echo ""
echo "5. 📁 DATA DIRECTORIES ANALYSIS:"
echo "-------------------------------"
DATA_DIR="/var/lib/trackandtrace"
LOG_DIR="/var/log/trackandtrace"

for dir in "$DATA_DIR" "$LOG_DIR"; do
    if [ -d "$dir" ]; then
        echo "   ✅ Directory exists: $dir"
        echo "   📋 Directory permissions:"
        ls -la "$dir"
    else
        echo "   ❌ Directory NOT found: $dir"
    fi
done

# 6. Check user and permissions
echo ""
echo "6. 👤 USER AND PERMISSIONS ANALYSIS:"
echo "-----------------------------------"
if id "trackandtrace" &>/dev/null; then
    echo "   ✅ User 'trackandtrace' exists"
    echo "   📋 User info:"
    id trackandtrace
else
    echo "   ❌ User 'trackandtrace' NOT found"
fi

# 7. Test manual execution
echo ""
echo "7. 🧪 MANUAL EXECUTION TEST:"
echo "---------------------------"
echo "   Testing manual execution as trackandtrace user..."
if [ -f "$CONFIG_FILE" ]; then
    echo "   Loading configuration and testing..."
    
    # Try to run the service manually
    echo "   Running: sudo -u trackandtrace /opt/trackandtrace/venv/bin/python -m trackandtrace.main_service test-config"
    
    # Source config and run test
    set +e  # Don't exit on error
    (
        source "$CONFIG_FILE"
        cd "$INSTALL_DIR"
        sudo -u trackandtrace "$INSTALL_DIR/venv/bin/python" -m trackandtrace.main_service test-config
    )
    TEST_EXIT_CODE=$?
    set -e
    
    echo "   Test exit code: $TEST_EXIT_CODE"
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo "   ✅ Manual test PASSED"
    else
        echo "   ❌ Manual test FAILED"
        echo "   This indicates the issue is in the service configuration or environment"
    fi
else
    echo "   ❌ Cannot test - config file not found"
fi

# 8. Check for common issues
echo ""
echo "8. 🔍 COMMON ISSUES CHECK:"
echo "-------------------------"

# Check if EnvironmentFile exists in service file
if grep -q "EnvironmentFile" "$SERVICE_FILE" 2>/dev/null; then
    echo "   ✅ EnvironmentFile directive found in service file"
else
    echo "   ❌ EnvironmentFile directive MISSING in service file"
    echo "   📋 This is likely the root cause!"
fi

# Check Python dependencies
echo "   🐍 Testing Python imports..."
cd "$INSTALL_DIR" 2>/dev/null || echo "   ⚠️  Cannot cd to install directory"
if [ -f "$VENV_PYTHON" ]; then
    "$VENV_PYTHON" -c "import trackandtrace.main_service; print('✅ Main module imports OK')" 2>/dev/null || echo "   ❌ Main module import failed"
    "$VENV_PYTHON" -c "import psycopg2; print('✅ PostgreSQL driver OK')" 2>/dev/null || echo "   ❌ PostgreSQL driver missing"
    "$VENV_PYTHON" -c "import pandas; print('✅ Pandas OK')" 2>/dev/null || echo "   ❌ Pandas missing"
fi

echo ""
echo "🎯 DIAGNOSIS SUMMARY:"
echo "==================="
echo "Check the sections above for ❌ marks - these indicate potential issues."
echo "Most common causes:"
echo "1. Missing EnvironmentFile in service file"
echo "2. Configuration file not found or wrong permissions"
echo "3. Installation directory or Python environment issues"
echo "4. User permissions problems"
echo ""
echo "Next steps:"
echo "1. Fix any ❌ issues found above"
echo "2. Run: sudo systemctl daemon-reload"
echo "3. Run: sudo systemctl restart trackandtrace"
echo "4. Run: sudo systemctl status trackandtrace" 