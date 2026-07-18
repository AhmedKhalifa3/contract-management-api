import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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

    @field_validator("status")
    @classmethod
    def must_be_initial_status(cls, v: ContractStatus) -> ContractStatus:
        # expiring/expired/renewed only make sense as the result of a
        # transition or renewal event, not as a starting point.
        if v not in (ContractStatus.DRAFT, ContractStatus.ACTIVE):
            raise ValueError("new contracts must start as 'draft' or 'active'")
        return v


class ContractUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    counterparty: str | None = Field(default=None, min_length=1, max_length=255)
    value: Decimal | None = Field(default=None, gt=0)
    start_date: date | None = None
    end_date: date | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)

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


class ContractTransition(BaseModel):
    status: ContractStatus


class ContractRenewal(BaseModel):
    new_end_date: date
    notes: str | None = None

    @field_validator("new_end_date")
    @classmethod
    def must_be_future(cls, v: date) -> date:
        if v <= date.today():
            raise ValueError("new_end_date must be in the future")
        return v
