def test_metrics_endpoint_exposes_prometheus_format(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/plain")
    assert b"http_requests_total" in resp.data
    assert b"http_request_duration_seconds" in resp.data


def test_metrics_labels_use_route_pattern_not_resolved_path(client, make_contract):
    contract = make_contract()
    client.get(f"/api/contracts/{contract['id']}")

    body = client.get("/metrics").get_data(as_text=True)

    # Cardinality guard: the route pattern should appear as a label value,
    # the resolved UUID path should not.
    assert 'endpoint="/api/contracts/<uuid:contract_id>"' in body
    assert contract["id"] not in body


def test_metrics_not_recorded_for_metrics_endpoint_itself(client):
    client.get("/metrics")
    body = client.get("/metrics").get_data(as_text=True)
    assert 'endpoint="/metrics"' not in body
