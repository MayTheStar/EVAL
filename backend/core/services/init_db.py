import asyncio
from ..database import engine, Base
from ..models.document import Document
from ..models.requirement import Requirement
from ..models.vendor_claim import VendorClaim

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
