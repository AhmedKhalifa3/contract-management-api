import uuid

from app.extensions import db
from app.models import Contract, ContractStatus
from app.utils.exceptions import AppValidationError, NotFoundError


def create_contract(data: dict) -> Contract:
    contract = Contract(**data)
    db.session.add(contract)
    db.session.commit()
    return contract


def get_contract(contract_id: uuid.UUID) -> Contract:
    contract = db.session.get(Contract, contract_id)
    if contract is None:
        raise NotFoundError(f"Contract {contract_id} not found")
    return contract


def list_contracts(
    status: str | None = None,
    category: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Contract], int]:
    query = db.session.query(Contract)

    if status:
        try:
            status = ContractStatus(status)
        except ValueError:
            raise AppValidationError(f"invalid status: {status}")
        query = query.filter(Contract.status == status)

    if category:
        query = query.filter(Contract.category == category)

    total = query.count()
    items = (
        query.order_by(Contract.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return items, total


def update_contract(contract_id: uuid.UUID, data: dict) -> Contract:
    contract = get_contract(contract_id)

    for key, value in data.items():
        setattr(contract, key, value)

    if contract.end_date <= contract.start_date:
        db.session.rollback()
        raise AppValidationError("end_date must be after start_date")

    db.session.commit()
    return contract


def delete_contract(contract_id: uuid.UUID) -> None:
    contract = get_contract(contract_id)
    db.session.delete(contract)
    db.session.commit()
