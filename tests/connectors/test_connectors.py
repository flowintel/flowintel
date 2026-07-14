ADMIN_KEY = "admin_api_key"
EDITOR_KEY = "editor_api_key"
READ_KEY = "read_api_key"
MISP_EDITOR_KEY = "misp_editor_api_key"
ORGADMIN_KEY = "orgadmin_api_key"
ORGADMIN_MISP_KEY = "orgadmin_misp_editor_api_key"


def create_connector(client, name="Test Connector", description="A test connector"):
    return client.post("/api/connectors/add_connector",
                       content_type="application/json",
                       headers={"X-API-KEY": ADMIN_KEY},
                       json={"name": name, "description": description})


def create_instance(client, connector_id, name="Test Instance", api_key=MISP_EDITOR_KEY, payload=None):
    json_payload = {
        "name": name,
        "description": "A test instance",
        "type_select": "send_to",
        "url": "https://example.com",
        "api_key": "test-api-key-12345",
        "is_global_connector": False
    }
    if payload:
        json_payload.update(payload)
    return client.post(f"/api/connectors/{connector_id}/add_instance",
                       content_type="application/json",
                       headers={"X-API-KEY": api_key},
                       json=json_payload)


def create_case(client, api_key=ADMIN_KEY, title="Test Case"):
    return client.post(
        "/api/case/create",
        content_type="application/json",
        headers={"X-API-KEY": api_key},
        json={"title": title}
    )


####################
## Connector CRUD ##
####################

def test_list_connectors(client):
    """Editor should be able to list connectors"""
    response = client.get("/api/connectors/all", headers={"X-API-KEY": EDITOR_KEY})
    assert response.status_code == 200
    assert "connectors" in response.json


def test_create_connector_admin(client):
    """Admin should be able to create connectors"""
    response = create_connector(client)
    assert response.status_code == 200
    assert "connector_id" in response.json


def test_create_connector_no_name(client):
    """Creating a connector without a name should fail"""
    response = client.post("/api/connectors/add_connector",
                           content_type="application/json",
                           headers={"X-API-KEY": ADMIN_KEY},
                           json={"description": "Missing name"})
    assert response.status_code == 400


def test_create_connector_editor_denied(client):
    """Editor should not be able to create connectors"""
    response = client.post("/api/connectors/add_connector",
                           content_type="application/json",
                           headers={"X-API-KEY": EDITOR_KEY},
                           json={"name": "Should fail"})
    assert response.status_code == 403


def test_create_connector_read_denied(client):
    """Read-only user should not be able to create connectors"""
    response = client.post("/api/connectors/add_connector",
                           content_type="application/json",
                           headers={"X-API-KEY": READ_KEY},
                           json={"name": "Should fail"})
    assert response.status_code == 403


def test_edit_connector_admin(client):
    """Admin should be able to edit connectors"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = client.post(f"/api/connectors/{cid}/edit_connector",
                           content_type="application/json",
                           headers={"X-API-KEY": ADMIN_KEY},
                           json={"name": "Edited Connector", "description": "Edited"})
    assert response.status_code == 200


def test_delete_connector_admin(client):
    """Admin should be able to delete connectors"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = client.get(f"/api/connectors/{cid}/delete", headers={"X-API-KEY": ADMIN_KEY})
    assert response.status_code == 200
    assert "Connector deleted" in response.json["message"]


def test_delete_connector_editor_denied(client):
    """Editor should not be able to delete connectors"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = client.get(f"/api/connectors/{cid}/delete", headers={"X-API-KEY": EDITOR_KEY})
    assert response.status_code == 403


def test_delete_nonexistent_connector(client):
    """Deleting a non-existent connector should return 404"""
    response = client.get("/api/connectors/9999/delete", headers={"X-API-KEY": ADMIN_KEY})
    assert response.status_code == 404


###################
## Instance CRUD ##
###################

def test_create_instance_misp_editor(client):
    """MISP editor should be able to create instances"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = create_instance(client, cid)
    assert response.status_code == 200
    assert "connector_id" in response.json


