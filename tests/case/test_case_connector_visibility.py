import json
import uuid

import pytest
from flask import template_rendered
from flask.sessions import SecureCookieSessionInterface

from app.case import common_core as CommonModel
from app.case.CaseCore import CaseModel
from app.db_class.db import (
    AnonymousUser, Case, Case_Connector_Instance, Case_Org, Connector, Connector_Instance,
    User, User_Connector_Instance, db,
)


@pytest.fixture
def connected_case(client, app):
    response = client.post("/api/case/create", headers={"X-API-KEY": "editor_api_key"},
                           json={"title": "Connector visibility case"})
    assert response.status_code == 201
    cid = response.json["case_id"]
    with app.app_context():
        users = {key: User.query.filter_by(api_key=key + "_api_key").one()
                 for key in ("read", "editor", "misp_editor", "admin", "caseadmin")}
        for key in ("read", "misp_editor", "caseadmin"):
            db.session.add(Case_Org(case_id=cid, org_id=users[key].org_id))
        connector = Connector(name="Visibility test connector", uuid=str(uuid.uuid4()))
        db.session.add(connector)
        db.session.flush()
        instances = {}
        for name, scope, org in (
            ("own-personal", "personal", None),
            ("other-personal", "personal", None),
            ("reader-org", "org", users["read"].org_id),
            ("editor-org", "org", users["editor"].org_id),
            ("global", "global", None),
        ):
            instance = Connector_Instance(
                connector_id=connector.id, name=name, sharing_scope=scope, shared_org_id=org,
                url=f"https://{name}.example.invalid", description=f"METADATA-{name}", uuid=str(uuid.uuid4()),
                global_api_key="DO-NOT-EXPOSE-GLOBAL-KEY" if scope == "global" else None,
            )
            db.session.add(instance)
            db.session.flush()
            db.session.add(Case_Connector_Instance(case_id=cid, instance_id=instance.id, identifier="test"))
            if scope == "personal":
                owner = users["misp_editor"] if name == "own-personal" else users["admin"]
                db.session.add(User_Connector_Instance(user_id=owner.id, instance_id=instance.id,
                                                       api_key="DO-NOT-EXPOSE-PERSONAL-KEY"))
            instances[name] = instance.to_json()
        db.session.commit()
        return {"case": cid, "connector": connector.id, "instances": instances}


def expected_names(key):
    return {
        "read": {"global", "reader-org"},
        "editor": {"global", "editor-org"},
        "misp_editor": {"global", "own-personal"},
        "admin": {"global", "reader-org", "editor-org", "own-personal", "other-personal"},
        "caseadmin": {"global", "reader-org", "editor-org", "own-personal", "other-personal"},
    }[key]


def assert_metadata(case, data, names):
    expected = [item for name, item in data["instances"].items() if name in names]
    assert sorted(case["connectors"], key=lambda item: item["id"]) == sorted(expected, key=lambda item: item["id"])
    body = json.dumps(case)
    for name, item in data["instances"].items():
        if name not in names:
            assert item["url"] not in body
            assert item["description"] not in body
            assert item["uuid"] not in body
    assert "DO-NOT-EXPOSE-GLOBAL-KEY" not in body
    assert "DO-NOT-EXPOSE-PERSONAL-KEY" not in body


def login(client, app, key):
    app.session_interface = SecureCookieSessionInterface()
    with app.app_context():
        login_id = User.query.filter_by(api_key=key + "_api_key").one().get_id()
    with client.session_transaction() as session:
        session["_user_id"] = login_id
        session["_fresh"] = True


