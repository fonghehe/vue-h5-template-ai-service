"""Database engine lifecycle and FastAPI session dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from fastapi import Request
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.db.models import Base


@dataclass(slots=True)
class Database:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]

    @classmethod
    def create(cls, url: str, *, settings: Settings | None = None) -> Database:
        if url.startswith("sqlite+aiosqlite:///") and ":memory:" not in url:
            Path(url.removeprefix("sqlite+aiosqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        options: dict[str, object] = {"pool_pre_ping": True, "hide_parameters": True}
        if url.startswith("postgresql") and settings is not None:
            options.update(
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_timeout=settings.database_pool_timeout,
                pool_recycle=settings.database_pool_recycle,
            )
        engine = create_async_engine(url, **options)
        if engine.dialect.name == "sqlite":

            @event.listens_for(engine.sync_engine, "connect")
            def enable_foreign_keys(connection: object, _: object) -> None:
                cursor = connection.cursor()  # type: ignore[attr-defined]
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        return cls(engine=engine, sessions=async_sessionmaker(engine, expire_on_commit=False))

    async def create_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def ping(self) -> bool:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True

    async def aclose(self) -> None:
        await self.engine.dispose()


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.sessions() as session:
        yield session
