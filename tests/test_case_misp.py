import pytest

from app.db_class.db import User
from app.case.CaseCore import CaseModel
from app.utils import utils


@pytest.fixture
def create_case(app):
    with app.app_context():
        user = User.query.filter_by(api_key="editor_api_key").first()
        form = {
            "title": "test case",
            "description": "desc",
            "deadline_date": "",
            "deadline_time": "",
            "tags": [],
            "clusters": [],
            "custom_tags": [],
            "time_required": 0,
            "is_private": False,
            "ticket_id": ""
        }
        case = CaseModel.create_case(form, user)
        # keep the app context (and DB session) active for the duration
        # of the test by yielding the created objects
        yield case, user


def create_object_via_api(client, cid, api_key, template, attributes):
    payload = {
        "object-template": {"uuid": template["uuid"], "name": template["name"]},
        "attributes": attributes,
    }
    return client.post(f"/api/case/{cid}/create_misp_object", json=payload, headers={"X-API-KEY": api_key})


def get_case_objects(client, cid, api_key):
    res = client.get(f"/api/case/{cid}/get_case_misp_object", headers={"X-API-KEY": api_key})
    assert res.status_code == 200
    return res.get_json()["misp-object"]


def test_create_misp_object(create_case, client):
    case, user = create_case
    api_key = "editor_api_key"

    templates = utils.get_object_templates()
    assert templates, "No misp object templates available"
    template = templates[0]

    attributes = [
        {
            "value": "1.2.3.4",
            "type": "ip-src",
            "object_relation": "",
            "first_seen": "",
            "last_seen": "",
            "ids_flag": False,
            "disable_correlation": False,
            "comment": "initial"
        }
    ]

    res = create_object_via_api(client, case.id, api_key, template, attributes)
    assert res.status_code == 200

    objs = get_case_objects(client, case.id, api_key)
    assert len(objs) == 1


def test_add_attributes(create_case, client):
    case, user = create_case
    api_key = "editor_api_key"
    templates = utils.get_object_templates()
    template = templates[0]

    # create object
    attributes = [
        {"value": "10.0.0.1", "type": "ip-src", "object_relation": "", "first_seen": "", "last_seen": "", "ids_flag": False, "disable_correlation": False, "comment": "a"}
    ]
    res = create_object_via_api(client, case.id, api_key, template, attributes)
    assert res.status_code == 200

    objs = get_case_objects(client, case.id, api_key)
    oid = objs[0]["object_id"]

    add_payload = {
        "object-template": {"uuid": template["uuid"], "name": template["name"]},
        "attributes": [
            {"value": "example.com", "type": "domain", "object_relation": "", "first_seen": "", "last_seen": "", "ids_flag": False, "disable_correlation": False, "comment": "added"}
        ]
    }
    res = client.post(f"/api/case/{case.id}/add_attributes/{oid}", json=add_payload, headers={"X-API-KEY": api_key})
    assert res.status_code == 200

    objs = get_case_objects(client, case.id, api_key)
    assert len(objs[0]["attributes"]) == 2


def test_edit_attribute(create_case, client):
    case, user = create_case
    api_key = "editor_api_key"
    templates = utils.get_object_templates()
    template = templates[0]

    # create object with one attribute
    attributes = [
        {"value": "2.2.2.2", "type": "ip-src", "object_relation": "", "first_seen": "", "last_seen": "", "ids_flag": False, "disable_correlation": False, "comment": "orig"}
    ]
    res = create_object_via_api(client, case.id, api_key, template, attributes)
    assert res.status_code == 200

    objs = get_case_objects(client, case.id, api_key)
    oid = objs[0]["object_id"]
    aid = objs[0]["attributes"][0]["id"]

    edit_payload = {
        "value": "3.3.3.3",
        "type": "ip-src",
        "object_relation": "",
        "first_seen": "",
        "last_seen": "",
        "ids_flag": False,
        "disable_correlation": False,
        "comment": "edited"
    }
    res = client.post(f"/api/case/{case.id}/misp_object/{oid}/edit_attr/{aid}", json=edit_payload, headers={"X-API-KEY": api_key})
    assert res.status_code == 200

    # verify change
    objs = get_case_objects(client, case.id, api_key)
    assert objs[0]["attributes"][0]["value"] == "3.3.3.3"