def test_create_instance_editor_denied(client):
    """Editor should not be able to create instances"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = create_instance(client, cid, name="Should fail", api_key=EDITOR_KEY)
    assert response.status_code == 403


def test_create_instance_orgadmin_denied_without_misp_editor(client):
    """OrgAdmin alone should not be able to create instances."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = create_instance(client, cid, name="Should fail", api_key=ORGADMIN_KEY)
    assert response.status_code == 403


def test_create_global_instance_admin(client):
    """Admin should be able to create a platform-global instance."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = create_instance(
        client,
        cid,
        api_key=ADMIN_KEY,
        payload={"sharing_scope": "global", "is_global_connector": True}
    )
    assert response.status_code == 200

    instances = client.get(f"/api/connectors/{cid}/instances", headers={"X-API-KEY": EDITOR_KEY})
    assert instances.status_code == 200
    assert instances.json["instances"][0]["sharing_scope"] == "global"


def test_create_global_instance_orgadmin_denied(client):
    """OrgAdmin should not be able to create a platform-global instance."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = create_instance(
        client,
        cid,
        api_key=ORGADMIN_MISP_KEY,
        payload={"sharing_scope": "global", "is_global_connector": True}
    )
    assert response.status_code == 403


def test_create_org_shared_instance_orgadmin(client):
    """OrgAdmin should be able to create an org-shared instance."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = create_instance(
        client,
        cid,
        api_key=ORGADMIN_MISP_KEY,
        payload={"sharing_scope": "org", "is_global_connector": True}
    )
    assert response.status_code == 200

    instances = client.get(f"/api/connectors/{cid}/instances", headers={"X-API-KEY": ORGADMIN_MISP_KEY})
    assert instances.status_code == 200
    assert instances.json["instances"][0]["sharing_scope"] == "org"


def test_create_org_shared_instance_without_api_key_keeps_scope(client):
    """Org-shared instances should stay org-scoped even without a shared API key."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = create_instance(
        client,
        cid,
        api_key=ORGADMIN_MISP_KEY,
        payload={"sharing_scope": "org", "is_global_connector": True, "api_key": ""}
    )
    assert response.status_code == 200

    instances = client.get(f"/api/connectors/{cid}/instances", headers={"X-API-KEY": ORGADMIN_MISP_KEY})
    assert instances.status_code == 200
    assert instances.json["instances"][0]["sharing_scope"] == "org"


def test_create_global_instance_without_api_key_keeps_scope(client):
    """Global instances should stay global-scoped even without a shared API key."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = create_instance(
        client,
        cid,
        api_key=ADMIN_KEY,
        payload={"sharing_scope": "global", "is_global_connector": True, "api_key": ""}
    )
    assert response.status_code == 200

    instances = client.get(f"/api/connectors/{cid}/instances", headers={"X-API-KEY": EDITOR_KEY})
    assert instances.status_code == 200
    assert instances.json["instances"][0]["sharing_scope"] == "global"


def test_org_shared_instance_hidden_from_other_orgs(client):
    """Org-shared instances should not be visible outside the owning organisation."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    create_instance(
        client,
        cid,
        api_key=ORGADMIN_MISP_KEY,
        payload={"sharing_scope": "org", "is_global_connector": True}
    )

    own_org_instances = client.get(f"/api/connectors/{cid}/instances", headers={"X-API-KEY": ORGADMIN_MISP_KEY})
    other_org_instances = client.get(f"/api/connectors/{cid}/instances", headers={"X-API-KEY": MISP_EDITOR_KEY})

    assert own_org_instances.status_code == 200
    assert len(own_org_instances.json["instances"]) == 1
    assert other_org_instances.status_code == 200
    assert other_org_instances.json["instances"] == []


