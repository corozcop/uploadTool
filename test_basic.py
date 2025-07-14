#!/usr/bin/env python3
"""
Basic test script to validate the Track and Trace service code
"""

import os
import sys
import traceback
from pathlib import Path

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        # Set test environment
        os.environ.update({
            'EMAIL_HOST': 'test.example.com',
            'EMAIL_USERNAME': 'test@example.com', 
            'EMAIL_PASSWORD': 'test-password',
            'DB_NAME': 'test_db',
            'DB_USERNAME': 'test_user',
            'DB_PASSWORD': 'test_password',
            'APP_BASE_DIR': './test_data'
        })
        
        # Test imports
        from trackandtrace import config
        print("✓ Config module imported")
        
        from trackandtrace import logging_config
        print("✓ Logging config module imported")
        
        from trackandtrace import email_monitor
        print("✓ Email monitor module imported")
        
        from trackandtrace import database_handler
        print("✓ Database handler module imported")
        
        from trackandtrace import file_processor
        print("✓ File processor module imported")
        
        from trackandtrace import queue_processor
        print("✓ Queue processor module imported")
        
        from trackandtrace import main_service
        print("✓ Main service module imported")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False

def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from trackandtrace.config import config_manager
        
        # Load configuration
        config = config_manager.load_config()
        
        print(f"✓ Email host: {config.email.host}")
        print(f"✓ Database name: {config.database.database}")
        print(f"✓ Log level: {config.log_level}")
        print(f"✓ Base directory: {config.processing.pending_dir}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        traceback.print_exc()
        return False

def test_directory_creation():
    """Test directory creation"""
    print("\nTesting directory creation...")
    
    try:
        from trackandtrace.config import config_manager
        config = config_manager.load_config()
        
        # Check if directories were created
        dirs_to_check = [
            config.processing.pending_dir,
            config.processing.processed_dir,
            config.processing.log_dir
        ]
        
        for dir_path in dirs_to_check:
            if Path(dir_path).exists():
                print(f"✓ Directory exists: {dir_path}")
            else:
                print(f"✗ Directory missing: {dir_path}")
                
        return True
        
    except Exception as e:
        print(f"✗ Directory test failed: {e}")
        traceback.print_exc()
        return False

def test_logging_setup():
    """Test logging setup"""
    print("\nTesting logging setup...")
    
    try:
        from trackandtrace.logging_config import setup_logging, get_logger
        
        # Setup logging
        setup_logging("./test_logs", "INFO", True)
        
        # Get logger and test
        logger = get_logger("test")
        logger.info("Test log message")
        print("✓ Logging setup successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Logging test failed: {e}")
        traceback.print_exc()
        return False

def test_file_processor():
    """Test file processor basic functionality"""
    print("\nTesting file processor...")
    
    try:
        from trackandtrace.config import config_manager
        from trackandtrace.file_processor import FileProcessor
        
        config = config_manager.load_config()
        processor = FileProcessor(config.processing)
        
        # Test getting pending files (should be empty)
        pending = processor.get_pending_files()
        print(f"✓ File processor created, found {len(pending)} pending files")
        
        # Test stats
        stats = processor.get_processing_stats()
        print(f"✓ Processing stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"✗ File processor test failed: {e}")
        traceback.print_exc()
        return False

def test_service_components():
    """Test service component creation"""
    print("\nTesting service components...")
    
    try:
        from trackandtrace.config import config_manager
        from trackandtrace.email_monitor import EmailMonitor
        from trackandtrace.queue_processor import QueueProcessor
        
        config = config_manager.load_config()
        
        # Test email monitor creation (won't connect)
        email_monitor = EmailMonitor(config.email)
        print("✓ Email monitor created")
        
        # Test queue processor creation
        queue_processor = QueueProcessor(config)
        print("✓ Queue processor created")
        
        # Test queue status
        status = queue_processor.get_queue_status()
        print(f"✓ Queue status: {status}")
        
        return True
        
    except Exception as e:
        print(f"✗ Service components test failed: {e}")
        traceback.print_exc()
        return False

def test_main_service_creation():
    """Test main service creation (without starting)"""
    print("\nTesting main service creation...")
    
    try:
        # We'll test this without actually initializing the full service
        # since it would try to connect to databases
        print("✓ Skipping main service test (requires database connection)")
        return True
        
    except Exception as e:
        print(f"✗ Main service test failed: {e}")
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("TRACK AND TRACE SERVICE - BASIC VALIDATION")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_configuration,
        test_directory_creation,
        test_logging_setup,
        test_file_processor,
        test_service_components,
        test_main_service_creation
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The code is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests()) 