ADMIN_API_KEY = "admin_api_key"
TEMPLATE_EDITOR_API_KEY = "template_editor_api_key"
EDITOR_API_KEY = "editor_api_key"
MISP_EDITOR_API_KEY = "misp_editor_api_key"


def create_case_template(client):
    return client.post("/api/templating/create_case",
                       content_type="application/json",
                       headers={"X-API-KEY": ADMIN_API_KEY},
                       json={"title": "Connector Template"})


def create_connector(client):
    return client.post("/api/connectors/add_connector",
                       content_type="application/json",
                       headers={"X-API-KEY": ADMIN_API_KEY},
                       json={"name": "Template Test Connector", "description": "For template tests"})


def create_instance(client, connector_id):
    return client.post(f"/api/connectors/{connector_id}/add_instance",
                       content_type="application/json",
                       headers={"X-API-KEY": MISP_EDITOR_API_KEY},
                       json={
                           "name": "Template Test Instance",
                           "description": "For template tests",
                           "type_select": "send_to",
                           "url": "https://example.com",
                           "api_key": "test-key-12345",
                           "is_global_connector": False
                       })


########################
## Add connector ##
########################

def test_add_connector_to_template(client):
    """Template editor should be able to add a connector to a case template"""
    template_id = create_case_template(client).json["message"].split(": ")[1]
    conn_id = create_connector(client).json["connector_id"]
    instance_id = create_instance(client, conn_id).json["connector_id"]

    response = client.post(f"/api/templating/add_connector/{template_id}",
                           content_type="application/json",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={"connectors": [{"id": instance_id, "identifier": "main"}]})
    assert response.status_code == 200
    assert "Connector added" in response.json["message"]


def test_add_connector_no_data(client):
    """Adding a connector without data should fail"""
    template_id = create_case_template(client).json["message"].split(": ")[1]

    response = client.post(f"/api/templating/add_connector/{template_id}",
                           content_type="application/json",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={})
    assert response.status_code == 400


def test_add_connector_nonexistent_template(client):
    """Adding a connector to a non-existent template should return 404"""
    response = client.post("/api/templating/add_connector/9999",
                           content_type="application/json",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={"connectors": [{"id": 1, "identifier": "main"}]})
    assert response.status_code == 404


def test_add_connector_editor_denied(client):
    """Regular editor should not be able to add connectors to templates"""
    template_id = create_case_template(client).json["message"].split(": ")[1]

    response = client.post(f"/api/templating/add_connector/{template_id}",
                           content_type="application/json",
                           headers={"X-API-KEY": EDITOR_API_KEY},
                           json={"connectors": [{"id": 1, "identifier": "main"}]})
    assert response.status_code == 403


#########################
## Edit connector ##
#########################

def test_edit_connector(client):
    """Template editor should be able to edit a connector identifier"""
    template_id = create_case_template(client).json["message"].split(": ")[1]
    conn_id = create_connector(client).json["connector_id"]
    instance_id = create_instance(client, conn_id).json["connector_id"]

    client.post(f"/api/templating/add_connector/{template_id}",
                content_type="application/json",
                headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                json={"connectors": [{"id": instance_id, "identifier": "main"}]})

    # Get the template connector instance ID
    instances = client.get(f"/api/templating/get_case_template_connector_instances/{template_id}",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY})
    ciid = instances.json["connector_instances"][0]["template_instance_id"]

    response = client.post(f"/api/templating/{template_id}/edit_connector/{ciid}",
                           content_type="application/json",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={"identifier": "updated"})
    assert response.status_code == 200
    assert "Connector edited" in response.json["message"]


def test_edit_connector_no_identifier(client):
    """Editing a connector without an identifier should fail"""
    template_id = create_case_template(client).json["message"].split(": ")[1]

    response = client.post(f"/api/templating/{template_id}/edit_connector/9999",
                           content_type="application/json",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={})
    assert response.status_code == 400


def test_edit_connector_nonexistent(client):
    """Editing a non-existent connector instance should return 404"""
    template_id = create_case_template(client).json["message"].split(": ")[1]

    response = client.post(f"/api/templating/{template_id}/edit_connector/9999",
                           content_type="application/json",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={"identifier": "test"})
    assert response.status_code == 404


###########################
## Remove connector ##
###########################

def test_remove_connector(client):
    """Template editor should be able to remove a connector"""
    template_id = create_case_template(client).json["message"].split(": ")[1]
    conn_id = create_connector(client).json["connector_id"]
    instance_id = create_instance(client, conn_id).json["connector_id"]

    client.post(f"/api/templating/add_connector/{template_id}",
                content_type="application/json",
                headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                json={"connectors": [{"id": instance_id, "identifier": "main"}]})

    instances = client.get(f"/api/templating/get_case_template_connector_instances/{template_id}",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY})
    ciid = instances.json["connector_instances"][0]["template_instance_id"]

    response = client.delete(f"/api/templating/{template_id}/remove_connector/{ciid}",
                             headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY})
    assert response.status_code == 200
    assert "Connector removed" in response.json["message"]


def test_remove_connector_nonexistent(client):
    """Removing a non-existent connector instance should return 404"""
    template_id = create_case_template(client).json["message"].split(": ")[1]

    response = client.delete(f"/api/templating/{template_id}/remove_connector/9999",
                             headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY})
    assert response.status_code == 404
