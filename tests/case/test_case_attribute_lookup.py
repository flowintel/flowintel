import uuid

import pytest

from app.db_class.db import Case, Case_Misp_Object, Case_Org, Misp_Attribute, User, db


ENDPOINT = "/api/case/search/attribute"
READ_HEADERS = {"X-API-KEY": "read_api_key"}


def add_case(title, value="example.org", private=False, completed=False, object_attribute=False):
    case = Case(title=title, uuid=str(uuid.uuid4()), is_private=private, completed=completed)
    db.session.add(case)
    db.session.flush()
    attribute = Misp_Attribute(value=value, type="domain")
    if object_attribute:
        obj = Case_Misp_Object(case_id=case.id, name="domain-ip")
        db.session.add(obj)
        db.session.flush()
        attribute.case_misp_object_id = obj.id
    else:
        attribute.case_id = case.id
    db.session.add(attribute)
    db.session.commit()
    return case


def test_standalone_object_and_completed_cases_are_deduplicated(client, app):
    with app.app_context():
        standalone = add_case("Standalone")
        object_case = add_case("Object case", object_attribute=True)
        closed = add_case("Completed", completed=True)
        db.session.add(Misp_Attribute(case_id=object_case.id, value="example.org", type="hostname"))
        db.session.commit()
        expected = [
            {"id": c.id, "uuid": c.uuid, "title": c.title, "completed": c.completed}
            for c in (standalone, object_case, closed)
        ]

    response = client.post(ENDPOINT, headers=READ_HEADERS, json={"value": "example.org"})
    assert response.status_code == 200
    assert response.json == {"cases": expected}


def test_private_visibility_for_read_only_org_member_and_admin(client, app):
    with app.app_context():
        # Public cases need not have an organisation attached to be visible.
        public = add_case("Public")
        shared = add_case("Shared private", private=True, object_attribute=True)
        hidden = add_case("Other organisation", private=True)
        read_user = User.query.filter_by(api_key="read_api_key").one()
        editor_user = User.query.filter_by(api_key="editor_api_key").one()
        db.session.add_all([
            Case_Org(case_id=shared.id, org_id=read_user.org_id),
            Case_Org(case_id=hidden.id, org_id=editor_user.org_id),
        ])
        db.session.commit()
        visible_ids = [public.id, shared.id]
        all_ids = [public.id, shared.id, hidden.id]

    response = client.post(ENDPOINT, headers=READ_HEADERS, json={"value": "example.org"})
    assert response.status_code == 200
    assert [c["id"] for c in response.json["cases"]] == visible_ids
    assert "Other organisation" not in response.get_data(as_text=True)

    response = client.post(ENDPOINT, headers={"X-API-KEY": "admin_api_key"}, json={"value": "example.org"})
    assert response.status_code == 200
    assert [c["id"] for c in response.json["cases"]] == all_ids


def test_exact_values_no_wildcards_and_no_title_search(client, app):
    with app.app_context():
        add_case("example.org", value="sub.example.org")
        literal = add_case("Literal wildcard", value="literal_%")
        add_case("Similar value", value="literal_abc")
        composite = add_case("Composite", value="file.exe|abc123")
        literal_id, composite_id = literal.id, composite.id

    for value in ("example.org", "%", "literal_", "abc123", "missing"):
        response = client.post(ENDPOINT, headers=READ_HEADERS, json={"value": value})
        assert response.status_code == 200
        assert response.json == {"cases": []}
    for value, expected_id in (("literal_%", literal_id), ("file.exe|abc123", composite_id)):
        response = client.post(ENDPOINT, headers=READ_HEADERS, json={"value": value})
        assert response.status_code == 200
        assert [c["id"] for c in response.json["cases"]] == [expected_id]


@pytest.mark.parametrize("payload", [{}, {"value": ""}, {"value": "  "}, {"value": None},
                                     {"value": 42}, {"value": ["example.org"]}, [], "example.org"])
def test_invalid_input(client, payload):
    response = client.post(ENDPOINT, headers=READ_HEADERS, json=payload)
    assert response.status_code == 400


def test_malformed_json(client):
    response = client.post(ENDPOINT, headers=READ_HEADERS, data="{invalid", content_type="application/json")
    assert response.status_code == 400


@pytest.mark.parametrize("headers", [{}, {"X-API-KEY": "invalid"}])
def test_authentication_required(client, headers):
    response = client.post(ENDPOINT, headers=headers, json={"value": "example.org"})
    assert response.status_code == 403
