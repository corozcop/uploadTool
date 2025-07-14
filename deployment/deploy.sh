#!/bin/bash

# Track and Trace Service Deployment Script
# This script installs and configures the Track and Trace service on a Debian-based system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="trackandtrace"
SERVICE_USER="trackandtrace"
SERVICE_GROUP="trackandtrace"
INSTALL_DIR="/opt/trackandtrace"
DATA_DIR="/var/lib/trackandtrace"
LOG_DIR="/var/log/trackandtrace"
CONFIG_FILE="/etc/trackandtrace/config.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        postgresql-client \
        supervisor \
        curl \
        wget \
        unzip
    
    log_info "System dependencies installed"
}

# Create service user and group
create_service_user() {
    log_info "Creating service user and group..."
    
    # Create group if it doesn't exist
    if ! getent group "$SERVICE_GROUP" > /dev/null 2>&1; then
        groupadd --system "$SERVICE_GROUP"
        log_info "Created group: $SERVICE_GROUP"
    fi
    
    # Create user if it doesn't exist
    if ! getent passwd "$SERVICE_USER" > /dev/null 2>&1; then
        useradd --system --gid "$SERVICE_GROUP" --shell /bin/false \
                --home-dir "$DATA_DIR" --create-home \
                --comment "Track and Trace Service" "$SERVICE_USER"
        log_info "Created user: $SERVICE_USER"
    fi
}

# Create directories
create_directories() {
    log_info "Creating directories..."
    
    # Create main directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$DATA_DIR"/{pending,processed,logs}
    mkdir -p "$LOG_DIR"
    mkdir -p "/etc/trackandtrace"
    
    # Set permissions
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DATA_DIR"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"
    
    log_info "Directories created and permissions set"
}

# Install application
install_application() {
    log_info "Installing application..."
    
    # Copy application files
    cp -r "$PROJECT_DIR/trackandtrace" "$INSTALL_DIR/"
    cp "$PROJECT_DIR/requirements.txt" "$INSTALL_DIR/"
    
    # Create virtual environment
    cd "$INSTALL_DIR"
    python3 -m venv venv
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Set permissions
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    
    log_info "Application installed"
}

# Create configuration file
create_config() {
    log_info "Creating configuration file..."
    
    cat > "$CONFIG_FILE" << 'EOF'
# Track and Trace Service Configuration
# Copy this file and update with your actual values

# Email Configuration
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_USE_SSL=true
EMAIL_SUBJECT_FILTER=Track and Trace
EMAIL_FOLDER=INBOX

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trackandtrace
DB_USERNAME=trackandtrace
DB_PASSWORD=your-db-password
DB_TEMP_SCHEMA=temp_processing
DB_TARGET_TABLE=tracking_data
DB_UNIQUE_KEY=hawb

# Processing Configuration
APP_BASE_DIR=/var/lib/trackandtrace
MAX_CONCURRENT_JOBS=1
SCHEDULE_INTERVAL_HOURS=1
FILE_RETENTION_DAYS=30

# Application Configuration
DEBUG=false
LOG_LEVEL=INFO
EOF
    
    chmod 600 "$CONFIG_FILE"
    chown root:root "$CONFIG_FILE"
    
    log_info "Configuration file created at $CONFIG_FILE"
}

# Install systemd service
install_systemd_service() {
    log_info "Installing systemd service..."
    
    # Copy service file
    cp "$PROJECT_DIR/systemd/trackandtrace.service" "/etc/systemd/system/"
    
    # Set permissions
    chmod 644 "/etc/systemd/system/trackandtrace.service"
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable trackandtrace.service
    
    log_info "Systemd service installed and enabled"
}

# Create management scripts
create_management_scripts() {
    log_info "Creating management scripts..."
    
    # Create start script
    cat > "/usr/local/bin/trackandtrace-start" << EOF
#!/bin/bash
source $CONFIG_FILE
cd $INSTALL_DIR
sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/python -m trackandtrace.main_service start
EOF
    
    # Create stop script
    cat > "/usr/local/bin/trackandtrace-stop" << EOF
#!/bin/bash
sudo systemctl stop trackandtrace.service
EOF
    
    # Create status script
    cat > "/usr/local/bin/trackandtrace-status" << EOF
#!/bin/bash
sudo systemctl status trackandtrace.service
EOF
    
    # Create logs script
    cat > "/usr/local/bin/trackandtrace-logs" << EOF
#!/bin/bash
sudo journalctl -u trackandtrace.service -f
EOF
    
    # Create test script
    cat > "/usr/local/bin/trackandtrace-test" << EOF
#!/bin/bash
source $CONFIG_FILE
cd $INSTALL_DIR
sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/python -m trackandtrace.main_service test-config
EOF
    
    # Set permissions
    chmod +x /usr/local/bin/trackandtrace-*
    
    log_info "Management scripts created"
}

# Create logrotate configuration
create_logrotate() {
    log_info "Creating logrotate configuration..."
    
    cat > "/etc/logrotate.d/trackandtrace" << EOF
$LOG_DIR/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $SERVICE_USER $SERVICE_GROUP
    postrotate
        systemctl reload trackandtrace.service > /dev/null 2>&1 || true
    endscript
}
EOF
    
    log_info "Logrotate configuration created"
}

# Display post-installation instructions
post_install_instructions() {
    log_info "Installation completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Edit the configuration file: $CONFIG_FILE"
    echo "2. Test the configuration: trackandtrace-test"
    echo "3. Start the service: systemctl start trackandtrace.service"
    echo "4. Check service status: trackandtrace-status"
    echo "5. View logs: trackandtrace-logs"
    echo
    echo "Management commands:"
    echo "- trackandtrace-start   : Start the service"
    echo "- trackandtrace-stop    : Stop the service"
    echo "- trackandtrace-status  : Check service status"
    echo "- trackandtrace-logs    : View service logs"
    echo "- trackandtrace-test    : Test configuration"
    echo
    echo "Service will be automatically started on boot."
}

# Uninstall function
uninstall() {
    log_info "Uninstalling Track and Trace service..."
    
    # Stop and disable service
    systemctl stop trackandtrace.service 2>/dev/null || true
    systemctl disable trackandtrace.service 2>/dev/null || true
    
    # Remove service file
    rm -f /etc/systemd/system/trackandtrace.service
    systemctl daemon-reload
    
    # Remove management scripts
    rm -f /usr/local/bin/trackandtrace-*
    
    # Remove logrotate configuration
    rm -f /etc/logrotate.d/trackandtrace
    
    # Remove directories (with confirmation)
    read -p "Remove data directory $DATA_DIR? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$DATA_DIR"
        log_info "Data directory removed"
    fi
    
    read -p "Remove installation directory $INSTALL_DIR? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
        log_info "Installation directory removed"
    fi
    
    read -p "Remove log directory $LOG_DIR? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$LOG_DIR"
        log_info "Log directory removed"
    fi
    
    read -p "Remove service user $SERVICE_USER? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        userdel "$SERVICE_USER" 2>/dev/null || true
        groupdel "$SERVICE_GROUP" 2>/dev/null || true
        log_info "Service user removed"
    fi
    
    log_info "Uninstallation completed"
}

# Main function
main() {
    case "${1:-install}" in
        install)
            check_root
            install_dependencies
            create_service_user
            create_directories
            install_application
            create_config
            install_systemd_service
            create_management_scripts
            create_logrotate
            post_install_instructions
            ;;
        uninstall)
            check_root
            uninstall
            ;;
        *)
            echo "Usage: $0 {install|uninstall}"
            exit 1
            ;;
    esac
}

# Run main function
main "$@" 