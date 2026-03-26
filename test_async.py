import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, BigInteger, String, select

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)

engine = create_async_engine("sqlite+aiosqlite:///test_db.db", echo=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 1. Create User
    async with async_session() as session:
        u = User(tg_id=123, username="test")
        session.add(u)
        await session.commit()
        print("Created User: ", u.phone_number)
        
    # 2. Emulate get_or_create and update
    async with async_session() as session:
        u = (await session.execute(select(User).where(User.tg_id == 123))).scalar_one_or_none()
        print("Got User Before Update: ", u.phone_number)
        u.phone_number = "+7123"
        await session.commit()
        print("Updated User, object value is: ", u.phone_number)
        
    # 3. Read back
    async with async_session() as session:
        u = (await session.execute(select(User).where(User.tg_id == 123))).scalar_one_or_none()
        print("Got User After Update from DB: ", u.phone_number)

if __name__ == "__main__":
    asyncio.run(main())
