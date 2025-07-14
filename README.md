# Track and Trace Email Processing Service

A production-grade Python service that monitors email inboxes for Excel attachments and processes them into a PostgreSQL database. Designed to run as a background service on Debian-based Linux systems.

## Features

- **Email Monitoring**: Secure IMAP connection with configurable filters
- **Excel Processing**: Automatic download and processing of Excel attachments
- **Database Integration**: PostgreSQL integration with upsert operations
- **Duplicate Detection**: File and content-based duplicate prevention
- **Queue Processing**: Sequential job processing to avoid concurrency issues
- **Systemd Integration**: Native Linux service with automatic startup
- **Structured Logging**: Comprehensive logging with rotation
- **Error Handling**: Robust error handling and retry mechanisms
- **Configuration Management**: Environment-based configuration
- **Monitoring**: Built-in statistics and status monitoring

## Architecture

### Core Components

1. **Email Monitor** (`email_monitor.py`): IMAP client for inbox monitoring
2. **Database Handler** (`database_handler.py`): PostgreSQL operations and connection management
3. **File Processor** (`file_processor.py`): Excel file processing and duplicate detection
4. **Queue Processor** (`queue_processor.py`): Sequential job processing system
5. **Main Service** (`main_service.py`): Service coordination and scheduling
6. **Configuration Manager** (`config.py`): Environment-based configuration

### Data Flow

```
Email Inbox → Email Monitor → Queue Processor → File Processor → Database Handler → PostgreSQL
```

## Installation

### System Requirements

- Debian-based Linux system (Ubuntu, Debian, etc.)
- Python 3.8+
- PostgreSQL 12+
- Root access for installation

### Automated Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourorg/trackandtrace-upload.git
   cd trackandtrace-upload
   ```

2. Run the deployment script:
   ```bash
   sudo ./deployment/deploy.sh install
   ```

3. Configure the service:
   ```bash
   sudo nano /etc/trackandtrace/config.env
   ```

4. Test the configuration:
   ```bash
   trackandtrace-test
   ```

5. Start the service:
   ```bash
   sudo systemctl start trackandtrace.service
   ```

### Manual Installation

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create configuration file:
   ```bash
   cp config.env.example config.env
   # Edit config.env with your settings
   ```

3. Create required directories:
   ```bash
   sudo mkdir -p /var/lib/trackandtrace/{pending,processed,logs}
   sudo mkdir -p /var/log/trackandtrace
   ```

4. Run the service:
   ```bash
   python -m trackandtrace.main_service start
   ```

## Configuration

### Environment Variables

#### Email Configuration
- `EMAIL_HOST`: IMAP server hostname (default: imap.gmail.com)
- `EMAIL_PORT`: IMAP server port (default: 993)
- `EMAIL_USERNAME`: Email username
- `EMAIL_PASSWORD`: Email password or app password
- `EMAIL_USE_SSL`: Use SSL connection (default: true)
- `EMAIL_SUBJECT_FILTER`: Subject line filter (default: "Track and Trace")
- `EMAIL_FOLDER`: Email folder to monitor (default: INBOX)

#### Database Configuration
- `DB_HOST`: PostgreSQL host (default: localhost)
- `DB_PORT`: PostgreSQL port (default: 5432)
- `DB_NAME`: Database name
- `DB_USERNAME`: Database username
- `DB_PASSWORD`: Database password
- `DB_TEMP_SCHEMA`: Temporary schema name (default: temp_processing)
- `DB_TARGET_TABLE`: Target table name (default: tracking_data)
- `DB_UNIQUE_KEY`: Unique key column (default: hawb)

#### Processing Configuration
- `APP_BASE_DIR`: Base directory for data storage (default: /var/lib/trackandtrace)
- `MAX_CONCURRENT_JOBS`: Maximum concurrent jobs (default: 1)
- `SCHEDULE_INTERVAL_HOURS`: Processing interval in hours (default: 1)
- `FILE_RETENTION_DAYS`: File retention period (default: 30)

#### Application Configuration
- `DEBUG`: Enable debug mode (default: false)
- `LOG_LEVEL`: Logging level (default: INFO)

### Example Configuration

```env
# Email Configuration
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USERNAME=processing@yourcompany.com
EMAIL_PASSWORD=your-app-password
EMAIL_SUBJECT_FILTER=Track and Trace Data

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trackandtrace
DB_USERNAME=trackandtrace
DB_PASSWORD=secure-password
DB_UNIQUE_KEY=hawb

# Processing Configuration
SCHEDULE_INTERVAL_HOURS=1
FILE_RETENTION_DAYS=30
LOG_LEVEL=INFO
```

## Usage

### Service Management

```bash
# Start service
sudo systemctl start trackandtrace.service

# Stop service
sudo systemctl stop trackandtrace.service

# Restart service
sudo systemctl restart trackandtrace.service

# Check status
sudo systemctl status trackandtrace.service

# View logs
sudo journalctl -u trackandtrace.service -f
```

### Management Commands

```bash
# Start service manually
trackandtrace-start

# Stop service
trackandtrace-stop

# Check service status
trackandtrace-status

# View logs
trackandtrace-logs

