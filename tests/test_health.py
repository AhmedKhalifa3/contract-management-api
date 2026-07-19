def test_healthz_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_healthz_not_counted_in_metrics(client):
    client.get("/healthz")
    body = client.get("/metrics").get_data(as_text=True)
    assert 'endpoint="/healthz"' not in body
