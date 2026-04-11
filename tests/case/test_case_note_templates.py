API_KEY = "editor_api_key"
READ_KEY = "read_api_key"


def create_case(client):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": "Note Template Test Case"})


########################
## Get note template ##
########################

def test_get_note_template_none_attached(client):
    """Getting a note template when none is attached should return 404"""
    case_id = create_case(client).json["case_id"]

    response = client.get(f"/api/case/{case_id}/get_note_template",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404
    assert "no note template" in response.json["message"]


def test_get_note_template_nonexistent_case(client):
    """Getting a note template for a non-existent case should return 404"""
    response = client.get("/api/case/9999/get_note_template",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404


########################
## Add note template ##
########################

def test_add_note_template_invalid_id(client):
    """Adding a note template with a non-existent ID should return 400"""
    case_id = create_case(client).json["case_id"]

    response = client.get(f"/api/case/{case_id}/add_note_template?note_template_id=9999",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 400


def test_add_note_template_nonexistent_case(client):
    """Adding a note template to a non-existent case should return 404"""
    response = client.get("/api/case/9999/add_note_template?note_template_id=1",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404


def test_add_note_template_read_only_denied(client):
    """Read-only user should not be able to add a note template"""
    case_id = create_case(client).json["case_id"]

    response = client.get(f"/api/case/{case_id}/add_note_template?note_template_id=1",
                          headers={"X-API-KEY": READ_KEY})
    assert response.status_code == 403


###########################
## Modify note template ##
###########################

def test_modif_values_no_template(client):
    """Modifying note template values when none is attached should fail"""
    case_id = create_case(client).json["case_id"]

    response = client.post(f"/api/case/{case_id}/modif_values_note_template",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"values": {"key": "value"}})
    assert response.status_code == 400


def test_modif_values_missing_key(client):
    """Modifying note template values without 'values' key should fail"""
    case_id = create_case(client).json["case_id"]

    response = client.post(f"/api/case/{case_id}/modif_values_note_template",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={})
    assert response.status_code == 400
    assert "values" in response.json["message"]


def test_modif_content_missing_key(client):
    """Modifying note template content without 'content' key should fail"""
    case_id = create_case(client).json["case_id"]

    response = client.post(f"/api/case/{case_id}/modif_content_note_template",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={})
    assert response.status_code == 400
    assert "content" in response.json["message"]


def test_modif_values_nonexistent_case(client):
    """Modifying note template on a non-existent case should return 404"""
    response = client.post("/api/case/9999/modif_values_note_template",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"values": {}})
    assert response.status_code == 404


def test_modif_content_read_only_denied(client):
    """Read-only user should not be able to modify note template content"""
    case_id = create_case(client).json["case_id"]

    response = client.post(f"/api/case/{case_id}/modif_content_note_template",
                           content_type="application/json",
                           headers={"X-API-KEY": READ_KEY},
                           json={"content": "test"})
    assert response.status_code == 403


###########################
## Remove note template ##
###########################

def test_remove_note_template_none_attached(client):
    """Removing a note template when none is attached should fail"""
    case_id = create_case(client).json["case_id"]

    response = client.get(f"/api/case/{case_id}/remove_note_template",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 400


def test_remove_note_template_nonexistent_case(client):
    """Removing a note template from a non-existent case should return 404"""
    response = client.get("/api/case/9999/remove_note_template",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404


def test_remove_note_template_read_only_denied(client):
    """Read-only user should not be able to remove a note template"""
    case_id = create_case(client).json["case_id"]

    response = client.get(f"/api/case/{case_id}/remove_note_template",
                          headers={"X-API-KEY": READ_KEY})
    assert response.status_code == 403
