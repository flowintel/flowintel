IMPORTER_KEY = "importer_api_key"
TEMPLATE_EDITOR_KEY = "template_editor_api_key"
EDITOR_KEY = "editor_api_key"


def minimal_case(title="Imported Case"):
    """Build the minimum valid payload for the case importer."""
    return {
        "title": title,
        "description": "",
        "uuid": "",
        "deadline": "",
        "recurring_date": "",
        "recurring_type": "",
        "notes": "",
        "is_private": False,
        "time_required": "",
        "ticket_id": "",
        "tasks": [],
        "tags": [],
        "clusters": [],
        "custom_tags": [],
        "misp-objects": []
    }


def minimal_template(title="Imported Template"):
    """Build the minimum valid payload for the template importer."""
    return {
        "title": title,
        "description": "",
        "uuid": "",
        "notes": "",
        "is_private": False,
        "time_required": "",
        "tasks_template": [],
        "tags": [],
        "clusters": [],
        "custom_tags": []
    }


######################
## Import case ##
######################

def test_import_case_minimal(client):
    """Importer should be able to create a case from valid JSON"""
    response = client.post("/api/importer/case",
                           content_type="application/json",
                           headers={"X-API-KEY": IMPORTER_KEY},
                           json=minimal_case())
    assert response.status_code == 200
    assert "All created" in response.json["message"]


def test_import_case_with_task(client):
    """Importer should be able to create a case with tasks"""
    payload = minimal_case("Case With Task")
    payload["tasks"] = [{
        "title": "Imported Task",
        "description": "",
        "uuid": "",
        "deadline": "",
        "time_required": "",
        "urls_tools": [],
        "notes": [],
        "tags": [],
        "clusters": [],
        "subtasks": [],
        "custom_tags": []
    }]

    response = client.post("/api/importer/case",
                           content_type="application/json",
                           headers={"X-API-KEY": IMPORTER_KEY},
                           json=payload)
    assert response.status_code == 200
    assert "All created" in response.json["message"]


def test_import_case_batch(client):
    """Importer should be able to create multiple cases at once"""
    batch = [minimal_case("Batch Case A"), minimal_case("Batch Case B")]

    response = client.post("/api/importer/case",
                           content_type="application/json",
                           headers={"X-API-KEY": IMPORTER_KEY},
                           json=batch)
    assert response.status_code == 200
    assert "All created" in response.json["message"]


def test_import_case_duplicate_title(client):
    """Importing a case with an existing title should fail"""
    client.post("/api/importer/case",
                content_type="application/json",
                headers={"X-API-KEY": IMPORTER_KEY},
                json=minimal_case("Duplicate Title"))

    response = client.post("/api/importer/case",
                           content_type="application/json",
                           headers={"X-API-KEY": IMPORTER_KEY},
                           json=minimal_case("Duplicate Title"))
    assert response.status_code == 200
    assert "already exist" in response.json["message"]


def test_import_case_no_data(client):
    """Importing without a JSON body should be rejected"""
    response = client.post("/api/importer/case",
                           headers={"X-API-KEY": IMPORTER_KEY})
    assert response.status_code in (400, 415)


def test_import_case_editor_denied(client):
    """Regular editor should not be able to import cases"""
    response = client.post("/api/importer/case",
                           content_type="application/json",
                           headers={"X-API-KEY": EDITOR_KEY},
                           json=minimal_case())
    assert response.status_code == 403


def test_import_case_no_api_key(client):
    """Importing without an API key should be denied"""
    response = client.post("/api/importer/case",
                           content_type="application/json",
                           json=minimal_case())
    assert response.status_code == 403


########################
## Import template ##
########################

def test_import_template_minimal(client):
    """Template editor should be able to import a template"""
    response = client.post("/api/importer/template",
                           content_type="application/json",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_KEY},
                           json=minimal_template())
    assert response.status_code == 200
    assert "All created" in response.json["message"]


def test_import_template_duplicate_title(client):
    """Importing a template with an existing title should fail"""
    client.post("/api/importer/template",
                content_type="application/json",
                headers={"X-API-KEY": TEMPLATE_EDITOR_KEY},
                json=minimal_template("Dup Template"))

    response = client.post("/api/importer/template",
                           content_type="application/json",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_KEY},
                           json=minimal_template("Dup Template"))
    assert response.status_code == 200
    assert "already exist" in response.json["message"]


def test_import_template_editor_denied(client):
    """Regular editor should not be able to import templates"""
    response = client.post("/api/importer/template",
                           content_type="application/json",
                           headers={"X-API-KEY": EDITOR_KEY},
                           json=minimal_template())
    assert response.status_code == 403