# Test configuration
trackandtrace-test
```

### Command Line Options

```bash
# Run service (default)
python -m trackandtrace.main_service start

# Run once and exit
python -m trackandtrace.main_service run-once

# Test configuration
python -m trackandtrace.main_service test-config

# Check service status
python -m trackandtrace.main_service status
```

## Database Schema

### Target Table Structure

The service expects a PostgreSQL table with the following structure:

```sql
CREATE TABLE tracking_data (
    hawb VARCHAR(50) PRIMARY KEY,
    -- Add your specific columns here
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_source VARCHAR(255),
    -- Additional tracking fields
);
```

### Temporary Schema

The service creates a temporary schema for processing:

```sql
CREATE SCHEMA IF NOT EXISTS temp_processing;
```

## Monitoring and Logging

### Log Files

- **Main Log**: `/var/log/trackandtrace/trackandtrace.log`
- **Email Processing**: `/var/log/trackandtrace/email_processing.log`
- **Database Operations**: `/var/log/trackandtrace/database_processing.log`
- **File Processing**: `/var/log/trackandtrace/file_processing.log`
- **Error Log**: `/var/log/trackandtrace/errors.log`

### Log Rotation

Logs are automatically rotated daily with 30-day retention using logrotate.

### Monitoring

The service provides built-in monitoring capabilities:

- Processing statistics
- Queue status
- Job history
- Error tracking
- Performance metrics

## Error Handling

### Retry Mechanism

Jobs are automatically retried with exponential backoff:
- Maximum 3 retries per job
- Exponential backoff: 2^attempt seconds
- Failed jobs are logged with detailed error information

### Common Issues

1. **Database Connection Errors**
   - Check database credentials
   - Verify PostgreSQL service is running
   - Check network connectivity

2. **Email Authentication Errors**
   - Use app passwords for Gmail
   - Check firewall settings
   - Verify IMAP is enabled

3. **File Processing Errors**
   - Check file permissions
   - Verify Excel file format
   - Ensure required columns exist

## Security Considerations

### Service Security

- Runs as dedicated system user
- Minimal privileges
- Secure file permissions
- Protected configuration files

### Data Security

- Encrypted database connections
- Secure email connections (SSL/TLS)
- Credential management via environment variables
- File integrity checks

## Performance Tuning

### Database Optimization

- Connection pooling enabled
- Batch operations for large datasets
- Temporary schema for processing
- Optimized upsert operations

### Memory Management

- Streaming file processing
- Automatic cleanup of temporary files
- Memory-efficient Excel processing

## Development

### Project Structure

```
trackandtrace/
├── trackandtrace/           # Main application package
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── logging_config.py   # Logging setup
│   ├── email_monitor.py    # Email monitoring
│   ├── database_handler.py # Database operations
│   ├── file_processor.py   # File processing
│   ├── queue_processor.py  # Job queue management
│   └── main_service.py     # Main service coordination
├── systemd/
│   └── trackandtrace.service  # Systemd service file
├── deployment/
│   └── deploy.sh           # Deployment script
├── requirements.txt        # Python dependencies
└── README.md
```

### Testing

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=trackandtrace tests/
```

### Code Quality

The project follows clean code principles:
- Type hints throughout
- Comprehensive error handling
- Structured logging
- Modular design
- Extensive documentation

## Deployment

### Production Deployment

1. **Database Setup**:
   ```sql
   CREATE DATABASE trackandtrace;
   CREATE USER trackandtrace WITH PASSWORD 'secure-password';
   GRANT ALL PRIVILEGES ON DATABASE trackandtrace TO trackandtrace;
   ```

2. **Service Installation**:
   ```bash
   sudo ./deployment/deploy.sh install
   ```

3. **Configuration**:
   ```bash
   sudo nano /etc/trackandtrace/config.env
   ```

4. **Service Start**:
   ```bash
   sudo systemctl start trackandtrace.service
   sudo systemctl enable trackandtrace.service
   ```

### Health Checks

The service includes built-in health checks:
- Database connectivity
- Email server connectivity
- File system permissions
- Configuration validation

## Troubleshooting

### Common Issues and Solutions

1. **Service Won't Start**
   ```bash
   # Check logs
   sudo journalctl -u trackandtrace.service -n 50
   
   # Test configuration
   trackandtrace-test
   
   # Check permissions
   sudo ls -la /var/lib/trackandtrace
   ```

2. **Database Connection Issues**
   ```bash
   # Test database connection
   sudo -u trackandtrace psql -h localhost -U trackandtrace -d trackandtrace
   
   # Check configuration
   grep DB_ /etc/trackandtrace/config.env
   ```

3. **Email Authentication Problems**
   ```bash
   # Test email connection
   python -c "
   import imaplib
   mail = imaplib.IMAP4_SSL('imap.gmail.com')
   mail.login('user@gmail.com', 'app-password')
   print('Connection successful')
   "
   ```

## Support

For issues and questions:
- Check the logs: `trackandtrace-logs`
- Review configuration: `/etc/trackandtrace/config.env`
- Test connectivity: `trackandtrace-test`
- Check service status: `trackandtrace-status`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

Please follow the existing code style and include appropriate tests for new functionality. 