def test_add_org_shared_instance_to_case(client):
    """An org-shared connector instance should be attachable to a case in the same org."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(
        client,
        cid,
        api_key=ORGADMIN_MISP_KEY,
        payload={"sharing_scope": "org", "is_global_connector": True}
    )
    instance_id = instance_response.json["connector_id"]

    case_response = create_case(client, api_key=ORGADMIN_MISP_KEY, title="Org Scoped Connector Case")
    case_id = case_response.json["case_id"]

    attach_response = client.post(
        f"/api/case/{case_id}/add_connectors",
        content_type="application/json",
        headers={"X-API-KEY": ORGADMIN_MISP_KEY},
        json={"connectors": [{"id": instance_id, "name": "Test Instance", "identifier": "org-scope-id"}]}
    )
    assert attach_response.status_code == 200

    case_connectors = client.get(
        f"/api/case/get_case_connectors/{case_id}",
        headers={"X-API-KEY": ORGADMIN_MISP_KEY}
    )
    assert case_connectors.status_code == 200
    assert len(case_connectors.json["connectors"]) == 1
    assert case_connectors.json["connectors"][0]["id"] == instance_id


def test_create_instance_no_url(client):
    """Creating an instance without a URL should fail"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]

    response = client.post(f"/api/connectors/{cid}/add_instance",
                           content_type="application/json",
                           headers={"X-API-KEY": MISP_EDITOR_KEY},
                           json={"name": "No URL", "type_select": "send_to"})
    assert response.status_code == 400


def test_create_instance_bad_url(client):
    """Creating an instance with an invalid URL should fail"""
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
    """Creating an instance for a non-existent connector should fail"""
    response = create_instance(client, 9999, name="Orphan")
    assert response.status_code == 404


def test_get_instances(client):
    """MISP editor should be able to list instances"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    create_instance(client, cid)

    response = client.get(f"/api/connectors/{cid}/instances",
                          headers={"X-API-KEY": MISP_EDITOR_KEY})
    assert response.status_code == 200
    assert "instances" in response.json


def test_delete_instance_misp_editor(client):
    """MISP editor should be able to delete instances"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(client, cid)
    iid = instance_response.json["connector_id"]

    response = client.get(f"/api/connectors/{cid}/instance/{iid}/delete",
                          headers={"X-API-KEY": MISP_EDITOR_KEY})
    assert response.status_code == 200
    assert "Instance deleted" in response.json["message"]


def test_delete_instance_editor_denied(client):
    """Editor should not be able to delete instances"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(client, cid)
    iid = instance_response.json["connector_id"]

    response = client.get(f"/api/connectors/{cid}/instance/{iid}/delete",
                          headers={"X-API-KEY": EDITOR_KEY})
    assert response.status_code == 403


def test_delete_org_shared_instance_orgadmin(client):
    """OrgAdmin should be able to delete an org-shared instance from their organisation."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(
        client,
        cid,
        api_key=ORGADMIN_MISP_KEY,
        payload={"sharing_scope": "org", "is_global_connector": True}
    )
    iid = instance_response.json["connector_id"]

    response = client.get(f"/api/connectors/{cid}/instance/{iid}/delete",
                          headers={"X-API-KEY": ORGADMIN_MISP_KEY})
    assert response.status_code == 200


def test_delete_org_shared_instance_admin_denied(client):
    """Admin should not be able to delete an org-scoped instance."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(
        client,
        cid,
        api_key=ORGADMIN_MISP_KEY,
        payload={"sharing_scope": "org", "is_global_connector": True}
    )
    iid = instance_response.json["connector_id"]

    response = client.get(f"/api/connectors/{cid}/instance/{iid}/delete",
                          headers={"X-API-KEY": ADMIN_KEY})
    assert response.status_code == 403


#####################
## Edit instance ##
#####################

def test_edit_instance(client):
    """MISP editor should be able to edit an instance"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(client, cid)
    iid = instance_response.json["connector_id"]

    response = client.post(f"/api/connectors/{cid}/edit_instance/{iid}",
                           content_type="application/json",
                           headers={"X-API-KEY": MISP_EDITOR_KEY},
                           json={"name": "Edited Instance",
                                 "url": "https://edited.example.com"})
    assert response.status_code == 200
    assert "Instance edited" in response.json["message"]


