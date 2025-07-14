"""
File Processor Module
====================

Handles Excel file processing, duplicate detection, and file management operations.
"""

import os
import shutil
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd

from .config import ProcessingConfig
from .logging_config import get_logger

logger = get_logger(__name__)


class FileProcessor:
    """File processing and management class"""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.processed_files_db = Path(config.processed_dir) / "processed_files.json"
        self.duplicates_db = Path(config.processed_dir) / "duplicates_tracking.json"
        self._processed_files: Dict[str, Dict[str, Any]] = {}
        self._duplicates_tracking: Dict[str, List[str]] = {}
        self._load_processed_files()
        self._load_duplicates_tracking()
    
    def _load_processed_files(self):
        """Load processed files database"""
        try:
            if self.processed_files_db.exists():
                with open(self.processed_files_db, 'r') as f:
                    self._processed_files = json.load(f)
                logger.info(f"Loaded {len(self._processed_files)} processed files from database")
            else:
                self._processed_files = {}
                logger.info("No processed files database found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading processed files database: {e}")
            self._processed_files = {}
    
    def _load_duplicates_tracking(self):
        """Load duplicates tracking database"""
        try:
            if self.duplicates_db.exists():
                with open(self.duplicates_db, 'r') as f:
                    self._duplicates_tracking = json.load(f)
                logger.info(f"Loaded duplicates tracking with {len(self._duplicates_tracking)} entries")
            else:
                self._duplicates_tracking = {}
                logger.info("No duplicates tracking database found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading duplicates tracking database: {e}")
            self._duplicates_tracking = {}
    
    def _save_processed_files(self):
        """Save processed files database"""
        try:
            with open(self.processed_files_db, 'w') as f:
                json.dump(self._processed_files, f, indent=2, default=str)
            logger.debug("Saved processed files database")
        except Exception as e:
            logger.error(f"Error saving processed files database: {e}")
    
    def _save_duplicates_tracking(self):
        """Save duplicates tracking database"""
        try:
            with open(self.duplicates_db, 'w') as f:
                json.dump(self._duplicates_tracking, f, indent=2, default=str)
            logger.debug("Saved duplicates tracking database")
        except Exception as e:
            logger.error(f"Error saving duplicates tracking database: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash for {file_path}: {e}")
            return ""
    
    def _calculate_content_hash(self, df: pd.DataFrame) -> str:
        """Calculate hash of DataFrame content"""
        try:
            # Convert DataFrame to string and calculate hash
            content_str = df.to_string(index=False)
            return hashlib.md5(content_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating content hash: {e}")
            return ""
    
    def is_duplicate_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check if file is a duplicate based on hash"""
        try:
            file_hash = self._calculate_file_hash(file_path)
            
            if not file_hash:
                return False, None
            
            # Check if hash exists in processed files
            for processed_file, info in self._processed_files.items():
                if info.get('file_hash') == file_hash:
                    logger.warning(f"Duplicate file detected: {file_path} matches {processed_file}")
                    return True, processed_file
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking duplicate file {file_path}: {e}")
            return False, None
    
    def is_duplicate_content(self, df: pd.DataFrame, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check if DataFrame content is duplicate"""
        try:
            content_hash = self._calculate_content_hash(df)
            
            if not content_hash:
                return False, None
            
            # Check if content hash exists
            for processed_file, info in self._processed_files.items():
                if info.get('content_hash') == content_hash:
                    logger.warning(f"Duplicate content detected in {file_path}")
                    return True, processed_file
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking duplicate content: {e}")
            return False, None
    
    def validate_excel_file(self, file_path: str) -> Tuple[bool, Optional[str], Optional[pd.DataFrame]]:
        """Validate Excel file and return DataFrame if valid"""
        try:
            # Check file exists
            if not Path(file_path).exists():
                return False, f"File does not exist: {file_path}", None
            
            # Check file size
            file_size = Path(file_path).stat().st_size
            if file_size == 0:
                return False, f"File is empty: {file_path}", None
            
            # Check file extension
            if not file_path.lower().endswith(('.xlsx', '.xls')):
                return False, f"Not an Excel file: {file_path}", None
            
            # Try to read Excel file
            try:
                df = pd.read_excel(file_path)
            except Exception as e:
                return False, f"Error reading Excel file: {e}", None
            
            # Check if DataFrame is empty
            if df.empty:
                return False, f"Excel file contains no data: {file_path}", None
            
            # Check for minimum required columns (this can be configured)
            required_columns = ['hawb']  # Default required column
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return False, f"Missing required columns: {missing_columns}", None
            
            logger.info(f"Excel file validation successful: {file_path} ({len(df)} rows)")
            return True, None, df
            
        except Exception as e:
            logger.error(f"Error validating Excel file {file_path}: {e}")
            return False, f"Validation error: {e}", None
    
    def process_excel_file(self, file_path: str) -> Tuple[bool, Optional[str], Optional[pd.DataFrame]]:
        """Process Excel file with duplicate detection"""
        try:
            # Validate file
            is_valid, error_msg, df = self.validate_excel_file(file_path)
            
            if not is_valid:
                logger.error(f"File validation failed: {error_msg}")
                return False, error_msg, None
            
            # Check for file duplicates
            is_file_duplicate, duplicate_file = self.is_duplicate_file(file_path)
            if is_file_duplicate:
                error_msg = f"File is duplicate of {duplicate_file}"
                logger.warning(error_msg)
                return False, error_msg, None
            
            # Check for content duplicates
            is_content_duplicate, duplicate_content_file = self.is_duplicate_content(df, file_path)
            if is_content_duplicate:
                error_msg = f"Content is duplicate of {duplicate_content_file}"
                logger.warning(error_msg)
                return False, error_msg, None
            
            # Process and clean the DataFrame
            df = self._process_dataframe(df, file_path)
            
            logger.info(f"Successfully processed Excel file: {file_path}")
            return True, None, df
            
        except Exception as e:
            logger.error(f"Error processing Excel file {file_path}: {e}")
            return False, f"Processing error: {e}", None
    
    def _process_dataframe(self, df: pd.DataFrame, file_path: str) -> pd.DataFrame:
        """Process and clean DataFrame"""
        try:
            # Remove completely empty rows
            df = df.dropna(how='all')
            
            # Remove duplicate rows based on unique key
            unique_key = 'hawb'  # This should come from config
            if unique_key in df.columns:
                initial_count = len(df)
                df = df.drop_duplicates(subset=[unique_key], keep='first')
                removed_count = initial_count - len(df)
                
                if removed_count > 0:
                    logger.info(f"Removed {removed_count} duplicate rows from {file_path}")
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Add processing metadata
            df['file_source'] = Path(file_path).name
            df['processed_at'] = datetime.now()
            
            # Data type conversions and cleaning
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Clean string columns
                    df[col] = df[col].astype(str).str.strip()
                    df[col] = df[col].replace('nan', '')
                    df[col] = df[col].replace('', None)
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing DataFrame: {e}")
            return df
    
    def mark_file_as_processed(self, file_path: str, df: pd.DataFrame, 
                             processing_stats: Dict[str, Any]):
        """Mark file as processed in the database"""
        try:
            file_hash = self._calculate_file_hash(file_path)
            content_hash = self._calculate_content_hash(df)
            
            file_info = {
                'file_path': file_path,
                'file_hash': file_hash,
                'content_hash': content_hash,
                'processed_at': datetime.now().isoformat(),
                'file_size': Path(file_path).stat().st_size,
                'records_count': len(df),
                'processing_stats': processing_stats
            }
            
            self._processed_files[file_path] = file_info
            self._save_processed_files()
            
            logger.info(f"Marked file as processed: {file_path}")
            
        except Exception as e:
            logger.error(f"Error marking file as processed: {e}")
    
    def move_to_processed(self, file_path: str) -> bool:
        """Move file to processed directory"""
        try:
            source_path = Path(file_path)
            
            if not source_path.exists():
                logger.error(f"Source file does not exist: {file_path}")
                return False
            
            # Create timestamp-based subdirectory
            timestamp = datetime.now().strftime("%Y%m%d")
            processed_subdir = Path(self.config.processed_dir) / timestamp
            processed_subdir.mkdir(parents=True, exist_ok=True)
            
            # Generate destination path
            destination_path = processed_subdir / source_path.name
            
            # Handle filename conflicts
            counter = 1
            while destination_path.exists():
                name, ext = source_path.stem, source_path.suffix
                destination_path = processed_subdir / f"{name}_{counter}{ext}"
                counter += 1
            
            # Move file
            shutil.move(str(source_path), str(destination_path))
            
            logger.info(f"Moved file to processed: {file_path} -> {destination_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving file to processed: {e}")
            return False
    
    def cleanup_old_files(self):
        """Clean up old processed files based on retention policy"""
        try:
            retention_days = self.config.file_retention_days
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            processed_dir = Path(self.config.processed_dir)
            deleted_count = 0
            
            for file_path in processed_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        if file_mtime < cutoff_date:
                            file_path.unlink()
                            deleted_count += 1
                            logger.debug(f"Deleted old file: {file_path}")
                            
                    except Exception as e:
                        logger.warning(f"Error deleting old file {file_path}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old files")
            
            # Clean up processed files database
            self._cleanup_processed_files_db(cutoff_date)
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _cleanup_processed_files_db(self, cutoff_date: datetime):
        """Clean up processed files database"""
        try:
            initial_count = len(self._processed_files)
            
            # Filter out old entries
            self._processed_files = {
                file_path: info for file_path, info in self._processed_files.items()
                if datetime.fromisoformat(info['processed_at']) >= cutoff_date
            }
            
            removed_count = initial_count - len(self._processed_files)
            
            if removed_count > 0:
                self._save_processed_files()
                logger.info(f"Cleaned up {removed_count} old entries from processed files database")
                
        except Exception as e:
            logger.error(f"Error cleaning up processed files database: {e}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get file processing statistics"""
        try:
            stats = {
                'total_processed_files': len(self._processed_files),
                'total_duplicates_detected': len(self._duplicates_tracking),
                'processed_today': 0,
                'processed_this_week': 0,
                'latest_processing': None
            }
            
            now = datetime.now()
            today = now.date()
            week_ago = now - timedelta(days=7)
            
            latest_processing = None
            
            for file_path, info in self._processed_files.items():
                processed_at = datetime.fromisoformat(info['processed_at'])
                
                if processed_at.date() == today:
                    stats['processed_today'] += 1
                
                if processed_at >= week_ago:
                    stats['processed_this_week'] += 1
                
                if latest_processing is None or processed_at > latest_processing:
                    latest_processing = processed_at
            
            stats['latest_processing'] = latest_processing
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {}
    
    def get_pending_files(self) -> List[str]:
        """Get list of pending files to process"""
        try:
            pending_dir = Path(self.config.pending_dir)
            pending_files = []
            
            for file_path in pending_dir.glob("*.xlsx"):
                pending_files.append(str(file_path))
            
            for file_path in pending_dir.glob("*.xls"):
                pending_files.append(str(file_path))
            
            logger.info(f"Found {len(pending_files)} pending files")
            return pending_files
            
        except Exception as e:
            logger.error(f"Error getting pending files: {e}")
            return [] 