import uuid
from datetime import datetime, timezone

import pytest
from flask.sessions import SecureCookieSessionInterface

from app.case import common_core as CommonModel
from app.case.TaskCore import TaskModel
from app.db_class.db import Case, Case_Org, Notification, Status, Task, Task_User, User, db


@pytest.fixture
def workflow(client, app):
    response = client.post("/api/case/create", headers={"X-API-KEY": "editor_api_key"},
                           json={"title": "Final review case"})
    assert response.status_code == 201
    cid = response.json["case_id"]
    with app.app_context():
        case = db.session.get(Case, cid)
        case.privileged_case = True
        for key in ("queuer", "caseadmin", "queue_admin"):
            user = User.query.filter_by(api_key=key + "_api_key").one()
            db.session.add(Case_Org(case_id=cid, org_id=user.org_id))
        statuses = {status.name: status.id for status in Status.query.all()}
        task = Task(case_id=cid, title="Work awaiting review", uuid=str(uuid.uuid4()),
                    status_id=statuses["Approved"], completed=False, case_order_id=1,
                    creation_date=datetime.now(timezone.utc), last_modif=datetime.now(timezone.utc))
        sibling = Task(case_id=cid, title="Other work", uuid=str(uuid.uuid4()),
                       status_id=statuses["Ongoing"], completed=False, case_order_id=2,
                       creation_date=datetime.now(timezone.utc), last_modif=datetime.now(timezone.utc))
        db.session.add_all([task, sibling])
        db.session.flush()
        editor = User.query.filter_by(api_key="editor_api_key").one()
        db.session.add(Task_User(task_id=task.id, user_id=editor.id))
        case.nb_tasks = 2
        db.session.commit()
        return {"case": cid, "task": task.id, "task_uuid": task.uuid,
                "sibling": sibling.id, "statuses": statuses}


def login(client, app, key):
    app.session_interface = SecureCookieSessionInterface()
    with app.app_context():
        login_id = User.query.filter_by(api_key=key + "_api_key").one().get_id()
    with client.session_transaction() as session:
        session["_user_id"] = login_id
        session["_fresh"] = True


def finish(client, workflow, mode, key, destination=None, task_id=None):
    tid = workflow["task"] if task_id is None else task_id
    destination = workflow["statuses"]["Finished"] if destination is None else destination
    headers = {"X-API-KEY": key + "_api_key"}
    if mode == "api_complete":
        return client.get(f"/api/task/{tid}/complete", headers=headers)
    if mode == "browser_complete":
        return client.get(f"/case/complete_task/{tid}")
    if mode == "api_status":
        return client.post(f"/api/task/{tid}/change_status", headers=headers, json={"status_id": destination})
    return client.post(f"/case/{workflow['case']}/change_task_status/{tid}", json={"status": destination})


def reset_task(app, workflow, status="Approved", completed=False):
    with app.app_context():
        task = db.session.get(Task, workflow["task"])
        task.status_id = workflow["statuses"][status]
        task.completed = completed
        task.finish_date = datetime.now(timezone.utc) if completed else None
        task.case_order_id = -1 if completed else 1
        db.session.commit()


def snapshot(app, workflow):
    with app.app_context():
        task = db.session.get(Task, workflow["task"])
        sibling = db.session.get(Task, workflow["sibling"])
        case = db.session.get(Case, workflow["case"])
        return (
            task.completed, task.status_id, task.finish_date, task.case_order_id, task.last_modif,
            sibling.case_order_id, case.completed, case.finish_date, case.status_id, case.last_modif,
            Notification.query.count(), CommonModel.get_history(case.uuid),
        )


MODES = ("api_complete", "browser_complete", "api_status", "browser_status")


@pytest.mark.parametrize("key", ["editor", "queuer"])
def test_non_approvers_cannot_finish_privileged_tasks(client, app, workflow, key):
    login(client, app, key)
    for status in ("Created", "Approved", "Ongoing", "Requested", "Rejected", "Request Review", "Finished"):
        reset_task(app, workflow, status=status)
        for mode in MODES:
            before = snapshot(app, workflow)
            response = finish(client, workflow, mode, key)
            assert response.status_code == 403
            assert snapshot(app, workflow) == before
    # String status IDs and UUID task aliases must not bypass the same permission.
    reset_task(app, workflow)
    for mode in MODES:
        before = snapshot(app, workflow)
        response = finish(client, workflow, mode, key,
                          destination=str(workflow["statuses"]["Finished"]), task_id=workflow["task_uuid"])
        assert response.status_code == 403
        assert snapshot(app, workflow) == before


@pytest.mark.parametrize("key", ["admin", "caseadmin", "queue_admin"])
def test_approvers_can_finish_reviewed_tasks(client, app, workflow, key):
    login(client, app, key)
    for status in ("Approved", "Ongoing", "Request Review"):
        for mode in MODES:
            reset_task(app, workflow, status=status)
            response = finish(client, workflow, mode, key)
            assert response.status_code == 200
            with app.app_context():
                task = db.session.get(Task, workflow["task"])
                assert task.completed is True
                assert task.status_id == workflow["statuses"]["Finished"]
                assert task.finish_date is not None


