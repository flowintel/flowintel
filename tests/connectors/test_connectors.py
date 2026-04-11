ADMIN_KEY = "admin_api_key"
EDITOR_KEY = "editor_api_key"
READ_KEY = "read_api_key"
MISP_EDITOR_KEY = "misp_editor_api_key"


def create_connector(client, name="Test Connector", description="A test connector"):
    return client.post("/api/connectors/add_connector",
                       content_type="application/json",
                       headers={"X-API-KEY": ADMIN_KEY},
                       json={"name": name, "description": description})


def create_instance(client, connector_id, name="Test Instance", api_key=MISP_EDITOR_KEY):
    return client.post(f"/api/connectors/{connector_id}/add_instance",
                       content_type="application/json",
                       headers={"X-API-KEY": api_key},
                       json={
                           "name": name,
                           "description": "A test instance",
                           "type_select": "send_to",
                           "url": "https://example.com",
                           "api_key": "test-api-key-12345",
                           "is_global_connector": False
                       })


################
# Connector CRUD
################

def test_list_connectors(client):
    response = client.get("/api/connectors/all", headers={"X-API-KEY": EDITOR_KEY})
    assert response.status_code == 200
    assert "connectors" in response.json


def test_create_connector_admin(client):
    response = create_connector(client)
    assert response.status_code == 200
    assert "connector_id" in response.json


def test_create_connector_no_name(client):
    response = client.post("/api/connectors/add_connector",
                           content_type="application/json",
                           headers={"X-API-KEY": ADMIN_KEY},
                           json={"description": "Missing name"})
    assert response.status_code == 400


def test_create_connector_editor_denied(client):
    response = client.post("/api/connectors/add_connector",
                           content_type="application/json",
                           headers={"X-API-KEY": EDITOR_KEY},
                           json={"name": "Should fail"})
    assert response.status_code == 403


def test_create_connector_read_denied(client):
    response = client.post("/api/connectors/add_connector",
                           content_type="application/json",
                           headers={"X-API-KEY": READ_KEY},
                           json={"name": "Should fail"})
    assert response.status_code == 403


def test_edit_connector_admin(client):
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = client.post(f"/api/connectors/{cid}/edit_connector",
                           content_type="application/json",
                           headers={"X-API-KEY": ADMIN_KEY},
                           json={"name": "Edited Connector", "description": "Edited"})
    assert response.status_code == 200


def test_delete_connector_admin(client):
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = client.get(f"/api/connectors/{cid}/delete", headers={"X-API-KEY": ADMIN_KEY})
    assert response.status_code == 200
    assert "Connector deleted" in response.json["message"]


def test_delete_connector_editor_denied(client):
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = client.get(f"/api/connectors/{cid}/delete", headers={"X-API-KEY": EDITOR_KEY})
    assert response.status_code == 403


def test_delete_nonexistent_connector(client):
    response = client.get("/api/connectors/9999/delete", headers={"X-API-KEY": ADMIN_KEY})
    assert response.status_code == 404


###############
# Instance CRUD
###############

def test_create_instance_misp_editor(client):
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = create_instance(client, cid)
    assert response.status_code == 200
    assert "connector_id" in response.json


def test_create_instance_editor_denied(client):
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = create_instance(client, cid, name="Should fail", api_key=EDITOR_KEY)
    assert response.status_code == 403


def test_create_instance_no_url(client):
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = client.post(f"/api/connectors/{cid}/add_instance",
                           content_type="application/json",
                           headers={"X-API-KEY": MISP_EDITOR_KEY},
                           json={"name": "No URL", "type_select": "send_to"})
    assert response.status_code == 400


def test_create_instance_bad_url(client):
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = client.post(f"/api/connectors/{cid}/add_instance",
                           content_type="application/json",
                           headers={"X-API-KEY": MISP_EDITOR_KEY},
                           json={
                               "name": "Bad URL",
                               "type_select": "send_to",
                               "url": "ftp://invalid"
                           })
    assert response.status_code == 400


def test_create_instance_nonexistent_connector(client):
    response = create_instance(client, 9999, name="Orphan")
    assert response.status_code == 404


def test_get_instances(client):
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    create_instance(client, cid)

    response = client.get(f"/api/connectors/{cid}/instances",
                          headers={"X-API-KEY": MISP_EDITOR_KEY})
    assert response.status_code == 200
    assert "instances" in response.json


def test_delete_instance_misp_editor(client):
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(client, cid)
    iid = instance_response.json["connector_id"]

    response = client.get(f"/api/connectors/{cid}/instance/{iid}/delete",
                          headers={"X-API-KEY": MISP_EDITOR_KEY})
    assert response.status_code == 200
    assert "Instance deleted" in response.json["message"]


def test_delete_instance_editor_denied(client):
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(client, cid)
    iid = instance_response.json["connector_id"]

    response = client.get(f"/api/connectors/{cid}/instance/{iid}/delete",
                          headers={"X-API-KEY": EDITOR_KEY})
    assert response.status_code == 403


def test_type_select(client):
    response = client.get("/api/connectors/type_select",
                          headers={"X-API-KEY": EDITOR_KEY})
    assert response.status_code == 200
    assert "type_select" in response.json
    assert isinstance(response.json["type_select"], list)
