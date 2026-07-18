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
