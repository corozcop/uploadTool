"""
Queue Processor Module
=====================

Handles sequential job processing to avoid concurrency issues.
"""

import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import queue
from pathlib import Path

from .config import AppConfig
from .email_monitor import EmailMonitor
from .database_handler import DatabaseHandler
from .file_processor import FileProcessor
from .logging_config import get_logger

logger = get_logger(__name__)


class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProcessingJob:
    """Processing job definition"""
    id: str
    email_uid: int
    subject: str
    sender: str
    date: datetime
    files: List[str]
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    processing_stats: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3


class JobProcessor:
    """Individual job processor"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.db_handler = DatabaseHandler(config.database)
        self.file_processor = FileProcessor(config.processing)
        self.email_monitor = EmailMonitor(config.email)
    
    def process_job(self, job: ProcessingJob) -> bool:
        """Process a single job"""
        try:
            job.status = JobStatus.IN_PROGRESS
            job.started_at = datetime.now()
            
            logger.info(f"Starting job processing: {job.id}")
            
            # Create temporary schema if not exists
            if not self.db_handler.create_temp_schema():
                raise Exception("Failed to create temporary schema")
            
            # Process each file in the job
            total_records = 0
            processed_files = []
            
            for file_path in job.files:
                try:
                    # Process Excel file
                    is_valid, error_msg, df = self.file_processor.process_excel_file(file_path)
                    
                    if not is_valid:
                        logger.error(f"File processing failed: {error_msg}")
                        continue
                    
                    # Generate unique temp table name
                    temp_table_name = f"temp_job_{job.id}_{uuid.uuid4().hex[:8]}"
                    
                    # Load to temporary table
                    success, loaded_df = self.db_handler.load_excel_to_temp_table(
                        file_path, temp_table_name
                    )
                    
                    if not success:
                        logger.error(f"Failed to load file to temp table: {file_path}")
                        continue
                    
                    # Upsert to target table
                    if not self.db_handler.upsert_data_to_target_table(temp_table_name):
                        logger.error(f"Failed to upsert data to target table: {file_path}")
                        continue
                    
                    # Get record count
                    record_count = len(loaded_df)
                    total_records += record_count
                    
                    # Mark file as processed
                    processing_stats = {
                        'records_processed': record_count,
                        'temp_table': temp_table_name,
                        'processing_time': (datetime.now() - job.started_at).total_seconds()
                    }
                    
                    self.file_processor.mark_file_as_processed(
                        file_path, loaded_df, processing_stats
                    )
                    
                    # Move file to processed directory
                    if self.file_processor.move_to_processed(file_path):
                        processed_files.append(file_path)
                        logger.info(f"Successfully processed file: {file_path}")
                    
                    # Clean up temp table
                    self.db_handler.cleanup_temp_table(temp_table_name)
                    
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    continue
            
            # Mark email as read if all files processed successfully
            if processed_files:
                try:
                    with self.email_monitor:
                        self.email_monitor.mark_email_as_read(job.email_uid)
                except Exception as e:
                    logger.warning(f"Failed to mark email as read: {e}")
            
            # Update job status
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.processing_stats = {
                'total_records': total_records,
                'processed_files': len(processed_files),
                'failed_files': len(job.files) - len(processed_files),
                'processing_time': (job.completed_at - job.started_at).total_seconds()
            }
            
            logger.info(f"Job completed successfully: {job.id}")
            return True
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            
            logger.error(f"Job failed: {job.id} - {e}")
            return False


class QueueProcessor:
    """Queue processor for sequential job execution"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.job_queue: queue.Queue = queue.Queue()
        self.job_processor = JobProcessor(config)
        self.processed_jobs: Dict[str, ProcessingJob] = {}
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def add_job(self, job_data: Dict[str, Any]) -> ProcessingJob:
        """Add a new job to the queue"""
        job = ProcessingJob(
            id=job_data['id'],
            email_uid=job_data['email_uid'],
            subject=job_data['subject'],
            sender=job_data['sender'],
            date=job_data['date'],
            files=job_data['files'],
            status=JobStatus.PENDING,
            created_at=datetime.now()
        )
        
        with self._lock:
            self.job_queue.put(job)
            logger.info(f"Added job to queue: {job.id}")
        
        return job
    
    def add_jobs(self, jobs_data: List[Dict[str, Any]]) -> List[ProcessingJob]:
        """Add multiple jobs to the queue"""
        jobs = []
        for job_data in jobs_data:
            job = self.add_job(job_data)
            jobs.append(job)
        
        logger.info(f"Added {len(jobs)} jobs to queue")
        return jobs
    
    def start_processing(self):
        """Start the queue processor"""
        if self.is_running:
            logger.warning("Queue processor is already running")
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info("Queue processor started")
    
    def stop_processing(self):
        """Stop the queue processor"""
        self.is_running = False
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=30)
        
        logger.info("Queue processor stopped")
    
    def _worker_loop(self):
        """Main worker loop for processing jobs"""
        while self.is_running:
            try:
                # Get job from queue with timeout
                job = self.job_queue.get(timeout=1)
                
                if job is None:
                    continue
                
                # Process job
                success = self._process_job_with_retry(job)
                
                # Store processed job
                with self._lock:
                    self.processed_jobs[job.id] = job
                
                # Mark task as done
                self.job_queue.task_done()
                
                # Log processing result
                if success:
                    logger.info(f"Job processed successfully: {job.id}")
                else:
                    logger.error(f"Job processing failed: {job.id}")
                
            except queue.Empty:
                # Timeout - continue loop
                continue
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                continue
    
    def _process_job_with_retry(self, job: ProcessingJob) -> bool:
        """Process job with retry logic"""
        for attempt in range(job.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retrying job {job.id} (attempt {attempt + 1})")
                    job.retry_count = attempt
                
                # Process the job
                success = self.job_processor.process_job(job)
                
                if success:
                    return True
                
                # If not the last attempt, wait before retrying
                if attempt < job.max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Job processing error (attempt {attempt + 1}): {e}")
                
                if attempt < job.max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    job.completed_at = datetime.now()
        
        return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        with self._lock:
            pending_jobs = self.job_queue.qsize()
            
            # Count jobs by status
            status_counts = {status.value: 0 for status in JobStatus}
            
            for job in self.processed_jobs.values():
                status_counts[job.status.value] += 1
            
            return {
                'is_running': self.is_running,
                'pending_jobs': pending_jobs,
                'total_processed': len(self.processed_jobs),
                'status_counts': status_counts
            }
    
    def get_job_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get job processing history"""
        with self._lock:
            jobs = list(self.processed_jobs.values())
            
            # Sort by completion time (most recent first)
            jobs.sort(key=lambda x: x.completed_at or x.created_at, reverse=True)
            
            # Convert to serializable format
            history = []
            for job in jobs[:limit]:
                history.append({
                    'id': job.id,
                    'email_uid': job.email_uid,
                    'subject': job.subject,
                    'sender': job.sender,
                    'status': job.status.value,
                    'created_at': job.created_at.isoformat(),
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'error_message': job.error_message,
                    'processing_stats': job.processing_stats,
                    'retry_count': job.retry_count
                })
            
            return history
    
    def get_active_job(self) -> Optional[ProcessingJob]:
        """Get currently active job"""
        with self._lock:
            for job in self.processed_jobs.values():
                if job.status == JobStatus.IN_PROGRESS:
                    return job
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        with self._lock:
            if job_id in self.processed_jobs:
                job = self.processed_jobs[job_id]
                if job.status == JobStatus.PENDING:
                    job.status = JobStatus.CANCELLED
                    job.completed_at = datetime.now()
                    logger.info(f"Job cancelled: {job_id}")
                    return True
                else:
                    logger.warning(f"Cannot cancel job in status {job.status.value}: {job_id}")
                    return False
            
            logger.warning(f"Job not found: {job_id}")
            return False
    
    def clear_completed_jobs(self):
        """Clear completed jobs from history"""
        with self._lock:
            initial_count = len(self.processed_jobs)
            
            self.processed_jobs = {
                job_id: job for job_id, job in self.processed_jobs.items()
                if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
            }
            
            cleared_count = initial_count - len(self.processed_jobs)
            
            if cleared_count > 0:
                logger.info(f"Cleared {cleared_count} completed jobs from history")
    
    def wait_for_completion(self, timeout: Optional[int] = None) -> bool:
        """Wait for all jobs to complete"""
        try:
            if timeout:
                self.job_queue.join()
                return True
            else:
                # Wait with timeout
                start_time = time.time()
                while not self.job_queue.empty():
                    if time.time() - start_time > timeout:
                        return False
                    time.sleep(0.1)
                return True
        except Exception as e:
            logger.error(f"Error waiting for completion: {e}")
            return False
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get overall processing statistics"""
        with self._lock:
            stats = {
                'total_jobs': len(self.processed_jobs),
                'successful_jobs': 0,
                'failed_jobs': 0,
                'cancelled_jobs': 0,
                'total_records_processed': 0,
                'total_files_processed': 0,
                'average_processing_time': 0
            }
            
            processing_times = []
            
            for job in self.processed_jobs.values():
                if job.status == JobStatus.COMPLETED:
                    stats['successful_jobs'] += 1
                    if job.processing_stats:
                        stats['total_records_processed'] += job.processing_stats.get('total_records', 0)
                        stats['total_files_processed'] += job.processing_stats.get('processed_files', 0)
                        
                        processing_time = job.processing_stats.get('processing_time', 0)
                        if processing_time > 0:
                            processing_times.append(processing_time)
                
                elif job.status == JobStatus.FAILED:
                    stats['failed_jobs'] += 1
                elif job.status == JobStatus.CANCELLED:
                    stats['cancelled_jobs'] += 1
            
            # Calculate average processing time
            if processing_times:
                stats['average_processing_time'] = sum(processing_times) / len(processing_times)
            
            return stats 