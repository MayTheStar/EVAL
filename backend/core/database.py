from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.core.core_config import settings

# إنشاء الاتصال بقاعدة البيانات
engine = create_engine(settings.DATABASE_URL, echo=False)

# إنشاء SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# قاعدة النماذج
Base = declarative_base()

# دالة لتوليد Session لكل طلب
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

