from sqlalchemy import Column, Text, Enum, ForeignKey, String, DateTime, func, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base
import enum, uuid

class ComplianceStatus(str, enum.Enum):
    compliant = "compliant"
    partially = "partially"
    non_compliant = "non_compliant"
    unclear = "unclear"

class VendorClaim(Base):
    __tablename__ = "vendor_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"))
    requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("requirements.id", ondelete="CASCADE"))
    claim_text: Mapped[str | None] = mapped_column(Text)
    evidence_pages: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    compliance: Mapped[ComplianceStatus | None] = mapped_column(Enum(ComplianceStatus, native_enum=False))
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("vendor_document_id", "requirement_id", name="uq_vendor_req"),
    )
