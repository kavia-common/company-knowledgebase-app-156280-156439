from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def init_db():
    # Place for migrations (Alembic), ensure connection
    async with engine.begin() as conn:
        await conn.run_sync(lambda conn: None)

async def close_db():
    await engine.dispose()

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
