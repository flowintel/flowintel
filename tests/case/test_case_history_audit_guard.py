API_KEY = "editor_api_key"
ADMIN_KEY = "admin_api_key"
AUDIT_VIEWER_KEY = "audit_viewer_api_key"
READ_KEY = "read_api_key"


def create_case(client):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": "Audit Guard Case"})


def test_history_admin_allowed(client):
    """Admin can read case history via the API"""
    cid = create_case(client).json["case_id"]
    response = client.get(f"/api/case/{cid}/history",
                          headers={"X-API-KEY": ADMIN_KEY})
    assert response.status_code == 200


def test_history_audit_viewer_allowed(client):
    """AuditViewer can read case history via the API"""
    cid = create_case(client).json["case_id"]
    response = client.get(f"/api/case/{cid}/history",
                          headers={"X-API-KEY": AUDIT_VIEWER_KEY})
    assert response.status_code == 200


def test_history_editor_denied(client):
    """Plain Editor cannot read case history via the API"""
    cid = create_case(client).json["case_id"]
    response = client.get(f"/api/case/{cid}/history",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403
    assert response.json["message"] == "Access restricted"


def test_history_read_only_denied(client):
    """Read-only user cannot read case history via the API"""
    cid = create_case(client).json["case_id"]
    response = client.get(f"/api/case/{cid}/history",
                          headers={"X-API-KEY": READ_KEY})
    assert response.status_code == 403
