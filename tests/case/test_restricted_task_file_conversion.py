import importlib
import uuid

import pytest
from flask.sessions import SecureCookieSessionInterface

from app.case import common_core as CommonModel
from app.db_class.db import Case, Case_Org, Case_Timeline_Event, File, Note, Notification, Status, Task, User, db


CONTENTS = {
    "txt": (b"Investigation evidence\n", "Investigation evidence"),
    "csv": (b"Indicator,Value\nip,192.0.2.1\n", "| Indicator | Value |"),
    "json": (b'[{"Indicator":"ip","Value":"192.0.2.1"}]', "| Indicator | Value |"),
}


@pytest.fixture
def conversion(client, app, tmp_path, monkeypatch):
    monkeypatch.setattr(importlib.import_module("app.case.task"), "FILE_FOLDER", str(tmp_path))
    response = client.post("/api/case/create", headers={"X-API-KEY": "editor_api_key"},
                           json={"title": "File conversion permission case"})
    assert response.status_code == 201
    cid = response.json["case_id"]
    response = client.post(f"/api/case/{cid}/create_task", headers={"X-API-KEY": "editor_api_key"},
                           json={"title": "File conversion task"})
    assert response.status_code == 201
    with app.app_context():
        case = db.session.get(Case, cid)
        case.privileged_case = True
        case.is_private = True
        for key in ("queuer", "caseadmin", "queue_admin", "read"):
            user = User.query.filter_by(api_key=key + "_api_key").one()
            db.session.add(Case_Org(case_id=cid, org_id=user.org_id))
        statuses = {status.name: status.id for status in Status.query.all()}
        task = db.session.get(Task, response.json["task_id"])
        task.status_id = statuses["Requested"]
        sibling = Task(case_id=cid, title="Other task", uuid=str(uuid.uuid4()),
                       status_id=statuses["Approved"], completed=False)
        file = File(task_id=task.id, name="evidence.txt", uuid=str(uuid.uuid4()),
                    file_type="text/plain", file_size=len(CONTENTS["txt"][0]))
        db.session.add_all([sibling, file])
        db.session.flush()
        event = Case_Timeline_Event(case_id=cid, file_id=file.id,
                                    date_text="2026-11-16", description="Conversion source evidence")
        db.session.add(event)
        db.session.commit()
        path = tmp_path / file.uuid
        path.write_bytes(CONTENTS["txt"][0])
        return {"case": cid, "task": task.id, "task_uuid": task.uuid, "sibling": sibling.id,
                "file": file.id, "event": event.id, "path": path, "statuses": statuses}


def login(client, app, key):
    app.session_interface = SecureCookieSessionInterface()
    with app.app_context():
        login_id = User.query.filter_by(api_key=key + "_api_key").one().get_id()
    with client.session_transaction() as session:
        session["_user_id"] = login_id
        session["_fresh"] = True


def convert(client, conversion, tid=None, fid=None, headers=None):
    tid = conversion["task"] if tid is None else tid
    fid = conversion["file"] if fid is None else fid
    return client.post(f"/case/task/{tid}/convert_file_to_note/{fid}", headers=headers)


def set_format(app, conversion, extension):
    with app.app_context():
        db.session.get(File, conversion["file"]).name = "evidence." + extension.upper()
        db.session.commit()
    conversion["path"].write_bytes(CONTENTS[extension][0])


def snapshot(app, conversion):
    with app.app_context():
        case = db.session.get(Case, conversion["case"])
        task = db.session.get(Task, conversion["task"])
        file = db.session.get(File, conversion["file"])
        event = db.session.get(Case_Timeline_Event, conversion["event"])
        return ([note.to_json() for note in Note.query.order_by(Note.id).all()],
                task.nb_notes, task.last_modif, task.status_id, task.completed,
                case.last_modif, case.notes, file.to_json(), event.to_json(),
                CommonModel.get_history(case.uuid), Notification.query.count(),
                conversion["path"].read_bytes() if conversion["path"].exists() else None)


@pytest.mark.parametrize("key", ["editor", "queuer"])
def test_restricted_file_conversion_denied(client, app, conversion, key):
    login(client, app, key)
    for status in ("Requested", "Rejected", "Request Review"):
        with app.app_context():
            db.session.get(Task, conversion["task"]).status_id = conversion["statuses"][status]
            db.session.commit()
        for extension in CONTENTS:
            set_format(app, conversion, extension)
            for tid in (conversion["task"], conversion["task_uuid"]):
                before = snapshot(app, conversion)
                response = convert(client, conversion, tid=tid)
                assert response.status_code == 403
                assert "restricted status" in response.json["message"]
                assert snapshot(app, conversion) == before


