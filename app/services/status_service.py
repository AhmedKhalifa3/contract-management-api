import uuid
from datetime import date, timedelta

from app.extensions import db
from app.models import Contract, ContractStatus, RenewalHistory
from app.services import contract_service
from app.utils.exceptions import AppValidationError

ALLOWED_TRANSITIONS: dict[ContractStatus, set[ContractStatus]] = {
    ContractStatus.DRAFT: {ContractStatus.ACTIVE},
    ContractStatus.ACTIVE: {ContractStatus.EXPIRING, ContractStatus.RENEWED},
    ContractStatus.EXPIRING: {ContractStatus.EXPIRED, ContractStatus.RENEWED},
    ContractStatus.EXPIRED: {ContractStatus.RENEWED},
    ContractStatus.RENEWED: {ContractStatus.ACTIVE},
}


def validate_transition(current: ContractStatus, new: ContractStatus) -> None:
    if current == new:
        return
    if new not in ALLOWED_TRANSITIONS.get(current, set()):
        raise AppValidationError(
            f"cannot transition contract from '{current.value}' to '{new.value}'"
        )


def transition_contract(contract_id: uuid.UUID, new_status: ContractStatus) -> Contract:
    contract = contract_service.get_contract(contract_id)
    validate_transition(contract.status, new_status)
    contract.status = new_status
    db.session.commit()
    return contract


def renew_contract(
    contract_id: uuid.UUID, new_end_date: date, notes: str | None = None
) -> Contract:
    contract = contract_service.get_contract(contract_id)
    validate_transition(contract.status, ContractStatus.RENEWED)

    if new_end_date <= contract.end_date:
        raise AppValidationError("new_end_date must be after the current end_date")

    db.session.add(
        RenewalHistory(
            contract_id=contract.id,
            previous_end_date=contract.end_date,
            new_end_date=new_end_date,
            notes=notes,
        )
    )
    contract.end_date = new_end_date
    contract.status = ContractStatus.RENEWED
    db.session.commit()
    return contract


def list_expiring_soon(threshold_days: int = 30) -> list[Contract]:
    cutoff = date.today() + timedelta(days=threshold_days)
    return (
        db.session.query(Contract)
        .filter(Contract.status == ContractStatus.ACTIVE, Contract.end_date <= cutoff)
        .order_by(Contract.end_date.asc())
        .all()
    )


def sweep_expiring(threshold_days: int = 30) -> list[Contract]:
    contracts = list_expiring_soon(threshold_days)
    for contract in contracts:
        contract.status = ContractStatus.EXPIRING
    db.session.commit()
    return contracts


def sweep_expired() -> list[Contract]:
    today = date.today()
    contracts = (
        db.session.query(Contract)
        .filter(
            Contract.status.in_([ContractStatus.ACTIVE, ContractStatus.EXPIRING]),
            Contract.end_date < today,
        )
        .all()
    )
    for contract in contracts:
        contract.status = ContractStatus.EXPIRED
    db.session.commit()
    return contracts
