from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass

# المحرك Engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# جلسة الاتصال بالقاعدة
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
