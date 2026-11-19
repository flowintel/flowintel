import pytest
from flask.sessions import SecureCookieSessionInterface

from app import db
from app.alerting import alerting_core as AlertingCore
from app.db_class.db import Case, Case_Org, ExternalAlert, ExternalAlertAction, User


@pytest.fixture
def review_alert(app, monkeypatch):
    monkeypatch.setattr(app, "session_interface", SecureCookieSessionInterface())
    monkeypatch.setitem(app.config, "SESSION_REDIS", None)
    with app.app_context():
        owner = User.query.filter_by(api_key="editor_api_key").one()
        admin = User.query.filter_by(api_key="admin_api_key").one()
        other = User.query.filter_by(api_key="orgadmin_api_key").one()
        case = Case(title="Private alert investigation", is_private=True)
        db.session.add(case)
        db.session.flush()
        db.session.add(Case_Org(case_id=case.id, org_id=owner.org_id))
        alert = ExternalAlert(case_id=case.id, owner_user_id=owner.id, title="Alert title",
                              review_status="reviewing", review_comment="PRIVATE REVIEW COMMENT",
                              reviewed_by_id=admin.id, reviewed_at=AlertingCore.utcnow(), is_read=False,
                              raw_payload={"private": "PRIVATE PAYLOAD"})
        db.session.add(alert)
        db.session.flush()
        AlertingCore.record_alert_action(alert, "reviewing", admin, comment="PRIVATE ACTOR COMMENT")
        db.session.commit()
        return {"alert": alert.id, "case": case.id, "owner": owner.id, "admin": admin.id,
                "org": owner.org_id, "other_org": other.org_id, "other": other.id}


def login(client, app, user_id):
    with app.app_context():
        login_id = db.session.get(User, user_id).get_id()
    with client.session_transaction() as session:
        session["_user_id"] = login_id
        session["_fresh"] = True


def snapshot(alert):
    return ({column.name: getattr(alert, column.name) for column in ExternalAlert.__table__.columns},
            [action.to_json() for action in ExternalAlertAction.query.filter_by(alert_id=alert.id).all()])


@pytest.mark.parametrize("scope,loss", [
    (scope, loss) for scope in ("personal", "org", "global")
    for loss in ("membership", "privacy", "demotion")
] + [("personal", "organization")])
def test_revoked_case_access_blocks_direct_alert_actions(client, app, review_alert, scope, loss):
    data = review_alert
    with app.app_context():
        owner = db.session.get(User, data["owner"])
        alert = db.session.get(ExternalAlert, data["alert"])
        case = db.session.get(Case, data["case"])
        if scope != "personal":
            alert.owner_user_id = None
            alert.owner_org_id = owner.org_id if scope == "org" else None
        if loss == "privacy":
            case.is_private = False
            Case_Org.query.filter_by(case_id=case.id).delete()
        elif loss == "demotion":
            owner.role_id = db.session.get(User, data["admin"]).role_id
            Case_Org.query.filter_by(case_id=case.id).delete()
        db.session.commit()
        assert AlertingCore.can_user_view_alert(alert, owner)

    if loss == "organization":
        response = client.post(f"/api/admin/edit_user/{data['owner']}",
                               headers={"X-API-KEY": "admin_api_key"}, json={"org": data["other_org"]})
        assert response.status_code == 200
    with app.app_context():
        if loss == "membership":
            Case_Org.query.filter_by(case_id=data["case"]).delete()
        elif loss == "privacy":
            db.session.get(Case, data["case"]).is_private = True
        elif loss == "demotion":
            db.session.get(User, data["owner"]).role_id = db.session.get(User, data["other"]).role_id
        db.session.commit()
        before = snapshot(db.session.get(ExternalAlert, data["alert"]))
        cases_before = Case.query.count()

    login(client, app, data["owner"])
    # Lists already hide the alert; direct requests must enforce the same boundary.
    assert client.get("/alerting/api").json == []
    assert client.get("/alerting/api/unread").json == {"count": 0}
    for status in sorted(AlertingCore.ALERT_REVIEW_STATUSES):
        response = client.post(f"/alerting/api/{data['alert']}/review",
                               json={"review_status": status, "comment": "Unauthorized review"})
        assert response.status_code == 403
        assert response.json == {"message": "Permission denied"}
    response = client.post(f"/alerting/api/{data['alert']}/case", json={"title": "Unauthorized duplicate"})
    assert response.status_code == 403
    assert response.json == {"message": "Permission denied"}
    assert client.post(f"/alerting/api/{data['alert']}/read").json == {"status": "ok"}
    assert client.post("/alerting/api/read_all").json == {"status": "ok", "count": 0}
    with app.app_context():
        assert snapshot(db.session.get(ExternalAlert, data["alert"])) == before
        assert Case.query.count() == cases_before


