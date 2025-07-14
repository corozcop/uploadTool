# Manual Update Steps for Production Service

## Step 1: Upload the fixed files to your server

```bash
# Copy the updated service file to your server
scp systemd/trackandtrace.service user@your-server:/tmp/
scp fix_production.sh user@your-server:/tmp/
```

## Step 2: Connect to your server and run the update

```bash
# SSH into your production server
ssh user@your-server

# Navigate to the project directory (if you have it)
cd /opt/trackandtrace

# Or work from /tmp where you uploaded the files
cd /tmp
```

## Step 3: Stop the service

```bash
sudo systemctl stop trackandtrace
```

## Step 4: Update the service file

```bash
# Backup the current service file
sudo cp /etc/systemd/system/trackandtrace.service /etc/systemd/system/trackandtrace.service.backup

# Copy the updated service file
sudo cp trackandtrace.service /etc/systemd/system/

# Or if you're in the project directory:
sudo cp systemd/trackandtrace.service /etc/systemd/system/
```

## Step 5: Reload and restart

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Start the service
sudo systemctl start trackandtrace

# Check status
sudo systemctl status trackandtrace
```

## Step 6: Verify the fix

```bash
# Test configuration
sudo trackandtrace-test

# Monitor logs
sudo journalctl -u trackandtrace -f
```

## Step 7: Enable automatic startup (if not already done)

```bash
sudo systemctl enable trackandtrace
``` 