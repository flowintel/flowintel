"""
Test cases for Template Editor user
"""

API_KEY = "template_editor_api_key"

def create_case(client):
    return client.post("/api/case/create",
                       content_type='application/json',
                       headers={"X-API-KEY": API_KEY},
                       json={"title": "Test Case template editor"})

def test_create_case(client):
    response = create_case(client)
    assert response.status_code == 201
    assert "case_id" in response.json

def test_create_template(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]

    response = client.post(f"/api/case/{case_id}/create_template", headers={"X-API-KEY": API_KEY},
                           json={"title_template": "Template from case template editor"})
    assert response.status_code == 201
    assert "template_id" in response.json
