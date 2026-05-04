API_KEY = "editor_api_key"
READ_KEY = "read_api_key"


def create_case(client, title="Link Test Case"):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": title})


def test_add_case_link(client):
    """Editor can link two cases via the API"""
    cid_a = create_case(client, "Case A").json["case_id"]
    cid_b = create_case(client, "Case B").json["case_id"]

    response = client.post(f"/api/case/{cid_a}/add_link",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"case_id": [cid_b]})
    assert response.status_code == 200
    assert response.json["message"] == "Link added"


def test_add_case_link_missing_payload(client):
    """add_link without 'case_id' returns 400"""
    cid = create_case(client).json["case_id"]
    response = client.post(f"/api/case/{cid}/add_link",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={})
    assert response.status_code == 400


def test_add_case_link_unknown_target(client):
    """Linking to a non-existent case returns 404"""
    cid = create_case(client).json["case_id"]
    response = client.post(f"/api/case/{cid}/add_link",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"case_id": [9999]})
    assert response.status_code == 404


def test_add_case_link_read_only_denied(client):
    """Read-only user cannot link cases"""
    cid_a = create_case(client, "Case A").json["case_id"]
    cid_b = create_case(client, "Case B").json["case_id"]
    response = client.post(f"/api/case/{cid_a}/add_link",
                           content_type="application/json",
                           headers={"X-API-KEY": READ_KEY},
                           json={"case_id": [cid_b]})
    assert response.status_code == 403


def test_remove_case_link(client):
    """Editor can remove a case link via the API"""
    cid_a = create_case(client, "Case A").json["case_id"]
    cid_b = create_case(client, "Case B").json["case_id"]
    client.post(f"/api/case/{cid_a}/add_link",
                content_type="application/json",
                headers={"X-API-KEY": API_KEY},
                json={"case_id": [cid_b]})

    response = client.get(f"/api/case/{cid_a}/remove_link/{cid_b}",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["message"] == "Link removed"


def test_remove_case_link_unknown(client):
    """Removing a non-existent link returns 400"""
    cid = create_case(client).json["case_id"]
    response = client.get(f"/api/case/{cid}/remove_link/9999",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 400


def test_remove_case_link_read_only_denied(client):
    """Read-only user cannot remove case links"""
    cid_a = create_case(client, "Case A").json["case_id"]
    cid_b = create_case(client, "Case B").json["case_id"]
    response = client.get(f"/api/case/{cid_a}/remove_link/{cid_b}",
                          headers={"X-API-KEY": READ_KEY})
    assert response.status_code == 403
