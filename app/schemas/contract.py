import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.contract import ContractStatus


class ContractBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    counterparty: str = Field(min_length=1, max_length=255)
    value: Decimal = Field(gt=0)
    start_date: date
    end_date: date
    category: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def check_date_order(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class ContractCreate(ContractBase):
    status: ContractStatus = ContractStatus.DRAFT


class ContractUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    counterparty: str | None = Field(default=None, min_length=1, max_length=255)
    value: Decimal | None = Field(default=None, gt=0)
    start_date: date | None = None
    end_date: date | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)
    status: ContractStatus | None = None

    @model_validator(mode="after")
    def check_date_order(self):
        # Both provided: can validate here. If only one is provided, the
        # service layer re-checks against the persisted value before commit.
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class ContractRead(ContractBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ContractStatus
    created_at: datetime
    updated_at: datetime
