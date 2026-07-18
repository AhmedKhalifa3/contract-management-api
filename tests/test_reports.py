from datetime import date, timedelta


def test_value_by_category_empty(client):
    resp = client.get("/api/reports/value-by-category")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_value_by_category_aggregates_and_sorts_desc(client, make_contract):
    make_contract(category="supply", value="100.00")
    make_contract(category="supply", value="50.00")
    make_contract(category="lease", value="500.00")

    resp = client.get("/api/reports/value-by-category")
    assert resp.status_code == 200
    body = resp.get_json()

    by_category = {row["category"]: row for row in body}
    assert by_category["supply"]["contract_count"] == 2
    assert by_category["supply"]["total_value"] == 150.0
    assert by_category["lease"]["contract_count"] == 1
    assert by_category["lease"]["total_value"] == 500.0
    # sorted by total_value descending
    assert [row["category"] for row in body] == ["lease", "supply"]


def test_value_by_category_csv(client, make_contract):
    make_contract(category="supply", value="100.00")

    resp = client.get("/api/reports/value-by-category?format=csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "attachment" in resp.headers["Content-Disposition"]
    body = resp.get_data(as_text=True)
    assert "category,contract_count,total_value" in body
    assert "supply,1,100.0" in body


def test_value_by_category_invalid_format(client):
    resp = client.get("/api/reports/value-by-category?format=xml")
    assert resp.status_code == 400


def test_expiring_soon_summary_only_includes_qualifying_contracts(client, make_contract):
    soon = make_contract(
        status="active",
        category="supply",
        value="1000.00",
        end_date=(date.today() + timedelta(days=10)).isoformat(),
    )
    make_contract(
        status="active",
        category="supply",
        value="2000.00",
        end_date=(date.today() + timedelta(days=200)).isoformat(),
    )

    resp = client.get("/api/reports/expiring-soon-summary?days=30")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body) == 1
    assert body[0]["category"] == "supply"
    assert body[0]["contract_count"] == 1
    assert body[0]["total_value"] == 1000.0
    assert body[0]["nearest_end_date"] == soon["end_date"]
