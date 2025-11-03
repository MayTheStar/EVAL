from sqlalchemy import Column, Text, Enum, ForeignKey, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base
import enum, uuid

class ReqPriority(str, enum.Enum):
    must = "must"
    should = "should"
    nice = "nice"

class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"))
    section: Mapped[str | None] = mapped_column(Text)
    requirement_text: Mapped[str] = mapped_column(Text)
    priority: Mapped[ReqPriority | None] = mapped_column(Enum(ReqPriority, native_enum=False))
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
