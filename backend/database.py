import os
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set.")

# Create the async database engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create an ASYNC session maker
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_db_and_tables():
    """Asynchronously create all tables defined in the SQLModel metadata."""
    async with engine.begin() as conn:
        # Use run_sync for the synchronous create_all method
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession | Any, Any]:
    """FastAPI dependency to get an async database session."""
    async with async_session_maker() as session:
        yield session