def test_edit_instance_duplicate_name(client):
    """Editing an instance to use an existing name should fail"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    create_instance(client, cid)

    # Create a second instance with a different name
    second = client.post(f"/api/connectors/{cid}/add_instance",
                         content_type="application/json",
                         headers={"X-API-KEY": MISP_EDITOR_KEY},
                         json={"name": "Second Instance",
                               "description": "test",
                               "type_select": "send_to",
                               "url": "https://second.example.com",
                               "api_key": "key2",
                               "is_global_connector": False})
    second_id = second.json["connector_id"]

    # Try to rename second instance to same name as first
    response = client.post(f"/api/connectors/{cid}/edit_instance/{second_id}",
                           content_type="application/json",
                           headers={"X-API-KEY": MISP_EDITOR_KEY},
                           json={"name": "Test Instance"})
    assert response.status_code == 400
    assert "Name already exist" in response.json["message"]


def test_edit_global_instance_orgadmin_denied(client):
    """OrgAdmin should not be able to take over a platform-global instance."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(
        client,
        cid,
        api_key=ADMIN_KEY,
        payload={"sharing_scope": "global", "is_global_connector": True}
    )
    iid = instance_response.json["connector_id"]

    response = client.post(f"/api/connectors/{cid}/edit_instance/{iid}",
                           content_type="application/json",
                           headers={"X-API-KEY": ORGADMIN_MISP_KEY},
                           json={"name": "Hijacked Instance"})
    assert response.status_code == 403


def test_edit_org_shared_instance_admin_denied(client):
    """Admin should not be able to edit an org-scoped instance."""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(
        client,
        cid,
        api_key=ORGADMIN_MISP_KEY,
        payload={"sharing_scope": "org", "is_global_connector": True}
    )
    iid = instance_response.json["connector_id"]

    response = client.post(f"/api/connectors/{cid}/edit_instance/{iid}",
                           content_type="application/json",
                           headers={"X-API-KEY": ADMIN_KEY},
                           json={"name": "Admin Edit Attempt"})
    assert response.status_code == 403


def test_edit_instance_invalid_url(client):
    """Editing an instance with an invalid URL should fail"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(client, cid)
    iid = instance_response.json["connector_id"]

    response = client.post(f"/api/connectors/{cid}/edit_instance/{iid}",
                           content_type="application/json",
                           headers={"X-API-KEY": MISP_EDITOR_KEY},
                           json={"url": "ftp://invalid.com"})
    assert response.status_code == 400
    assert "URL must start with http" in response.json["message"]


def test_edit_instance_no_data(client):
    """Editing an instance without meaningful data should return 400"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(client, cid)
    iid = instance_response.json["connector_id"]

    response = client.post(f"/api/connectors/{cid}/edit_instance/{iid}",
                           content_type="application/json",
                           headers={"X-API-KEY": MISP_EDITOR_KEY},
                           json={})
    assert response.status_code == 400


def test_edit_instance_nonexistent_connector(client):
    """Editing an instance on a non-existent connector should return 404"""
    response = client.post("/api/connectors/9999/edit_instance/1",
                           content_type="application/json",
                           headers={"X-API-KEY": MISP_EDITOR_KEY},
                           json={"name": "test"})
    assert response.status_code == 404


def test_edit_instance_editor_denied(client):
    """Regular editor should not be able to edit instances"""
    create_response = create_connector(client)
    cid = create_response.json["connector_id"]
    instance_response = create_instance(client, cid)
    iid = instance_response.json["connector_id"]

    response = client.post(f"/api/connectors/{cid}/edit_instance/{iid}",
                           content_type="application/json",
                           headers={"X-API-KEY": EDITOR_KEY},
                           json={"name": "test"})
    assert response.status_code == 403
