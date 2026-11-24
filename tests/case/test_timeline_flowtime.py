"""Case page assets and existing timeline API contract used by Flowtime."""
from flask.sessions import SecureCookieSessionInterface

from app.db_class.db import User


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
