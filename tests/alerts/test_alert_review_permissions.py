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
    queue = client.get("/alerting/api/queue?q=PRIVATE+ACTOR+COMMENT").json
    assert queue["items"] == [] and queue["total"] == 0
    assert queue["counts"] == {"unread": 0, "new": 0, "critical": 0}
    assert client.get(f"/alerting/api/{data['alert']}").status_code == 404
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
    assert client.post("/alerting/api/bulk_review", json={
        "alert_ids": [data["alert"]], "review_status": "dismissed",
    }).status_code == 403
    assert client.post("/alerting/api/bulk_review", json={
        "filters": {"review_status": "all"}, "review_status": "dismissed",
    }).status_code == 403
    assert client.post(f"/alerting/api/{data['alert']}/case", json={"title": "Read-only case"}).status_code == 403
    with app.app_context():
        assert snapshot(db.session.get(ExternalAlert, data["alert"])) == before


def test_alert_queue_filters_and_paginates_past_previous_limit(client, app, review_alert):
    data = review_alert
    with app.app_context():
        old_alert = db.session.get(ExternalAlert, data["alert"])
        old_alert.severity = "critical"
        old_alert.observables = [{"value": "Alert-Sensor%_Alpha"}]
        # Identical timestamps need a stable order across page boundaries.
        timestamp = AlertingCore.utcnow()
        newer = [ExternalAlert(title=f"New alert {i}", creation_date=timestamp) for i in range(200)]
        hidden = ExternalAlert(title="Alert-Sensor%_Alpha", severity="critical", owner_user_id=data["other"])
        wildcard = ExternalAlert(title="Alert-SensorXYZAlpha", severity="critical")
        db.session.add_all([*newer, hidden, wildcard])
        db.session.commit()
        expected = [wildcard.id, *(a.id for a in reversed(newer)), old_alert.id]

    login(client, app, data["owner"])
    first = client.get("/alerting/api/queue").json
    second = client.get("/alerting/api/queue?page=2").json
    last = client.get("/alerting/api/queue?page=500").json
    assert first["total"] == 202 and first["pages"] == 9
    assert first["counts"] == {"unread": 202, "new": 201, "critical": 2}
    assert [a["id"] for a in first["items"] + second["items"]] == expected[:50]
    assert last["page"] == 9
    assert [a["id"] for a in last["items"]] == expected[200:]
    for term in ("alert-sensor%_alpha", "private actor comment", "private alert investigation"):
        response = client.get("/alerting/api/queue", query_string={
            "q": term, "review_status": "reviewing", "severity": "critical",
        })
        assert response.status_code == 200
        row, = response.json["items"]
        assert row["id"] == data["alert"]
        assert row["observable_count"] == 1 and row["last_action"]["user_id"] == data["admin"]
        assert {"raw_payload", "observables", "action_history"}.isdisjoint(row)
    assert client.get("/alerting/api/queue", query_string={"q": "alert-sensor%_alpha"}).json["total"] == 1
    detail = client.get(f"/alerting/api/{data['alert']}").json
    assert detail["raw_payload"] == {"private": "PRIVATE PAYLOAD"}
    assert detail["action_history"][0]["comment"] == "PRIVATE ACTOR COMMENT"
    page = client.get(f"/alerting/?alert_id={data['alert']}")
    assert page.status_code == 200 and b"PRIVATE PAYLOAD" not in page.data
    assert client.post("/alerting/api/read_all").json == {"status": "ok", "count": 202}
    assert client.get("/alerting/api/unread").json == {"count": 0}


def test_bulk_alert_review_is_atomic_and_records_one_action_per_change(client, app, review_alert):
    data = review_alert
    with app.app_context():
        first = db.session.get(ExternalAlert, data["alert"])
        second = ExternalAlert(title="Shared alert", owner_org_id=data["org"])
        hidden = ExternalAlert(title="Private case alert", case_id=data["case"], owner_user_id=data["other"])
        db.session.add_all([second, hidden])
        db.session.commit()
        visible_ids, hidden_id = [first.id, second.id], hidden.id

    login(client, app, data["owner"])
    path = "/alerting/api/bulk_review"
    for invalid in ([], [True], [2**31], [1] * 101):
        assert client.post(path, json={"alert_ids": invalid, "review_status": "dismissed"}).status_code == 400
    assert client.post(path, json={"alert_ids": visible_ids, "review_status": "case_created"}).status_code == 400
    assert client.post(path, json={"alert_ids": [*visible_ids, hidden_id], "review_status": "dismissed"}).status_code == 403
    with app.app_context():
        assert [db.session.get(ExternalAlert, aid).review_status for aid in visible_ids] == ["reviewing", "new"]
        assert ExternalAlertAction.query.filter_by(action="dismissed").count() == 0

    request = {"alert_ids": [*visible_ids, visible_ids[0]], "review_status": "dismissed"}
    assert client.post(path, json=request).json == {"count": 2}
    assert client.post(path, json=request).json == {"count": 0}
    assert client.get("/alerting/api/queue").json["total"] == 0
    assert client.get("/alerting/api/queue?review_status=closed").json["total"] == 2
    with app.app_context():
        assert db.session.get(ExternalAlert, hidden_id).review_status == "new"
        for aid in visible_ids:
            alert = db.session.get(ExternalAlert, aid)
            assert alert.review_status == alert.status == "dismissed"
            assert alert.is_read and alert.reviewed_by_id == data["owner"]
            action = ExternalAlertAction.query.filter_by(alert_id=aid, action="dismissed").one()
            assert action.user_id == data["owner"]