@pytest.mark.parametrize("key", ["read", "editor", "misp_editor", "admin", "caseadmin"])
def test_case_api_respects_connector_metadata_visibility(client, connected_case, key):
    data = connected_case
    cid = data["case"]
    listing = client.get(f"/api/connectors/{data['connector']}/instances",
                         headers={"X-API-KEY": key + "_api_key"})
    assert listing.status_code == 200
    general_visibility = {"global"} if key == "caseadmin" else expected_names(key)
    assert {item["name"] for item in listing.json["instances"]} == general_visibility
    for method, url, payload in (
        ("GET", f"/api/case/{cid}", None),
        ("GET", "/api/case/all", None),
        ("GET", "/api/case/not_completed", None),
        ("POST", "/api/case/title", {"title": "Connector visibility case"}),
        ("POST", "/api/case/search", {"search": "Connector visibility case"}),
    ):
        response = client.open(url, method=method, json=payload, headers={"X-API-KEY": key + "_api_key"})
        assert response.status_code == 200
        result = next(case for case in response.json["cases"] if case["id"] == cid) if "cases" in response.json else response.json
        assert_metadata(result, data, expected_names(key))


@pytest.mark.parametrize("key", ["read", "misp_editor", "admin", "caseadmin"])
def test_case_browser_representations_filter_connectors(client, app, connected_case, key):
    data = connected_case
    cid = data["case"]
    login(client, app, key)
    with app.app_context():
        month = db.session.get(Case, cid).creation_date.strftime("%Y-%m")
    urls = [f"/case/get_case/{cid}", f"/case/{cid}/get_case_info",
            "/case/search?text=Connector%20visibility%20case", "/last_case"]
    if key != "admin":
        urls.append(f"/calendar/get_case_month?date={month}&dead_creation=false")
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200
        if "cases" in response.json:
            result = next(case for case in response.json["cases"] if case["id"] == cid)
        else:
            result = response.json.get("case", response.json)
        assert_metadata(result, data, expected_names(key))
    contexts = []

    def capture(sender, template, context, **extra):
        if "case" in context:
            contexts.append(context["case"])

    with template_rendered.connected_to(capture, app):
        response = client.get(f"/case/{cid}")
    assert response.status_code == 200
    assert_metadata(contexts[-1], data, expected_names(key))


def test_serialization_without_authenticated_user_omits_connectors(app, connected_case):
    with app.app_context():
        case = db.session.get(Case, connected_case["case"])
        assert case.to_json()["connectors"] == []
        assert case.to_json(AnonymousUser())["connectors"] == []


@pytest.mark.parametrize("session_key,api_key", [("admin", "read"), ("read", "admin")])
def test_case_connector_metadata_uses_api_identity(client, app, connected_case, session_key, api_key):
    login(client, app, session_key)
    response = client.get(f"/api/case/{connected_case['case']}", headers={"X-API-KEY": api_key + "_api_key"})
    assert response.status_code == 200
    assert_metadata(response.json, connected_case, expected_names(api_key))


@pytest.mark.parametrize("delegate_key", ["read", "admin"])
def test_case_connector_metadata_uses_relay_delegate(client, app, connected_case, delegate_key):
    with app.app_context():
        admin = User.query.filter_by(api_key="admin_api_key").one()
        delegate = User.query.filter_by(api_key=delegate_key + "_api_key").one()
        delegate.matrix_id = "@connector-test:example.org"
        db.session.add(User(first_name="Connector", last_name="Relay", email="connector-relay@example.org",
                            role_id=admin.role_id, org_id=admin.org_id, is_bot=True, api_key="connector_relay_test"))
        db.session.commit()
    response = client.get(f"/api/case/{connected_case['case']}",
                          headers={"X-API-KEY": "connector_relay_test", "MATRIX-ID": "@connector-test:example.org"})
    assert response.status_code == 200
    assert_metadata(response.json, connected_case, expected_names(delegate_key))


def test_case_admin_inspection_requires_membership_and_does_not_grant_key_use(client, app, connected_case):
    data = connected_case
    with app.app_context():
        user = User.query.filter_by(api_key="caseadmin_api_key").one()
        personal = db.session.get(Connector_Instance, data["instances"]["other-personal"]["id"])
        assert CommonModel.can_access_all_case_connectors(data["case"], user)
        assert not CommonModel.can_use_case_connector(personal, user, data["case"])
        Case_Org.query.filter_by(case_id=data["case"], org_id=user.org_id).delete()
        db.session.commit()
    response = client.get(f"/api/case/{data['case']}", headers={"X-API-KEY": "caseadmin_api_key"})
    assert response.status_code == 200
    assert_metadata(response.json, data, {"global"})


