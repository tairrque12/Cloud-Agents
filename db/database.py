# db/database.py
# Inkbook — Database Connection
# SQLAlchemy async setup for PostgreSQL
# Last updated: April 30, 2026

import os
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# DATABASE URL
# For MVP uses local PostgreSQL
# For production uses AWS RDS URL
# ─────────────────────────────────────────

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/inkbook"
)

# ─────────────────────────────────────────
# ENGINE
# ─────────────────────────────────────────

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300
)

# ─────────────────────────────────────────
# SESSION FACTORY
# ─────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# ─────────────────────────────────────────
# BASE MODEL
# All ORM models inherit from this
# ─────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────
# DEPENDENCY
# Used in FastAPI routes to get a session
# ─────────────────────────────────────────

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()