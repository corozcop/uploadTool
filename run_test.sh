#!/bin/bash
set -e

# Load test configuration (ignore comments and empty lines)
echo "Loading test configuration..."
export $(grep -v '^#' test_config.env | grep -v '^$' | xargs)

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Run the test
echo "Running configuration test..."
python -m trackandtrace.main_service test-config

echo "Test completed with exit code: $?" 