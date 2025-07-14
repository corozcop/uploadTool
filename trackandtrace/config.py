"""
Configuration Management Module
==============================

Handles application configuration from environment variables and config files.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Email configuration settings"""
    host: str
    port: int
    username: str
    password: str
    use_ssl: bool = True
    subject_filter: str = "Track and Trace"
    folder: str = "INBOX"


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    host: str
    port: int
    database: str
    username: str
    password: str
    temp_schema: str = "temp_processing"
    target_table: str = "tracking_data"
    unique_key: str = "hawb"


@dataclass
class ProcessingConfig:
    """Processing configuration settings"""
    pending_dir: str
    processed_dir: str
    log_dir: str
    max_concurrent_jobs: int = 1
    schedule_interval_hours: int = 1
    file_retention_days: int = 30


@dataclass
class AppConfig:
    """Main application configuration"""
    email: EmailConfig
    database: DatabaseConfig
    processing: ProcessingConfig
    debug: bool = False
    log_level: str = "INFO"


class ConfigManager:
    """Configuration manager for the application"""
    
    def __init__(self):
        self._config: Optional[AppConfig] = None
    
    def load_config(self) -> AppConfig:
        """Load configuration from environment variables"""
        if self._config is None:
            self._config = self._create_config()
        return self._config
    
    def _create_config(self) -> AppConfig:
        """Create configuration from environment variables"""
        # Email configuration
        email_config = EmailConfig(
            host=self._get_env_var("EMAIL_HOST", "imap.gmail.com"),
            port=int(self._get_env_var("EMAIL_PORT", "993")),
            username=self._get_env_var("EMAIL_USERNAME"),
            password=self._get_env_var("EMAIL_PASSWORD"),
            use_ssl=self._get_env_var("EMAIL_USE_SSL", "true").lower() == "true",
            subject_filter=self._get_env_var("EMAIL_SUBJECT_FILTER", "Track and Trace"),
            folder=self._get_env_var("EMAIL_FOLDER", "INBOX")
        )
        
        # Database configuration
        database_config = DatabaseConfig(
            host=self._get_env_var("DB_HOST", "localhost"),
            port=int(self._get_env_var("DB_PORT", "5432")),
            database=self._get_env_var("DB_NAME"),
            username=self._get_env_var("DB_USERNAME"),
            password=self._get_env_var("DB_PASSWORD"),
            temp_schema=self._get_env_var("DB_TEMP_SCHEMA", "temp_processing"),
            target_table=self._get_env_var("DB_TARGET_TABLE", "tracking_data"),
            unique_key=self._get_env_var("DB_UNIQUE_KEY", "hawb")
        )
        
        # Processing configuration
        base_dir = Path(self._get_env_var("APP_BASE_DIR", "/var/lib/trackandtrace"))
        processing_config = ProcessingConfig(
            pending_dir=str(base_dir / "pending"),
            processed_dir=str(base_dir / "processed"),
            log_dir=str(base_dir / "logs"),
            max_concurrent_jobs=int(self._get_env_var("MAX_CONCURRENT_JOBS", "1")),
            schedule_interval_hours=int(self._get_env_var("SCHEDULE_INTERVAL_HOURS", "1")),
            file_retention_days=int(self._get_env_var("FILE_RETENTION_DAYS", "30"))
        )
        
        # Create directories if they don't exist
        self._ensure_directories_exist(processing_config)
        
        return AppConfig(
            email=email_config,
            database=database_config,
            processing=processing_config,
            debug=self._get_env_var("DEBUG", "false").lower() == "true",
            log_level=self._get_env_var("LOG_LEVEL", "INFO")
        )
    
    def _get_env_var(self, key: str, default: Optional[str] = None) -> str:
        """Get environment variable with optional default"""
        value = os.getenv(key, default)
        if value is None:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def _ensure_directories_exist(self, config: ProcessingConfig):
        """Ensure required directories exist"""
        for dir_path in [config.pending_dir, config.processed_dir, config.log_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {dir_path}")
    
    def get_database_url(self) -> str:
        """Get database connection URL"""
        config = self.load_config()
        db = config.database
        return f"postgresql://{db.username}:{db.password}@{db.host}:{db.port}/{db.database}"
    
    def validate_config(self) -> bool:
        """Validate configuration settings"""
        try:
            config = self.load_config()
            
            # Validate email configuration
            if not config.email.host or not config.email.username or not config.email.password:
                logger.error("Email configuration is incomplete")
                return False
            
            # Validate database configuration
            if not config.database.host or not config.database.database:
                logger.error("Database configuration is incomplete")
                return False
            
            # Validate directories
            for dir_path in [config.processing.pending_dir, config.processing.processed_dir]:
                if not Path(dir_path).exists():
                    logger.error(f"Directory does not exist: {dir_path}")
                    return False
            
            logger.info("Configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


# Global configuration manager instance
config_manager = ConfigManager() 