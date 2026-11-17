import pytest
from flask import template_rendered
from flask.sessions import SecureCookieSessionInterface

from app.extensions import db
from app.db_class.db import AnonymousUser, Case, Case_Org, User


@pytest.fixture
def linked_cases(client, app):
    def create(title, key, private=False):
        response = client.post(
            "/api/case/create",
            headers={"X-API-KEY": key},
            json={"title": title, "description": title + " description", "is_private": private},
        )
        assert response.status_code == 201
        return {"id": response.json["case_id"], "title": title, "description": title + " description"}

    source = create("Link visibility source", "editor_api_key")
    public = create("PUBLIC LINK TARGET", "admin_api_key")
    private = create("PRIVATE LINK TARGET", "admin_api_key", private=True)
    response = client.post(
        f"/api/case/{source['id']}/add_link",
        headers={"X-API-KEY": "admin_api_key"},
        json={"case_id": [public["id"], private["id"]]},
    )
    assert response.status_code == 200
    with app.app_context():
        editor = User.query.filter_by(api_key="editor_api_key").one()
        reader = User.query.filter_by(api_key="read_api_key").one()
        # Editor is a private-target member; reader can see only the public source/target.
        db.session.add(Case_Org(case_id=private["id"], org_id=editor.org_id))
        db.session.add(Case_Org(case_id=source["id"], org_id=reader.org_id))
        db.session.commit()
    return source, public, private


def login(client, app, key):
    app.session_interface = SecureCookieSessionInterface()
    with app.app_context():
        login_id = User.query.filter_by(api_key=key).one().get_id()
    with client.session_transaction() as session:
        session["_user_id"] = login_id
        session["_fresh"] = True


@pytest.mark.parametrize("key", ["read_api_key", "editor_api_key", "admin_api_key"])
def test_api_case_representations_filter_linked_cases(client, app, linked_cases, key):
    source, public, private = linked_cases
    headers = {"X-API-KEY": key}
    expected = [public] if key == "read_api_key" else [public, private]
    direct = client.get(f"/api/case/{private['id']}", headers=headers)
    assert direct.status_code == (403 if key == "read_api_key" else 200)

    requests = [
        ("GET", f"/api/case/{source['id']}", None),
        ("GET", "/api/case/all", None),
        ("GET", "/api/case/not_completed", None),
        ("POST", "/api/case/title", {"title": source["title"]}),
        ("POST", "/api/case/search", {"search": source["title"]}),
    ]
    for method, url, payload in requests:
        response = client.open(url, method=method, json=payload, headers=headers)
        assert response.status_code == 200
        cases = response.json.get("cases", [response.json])
        result = next(case for case in cases if case["id"] == source["id"])
        assert sorted(result["link_to"], key=lambda link: link["id"]) == expected

    with app.app_context():
        db.session.get(Case, source["id"]).completed = True
        db.session.commit()
    response = client.get("/api/case/completed", headers=headers)
    assert response.status_code == 200
    result = next(case for case in response.json["cases"] if case["id"] == source["id"])
    assert sorted(result["link_to"], key=lambda link: link["id"]) == expected


@pytest.mark.parametrize("key", ["read_api_key", "editor_api_key", "admin_api_key"])
def test_browser_case_representations_filter_linked_cases(client, app, linked_cases, key):
    source, public, private = linked_cases
    expected = [public] if key == "read_api_key" else [public, private]
    login(client, app, key)
    urls = [
        f"/case/get_case/{source['id']}",
        f"/case/{source['id']}/get_case_info",
        "/case/search?text=Link%20visibility%20source",
        "/last_case",
    ]
    if key != "admin_api_key":
        with app.app_context():
            month = db.session.get(Case, source["id"]).creation_date.strftime("%Y-%m")
        urls.append(f"/calendar/get_case_month?date={month}&dead_creation=false")
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200
        if "cases" in response.json:
            result = next(case for case in response.json["cases"] if case["id"] == source["id"])
        else:
            result = response.json.get("case", response.json)
        assert sorted(result["link_to"], key=lambda link: link["id"]) == expected

    rendered_cases = []

    def capture_case(sender, template, context, **extra):
        if "case" in context:
            rendered_cases.append(context["case"])

    with template_rendered.connected_to(capture_case, app):
        response = client.get(f"/case/{source['id']}")
    assert response.status_code == 200
    assert sorted(rendered_cases[-1]["link_to"], key=lambda link: link["id"]) == expected


@pytest.mark.parametrize(
    "session_key,api_key", [("admin_api_key", "read_api_key"), ("read_api_key", "admin_api_key")]
)
def test_api_link_visibility_uses_api_identity(client, app, linked_cases, session_key, api_key):
    source, public, private = linked_cases
    login(client, app, session_key)
    response = client.get(f"/api/case/{source['id']}", headers={"X-API-KEY": api_key})
    assert response.status_code == 200
    expected = [public] if api_key == "read_api_key" else [public, private]
    assert sorted(response.json["link_to"], key=lambda link: link["id"]) == expected


def test_link_serialization_without_user_fails_closed(app, linked_cases):
    source, public, private = linked_cases
    with app.app_context():
        case = db.session.get(Case, source["id"])
        assert case.to_json()["link_to"] == [public]
        assert case.to_json(AnonymousUser())["link_to"] == [public]
        admin = User.query.filter_by(api_key="admin_api_key").one()
        assert sorted(case.to_json(admin)["link_to"], key=lambda link: link["id"]) == [public, private]


@pytest.mark.parametrize("delegate_key", ["read_api_key", "admin_api_key"])
def test_relay_link_visibility_uses_delegated_identity(client, app, linked_cases, delegate_key):
    source, public, private = linked_cases
    with app.app_context():
        admin = User.query.filter_by(api_key="admin_api_key").one()
        delegate = User.query.filter_by(api_key=delegate_key).one()
        delegate.matrix_id = "@link-test:example.org"
        db.session.add(User(
            first_name="Relay", last_name="Test", email="link-relay@example.org",
            api_key="link_relay_test_key", role_id=admin.role_id, org_id=admin.org_id, is_bot=True,
        ))
        db.session.commit()
    headers = {"X-API-KEY": "link_relay_test_key", "MATRIX-ID": "@link-test:example.org"}
    response = client.get(f"/api/case/{source['id']}", headers=headers)
    assert response.status_code == 200
    expected = [public] if delegate_key == "read_api_key" else [public, private]
    assert sorted(response.json["link_to"], key=lambda link: link["id"]) == expected


def test_existing_links_recheck_visibility_after_membership_change(client, app, linked_cases):
    source, public, private = linked_cases
    headers = {"X-API-KEY": "editor_api_key"}
    assert len(client.get(f"/api/case/{source['id']}", headers=headers).json["link_to"]) == 2
    with app.app_context():
        editor = User.query.filter_by(api_key="editor_api_key").one()
        Case_Org.query.filter_by(case_id=private["id"], org_id=editor.org_id).delete()
        db.session.commit()
    assert client.get(f"/api/case/{private['id']}", headers=headers).status_code == 403
    response = client.get(f"/api/case/{source['id']}", headers=headers)
    assert response.json["link_to"] == [public]
    with app.app_context():
        db.session.get(Case, private["id"]).is_private = False
        db.session.commit()
    response = client.get(f"/api/case/{source['id']}", headers=headers)
    assert sorted(response.json["link_to"], key=lambda link: link["id"]) == [public, private]
