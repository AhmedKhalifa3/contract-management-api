import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin


class RenewalHistory(UUIDPKMixin, db.Model):
    __tablename__ = "renewal_history"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False, index=True
    )
    previous_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    new_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    renewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    contract: Mapped["Contract"] = relationship(back_populates="renewals")

    def __repr__(self) -> str:
        return f"<RenewalHistory {self.id} contract={self.contract_id}>"
