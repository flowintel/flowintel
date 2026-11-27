"""Case page assets and existing timeline API contract used by Flowtime."""
from flask.sessions import SecureCookieSessionInterface

from app.db_class.db import Case, Case_Misp_Object, Case_Timeline_Event, File, Misp_Attribute, Task, User, db


def login_admin(client, app):
    app.session_interface = SecureCookieSessionInterface()
    with app.app_context():
        login_id = User.query.filter_by(api_key="admin_api_key").one().get_id()
    with client.session_transaction() as session:
        session["_user_id"] = login_id
        session["_fresh"] = True


def create_case(client):
    response = client.post("/api/case/create", headers={"X-API-KEY": "admin_api_key"},
                           json={"title": "Flowtime integration"})
    assert response.status_code == 201
    return response.json["case_id"]


def test_case_loads_flowtime_assets_and_not_timelinejs(client, app):
    case_id = create_case(client)
    login_admin(client, app)
    response = client.get(f"/case/{case_id}")
    assert response.status_code == 200
    assert b"css/vendor/vitrine/flowtime.css" in response.data
    assert b"css/case/timeline_view.css" in response.data
    assert b"timelinejs" not in response.data
    for asset in ("js/vendor/vitrine/flowtime.js", "js/case/flowtime_adapter.js",
                  "css/vendor/vitrine/flowtime.css"):
        assert client.get("/static/" + asset).status_code == 200
    assert client.get("/static/js/vendor/flowtime/flowtime.js").status_code == 404



def test_timeline_event_crud_still_supplies_parsed_dates_and_notes(client, app):
    case_id = create_case(client)
    login_admin(client, app)
    base = f"/case/{case_id}"
    payload = {"date_text": "19/11/2026 14h30", "description": "Suspicious sign-in",
               "additional_note": "<img src=x onerror=alert(1)> is plain text"}
    response = client.post(base + "/create_timeline_event", json=payload)
    assert response.status_code == 200
    event_id = response.json["event"]["id"]
    response = client.get(base + "/get_timeline_events")
    assert response.status_code == 200
    event = response.json["events"][0]
    assert event["date_parsed"] == "2026-11-19 14:30"
    assert event["additional_note"] == payload["additional_note"]
    assert event["description"] == payload["description"]
    payload.update(description="Sign-in investigated", additional_note="Analyst notes updated")
    response = client.post(base + f"/edit_timeline_event/{event_id}", json=payload)
    assert response.status_code == 200
    assert client.get(base + "/get_timeline_events").json["events"][0]["description"] == "Sign-in investigated"
    assert client.get(base + f"/delete_timeline_event/{event_id}").status_code == 200
    assert client.get(base + "/get_timeline_events").json["events"] == []


def test_timeline_mutations_remain_forbidden_for_read_only_users(client, app):
    case_id = create_case(client)
    login_admin(client, app)
    base = f"/case/{case_id}"
    payload = {"date_text": "2026-11-19 14:30", "description": "Protected event"}
    created = client.post(base + "/create_timeline_event", json=payload)
    assert created.status_code == 200
    event_id = created.json["event"]["id"]
    with app.app_context():
        read_id = User.query.filter_by(api_key="read_api_key").one().get_id()
    with client.session_transaction() as session:
        session["_user_id"] = read_id
        session["_fresh"] = True
    assert client.post(base + f"/edit_timeline_event/{event_id}", json=payload).status_code == 403
    assert client.get(base + f"/delete_timeline_event/{event_id}").status_code == 403
    assert len(client.get(base + "/get_timeline_events").json["events"]) == 1


def test_import_candidates_search_and_page_within_case(client, app):
    cid = create_case(client)
    login_admin(client, app)
    url = f"/case/{cid}/timeline_import_candidates"
    with app.app_context():
        foreign_case = Case(title="Other case", is_private=True)
        objects = [Case_Misp_Object(case_id=cid, name="domain-ip") for _ in range(23)]
        attr = Misp_Attribute(case_id=cid, type="text", value="literal_%")
        task = Task(case_id=cid, title="Collect evidence")
        db.session.add_all([foreign_case, *objects, attr, task])
        db.session.flush()
        foreign = Case_Misp_Object(case_id=foreign_case.id, name="external")
        foreign_task = Task(case_id=foreign_case.id, title=task.title)
        db.session.add_all([foreign, foreign_task])
        db.session.flush()
        file = File(task_id=task.id, name="capture.pcap")
        db.session.add_all([
            file, File(case_id=cid, name="case.log"), File(task_id=foreign_task.id, name="foreign.log"),
            Misp_Attribute(case_misp_object_id=objects[0].id, type="domain", value="Example.test"),
            Misp_Attribute(case_misp_object_id=foreign.id, type="domain", value="Example.test"),
            Misp_Attribute(case_id=foreign_case.id, type="text", value=attr.value),
        ])
        db.session.flush()
        for fields in ({"misp_object_id": objects[0].id}, {"misp_object_id": -attr.id}, {"file_id": file.id}):
            db.session.add(Case_Timeline_Event(case_id=cid, date_text="2026-01-01", description="Imported", **fields))
        db.session.commit()
        object_id, foreign_id = objects[0].id, foreign_case.id

    first = client.get(url).json
    second = client.get(url, query_string={"page": 2}).json
    assert first["has_next"] and len(first["items"]) == 20
    assert not second["has_next"] and len(second["items"]) == 3
    assert first["total_pages"] == second["total_pages"] == 2
    assert first["total"] == second["total"] == client.get(url, query_string={"page": 3}).json["total"] == 23
    assert len({row["id"] for row in first["items"] + second["items"]}) == 23
    result = client.get(url, query_string={"q": "EXAMPLE"}).json
    assert result["total"] == 1
    assert result["total_pages"] == 1
    assert result["items"] == [{"id": object_id, "label": "domain-ip", "detail": "Example.test", "is_imported": True}]
    eligible = client.get(url, query_string={"ids_only": 1}).json["ids"]
    assert set(eligible) == {row["id"] for row in first["items"] + second["items"] if not row["is_imported"]}
    assert client.get(url, query_string={"ids_only": 1, "q": "EXAMPLE"}).json["ids"] == []
    result = client.get(url, query_string={"source": "attributes", "q": "_%"}).json["items"]
    assert [(row["label"], row["is_imported"]) for row in result] == [("literal_%", True)]
    assert client.get(url, query_string={"source": "attributes", "ids_only": 1}).json["ids"] == []
    assert client.get(url, query_string={"source": "attributes", "q": "EXAMPLE"}).json == {
        "items": [], "total": 0, "total_pages": 0, "has_next": False
    }
    files = client.get(url, query_string={"source": "files"}).json["items"]
    assert {row["label"] for row in files} == {"capture.pcap", "case.log"}
    assert client.get(url, query_string={"source": "files", "ids_only": 1}).json["ids"] == [
        row["id"] for row in files if row["label"] == "case.log"
    ]
    files = client.get(url, query_string={"source": "files", "q": "collect"}).json["items"]
    assert [(row["label"], row["is_imported"]) for row in files] == [("capture.pcap", True)]
    assert client.get(url, query_string={"source": "unknown"}).status_code == 400
    assert client.get(url, query_string={"page": -1}).status_code == 400
    with app.app_context():
        reader = User.query.filter_by(api_key="read_api_key").one().get_id()
    with client.session_transaction() as session:
        session["_user_id"] = reader
    assert client.get(f"/case/{foreign_id}/timeline_import_candidates").status_code == 404