@pytest.mark.parametrize("key", ["admin", "caseadmin", "queue_admin"])
@pytest.mark.parametrize("extension", CONTENTS)
def test_approvers_can_convert_restricted_files(client, app, conversion, key, extension):
    login(client, app, key)
    set_format(app, conversion, extension)
    for order, status in enumerate(("Requested", "Rejected", "Request Review"), start=1):
        with app.app_context():
            db.session.get(Task, conversion["task"]).status_id = conversion["statuses"][status]
            db.session.commit()
        response = convert(client, conversion, tid=conversion["task_uuid"])
        assert response.status_code == 200
        assert response.json["toast_class"] == "success-subtle"
        with app.app_context():
            note = db.session.get(Note, response.json["note"]["id"])
            assert note.task_id == conversion["task"]
            assert note.task_order_id == order
            assert CONTENTS[extension][1] in note.note
            assert "Note imported from a file" in note.note
            assert f"evidence.{extension.upper()}" in note.note
            assert db.session.get(Task, conversion["task"]).nb_notes == order
            assert db.session.get(File, conversion["file"]) is not None
            assert db.session.get(Case_Timeline_Event, conversion["event"]) is not None
            case = db.session.get(Case, conversion["case"])
            assert any("Note created from file" in line for line in CommonModel.get_history(case.uuid))
        assert conversion["path"].read_bytes() == CONTENTS[extension][0]


@pytest.mark.parametrize("key", ["editor", "queuer"])
@pytest.mark.parametrize("privileged,status", [(False, "Created"), (False, "Requested"),
                                               (True, "Approved"), (True, "Ongoing")])
def test_unrestricted_conversion_still_allowed(client, app, conversion, key, privileged, status):
    login(client, app, key)
    with app.app_context():
        db.session.get(Case, conversion["case"]).privileged_case = privileged
        db.session.get(Task, conversion["task"]).status_id = conversion["statuses"][status]
        db.session.commit()
    assert convert(client, conversion).status_code == 200
    with app.app_context():
        assert db.session.get(Task, conversion["task"]).nb_notes == 1


def test_denied_conversion_does_not_open_source_file(client, app, conversion):
    login(client, app, "editor")
    conversion["path"].unlink()
    before = snapshot(app, conversion)
    assert convert(client, conversion).status_code == 403
    assert snapshot(app, conversion) == before


@pytest.mark.parametrize("key", ["editor", "caseadmin", "queue_admin", "read"])
def test_conversion_still_requires_membership_and_editor_permission(client, app, conversion, key):
    login(client, app, key)
    if key != "read":
        with app.app_context():
            user = User.query.filter_by(api_key=key + "_api_key").one()
            Case_Org.query.filter_by(case_id=conversion["case"], org_id=user.org_id).delete()
            db.session.commit()
    before = snapshot(app, conversion)
    assert convert(client, conversion).status_code == 403
    assert snapshot(app, conversion) == before


@pytest.mark.parametrize("session_key,api_key,expected", [("editor", "admin", 403), ("admin", "editor", 200)])
def test_conversion_uses_browser_identity(client, app, conversion, session_key, api_key, expected):
    login(client, app, session_key)
    before = snapshot(app, conversion)
    response = convert(client, conversion, headers={"X-API-KEY": api_key + "_api_key", "MATRIX-ID": "@other-user:example.org"})
    assert response.status_code == expected
    if expected == 403:
        assert snapshot(app, conversion) == before


def test_api_key_alone_cannot_authenticate_browser_conversion(client, app, conversion):
    before = snapshot(app, conversion)
    assert convert(client, conversion, headers={"X-API-KEY": "admin_api_key"}).status_code in (302, 401)
    assert snapshot(app, conversion) == before


@pytest.mark.parametrize("target", ["sibling", "missing_task", "missing_file", "case_file", "case_route"])
def test_conversion_rejects_mismatched_or_missing_targets(client, app, conversion, target):
    login(client, app, "admin")
    tid, fid = conversion["task"], conversion["file"]
    if target == "sibling":
        tid = conversion["sibling"]
    elif target == "missing_task":
        tid = str(uuid.uuid4())
    elif target == "missing_file":
        fid = 999999
    elif target == "case_file":
        with app.app_context():
            file = db.session.get(File, fid)
            file.task_id = None
            file.case_id = conversion["case"]
            db.session.commit()
    before = snapshot(app, conversion)
    if target == "case_route":
        response = client.post(f"/case/{conversion['case']}/convert_case_file_to_note/{fid}")
    else:
        response = convert(client, conversion, tid=tid, fid=fid)
    assert response.status_code == 404
    assert snapshot(app, conversion) == before


@pytest.mark.parametrize("invalid", ["extension", "nontext"])
def test_conversion_errors_preserve_notes_and_source(client, app, conversion, invalid):
    login(client, app, "admin")
    if invalid == "extension":
        with app.app_context():
            db.session.get(File, conversion["file"]).name = "evidence.pdf"
            db.session.commit()
    else:
        conversion["path"].write_bytes(b"\xff\xfe\x00")
    before = snapshot(app, conversion)
    assert convert(client, conversion).status_code == 400
    assert snapshot(app, conversion) == before
