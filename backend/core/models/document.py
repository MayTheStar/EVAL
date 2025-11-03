from sqlalchemy import Column, Text, Integer, Enum, JSON, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base
import enum, uuid

class DocSourceType(str, enum.Enum):
    rfp = "rfp"
    vendor_response = "vendor_response"
    other = "other"

class DocStatus(str, enum.Enum):
    uploaded = "uploaded"
    parsed = "parsed"
    failed = "failed"

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str | None] = mapped_column(Text)
    pages: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(Text, unique=True)
    source_type: Mapped[DocSourceType] = mapped_column(Enum(DocSourceType, native_enum=False))
    status: Mapped[DocStatus] = mapped_column(Enum(DocStatus, native_enum=False))
    uploaded_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    parsed_text: Mapped[str | None] = mapped_column(Text)
    metadata: Mapped[dict | None] = mapped_column(JSON, default=dict)
