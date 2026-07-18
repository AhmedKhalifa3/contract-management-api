from uuid import uuid4


def test_create_contract(client, contract_payload):
    resp = client.post("/api/contracts", json=contract_payload)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["title"] == contract_payload["title"]
    assert body["status"] == "draft"
    assert "id" in body


def test_create_contract_invalid_dates(client, contract_payload):
    contract_payload["end_date"] = contract_payload["start_date"]
    resp = client.post("/api/contracts", json=contract_payload)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_contract_negative_value(client, contract_payload):
    contract_payload["value"] = "-100.00"
    resp = client.post("/api/contracts", json=contract_payload)
    assert resp.status_code == 400


def test_get_contract(client, contract_payload):
    created = client.post("/api/contracts", json=contract_payload).get_json()
    resp = client.get(f"/api/contracts/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["id"] == created["id"]


def test_get_contract_not_found(client):
    resp = client.get(f"/api/contracts/{uuid4()}")
    assert resp.status_code == 404


def test_list_contracts(client, contract_payload):
    client.post("/api/contracts", json=contract_payload)
    resp = client.get("/api/contracts")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_list_contracts_filter_by_category(client, contract_payload):
    client.post("/api/contracts", json=contract_payload)
    other = dict(contract_payload, category="lease")
    client.post("/api/contracts", json=other)

    resp = client.get("/api/contracts?category=lease")
    body = resp.get_json()
    assert body["total"] == 1
    assert body["items"][0]["category"] == "lease"


def test_list_contracts_invalid_status(client):
    resp = client.get("/api/contracts?status=not_a_real_status")
    assert resp.status_code == 400


def test_update_contract(client, contract_payload):
    created = client.post("/api/contracts", json=contract_payload).get_json()
    resp = client.patch(
        f"/api/contracts/{created['id']}", json={"title": "Updated title"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Updated title"


def test_update_contract_invalid_date_range(client, contract_payload):
    created = client.post("/api/contracts", json=contract_payload).get_json()
    resp = client.patch(
        f"/api/contracts/{created['id']}",
        json={"end_date": contract_payload["start_date"]},
    )
    assert resp.status_code == 400


def test_update_contract_not_found(client):
    resp = client.patch(f"/api/contracts/{uuid4()}", json={"title": "x"})
    assert resp.status_code == 404


def test_delete_contract(client, contract_payload):
    created = client.post("/api/contracts", json=contract_payload).get_json()
    resp = client.delete(f"/api/contracts/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/api/contracts/{created['id']}")
    assert resp.status_code == 404