@pytest.mark.parametrize("scope", ["personal", "org", "global"])
@pytest.mark.parametrize("case_state", ["private", "public", "unlinked", "deleted"])
def test_authorized_alert_review_and_read_remain_available(client, app, review_alert, scope, case_state):
    data = review_alert
    with app.app_context():
        alert = db.session.get(ExternalAlert, data["alert"])
        if scope != "personal":
            alert.owner_user_id = None
            alert.owner_org_id = data["org"] if scope == "org" else None
        if case_state == "public":
            db.session.get(Case, data["case"]).is_private = False
            Case_Org.query.filter_by(case_id=data["case"]).delete()
        elif case_state == "unlinked":
            alert.case_id = None
        elif case_state == "deleted":
            Case_Org.query.filter_by(case_id=data["case"]).delete()
            db.session.delete(db.session.get(Case, data["case"]))
        db.session.commit()
    login(client, app, data["owner"])
    assert [alert["id"] for alert in client.get("/alerting/api").json] == [data["alert"]]
    assert client.get("/alerting/api/unread").json == {"count": 1}
    assert client.post(f"/alerting/api/{data['alert']}/read").json == {"status": "ok"}
    response = client.post(f"/alerting/api/{data['alert']}/review",
                           json={"review_status": "dismissed", "comment": "Authorized review"})
    assert response.status_code == 200
    assert response.json["alert"]["review_comment"] == "Authorized review"
    assert {action["comment"] for action in response.json["alert"]["action_history"]} == {
        "PRIVATE ACTOR COMMENT", "Authorized review"}
    with app.app_context():
        alert = db.session.get(ExternalAlert, data["alert"])
        assert alert.reviewed_by_id == data["owner"] and alert.is_read
        assert alert.status == "dismissed"


@pytest.mark.parametrize("actor", ["owner", "admin"])
def test_case_membership_does_not_override_connector_ownership(client, app, review_alert, actor):
    data = review_alert
    with app.app_context():
        alert = db.session.get(ExternalAlert, data["alert"])
        alert.owner_user_id = data["other"]
        # Personal ownership takes precedence over the stored org scope.
        alert.owner_org_id = data["org"]
        db.session.commit()
    login(client, app, data[actor])
    response = client.post(f"/alerting/api/{data['alert']}/review", json={"review_status": "reviewing"})
    assert response.status_code == (200 if actor == "admin" else 403)


@pytest.mark.parametrize("winner_access", ["private_outside", "private_member", "public", "admin"])
def test_case_claim_loser_rechecks_access_before_returning_winner_id(client, app, monkeypatch, review_alert, winner_access):
    data = review_alert
    with app.app_context():
        alert = db.session.get(ExternalAlert, data["alert"])
        alert.case_id = None
        if winner_access == "public":
            db.session.get(Case, data["case"]).is_private = False
        if winner_access in {"private_outside", "admin"}:
            Case_Org.query.filter_by(case_id=data["case"]).delete()
        db.session.commit()
        cases_before = Case.query.count()
    original_title = AlertingCore.unique_case_title

    def competing_claim(title, alert_id):
        # Interleave the winning claim after the initial guard but before this request's CAS.
        db.session.get(ExternalAlert, alert_id).case_id = data["case"]
        db.session.commit()
        return original_title(title, alert_id)

    monkeypatch.setattr(AlertingCore, "unique_case_title", competing_claim)
    login(client, app, data["admin"] if winner_access == "admin" else data["owner"])
    response = client.post(f"/alerting/api/{data['alert']}/case", json={"title": "Losing claim", "is_private": True})
    if winner_access == "private_outside":
        assert response.status_code == 403
        assert response.json == {"message": "Permission denied"}
    else:
        assert response.status_code == 400
        assert response.json == {"message": "Alert already linked to a case", "case_id": data["case"]}
    with app.app_context():
        assert Case.query.count() == cases_before
        assert db.session.get(ExternalAlert, data["alert"]).case_id == data["case"]
        assert Case.query.filter_by(title="Losing claim").count() == 0


