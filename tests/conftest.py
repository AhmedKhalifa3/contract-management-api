from datetime import date, timedelta

import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    flask_app = create_app("testing")
    with flask_app.app_context():
        yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _clean_tables(app):
    yield
    for table in reversed(_db.metadata.sorted_tables):
        _db.session.execute(table.delete())
    _db.session.commit()


@pytest.fixture()
def contract_payload():
    today = date.today()
    return {
        "title": "Master Services Agreement",
        "counterparty": "Acme Energy Co",
        "value": "125000.00",
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=365)).isoformat(),
        "category": "supply",
    }


@pytest.fixture()
def make_contract(client, contract_payload):
    """Create a contract, optionally driving it to a given status via the
    real transition endpoint (not a DB shortcut) so tests exercise the
    same state machine the API enforces."""

    def _make(status: str | None = None, **overrides):
        payload = {**contract_payload, **overrides}
        created = client.post("/api/contracts", json=payload).get_json()
        if status:
            client.post(
                f"/api/contracts/{created['id']}/transition", json={"status": status}
            )
            created = client.get(f"/api/contracts/{created['id']}").get_json()
        return created

    return _make