def test_bulk_review_updates_matching_alerts_across_pages(client, app, review_alert):
    data = review_alert
    with app.app_context():
        private_case = Case(title="Other organisation's investigation", is_private=True)
        db.session.add(private_case)
        db.session.flush()
        common = {"severity": "high", "observables": [{"value": "Sensor%_Alpha"}]}
        matches = [ExternalAlert(**common) for _ in range(501)]
        already_reviewing = ExternalAlert(**common, review_status="reviewing")
        excluded = [
            ExternalAlert(**common, review_status="dismissed"),
            ExternalAlert(**common, owner_org_id=data["other_org"]),
            ExternalAlert(**common, owner_user_id=data["owner"], case_id=private_case.id),
            ExternalAlert(severity="low", observables=common["observables"]),
            ExternalAlert(severity="high", title="SensorXYZAlpha"),
        ]
        db.session.add_all([*matches, already_reviewing, *excluded])
        db.session.commit()
        expected_ids = {alert.id for alert in matches}
        untouched = {alert.id: snapshot(alert) for alert in [already_reviewing, *excluded]}

    login(client, app, data["owner"])
    path = "/alerting/api/bulk_review"
    filters = {"review_status": "active", "severity": "high", "q": "sensor%_alpha"}
    queue = client.get("/alerting/api/queue", query_string=filters).json
    assert queue["total"] == 502 and len(queue["items"]) == 25
    for invalid in ({}, [], {**filters, "q": []}, {**filters, "severity": "unknown"}, {**filters, "status": "all"}):
        assert client.post(path, json={"filters": invalid, "review_status": "reviewing"}).status_code == 400
    assert client.post(path, json={"filters": filters, "alert_ids": [data["alert"]], "review_status": "reviewing"}).status_code == 400

    request = {"filters": filters, "review_status": "reviewing"}
    response = client.post(path, json=request)
    assert response.status_code == 200 and response.json == {"count": 501}
    assert client.post(path, json=request).json == {"count": 0}
    with app.app_context():
        actions = ExternalAlertAction.query.filter_by(action="reviewing", user_id=data["owner"]).all()
        assert len(actions) == len(expected_ids) and {action.alert_id for action in actions} == expected_ids
        updated = ExternalAlert.query.filter_by(review_status="reviewing", reviewed_by_id=data["owner"], is_read=True).all()
        assert {alert.id for alert in updated} == expected_ids
        for aid, before in untouched.items():
            assert snapshot(db.session.get(ExternalAlert, aid)) == before


def test_filtered_bulk_review_rolls_back_if_access_changes_during_update(client, app, review_alert, monkeypatch):
    data = review_alert
    with app.app_context():
        later_alert = ExternalAlert(title="Another matching alert")
        db.session.add(later_alert)
        db.session.commit()
        later_id = later_alert.id
        before = {aid: snapshot(db.session.get(ExternalAlert, aid)) for aid in (data["alert"], later_id)}

    monkeypatch.setattr(AlertingCore, "BULK_REVIEW_BATCH_SIZE", 1)
    original_batches = AlertingCore.matching_alert_id_batches

    def change_access_before_update(query):
        for ids in original_batches(query):
            if later_id in ids:
                db.session.get(ExternalAlert, later_id).owner_user_id = data["other"]
            yield ids

    monkeypatch.setattr(AlertingCore, "matching_alert_id_batches", change_access_before_update)
    login(client, app, data["owner"])
    response = client.post("/alerting/api/bulk_review", json={
        "filters": {"review_status": "active"}, "review_status": "dismissed",
    })
    assert response.status_code == 409
    with app.app_context():
        for aid, state in before.items():
            assert snapshot(db.session.get(ExternalAlert, aid)) == state


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
