from flask import Blueprint, jsonify, request

from app.schemas.contract import ContractCreate, ContractRead, ContractUpdate
from app.services import contract_service

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


@contracts_bp.delete("/<uuid:contract_id>")
def delete_contract(contract_id):
    contract_service.delete_contract(contract_id)
    return "", 204
