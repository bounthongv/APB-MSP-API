import cx_Oracle
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings
import logging

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._connection_string = None
    
    def get_connection_string(self):
        """Build Oracle connection string for service name (not SID)"""
        if not self._connection_string:
            # Oracle connection string format for SQLAlchemy with SERVICE_NAME
            # Format: oracle+cx_oracle://user:pass@host:port/?service_name=XEPDB1
            self._connection_string = (
                f"oracle+cx_oracle://{settings.oracle_username}:"
                f"{settings.oracle_password}@"
                f"{settings.oracle_host}:{settings.oracle_port}/"
                f"?service_name={settings.oracle_service_name}"
            )
        return self._connection_string
    
    def create_engine(self):
        """Create database engine with connection pooling"""
        try:
            connection_string = self.get_connection_string()
            logger.info(f"Connecting to Oracle with: {connection_string}")
            
            self.engine = create_engine(
                connection_string,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=settings.api_debug  # Enable SQL logging in debug mode
            )
            logger.info("Database engine created successfully")
            return self.engine
        except Exception as e:
            logger.error(f"Failed to create database engine: {str(e)}")
            raise
    
    def create_session_factory(self):
        """Create session factory"""
        if not self.engine:
            self.create_engine()
        
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False
        )
        return self.SessionLocal
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1 FROM DUAL"))
                row = result.fetchone()
                if row and row[0] == 1:
                    logger.info("Database connection test successful")
                    return True
                else:
                    logger.error("Database connection test failed")
                    return False
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
    
    def get_session(self):
        """Get database session - for Flask"""
        if not self.SessionLocal:
            self.create_session_factory()
        
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()


# Global database manager instance
db_manager = DatabaseManager()

# Function for Flask
def get_db():
    """Database session generator for Flask"""
    return db_manager.get_session()

# Initialize database on module import
def init_database():
    """Initialize database connection"""
    try:
        db_manager.create_engine()
        db_manager.create_session_factory()
        
        # Test connection
        if db_manager.test_connection():
            logger.info("Database initialized successfully")
            return True
        else:
            logger.error("Database initialization failed - connection test failed")
            return False
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return False


# For manual testing
if __name__ == "__main__":
    print("Testing database connection...")
    if init_database():
        print("✅ Database connection successful!")
        
        # Test a simple query
        try:
            with db_manager.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) as asset_count FROM treasures"))
                count = result.fetchone()
                print(f"✅ Found {count[0]} assets in database")
        except Exception as e:
            print(f"❌ Error querying database: {str(e)}")
    else:
        print("❌ Database connection failed!")
