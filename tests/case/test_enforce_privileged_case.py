"""
Test cases with ENFORCE_PRIVILEGED_CASE enabled
"""
import pytest

ADMIN_KEY = "admin_api_key"
CASE_ADMIN_KEY = "caseadmin_api_key"
EDITOR_KEY = "editor_api_key"
TEMPLATE_EDITOR_KEY = "template_editor_api_key"


@pytest.fixture(autouse=True)
def enforce_privileged(app):
    app.config["ENFORCE_PRIVILEGED_CASE"] = True
    yield
    app.config["ENFORCE_PRIVILEGED_CASE"] = False


def create_case(client, api_key=ADMIN_KEY):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": api_key},
                       json={"title": "Test enforced case"})


def test_case_is_privileged_by_default(client):
    resp = create_case(client, ADMIN_KEY)
    assert resp.status_code == 201
    case_id = resp.json["case_id"]

    resp = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": ADMIN_KEY})
    assert resp.status_code == 200
    assert resp.json["privileged_case"] is True


def test_editor_complete_denied(client):
    resp = create_case(client, EDITOR_KEY)
    case_id = resp.json["case_id"]

    resp = client.get(f"/api/case/{case_id}/complete",
                      headers={"X-API-KEY": EDITOR_KEY})
    assert resp.status_code == 403

def test_editor_delete_denied(client):
    resp = create_case(client, EDITOR_KEY)
    case_id = resp.json["case_id"]

    resp = client.get(f"/api/case/{case_id}/delete",
                      headers={"X-API-KEY": EDITOR_KEY})
    assert resp.status_code == 403

def test_editor_fork_denied(client):
    resp = create_case(client, EDITOR_KEY)
    case_id = resp.json["case_id"]

    resp = client.post(f"/api/case/{case_id}/fork",
                       content_type="application/json",
                       headers={"X-API-KEY": EDITOR_KEY},
                       json={"case_title_fork": "Forked enforced case"})
    assert resp.status_code == 403

def test_editor_recurring_denied(client):
    resp = create_case(client, EDITOR_KEY)
    case_id = resp.json["case_id"]

    resp = client.post(f"/api/case/{case_id}/recurring",
                       content_type="application/json",
                       headers={"X-API-KEY": EDITOR_KEY},
                       json={"once": "2025-01-01"})
    assert resp.status_code == 403

def test_template_editor_create_template_denied(client):
    resp = create_case(client, TEMPLATE_EDITOR_KEY)
    case_id = resp.json["case_id"]

    resp = client.post(f"/api/case/{case_id}/create_template",
                       content_type="application/json",
                       headers={"X-API-KEY": TEMPLATE_EDITOR_KEY},
                       json={"title_template": "Template from enforced case"})
    assert resp.status_code == 403


def test_admin_complete(client):
    resp = create_case(client, ADMIN_KEY)
    case_id = resp.json["case_id"]

    resp = client.get(f"/api/case/{case_id}/complete",
                      headers={"X-API-KEY": ADMIN_KEY})
    assert resp.status_code == 200

def test_admin_delete(client):
    resp = create_case(client, ADMIN_KEY)
    case_id = resp.json["case_id"]

    resp = client.get(f"/api/case/{case_id}/delete",
                      headers={"X-API-KEY": ADMIN_KEY})
    assert resp.status_code == 200

def test_admin_fork(client):
    resp = create_case(client, ADMIN_KEY)
    case_id = resp.json["case_id"]

    resp = client.post(f"/api/case/{case_id}/fork",
                       content_type="application/json",
                       headers={"X-API-KEY": ADMIN_KEY},
                       json={"case_title_fork": "Admin forked enforced"})
    assert resp.status_code == 201

def test_admin_recurring(client):
    resp = create_case(client, ADMIN_KEY)
    case_id = resp.json["case_id"]

    resp = client.post(f"/api/case/{case_id}/recurring",
                       content_type="application/json",
                       headers={"X-API-KEY": ADMIN_KEY},
                       json={"once": "2025-01-01"})
    assert resp.status_code == 200

def test_caseadmin_complete(client):
    resp = create_case(client, CASE_ADMIN_KEY)
    case_id = resp.json["case_id"]

    resp = client.get(f"/api/case/{case_id}/complete",
                      headers={"X-API-KEY": CASE_ADMIN_KEY})
    assert resp.status_code == 200

def test_caseadmin_fork(client):
    resp = create_case(client, CASE_ADMIN_KEY)
    case_id = resp.json["case_id"]

    resp = client.post(f"/api/case/{case_id}/fork",
                       content_type="application/json",
                       headers={"X-API-KEY": CASE_ADMIN_KEY},
                       json={"case_title_fork": "CaseAdmin forked enforced"})
    assert resp.status_code == 201
