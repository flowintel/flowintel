import importlib
import uuid
from datetime import datetime, timezone

import pytest
from flask.sessions import SecureCookieSessionInterface

from app.case import common_core as CommonModel
from app.case.TaskCore import TaskModel
from app.db_class.db import Case, Case_Org, Case_Timeline_Event, File, Notification, Status, Task, User, db


@pytest.fixture
def evidence(client, app, tmp_path, monkeypatch):
    for module in ("app.case.TaskCore", "app.case.CaseCore"):
        monkeypatch.setattr(importlib.import_module(module), "FILE_FOLDER", str(tmp_path))
    response = client.post("/api/case/create", headers={"X-API-KEY": "editor_api_key"},
                           json={"title": "Evidence permission case"})
    assert response.status_code == 201
    with app.app_context():
        case = db.session.get(Case, response.json["case_id"])
        case.privileged_case = True
        case.is_private = True
        for key in ("queuer", "caseadmin", "queue_admin", "read"):
            user = User.query.filter_by(api_key=key + "_api_key").one()
            db.session.add(Case_Org(case_id=case.id, org_id=user.org_id))
        statuses = {status.name: status.id for status in Status.query.all()}
        task = Task(case_id=case.id, title="Evidence awaiting review", uuid=str(uuid.uuid4()),
                    status_id=statuses["Requested"], completed=False, case_order_id=1,
                    creation_date=datetime.now(timezone.utc), last_modif=datetime.now(timezone.utc))
        sibling = Task(case_id=case.id, title="Unrestricted sibling", uuid=str(uuid.uuid4()),
                       status_id=statuses["Approved"], completed=False, case_order_id=2)
        db.session.add_all([task, sibling])
        db.session.flush()
        file = File(task_id=task.id, name="evidence.txt", uuid=str(uuid.uuid4()),
                    file_type="text/plain", file_size=8, upload_date=datetime.now(timezone.utc))
        db.session.add(file)
        db.session.flush()
        event = Case_Timeline_Event(case_id=case.id, file_id=file.id,
                                    date_text="2026-11-16", description="Evidence in timeline")
        db.session.add(event)
        case.nb_tasks = 2
        db.session.commit()
        path = tmp_path / file.uuid
        path.write_bytes(b"evidence")
        return {"case": case.id, "task": task.id, "task_uuid": task.uuid,
                "sibling": sibling.id, "file": file.id, "event": event.id,
                "path": path, "statuses": statuses}


def login(client, app, key):
    app.session_interface = SecureCookieSessionInterface()
    with app.app_context():
        login_id = User.query.filter_by(api_key=key + "_api_key").one().get_id()
    with client.session_transaction() as session:
        session["_user_id"] = login_id
        session["_fresh"] = True


def delete(client, evidence, mode, key, tid=None, fid=None):
    tid = evidence["task"] if tid is None else tid
    fid = evidence["file"] if fid is None else fid
    if mode == "api":
        return client.get(f"/api/task/{tid}/delete_file/{fid}",
                          headers={"X-API-KEY": key + "_api_key"})
    return client.get(f"/case/task/{tid}/delete_file/{fid}")


def snapshot(app, evidence):
    with app.app_context():
        task = db.session.get(Task, evidence["task"])
        case = db.session.get(Case, evidence["case"])
        file = db.session.get(File, evidence["file"])
        event = db.session.get(Case_Timeline_Event, evidence["event"])
        return (file.to_json() if file else None, event.to_json() if event else None,
                task.last_modif, task.completed, task.status_id, task.case_order_id,
                case.last_modif, case.completed, case.status_id,
                CommonModel.get_history(case.uuid), Notification.query.count(),
                evidence["path"].read_bytes() if evidence["path"].exists() else None)


@pytest.mark.parametrize("key", ["editor", "queuer"])
@pytest.mark.parametrize("mode", ["browser", "api"])
def test_restricted_task_file_deletion_denied(client, app, evidence, key, mode):
    login(client, app, key)
    for status in ("Requested", "Rejected", "Request Review"):
        with app.app_context():
            db.session.get(Task, evidence["task"]).status_id = evidence["statuses"][status]
            db.session.commit()
        for tid in (evidence["task"], evidence["task_uuid"]):
            before = snapshot(app, evidence)
            response = delete(client, evidence, mode, key, tid=tid)
            assert response.status_code == 403
            assert "restricted status" in response.json["message"]
            assert snapshot(app, evidence) == before


@pytest.mark.parametrize("key", ["admin", "caseadmin", "queue_admin"])
@pytest.mark.parametrize("mode", ["browser", "api"])
@pytest.mark.parametrize("status", ["Requested", "Rejected", "Request Review"])
def test_approvers_can_delete_restricted_task_files(client, app, evidence, key, mode, status):
    login(client, app, key)
    with app.app_context():
        db.session.get(Task, evidence["task"]).status_id = evidence["statuses"][status]
        db.session.commit()
    assert delete(client, evidence, mode, key).status_code == 200
    assert not evidence["path"].exists()
    with app.app_context():
        assert db.session.get(File, evidence["file"]) is None
        assert db.session.get(Case_Timeline_Event, evidence["event"]) is None
        case = db.session.get(Case, evidence["case"])
        assert any("File deleted for task" in line for line in CommonModel.get_history(case.uuid))


