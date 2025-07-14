"""
Logging Configuration Module
===========================

Configures structured logging for the application with proper formatting and levels.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import structlog
from colorlog import ColoredFormatter


class LoggingConfig:
    """Logging configuration and setup"""
    
    def __init__(self, log_dir: str, log_level: str = "INFO", debug: bool = False):
        self.log_dir = Path(log_dir)
        self.log_level = log_level
        self.debug = debug
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """Setup logging configuration with structured logging"""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.ConsoleRenderer() if self.debug else structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.getLevelName(self.log_level)
            ),
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        # Setup standard logging
        self._setup_standard_logging()
        
        # Setup file logging
        self._setup_file_logging()
        
        # Setup console logging
        self._setup_console_logging()
    
    def _setup_standard_logging(self):
        """Setup standard Python logging"""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[]
        )
    
    def _setup_file_logging(self):
        """Setup file logging with rotation"""
        # Main application log
        app_log_file = self.log_dir / "trackandtrace.log"
        app_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        app_handler.setLevel(getattr(logging, self.log_level))
        app_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        app_handler.setFormatter(app_formatter)
        
        # Error log
        error_log_file = self.log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(app_formatter)
        
        # Add handlers to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(app_handler)
        root_logger.addHandler(error_handler)
        
        # Setup specific loggers
        self._setup_module_loggers()
    
    def _setup_console_logging(self):
        """Setup console logging with colors"""
        if self.debug:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            
            # Colored formatter for console
            color_formatter = ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(color_formatter)
            
            # Add to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(console_handler)
    
    def _setup_module_loggers(self):
        """Setup specific loggers for different modules"""
        # Email processing logger
        email_logger = logging.getLogger('trackandtrace.email')
        email_log_file = self.log_dir / "email_processing.log"
        email_handler = logging.handlers.RotatingFileHandler(
            email_log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        email_handler.setLevel(logging.INFO)
        email_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        email_handler.setFormatter(email_formatter)
        email_logger.addHandler(email_handler)
        
        # Database processing logger
        db_logger = logging.getLogger('trackandtrace.database')
        db_log_file = self.log_dir / "database_processing.log"
        db_handler = logging.handlers.RotatingFileHandler(
            db_log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        db_handler.setLevel(logging.INFO)
        db_handler.setFormatter(email_formatter)
        db_logger.addHandler(db_handler)
        
        # File processing logger
        file_logger = logging.getLogger('trackandtrace.file')
        file_log_file = self.log_dir / "file_processing.log"
        file_handler = logging.handlers.RotatingFileHandler(
            file_log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(email_formatter)
        file_logger.addHandler(file_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance"""
        return logging.getLogger(name)
    
    def get_structured_logger(self, name: str) -> structlog.stdlib.BoundLogger:
        """Get a structured logger instance"""
        return structlog.get_logger(name)


def setup_logging(log_dir: str, log_level: str = "INFO", debug: bool = False) -> LoggingConfig:
    """Setup application logging"""
    logging_config = LoggingConfig(log_dir, log_level, debug)
    logging_config.setup_logging()
    return logging_config


# Convenience function to get structured logger
def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger"""
    return structlog.get_logger(name) 