def test_personal_access_revocation_rechecked_without_removing_attachment(client, app, connected_case):
    data = connected_case
    iid = data["instances"]["own-personal"]["id"]
    with app.app_context():
        user = User.query.filter_by(api_key="misp_editor_api_key").one()
        User_Connector_Instance.query.filter_by(instance_id=iid, user_id=user.id).delete()
        db.session.commit()
        assert Case_Connector_Instance.query.filter_by(case_id=data["case"], instance_id=iid).count() == 1
    response = client.get(f"/api/case/{data['case']}", headers={"X-API-KEY": "misp_editor_api_key"})
    assert response.status_code == 200
    assert_metadata(response.json, data, {"global"})


def test_scope_and_organization_changes_rechecked(client, app, connected_case):
    data = connected_case
    with app.app_context():
        instance = db.session.get(Connector_Instance, data["instances"]["global"]["id"])
        instance.sharing_scope = "personal"
        reader = User.query.filter_by(api_key="read_api_key").one()
        reader.org_id = User.query.filter_by(api_key="editor_api_key").one().org_id
        db.session.commit()
    response = client.get(f"/api/case/{data['case']}", headers={"X-API-KEY": "read_api_key"})
    assert response.status_code == 200
    assert_metadata(response.json, data, {"editor-org"})


def test_legacy_scope_fallback_matches_connector_catalog(client, app, connected_case):
    data = connected_case
    with app.app_context():
        instance = db.session.get(Connector_Instance, data["instances"]["reader-org"]["id"])
        instance.sharing_scope = ""
        db.session.commit()
        data["instances"]["reader-org"] = instance.to_json()
    response = client.get(f"/api/case/{data['case']}", headers={"X-API-KEY": "read_api_key"})
    assert response.status_code == 200
    assert_metadata(response.json, data, expected_names("read"))
    listing = client.get(f"/api/connectors/{data['connector']}/instances", headers={"X-API-KEY": "read_api_key"})
    assert {item["id"] for item in listing.json["instances"]} == {item["id"] for item in response.json["connectors"]}


@pytest.mark.parametrize("key", ["editor", "misp_editor", "admin"])
def test_fork_copies_only_connectors_visible_to_actor(client, app, connected_case, key):
    data = connected_case
    response = client.post(f"/api/case/{data['case']}/fork", headers={"X-API-KEY": key + "_api_key"},
                           json={"case_title_fork": "Forked connector visibility case"})
    assert response.status_code == 201
    expected = {item["id"] for name, item in data["instances"].items() if name in expected_names(key)}
    with app.app_context():
        copies = Case_Connector_Instance.query.filter_by(case_id=response.json["new_case_id"]).all()
        assert {copy.instance_id for copy in copies} == expected


def test_module_context_keeps_selected_connector_credential_checks(app, connected_case):
    data = connected_case
    with app.app_context():
        case = db.session.get(Case, data["case"])
        user = User.query.filter_by(api_key="misp_editor_api_key").one()
        own = Case_Connector_Instance.query.filter_by(case_id=case.id,
                instance_id=data["instances"]["own-personal"]["id"]).one()
        result, _, _, credentials = CaseModel._build_case_connector_module_context(own.id, case, user)
        assert_metadata(result, data, expected_names("misp_editor"))
        assert credentials["api_key"] == "DO-NOT-EXPOSE-PERSONAL-KEY"
        other = Case_Connector_Instance.query.filter_by(case_id=case.id,
                instance_id=data["instances"]["other-personal"]["id"]).one()
        result, _, _, error = CaseModel._build_case_connector_module_context(other.id, case, user)
        assert result is None
        assert error["message"] == "Action not allowed"