def test_standard_tasks_still_complete_and_reopen(client, app, workflow):
    with app.app_context():
        db.session.get(Case, workflow["case"]).privileged_case = False
        db.session.commit()
    login(client, app, "editor")
    for mode in MODES:
        reset_task(app, workflow, status="Ongoing")
        assert finish(client, workflow, mode, "editor").status_code == 200
        with app.app_context():
            assert db.session.get(Task, workflow["task"]).completed is True
        response = client.get(f"/api/task/{workflow['task']}/complete", headers={"X-API-KEY": "editor_api_key"})
        assert response.status_code == 200
        with app.app_context():
            assert db.session.get(Task, workflow["task"]).completed is False


def test_editors_submit_review_then_approver_finishes(client, app, workflow):
    response = finish(client, workflow, "api_status", "editor", destination=workflow["statuses"]["Request Review"])
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(Task, workflow["task"]).completed is False
    assert finish(client, workflow, "api_complete", "editor").status_code == 403
    assert finish(client, workflow, "api_status", "queue_admin").status_code == 200


def test_core_guards_and_failed_completion_do_not_write_finished(app, workflow, monkeypatch):
    with app.app_context():
        editor = User.query.filter_by(api_key="editor_api_key").one()
        task = db.session.get(Task, workflow["task"])
        assert TaskModel.complete_task(task.id, editor) is False
        assert TaskModel.change_task_status(workflow["statuses"]["Finished"], task, editor) is False
        db.session.commit()
        assert task.completed is False
        assert task.status_id == workflow["statuses"]["Approved"]
        admin = User.query.filter_by(api_key="admin_api_key").one()
        monkeypatch.setattr(TaskModel, "complete_task", lambda *args: False)
        assert TaskModel.change_task_status(workflow["statuses"]["Finished"], task, admin) is False
        db.session.commit()
        assert task.status_id == workflow["statuses"]["Approved"]


@pytest.mark.parametrize("key", ["editor", "queuer", "admin"])
def test_privileged_tasks_cannot_be_created_already_completed(client, app, workflow, key):
    response = client.post(f"/api/case/{workflow['case']}/create_task", headers={"X-API-KEY": key + "_api_key"},
                           json={"title": "Premature completion", "completed": True})
    assert response.status_code == 201
    with app.app_context():
        task = db.session.get(Task, response.json["task_id"])
        assert task.completed is False
        assert task.status_id == workflow["statuses"]["Requested"]


def test_standard_task_creation_preserves_completed_flag(client, app, workflow):
    with app.app_context():
        db.session.get(Case, workflow["case"]).privileged_case = False
        db.session.commit()
    response = client.post(f"/api/case/{workflow['case']}/create_task",
                           headers={"X-API-KEY": "editor_api_key"},
                           json={"title": "Imported completed task", "completed": True})
    assert response.status_code == 201
    with app.app_context():
        assert db.session.get(Task, response.json["task_id"]).completed is True


@pytest.mark.parametrize("key", ["admin", "caseadmin"])
def test_privileged_case_completion_still_completes_open_tasks(client, app, workflow, key):
    response = client.get(f"/api/case/{workflow['case']}/complete", headers={"X-API-KEY": key + "_api_key"})
    assert response.status_code == 200
    with app.app_context():
        case = db.session.get(Case, workflow["case"])
        assert case.completed is True
        assert all(task.completed for task in case.tasks)


def test_reopening_finished_privileged_task_is_unchanged(client, app, workflow):
    login(client, app, "editor")
    for mode in MODES:
        reset_task(app, workflow, status="Finished", completed=True)
        response = finish(client, workflow, mode, "editor", destination=workflow["statuses"]["Ongoing"])
        assert response.status_code == 200
        with app.app_context():
            assert db.session.get(Task, workflow["task"]).completed is False


@pytest.mark.parametrize("api_key,session_key,expected", [("editor", "admin", 403), ("admin", "editor", 200)])
def test_privileged_completion_uses_api_identity(client, app, workflow, api_key, session_key, expected):
    login(client, app, session_key)
    assert finish(client, workflow, "api_complete", api_key).status_code == expected


@pytest.mark.parametrize("delegate_key,expected", [("editor", 403), ("queue_admin", 200)])
def test_privileged_completion_uses_relay_delegate(client, app, workflow, delegate_key, expected):
    with app.app_context():
        admin = User.query.filter_by(api_key="admin_api_key").one()
        delegate = User.query.filter_by(api_key=delegate_key + "_api_key").one()
        delegate.matrix_id = "@review-test:example.org"
        db.session.add(User(first_name="Review", last_name="Relay", email="review-relay@example.org",
                            role_id=admin.role_id, org_id=admin.org_id, is_bot=True, api_key="review_relay_test"))
        db.session.commit()
    response = client.get(f"/api/task/{workflow['task']}/complete",
                          headers={"X-API-KEY": "review_relay_test", "MATRIX-ID": "@review-test:example.org"})
    assert response.status_code == expected
