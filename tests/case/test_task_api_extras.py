API_KEY = "editor_api_key"
READ_KEY = "read_api_key"
ADMIN_KEY = "admin_api_key"


def create_case(client):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": "Task API Test Case"})


def create_task(client, case_id):
    return client.post(f"/api/case/{case_id}/create_task",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": "Task API Test Task"})


###########################
## Delete task note (API) ##
###########################

def create_note(client, task_id, note="hello"):
    return client.post(f"/api/task/{task_id}/create_note",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"note": note})


def list_notes(client, task_id):
    return client.get(f"/api/task/{task_id}/get_all_notes",
                      headers={"X-API-KEY": API_KEY})


def test_delete_note_api(client):
    """Editor can delete a task note via the API"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    create_note(client, task_id)

    notes = list_notes(client, task_id).json["notes"]
    assert len(notes) == 1
    note_id = notes[0]["id"]

    response = client.get(f"/api/task/{task_id}/delete_note?note_id={note_id}",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200


def test_delete_note_api_missing_param(client):
    """delete_note without 'note_id' returns 400"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.get(f"/api/task/{task_id}/delete_note",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 400


def test_delete_note_api_read_only_denied(client):
    """Read-only user cannot delete task notes"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    create_note(client, task_id)
    note_id = list_notes(client, task_id).json["notes"][0]["id"]

    response = client.get(f"/api/task/{task_id}/delete_note?note_id={note_id}",
                          headers={"X-API-KEY": READ_KEY})
    assert response.status_code == 403


###############################
## External references (API) ##
###############################

def create_external_ref(client, task_id, url="https://example.com"):
    return client.post(f"/api/task/{task_id}/create_external_reference",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"url": url})


def test_create_external_reference_api(client):
    """Editor can create an external reference on a task via the API"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = create_external_ref(client, task_id)
    assert response.status_code == 201
    assert "external_ref_id" in response.json


def test_create_external_reference_api_missing_url(client):
    """create_external_reference without 'url' returns 400"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.post(f"/api/task/{task_id}/create_external_reference",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={})
    assert response.status_code == 400


def test_edit_external_reference_api(client):
    """Editor can edit an external reference"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    erid = create_external_ref(client, task_id).json["external_ref_id"]

    response = client.post(f"/api/task/{task_id}/edit_external_reference/{erid}",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"url": "https://edited.example.com"})
    assert response.status_code == 200


def test_edit_external_reference_api_unknown(client):
    """Editing a missing external reference returns 404"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.post(f"/api/task/{task_id}/edit_external_reference/9999",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"url": "https://x.com"})
    assert response.status_code == 404


def test_delete_external_reference_api(client):
    """Editor can delete an external reference"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    erid = create_external_ref(client, task_id).json["external_ref_id"]

    response = client.get(f"/api/task/{task_id}/delete_external_reference/{erid}",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200


def test_delete_external_reference_api_unknown(client):
    """Deleting a missing external reference returns 404"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.get(f"/api/task/{task_id}/delete_external_reference/9999",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404


def test_external_reference_read_only_denied(client):
    """Read-only user cannot create external references"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.post(f"/api/task/{task_id}/create_external_reference",
                           content_type="application/json",
                           headers={"X-API-KEY": READ_KEY},
                           json={"url": "https://example.com"})
    assert response.status_code == 403


########################
## Connectors on task ##
########################

def test_get_connectors_on_task(client):
    """Editor can list connectors on a task (empty by default)"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.get(f"/api/task/{task_id}/get_connectors",
                          headers={"X-API-KEY": ADMIN_KEY})
    assert response.status_code == 200
    assert response.json["connectors"] == []


def test_add_connectors_missing_payload(client):
    """add_connectors without 'connectors' returns 400"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.post(f"/api/task/{task_id}/add_connectors",
                           content_type="application/json",
                           headers={"X-API-KEY": ADMIN_KEY},
                           json={})
    assert response.status_code == 400


def test_add_connectors_unknown_instance(client):
    """add_connectors with an unknown instance returns 400"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.post(f"/api/task/{task_id}/add_connectors",
                           content_type="application/json",
                           headers={"X-API-KEY": ADMIN_KEY},
                           json={"connectors": [{"name": "no-such-instance", "identifier": ""}]})
    assert response.status_code == 400


def test_remove_connector_unknown(client):
    """remove_connector on unknown instance returns 400"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.get(f"/api/task/{task_id}/remove_connector/9999",
                          headers={"X-API-KEY": ADMIN_KEY})
    assert response.status_code == 400


def test_edit_connector_missing_payload(client):
    """edit_connector without 'identifier' returns 400"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.post(f"/api/task/{task_id}/edit_connector/9999",
                           content_type="application/json",
                           headers={"X-API-KEY": ADMIN_KEY},
                           json={})
    assert response.status_code == 400
