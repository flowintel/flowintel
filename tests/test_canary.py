API_KEY = "admin_api_key"

def test_canary_writes_and_must_not_leak(client):
    resp = client.post(
        "/api/admin/add_org",
        headers={"X-API-KEY": API_KEY},
        json={"name": "CANARY_ORG_DO_NOT_PERSIST"},
        
    )
    assert resp.status_code in (200, 201)


def test_canary_confirms_no_leak(client):
    # Uncomment to check this test by forcing it to fail
    # resp = client.post(
    #    "/api/admin/add_org",
    #    json={"name": "CANARY_ORG_DO_NOT_PERSIST"},
    #    headers={"X-API-KEY": API_KEY}
    #)
    resp = client.get(
        "/api/admin/orgs",
        headers={"X-API-KEY": API_KEY}
    )
    names = [o["name"] for o in resp.json["orgs"]]
    assert "CANARY_ORG_DO_NOT_PERSIST" not in names
