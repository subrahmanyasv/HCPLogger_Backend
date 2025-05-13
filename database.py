# backend/database.py

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings
from dotenv import load_dotenv, find_dotenv


expected_dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
print(f"Expected .env path: {expected_dotenv_path}")
loaded_successfully = load_dotenv(dotenv_path=expected_dotenv_path, override=True, verbose=True)
print(f"load_dotenv executed. Success: {loaded_successfully}")


# Define the default SQLite database file name
DEFAULT_DB_FILE = "hcp_interactions.db"
# Construct the default database URL relative to the current file's directory
# This ensures the .db file is created within the backend folder
DATABASE_FILE_PATH = os.path.join(os.path.dirname(__file__), DEFAULT_DB_FILE)

class Settings(BaseSettings):
    """Loads database configuration from environment variables."""
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DATABASE_FILE_PATH}")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY") # Get API key

    class Config:
        env_file = '.env' # Specify the .env file name if needed

settings = Settings()

# Create the SQLAlchemy async engine for SQLite
# connect_args={"check_same_thread": False} is required for SQLite with FastAPI/asyncio
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True, # echo=True for logging SQL
    connect_args={"check_same_thread": False} # Important for SQLite async usage
)

# Create a configured "Session" class
# expire_on_commit=False prevents attributes from expiring after commit
AsyncSessionFactory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency to get a DB session in path operations
async def get_db():
    """ FastAPI dependency that provides an AsyncSession """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit() # Commit the transaction after the request
        except Exception:
            await session.rollback() # Rollback in case of errors
            raise
        finally:
            await session.close()

# Base class for declarative class definitions
Base = declarative_base()

async def init_db():
    """ Initialize the database (create tables in the SQLite file) """
    print(f"Initializing SQLite database at: {settings.DATABASE_URL}")
    async with engine.begin() as conn:
        # This will create the .db file if it doesn't exist and create tables
        # await conn.run_sync(Base.metadata.drop_all) # Uncomment to drop tables first
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created (if they didn't exist).")

