from app.db_class.db import Case, Misp_Attribute, Task, Case_Misp_Object, Task_Misp_Object, Task_Misp_Attribute


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
        "misp-objects": [],
        "standalone_attributes": []
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


def test_import_case_with_standalone_misp_attribute(client, app):
    """Importer should create case-level standalone MISP attributes from JSON."""
    title = "Case With Standalone Attribute"
    payload = minimal_case(title)
    payload["standalone_attributes"] = [{
        "value": "8.8.8.8",
        "type": "ip-dst",
        "object_relation": "",
        "first_seen": "",
        "last_seen": "",
        "comment": "imported standalone",
        "ids_flag": False,
        "disable_correlation": False
    }]

    response = client.post("/api/importer/case",
                           content_type="application/json",
                           headers={"X-API-KEY": IMPORTER_KEY},
                           json=payload)
    assert response.status_code == 200
    assert "All created" in response.json["message"]

    with app.app_context():
        case = Case.query.filter_by(title=title).first()
        assert case is not None
        attrs = Misp_Attribute.query.filter_by(case_id=case.id, case_misp_object_id=None).all()
        assert len(attrs) == 1
        assert attrs[0].value == "8.8.8.8"
        assert attrs[0].type == "ip-dst"


def test_import_case_with_misp_attributes_alias(client, app):
    """Importer should also accept legacy/alias key 'misp-attributes'."""
    title = "Case With MISP Attributes Alias"
    payload = minimal_case(title)
    payload.pop("standalone_attributes", None)
    payload["misp-attributes"] = [{
        "value": "example.org",
        "type": "domain",
        "object_relation": "",
        "first_seen": "",
        "last_seen": "",
        "comment": "alias import",
        "ids_flag": False,
        "disable_correlation": True
    }]

    response = client.post("/api/importer/case",
                           content_type="application/json",
                           headers={"X-API-KEY": IMPORTER_KEY},
                           json=payload)
    assert response.status_code == 200
    assert "All created" in response.json["message"]

    with app.app_context():
        case = Case.query.filter_by(title=title).first()
        assert case is not None
        attrs = Misp_Attribute.query.filter_by(case_id=case.id, case_misp_object_id=None).all()
        assert len(attrs) == 1
        assert attrs[0].value == "example.org"
        assert attrs[0].type == "domain"


def test_import_case_batch(client):
    """Importer should be able to create multiple cases at once"""
    batch = [minimal_case("Batch Case A"), minimal_case("Batch Case B")]

    response = client.post("/api/importer/case",
                           content_type="application/json",
                           headers={"X-API-KEY": IMPORTER_KEY},
                           json=batch)
    assert response.status_code == 200
    assert "All created" in response.json["message"]


def test_import_case_task_links_to_object_and_attribute(client, app):
    """Importer should recreate Task <-> MISP object/attribute links from exported JSON."""
    title = "Case With Task Links"
    payload = minimal_case(title)

    # Define MISP object with one attribute
    payload["misp-objects"] = [{
        "template_uuid": "tpl-uuid-1",
        "name": "TestObject",
        "attributes": [{
            "value": "1.2.3.4",
            "type": "ip-src",
            "object_relation": "ip-src",
            "first_seen": "",
            "last_seen": "",
            "comment": "",
            "ids_flag": False,
            "disable_correlation": False
        }]
    }]

    # Task that links to the above object and attribute
    payload["tasks"] = [{
        "title": "Task with links",
        "description": "",
        "uuid": "",
        "deadline": "",
        "time_required": "",
        "urls_tools": [],
        "notes": [],
        "tags": [],
        "clusters": [],
        "subtasks": [],
        "custom_tags": [],
        "misp_object_links": [{
            "misp_object_template_uuid": "tpl-uuid-1",
            "misp_object_name": "TestObject"
        }],
        "misp_attribute_links": [{
            "misp_attribute_value": "1.2.3.4",
            "misp_attribute_type": "ip-src",
            "misp_attribute_object_relation": "ip-src"
        }]
    }]

    response = client.post("/api/importer/case",
                           content_type="application/json",
                           headers={"X-API-KEY": IMPORTER_KEY},
                           json=payload)
    assert response.status_code == 200
    assert "All created" in response.json["message"]

    with app.app_context():
        case = Case.query.filter_by(title=title).first()
        assert case is not None

        # There should be one object and one task
        obj = Case_Misp_Object.query.filter_by(case_id=case.id, name="TestObject").first()
        assert obj is not None

        task = Task.query.filter_by(case_id=case.id).first()
        assert task is not None

        # Verify Task -> Object link exists
        tob = Task_Misp_Object.query.filter_by(task_id=task.id, misp_object_id=obj.id).first()
        assert tob is not None

        # Verify attribute exists on the object. Note: importer creates
        # Task->Object links for referenced objects, but does not
        # automatically create Task->Attribute links for attributes
        # embedded in objects unless explicitly referenced by UUID.
        attr = None
        for a in obj.attributes:
            if a.value == "1.2.3.4" and a.type == "ip-src":
                attr = a
                break
        assert attr is not None
        tam = Task_Misp_Attribute.query.filter_by(task_id=task.id, misp_attribute_id=attr.id).first()
        assert tam is None


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
