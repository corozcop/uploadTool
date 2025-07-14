"""
Main Service Module
==================

Main service daemon that coordinates all components and handles scheduled execution.
"""

import signal
import sys
import time
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import schedule
import threading
from pathlib import Path

from .config import config_manager
from .logging_config import setup_logging, get_logger
from .email_monitor import EmailMonitor
from .queue_processor import QueueProcessor
from .file_processor import FileProcessor
from .database_handler import DatabaseHandler

logger = get_logger(__name__)


class TrackAndTraceService:
    """Main service class that coordinates all components"""
    
    def __init__(self):
        self.config = config_manager.load_config()
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.queue_processor: Optional[QueueProcessor] = None
        self.email_monitor: Optional[EmailMonitor] = None
        self.file_processor: Optional[FileProcessor] = None
        self.db_handler: Optional[DatabaseHandler] = None
        self.last_run_time: Optional[datetime] = None
        self.run_count = 0
        self.setup_components()
        self.setup_signal_handlers()
    
    def setup_components(self):
        """Initialize all service components"""
        try:
            # Setup logging
            setup_logging(
                self.config.processing.log_dir,
                self.config.log_level,
                self.config.debug
            )
            
            logger.info("Initializing Track and Trace Service")
            
            # Initialize components
            self.queue_processor = QueueProcessor(self.config)
            self.email_monitor = EmailMonitor(self.config.email)
            self.file_processor = FileProcessor(self.config.processing)
            self.db_handler = DatabaseHandler(self.config.database)
            
            # Validate configuration
            if not config_manager.validate_config():
                raise Exception("Configuration validation failed")
            
            # Test database connection
            if not self.db_handler.test_connection():
                raise Exception("Database connection test failed")
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.stop()
    
    def start(self):
        """Start the service"""
        if self.is_running:
            logger.warning("Service is already running")
            return
        
        try:
            logger.info("Starting Track and Trace Service")
            
            # Start queue processor
            self.queue_processor.start_processing()
            
            # Schedule email processing
            self.setup_schedule()
            
            # Start scheduler thread
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            
            logger.info("Service started successfully")
            
            # Run initial processing
            self.run_email_processing()
            
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop the service"""
        if not self.is_running:
            logger.info("Service is already stopped")
            return
        
        logger.info("Stopping Track and Trace Service")
        
        # Stop the service
        self.is_running = False
        
        # Stop queue processor
        if self.queue_processor:
            self.queue_processor.stop_processing()
        
        # Wait for scheduler thread to finish
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=30)
        
        # Close database connections
        if self.db_handler:
            self.db_handler.close()
        
        logger.info("Service stopped successfully")
    
    def setup_schedule(self):
        """Setup scheduled tasks"""
        interval_hours = self.config.processing.schedule_interval_hours
        
        # Schedule email processing
        schedule.every(interval_hours).hours.do(self.run_email_processing)
        
        # Schedule daily cleanup
        schedule.every().day.at("02:00").do(self.run_daily_cleanup)
        
        # Schedule weekly statistics logging
        schedule.every().week.do(self.log_weekly_stats)
        
        logger.info(f"Scheduled email processing every {interval_hours} hour(s)")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
        
        logger.info("Scheduler loop stopped")
    
    def run_email_processing(self):
        """Run email processing cycle"""
        try:
            logger.info("Starting email processing cycle")
            start_time = datetime.now()
            
            # Process emails and get jobs
            jobs = self.email_monitor.process_emails(self.config.processing.pending_dir)
            
            if not jobs:
                logger.info("No jobs to process")
                return
            
            # Add jobs to queue
            self.queue_processor.add_jobs(jobs)
            
            # Update statistics
            self.last_run_time = datetime.now()
            self.run_count += 1
            
            processing_time = (self.last_run_time - start_time).total_seconds()
            
            logger.info(f"Email processing cycle completed in {processing_time:.2f} seconds")
            logger.info(f"Queued {len(jobs)} jobs for processing")
            
        except Exception as e:
            logger.error(f"Error in email processing cycle: {e}")
    
    def run_daily_cleanup(self):
        """Run daily cleanup tasks"""
        try:
            logger.info("Starting daily cleanup")
            
            # Cleanup old files
            self.file_processor.cleanup_old_files()
            
            # Clear completed jobs
            self.queue_processor.clear_completed_jobs()
            
            logger.info("Daily cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in daily cleanup: {e}")
    
    def log_weekly_stats(self):
        """Log weekly statistics"""
        try:
            logger.info("Generating weekly statistics")
            
            # Get processing statistics
            queue_stats = self.queue_processor.get_processing_stats()
            file_stats = self.file_processor.get_processing_stats()
            db_stats = self.db_handler.get_processing_stats()
            
            # Log statistics
            logger.info("Weekly Statistics Summary:")
            logger.info(f"  Total jobs processed: {queue_stats.get('total_jobs', 0)}")
            logger.info(f"  Successful jobs: {queue_stats.get('successful_jobs', 0)}")
            logger.info(f"  Failed jobs: {queue_stats.get('failed_jobs', 0)}")
            logger.info(f"  Total records processed: {queue_stats.get('total_records_processed', 0)}")
            logger.info(f"  Total files processed: {file_stats.get('total_processed_files', 0)}")
            logger.info(f"  Database records: {db_stats.get('total_records', 0)}")
            
        except Exception as e:
            logger.error(f"Error generating weekly statistics: {e}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current service status"""
        try:
            return {
                'is_running': self.is_running,
                'last_run_time': self.last_run_time.isoformat() if self.last_run_time else None,
                'run_count': self.run_count,
                'queue_status': self.queue_processor.get_queue_status() if self.queue_processor else {},
                'config': {
                    'schedule_interval_hours': self.config.processing.schedule_interval_hours,
                    'pending_dir': self.config.processing.pending_dir,
                    'processed_dir': self.config.processing.processed_dir,
                    'log_dir': self.config.processing.log_dir
                }
            }
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {'error': str(e)}
    
    def get_processing_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get processing history"""
        try:
            return self.queue_processor.get_job_history(limit) if self.queue_processor else []
        except Exception as e:
            logger.error(f"Error getting processing history: {e}")
            return []
    
    def force_email_processing(self) -> bool:
        """Force immediate email processing"""
        try:
            logger.info("Forcing immediate email processing")
            self.run_email_processing()
            return True
        except Exception as e:
            logger.error(f"Error forcing email processing: {e}")
            return False
    
    def run_daemon(self):
        """Run service as daemon"""
        try:
            logger.info("Starting service in daemon mode")
            
            # Start the service
            self.start()
            
            # Keep the main thread alive
            while self.is_running:
                time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Error in daemon mode: {e}")
        finally:
            self.stop()


def main():
    """Main entry point"""
    try:
        # Create service instance
        service = TrackAndTraceService()
        
        # Check command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == 'start':
                service.run_daemon()
            elif command == 'run-once':
                service.start()
                service.run_email_processing()
                service.stop()
            elif command == 'test-config':
                print("Configuration test passed")
            elif command == 'status':
                status = service.get_service_status()
                print(f"Service status: {status}")
            else:
                print(f"Unknown command: {command}")
                print("Available commands: start, run-once, test-config, status")
                sys.exit(1)
        else:
            # Default to daemon mode
            service.run_daemon()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 