from datetime import date, timedelta
from uuid import uuid4


def test_valid_transition(client, make_contract):
    contract = make_contract()  # draft
    resp = client.post(
        f"/api/contracts/{contract['id']}/transition", json={"status": "active"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "active"


def test_invalid_transition_rejected(client, make_contract):
    contract = make_contract()  # draft
    resp = client.post(
        f"/api/contracts/{contract['id']}/transition", json={"status": "expired"}
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_transition_not_found(client):
    resp = client.post(
        f"/api/contracts/{uuid4()}/transition", json={"status": "active"}
    )
    assert resp.status_code == 404


def test_create_contract_disallows_non_initial_status(client, contract_payload):
    contract_payload["status"] = "expired"
    resp = client.post("/api/contracts", json=contract_payload)
    assert resp.status_code == 400


def test_renew_contract(client, make_contract):
    contract = make_contract(status="active")
    new_end = (date.fromisoformat(contract["end_date"]) + timedelta(days=180)).isoformat()

    resp = client.post(
        f"/api/contracts/{contract['id']}/renew",
        json={"new_end_date": new_end, "notes": "extended term"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "renewed"
    assert body["end_date"] == new_end


def test_renew_requires_later_end_date(client, make_contract):
    contract = make_contract(status="active")
    resp = client.post(
        f"/api/contracts/{contract['id']}/renew",
        json={"new_end_date": contract["end_date"]},
    )
    assert resp.status_code == 400


def test_renew_requires_future_date(client, make_contract):
    contract = make_contract(status="active")
    past = (date.today() - timedelta(days=1)).isoformat()
    resp = client.post(
        f"/api/contracts/{contract['id']}/renew", json={"new_end_date": past}
    )
    assert resp.status_code == 400


def test_expiring_soon_lists_only_active_contracts_near_end_date(client, make_contract):
    soon = make_contract(
        status="active", end_date=(date.today() + timedelta(days=10)).isoformat()
    )
    far = make_contract(
        status="active", end_date=(date.today() + timedelta(days=200)).isoformat()
    )

    resp = client.get("/api/contracts/expiring-soon?days=30")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.get_json()["items"]]
    assert soon["id"] in ids
    assert far["id"] not in ids


def test_sweep_expiring_updates_status(client, make_contract):
    soon = make_contract(
        status="active", end_date=(date.today() + timedelta(days=5)).isoformat()
    )

    resp = client.post("/api/contracts/expiring-soon/sweep?days=30")
    assert resp.status_code == 200
    assert soon["id"] in resp.get_json()["transitioned"]

    updated = client.get(f"/api/contracts/{soon['id']}").get_json()
    assert updated["status"] == "expiring"


def test_sweep_expired_updates_status(client, make_contract):
    past_end = date.today() - timedelta(days=1)
    past_start = past_end - timedelta(days=30)
    contract = make_contract(
        status="active",
        start_date=past_start.isoformat(),
        end_date=past_end.isoformat(),
    )

    resp = client.post("/api/contracts/expired/sweep")
    assert resp.status_code == 200
    assert contract["id"] in resp.get_json()["transitioned"]

    updated = client.get(f"/api/contracts/{contract['id']}").get_json()
    assert updated["status"] == "expired"