def test_editor_can_create_private_case_from_unlinked_alert(client, app, review_alert):
    data = review_alert
    with app.app_context():
        db.session.get(ExternalAlert, data["alert"]).case_id = None
        db.session.commit()
    login(client, app, data["owner"])
    response = client.post(f"/alerting/api/{data['alert']}/case", json={"title": "New private case", "is_private": True})
    assert response.status_code == 201
    with app.app_context():
        alert = db.session.get(ExternalAlert, data["alert"])
        assert AlertingCore.can_user_view_alert(alert, db.session.get(User, data["owner"]))
        assert db.session.get(Case, alert.case_id).is_private


@pytest.mark.parametrize("private", [False, True])
def test_personal_alert_owner_without_org(client, app, review_alert, private):
    data = review_alert
    with app.app_context():
        db.session.get(User, data["owner"]).org_id = None
        db.session.get(Case, data["case"]).is_private = private
        db.session.commit()
    login(client, app, data["owner"])
    response = client.post(f"/alerting/api/{data['alert']}/review", json={"review_status": "reviewing"})
    assert response.status_code == (403 if private else 200)


def test_alert_route_errors_and_readonly_permissions_preserved(client, app, review_alert):
    data = review_alert
    login(client, app, data["owner"])
    assert client.post(f"/alerting/api/{data['alert']}/review", json={"review_status": "invalid"}).status_code == 400
    for action in ("review", "case"):
        assert client.post(f"/alerting/api/999999/{action}", json={"review_status": "reviewing"}).status_code == 404
    with app.app_context():
        reader = User.query.filter_by(api_key="read_api_key").one()
        alert = db.session.get(ExternalAlert, data["alert"])
        alert.owner_user_id = reader.id
        db.session.add(Case_Org(case_id=data["case"], org_id=reader.org_id))
        db.session.commit()
        before = snapshot(alert)
        reader_id = reader.id
    login(client, app, reader_id)
    assert [item["id"] for item in client.get("/alerting/api").json] == [data["alert"]]
    assert client.post(f"/alerting/api/{data['alert']}/review", json={"review_status": "reviewing"}).status_code == 403
    assert client.post(f"/alerting/api/{data['alert']}/case", json={"title": "Read-only case"}).status_code == 403
    with app.app_context():
        assert snapshot(db.session.get(ExternalAlert, data["alert"])) == before


def test_review_response_rechecks_new_private_case_link(client, app, monkeypatch, review_alert):
    data = review_alert
    with app.app_context():
        db.session.get(ExternalAlert, data["alert"]).case_id = None
        db.session.commit()
    original_record = AlertingCore.record_alert_action
    winner_ids = []

    def competing_case_creation(alert, action, user, **kwargs):
        if user.id == data["owner"]:
            # A separate session links a private case after this review was authorized.
            with app.app_context():
                admin = db.session.get(User, data["admin"])
                current_alert = db.session.get(ExternalAlert, data["alert"])
                payload, status = AlertingCore.create_case_from_alert(
                    current_alert, admin, {"title": "Concurrent private investigation", "is_private": True})
                assert status == 201
                winner_ids.append(payload["case_id"])
        original_record(alert, action, user, **kwargs)

    monkeypatch.setattr(AlertingCore, "record_alert_action", competing_case_creation)
    login(client, app, data["owner"])
    response = client.post(f"/alerting/api/{data['alert']}/review",
                           json={"review_status": "reviewing", "comment": "Review started before linking"})
    assert winner_ids
    assert response.status_code == 403
    assert response.json == {"message": "Permission denied"}
    assert client.get("/alerting/api").json == []