def test_delete_attribute_and_object(create_case, client):
    case, user = create_case
    api_key = "editor_api_key"
    templates = utils.get_object_templates()
    template = templates[0]

    # create object with two attributes
    attributes = [
        {"value": "9.9.9.9", "type": "ip-src", "object_relation": "", "first_seen": "", "last_seen": "", "ids_flag": False, "disable_correlation": False, "comment": "a"},
        {"value": "sub.example", "type": "domain", "object_relation": "", "first_seen": "", "last_seen": "", "ids_flag": False, "disable_correlation": False, "comment": "b"}
    ]
    res = create_object_via_api(client, case.id, api_key, template, attributes)
    assert res.status_code == 200

    objs = get_case_objects(client, case.id, api_key)
    oid = objs[0]["object_id"]
    aids = [a["id"] for a in objs[0]["attributes"]]

    # delete first attribute
    res = client.get(f"/api/case/{case.id}/misp_object/{oid}/delete_attribute/{aids[0]}", headers={"X-API-KEY": api_key})
    assert res.status_code == 200

    # delete object
    res = client.get(f"/api/case/{case.id}/delete_object/{oid}", headers={"X-API-KEY": api_key})
    assert res.status_code == 200

    # verify no objects
    objs = get_case_objects(client, case.id, api_key)
    assert len(objs) == 0


def test_standalone_misp_attribute_lifecycle(create_case, client):
    case, user = create_case
    api_key = "admin_api_key"

    create_payload = {
        "value": "5.5.5.5",
        "type": "ip-dst",
        "comment": "standalone",
        "ids_flag": False,
        "disable_correlation": False,
        "first_seen": "",
        "last_seen": ""
    }

    res = client.post(
        f"/api/case/{case.id}/create_misp_attribute",
        json=create_payload,
        headers={"X-API-KEY": api_key}
    )
    assert res.status_code == 201
    created_attr = res.get_json()["attribute"]
    aid = created_attr["id"]

    res = client.get(f"/api/case/{case.id}/get_case_misp_attributes", headers={"X-API-KEY": api_key})
    assert res.status_code == 200
    attrs = res.get_json()["attributes"]
    assert any(attr["id"] == aid and attr["value"] == "5.5.5.5" for attr in attrs)

    edit_payload = {
        "value": "6.6.6.6",
        "type": "ip-dst",
        "comment": "edited standalone",
        "ids_flag": True,
        "disable_correlation": True,
        "first_seen": "",
        "last_seen": ""
    }
    res = client.post(
        f"/api/case/{case.id}/misp_attribute/{aid}/edit_misp_attribute",
        json=edit_payload,
        headers={"X-API-KEY": api_key}
    )
    assert res.status_code == 200

    res = client.get(f"/api/case/{case.id}/get_case_misp_attributes", headers={"X-API-KEY": api_key})
    assert res.status_code == 200
    attrs = res.get_json()["attributes"]
    edited = next(attr for attr in attrs if attr["id"] == aid)
    assert edited["value"] == "6.6.6.6"
    assert edited["ids_flag"] is True
    assert edited["disable_correlation"] is True

    res = client.get(
        f"/api/case/{case.id}/misp_attribute/{aid}/delete_misp_attribute",
        headers={"X-API-KEY": api_key}
    )
    assert res.status_code == 200

    res = client.get(f"/api/case/{case.id}/get_case_misp_attributes", headers={"X-API-KEY": api_key})
    assert res.status_code == 200
    attrs = res.get_json()["attributes"]
    assert all(attr["id"] != aid for attr in attrs)

