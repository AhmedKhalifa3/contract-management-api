from flask import Blueprint, jsonify, request

from app.schemas.contract import (
    ContractCreate,
    ContractRead,
    ContractRenewal,
    ContractTransition,
    ContractUpdate,
)
from app.services import contract_service, status_service

contracts_bp = Blueprint("contracts", __name__, url_prefix="/api/contracts")


@contracts_bp.post("")
def create_contract():
    payload = ContractCreate.model_validate(request.get_json())
    contract = contract_service.create_contract(payload.model_dump())
    return jsonify(ContractRead.model_validate(contract).model_dump(mode="json")), 201


@contracts_bp.get("")
def list_contracts():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    items, total = contract_service.list_contracts(
        status=request.args.get("status"),
        category=request.args.get("category"),
        page=page,
        per_page=per_page,
    )
    return jsonify(
        {
            "items": [
                ContractRead.model_validate(c).model_dump(mode="json") for c in items
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    )


@contracts_bp.get("/expiring-soon")
def expiring_soon():
    days = request.args.get("days", default=30, type=int)
    contracts = status_service.list_expiring_soon(days)
    return jsonify(
        {
            "items": [
                ContractRead.model_validate(c).model_dump(mode="json")
                for c in contracts
            ],
            "total": len(contracts),
            "threshold_days": days,
        }
    )


@contracts_bp.post("/expiring-soon/sweep")
def sweep_expiring():
    days = request.args.get("days", default=30, type=int)
    contracts = status_service.sweep_expiring(days)
    return jsonify(
        {"transitioned": [str(c.id) for c in contracts], "count": len(contracts)}
    )


@contracts_bp.post("/expired/sweep")
def sweep_expired():
    contracts = status_service.sweep_expired()
    return jsonify(
        {"transitioned": [str(c.id) for c in contracts], "count": len(contracts)}
    )


@contracts_bp.get("/<uuid:contract_id>")
def get_contract(contract_id):
    contract = contract_service.get_contract(contract_id)
    return jsonify(ContractRead.model_validate(contract).model_dump(mode="json"))


@contracts_bp.patch("/<uuid:contract_id>")
def update_contract(contract_id):
    payload = ContractUpdate.model_validate(request.get_json())
    contract = contract_service.update_contract(
        contract_id, payload.model_dump(exclude_unset=True)
    )
    return jsonify(ContractRead.model_validate(contract).model_dump(mode="json"))


@contracts_bp.post("/<uuid:contract_id>/transition")
def transition_contract(contract_id):
    payload = ContractTransition.model_validate(request.get_json())
    contract = status_service.transition_contract(contract_id, payload.status)
    return jsonify(ContractRead.model_validate(contract).model_dump(mode="json"))


@contracts_bp.post("/<uuid:contract_id>/renew")
def renew_contract(contract_id):
    payload = ContractRenewal.model_validate(request.get_json())
    contract = status_service.renew_contract(
        contract_id, payload.new_end_date, payload.notes
    )
    return jsonify(ContractRead.model_validate(contract).model_dump(mode="json"))


@contracts_bp.delete("/<uuid:contract_id>")
def delete_contract(contract_id):
    contract_service.delete_contract(contract_id)
    return "", 204
