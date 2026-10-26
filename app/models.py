from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

def utc_now():
    return datetime.now(timezone.utc)

class UnderwritingRecord(Base):
    __tablename__ = "underwriting_records"
    application_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    applicant_reference: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)

class AuditRecord(Base):
    __tablename__ = "audit_records"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False)
