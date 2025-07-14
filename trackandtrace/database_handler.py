"""
Database Handler Module
======================

Handles PostgreSQL database operations including connection management,
schema creation, and data operations.
"""

import os
import pandas as pd
import psycopg2
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import sqlalchemy
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, DateTime, Integer, Text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.pool import QueuePool

from .config import DatabaseConfig
from .logging_config import get_logger

logger = get_logger(__name__)


class DatabaseHandler:
    """Database handler for PostgreSQL operations"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine: Optional[sqlalchemy.Engine] = None
        self.SessionMaker: Optional[sessionmaker] = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize database connection and session maker"""
        try:
            connection_string = self._get_connection_string()
            
            # Create engine with connection pooling
            self.engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            
            # Create session maker
            self.SessionMaker = sessionmaker(bind=self.engine)
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def _get_connection_string(self) -> str:
        """Get database connection string"""
        return (
            f"postgresql://{self.config.username}:{self.config.password}@"
            f"{self.config.host}:{self.config.port}/{self.config.database}"
        )
    
    @contextmanager
    def get_session(self):
        """Get database session context manager"""
        if not self.SessionMaker:
            raise RuntimeError("Database connection not initialized")
        
        session = self.SessionMaker()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_connection(self):
        """Get database connection context manager"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        connection = self.engine.connect()
        try:
            yield connection
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            connection.close()
    
    def create_temp_schema(self) -> bool:
        """Create temporary schema if it doesn't exist"""
        try:
            with self.get_connection() as conn:
                # Check if schema exists
                schema_query = text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = :schema)"
                )
                result = conn.execute(schema_query, {"schema": self.config.temp_schema}).scalar()
                
                if not result:
                    # Create schema
                    create_schema_query = text(f"CREATE SCHEMA IF NOT EXISTS {self.config.temp_schema}")
                    conn.execute(create_schema_query)
                    conn.commit()
                    logger.info(f"Created temp schema: {self.config.temp_schema}")
                else:
                    logger.info(f"Temp schema already exists: {self.config.temp_schema}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating temp schema: {e}")
            return False
    
    def create_temp_table(self, table_name: str, df: pd.DataFrame) -> bool:
        """Create temporary table from DataFrame structure"""
        try:
            full_table_name = f"{self.config.temp_schema}.{table_name}"
            
            with self.get_connection() as conn:
                # Drop table if exists
                drop_query = text(f"DROP TABLE IF EXISTS {full_table_name}")
                conn.execute(drop_query)
                
                # Create table based on DataFrame structure
                df.to_sql(
                    table_name,
                    conn,
                    schema=self.config.temp_schema,
                    if_exists='replace',
                    index=False,
                    method='multi'
                )
                
                conn.commit()
                logger.info(f"Created temp table: {full_table_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating temp table {table_name}: {e}")
            return False
    
    def load_excel_to_temp_table(self, file_path: str, table_name: str) -> Tuple[bool, Optional[pd.DataFrame]]:
        """Load Excel file to temporary table"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            if df.empty:
                logger.warning(f"Excel file is empty: {file_path}")
                return False, None
            
            # Validate required columns
            if self.config.unique_key not in df.columns:
                logger.error(f"Required column '{self.config.unique_key}' not found in Excel file")
                return False, None
            
            # Clean and prepare data
            df = self._clean_dataframe(df)
            
            # Create temporary table
            if not self.create_temp_table(table_name, df):
                return False, None
            
            logger.info(f"Loaded {len(df)} records from {file_path} to temp table {table_name}")
            return True, df
            
        except Exception as e:
            logger.error(f"Error loading Excel file {file_path}: {e}")
            return False, None
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare DataFrame for database insertion"""
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Convert datetime columns
        for col in df.columns:
            if df[col].dtype == 'object':
                # Try to convert to datetime if it looks like a date
                try:
                    if any(df[col].astype(str).str.contains(r'\d{4}-\d{2}-\d{2}', na=False)):
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                except:
                    pass
        
        # Fill NaN values with appropriate defaults
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].fillna('')
            elif df[col].dtype in ['int64', 'float64']:
                df[col] = df[col].fillna(0)
        
        # Add processing metadata
        df['processed_at'] = datetime.now()
        df['file_source'] = 'email_attachment'
        
        return df
    
    def upsert_data_to_target_table(self, temp_table_name: str, target_table: str = None) -> bool:
        """Upsert data from temp table to target table"""
        if target_table is None:
            target_table = self.config.target_table
        
        try:
            full_temp_table = f"{self.config.temp_schema}.{temp_table_name}"
            unique_key = self.config.unique_key
            
            with self.get_connection() as conn:
                # Check if target table exists
                table_exists_query = text("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = :table_name
                    )
                """)
                
                table_exists = conn.execute(
                    table_exists_query, 
                    {"table_name": target_table}
                ).scalar()
                
                if not table_exists:
                    # Create target table from temp table structure
                    create_table_query = text(f"""
                        CREATE TABLE {target_table} AS 
                        SELECT * FROM {full_temp_table} WHERE 1=0
                    """)
                    conn.execute(create_table_query)
                    logger.info(f"Created target table: {target_table}")
                
                # Get column names from temp table
                columns_query = text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = :table_name AND table_schema = :schema
                    ORDER BY ordinal_position
                """)
                
                columns_result = conn.execute(columns_query, {
                    "table_name": temp_table_name,
                    "schema": self.config.temp_schema
                })
                columns = [row[0] for row in columns_result]
                
                # Prepare upsert query
                columns_str = ', '.join(columns)
                values_str = ', '.join([f"src.{col}" for col in columns])
                update_str = ', '.join([f"{col} = src.{col}" for col in columns if col != unique_key])
                
                upsert_query = text(f"""
                    INSERT INTO {target_table} ({columns_str})
                    SELECT {columns_str} FROM {full_temp_table} src
                    ON CONFLICT ({unique_key}) DO UPDATE SET
                    {update_str}
                """)
                
                result = conn.execute(upsert_query)
                conn.commit()
                
                logger.info(f"Upserted {result.rowcount} records to {target_table}")
                return True
                
        except Exception as e:
            logger.error(f"Error upserting data to target table: {e}")
            return False
    
    def cleanup_temp_table(self, table_name: str) -> bool:
        """Clean up temporary table"""
        try:
            full_table_name = f"{self.config.temp_schema}.{table_name}"
            
            with self.get_connection() as conn:
                drop_query = text(f"DROP TABLE IF EXISTS {full_table_name}")
                conn.execute(drop_query)
                conn.commit()
                
                logger.info(f"Cleaned up temp table: {full_table_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up temp table {table_name}: {e}")
            return False
    
    def get_record_count(self, table_name: str, schema: str = None) -> int:
        """Get record count from table"""
        try:
            if schema:
                full_table_name = f"{schema}.{table_name}"
            else:
                full_table_name = table_name
            
            with self.get_connection() as conn:
                count_query = text(f"SELECT COUNT(*) FROM {full_table_name}")
                result = conn.execute(count_query).scalar()
                return result or 0
                
        except Exception as e:
            logger.error(f"Error getting record count from {table_name}: {e}")
            return 0
    
    def check_duplicate_records(self, table_name: str, unique_key_values: List[str]) -> List[str]:
        """Check for duplicate records in target table"""
        try:
            placeholders = ', '.join([f"'{val}'" for val in unique_key_values])
            
            with self.get_connection() as conn:
                duplicate_query = text(f"""
                    SELECT {self.config.unique_key} 
                    FROM {self.config.target_table} 
                    WHERE {self.config.unique_key} IN ({placeholders})
                """)
                
                result = conn.execute(duplicate_query)
                duplicates = [row[0] for row in result]
                
                logger.info(f"Found {len(duplicates)} duplicate records")
                return duplicates
                
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
            return []
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        try:
            stats = {}
            
            with self.get_connection() as conn:
                # Total records in target table
                total_query = text(f"SELECT COUNT(*) FROM {self.config.target_table}")
                stats['total_records'] = conn.execute(total_query).scalar() or 0
                
                # Records processed today
                today_query = text(f"""
                    SELECT COUNT(*) FROM {self.config.target_table} 
                    WHERE DATE(processed_at) = CURRENT_DATE
                """)
                stats['today_records'] = conn.execute(today_query).scalar() or 0
                
                # Latest processing time
                latest_query = text(f"""
                    SELECT MAX(processed_at) FROM {self.config.target_table}
                """)
                stats['latest_processing'] = conn.execute(latest_query).scalar()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {}
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed") 