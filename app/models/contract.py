import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    RENEWED = "renewed"


class Contract(UUIDPKMixin, TimestampMixin, db.Model):
    __tablename__ = "contracts"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    counterparty: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, name="contract_status"),
        nullable=False,
        default=ContractStatus.DRAFT,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    renewals: Mapped[list["RenewalHistory"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Contract {self.id} {self.title!r} {self.status.value}>"
