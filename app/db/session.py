"""Database engine lifecycle and FastAPI session dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base


@dataclass(slots=True)
class Database:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]

    @classmethod
    def create(cls, url: str) -> Database:
        if url.startswith("sqlite+aiosqlite:///") and ":memory:" not in url:
            Path(url.removeprefix("sqlite+aiosqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        engine = create_async_engine(url, pool_pre_ping=True)
        return cls(engine=engine, sessions=async_sessionmaker(engine, expire_on_commit=False))

    async def create_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def aclose(self) -> None:
        await self.engine.dispose()


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.sessions() as session:
        yield session
