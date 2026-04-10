from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .saas_models import SaasBase

SAAS_DB_URL = "sqlite+aiosqlite:///saas_database.db"

saas_engine = create_async_engine(SAAS_DB_URL, echo=False)
saas_session = async_sessionmaker(saas_engine, expire_on_commit=False, class_=AsyncSession)


async def create_saas_db():
    async with saas_engine.begin() as conn:
        await conn.run_sync(SaasBase.metadata.create_all)