def test_core_restricted_file_deletion_has_no_side_effects(app, evidence):
    before = snapshot(app, evidence)
    with app.app_context():
        editor = User.query.filter_by(api_key="editor_api_key").one()
        assert TaskModel.delete_file(db.session.get(File, evidence["file"]),
                                     db.session.get(Task, evidence["task"]), editor) is False
        db.session.commit()
    assert snapshot(app, evidence) == before


def test_core_cannot_substitute_an_unrestricted_task(app, evidence):
    before = snapshot(app, evidence)
    with app.app_context():
        editor = User.query.filter_by(api_key="editor_api_key").one()
        assert TaskModel.delete_file(db.session.get(File, evidence["file"]),
                                     db.session.get(Task, evidence["sibling"]), editor) is False
        db.session.commit()
    assert snapshot(app, evidence) == before


@pytest.mark.parametrize("mode", ["browser", "api"])
@pytest.mark.parametrize("privileged,status", [(False, "Requested"), (True, "Approved"), (True, "Ongoing")])
def test_editors_can_delete_unrestricted_task_files(client, app, evidence, mode, privileged, status):
    login(client, app, "editor")
    with app.app_context():
        db.session.get(Case, evidence["case"]).privileged_case = privileged
        db.session.get(Task, evidence["task"]).status_id = evidence["statuses"][status]
        db.session.commit()
    assert delete(client, evidence, mode, "editor").status_code == 200
    assert not evidence["path"].exists()
    with app.app_context():
        assert db.session.get(File, evidence["file"]) is None


@pytest.mark.parametrize("mode", ["browser", "api"])
def test_other_task_or_case_cannot_delete_restricted_evidence(client, app, evidence, mode):
    login(client, app, "admin")
    before = snapshot(app, evidence)
    assert delete(client, evidence, mode, "admin", tid=evidence["sibling"]).status_code in (403, 404)
    if mode == "api":
        response = client.get(f"/api/case/{evidence['case']}/delete_file/{evidence['file']}",
                              headers={"X-API-KEY": "admin_api_key"})
    else:
        response = client.get(f"/case/{evidence['case']}/delete_case_file/{evidence['file']}")
    assert response.status_code == 404
    assert snapshot(app, evidence) == before


@pytest.mark.parametrize("mode", ["browser", "api"])
def test_read_only_member_cannot_delete_files(client, app, evidence, mode):
    login(client, app, "read")
    before = snapshot(app, evidence)
    assert delete(client, evidence, mode, "read").status_code == 403
    assert snapshot(app, evidence) == before


@pytest.mark.parametrize("key", ["editor", "caseadmin", "queue_admin"])
@pytest.mark.parametrize("mode", ["browser", "api"])
def test_non_members_cannot_delete_restricted_files(client, app, evidence, key, mode):
    login(client, app, key)
    with app.app_context():
        user = User.query.filter_by(api_key=key + "_api_key").one()
        Case_Org.query.filter_by(case_id=evidence["case"], org_id=user.org_id).delete()
        db.session.commit()
    before = snapshot(app, evidence)
    assert delete(client, evidence, mode, key).status_code == 403
    assert snapshot(app, evidence) == before


@pytest.mark.parametrize("api_key,session_key,expected", [("editor", "admin", 403), ("admin", "editor", 200)])
def test_file_deletion_uses_api_identity(client, app, evidence, api_key, session_key, expected):
    login(client, app, session_key)
    before = snapshot(app, evidence)
    assert delete(client, evidence, "api", api_key).status_code == expected
    if expected == 403:
        assert snapshot(app, evidence) == before


@pytest.mark.parametrize("key,expected", [("editor", 403), ("queue_admin", 200)])
def test_file_deletion_uses_matrix_delegate(client, app, evidence, key, expected):
    with app.app_context():
        admin = User.query.filter_by(api_key="admin_api_key").one()
        delegate = User.query.filter_by(api_key=key + "_api_key").one()
        delegate.matrix_id = "@evidence-test:example.org"
        db.session.add(User(first_name="Evidence", last_name="Relay", email="evidence-relay@example.org",
                            role_id=admin.role_id, org_id=admin.org_id, is_bot=True, api_key="evidence_relay_test"))
        db.session.commit()
    before = snapshot(app, evidence)
    response = client.get(f"/api/task/{evidence['task_uuid']}/delete_file/{evidence['file']}",
                          headers={"X-API-KEY": "evidence_relay_test", "MATRIX-ID": "@evidence-test:example.org"})
    assert response.status_code == expected
    if expected == 403:
        assert snapshot(app, evidence) == before
