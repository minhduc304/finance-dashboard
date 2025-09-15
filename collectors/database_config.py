"""
Centralized database configuration for all collectors
Uses PostgreSQL from docker-compose configuration
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL configuration from docker-compose
POSTGRES_USER = os.getenv("POSTGRES_USER", "myapp_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "secure_password_123")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "myapp_db")

# Build database URL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

def get_database_session():
    """
    Create and return a database session
    """
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

def get_database_engine():
    """
    Get database engine for creating tables
    """
    return create_engine(DATABASE_URL)

def test_connection():
    """
    Test database connection
    """
    try:
        engine = get_database_engine()
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"Connected to PostgreSQL: {version}")
            return True
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    print("Testing database connection...")
    print(f"Database URL: postgresql://{POSTGRES_USER}:***@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    test_connection()