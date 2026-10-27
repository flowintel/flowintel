import importlib.util
import re
from pathlib import Path
from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from flask.sessions import SecureCookieSessionInterface
from pymisp import MISPEvent

from app import db
from app.case.CaseCore import CaseModel
from app.connectors import connectors_core as ConnectorModel
from app.db_class.db import (
    Case, Case_Connector_Instance, Case_Misp_Sync_Conflict,
    Connector_Instance, Connector_Sync_Log, User,
)
from app.utils.utils import get_modules_list

from .test_connectors import ADMIN_KEY, create_case, create_connector, create_instance


HEADERS = {"X-API-KEY": ADMIN_KEY}


@pytest.fixture
def linked_instance(client, app):
    connector_id = create_connector(client, name="MISP").json["connector_id"]
    response = create_instance(client, connector_id, api_key=ADMIN_KEY,
                               payload={"read_only": True, "sharing_scope": "global"})
    assert response.status_code == 200
    instance_id = response.json["connector_id"]
    case_id = create_case(client).json["case_id"]
    with app.app_context():
        link = Case_Connector_Instance(case_id=case_id, instance_id=instance_id, identifier="42")
        db.session.add(link)
        db.session.commit()
        return connector_id, instance_id, case_id, link.id


def test_instance_read_only_api_create_edit_and_validation(client, app):
    connector_id = create_connector(client, name="MISP").json["connector_id"]
    for index, payload in enumerate(({}, {"read_only": False}, {"read_only": True})):
        response = create_instance(client, connector_id, name=f"Instance {index}", api_key=ADMIN_KEY, payload=payload)
        assert response.status_code == 200
        instance_id = response.json["connector_id"]
        with app.app_context():
            assert db.session.get(Connector_Instance, instance_id).read_only is payload.get("read_only", False)

    edit_url = f"/api/connectors/{connector_id}/edit_instance/{instance_id}"
    response = client.post(edit_url, headers=HEADERS, json={"description": "Still receive only"})
    assert response.status_code == 200
    instances = client.get(f"/api/connectors/{connector_id}/instances", headers=HEADERS).json["instances"]
    assert next(i for i in instances if i["id"] == instance_id)["read_only"] is True

    for invalid in ("false", "true", 0, 1, None, [], {}):
        response = client.post(edit_url, headers=HEADERS, json={"read_only": invalid})
        assert response.status_code == 400
        assert response.json["message"] == "read_only must be a boolean"
        response = create_instance(client, connector_id, name="Invalid", api_key=ADMIN_KEY, payload={"read_only": invalid})
        assert response.status_code == 400
    with app.app_context():
        assert db.session.get(Connector_Instance, instance_id).read_only is True

    response = client.post(edit_url, headers=HEADERS, json={"read_only": False})
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(Connector_Instance, instance_id).read_only is False


def test_instance_read_only_form_create_edit_and_display(client, app):
    # Cookie sessions keep this form test independent of a running Valkey server.
    app.session_interface = SecureCookieSessionInterface()
    with app.app_context():
        user_id = User.query.filter_by(api_key=ADMIN_KEY).one().id
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    connector_id = create_connector(client, name="MISP").json["connector_id"]
    form = {"name": "Read only MISP", "url": "https://misp.example", "api_key": "test-key",
            "sharing_scope": "personal", "read_only": "y"}
    response = client.post(f"/connectors/{connector_id}/add_instance", data=form)
    assert response.status_code == 302
    with app.app_context():
        instance = Connector_Instance.query.filter_by(name=form["name"]).one()
        instance_id = instance.id
        assert instance.read_only is True

    edit_url = f"/connectors/{connector_id}/edit_instance/{instance_id}"
    response = client.get(edit_url)
    assert response.status_code == 200
    checkbox = re.search(rb'<input[^>]*id="read_only"[^>]*>', response.data)
    assert checkbox and b"checked" in checkbox.group()
    form.pop("read_only")
    response = client.post(edit_url, data=form)
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Connector_Instance, instance_id).read_only is False


def test_read_only_blocks_all_exports_before_remote_access(client, app, linked_instance, monkeypatch):
    _, _, case_id, link_id = linked_instance
    modules, _ = get_modules_list()
    guard = Mock(side_effect=AssertionError("Read-only sends must not access MISP"))
    monkeypatch.setattr(CaseModel, "_misp_send_remote_change_guard", guard)
    for module_name in ("misp_event", "misp_event_partial", "misp_event_task", "misp_object_event"):
        handler = Mock(side_effect=AssertionError("Read-only sends must not run an export"))
        monkeypatch.setattr(modules[module_name], "handler", handler)
        response = client.post(f"/api/case/{case_id}/call_module_case", headers=HEADERS,
                               json={"module": module_name, "instance_id": link_id})
        assert response.status_code == 400
        assert "read only" in response.json["message"]
        with app.app_context():
            case = db.session.get(Case, case_id)
            user = User.query.filter_by(api_key=ADMIN_KEY).one()
            for trigger in ("scheduled", "case_change", "conflict_resolution"):
                result = CaseModel.call_module_case(module_name, link_id, case, user,
                                                    payload={"automation_trigger": trigger, "force_conflict_resolution": True})
                assert "read only" in result["message"]
        handler.assert_not_called()
    guard.assert_not_called()
    with app.app_context():
        assert db.session.get(Case_Connector_Instance, link_id).last_sync is None
        assert Connector_Sync_Log.query.count() == 0


def test_read_only_receives_from_misp(client, app, linked_instance, monkeypatch):
    _, _, case_id, link_id = linked_instance
    modules, _ = get_modules_list()
    event = MISPEvent()
    event.from_dict(id="42", info="Incoming event")
    event.add_attribute("ip-src", "192.0.2.1", comment="", to_ids=False,
                        uuid="71dc6ee6-3e9a-48bf-8958-cd21ae9ca77b")
    misp = Mock()
    misp.get_event.return_value = event
    monkeypatch.setattr(modules["receive_misp_object"], "PyMISP", Mock(return_value=misp))

    response = client.post(f"/api/case/{case_id}/call_module_case", headers=HEADERS,
                           json={"module": "receive_misp_object", "instance_id": link_id})
    assert response.status_code == 200, response.json
    misp.get_event.assert_called_once_with("42", pythonify=True)
    assert [call[0] for call in misp.method_calls] == ["get_event"]
    attributes = client.get(f"/api/case/{case_id}/get_case_misp_attributes", headers=HEADERS)
    assert attributes.status_code == 200
    assert any(attr["value"] == "192.0.2.1" for attr in attributes.json["attributes"])
    with app.app_context():
        assert db.session.get(Case_Connector_Instance, link_id).last_sync is not None
        assert Connector_Sync_Log.query.one().direction == "receive"


def test_read_only_automation_blocks_sends_and_preserves_receives(client, app, linked_instance):
    connector_id, instance_id, case_id, link_id = linked_instance
    edit_url = f"/api/connectors/{connector_id}/edit_instance/{instance_id}"
    sync_url = f"/api/case/{case_id}/connectors/{link_id}/sync_automation"
    for direction, module in (("send", "misp_object_event"), ("receive", "misp_event")):
        response = client.post(sync_url, headers=HEADERS,
                               json={"direction": direction, "enabled": True, "interval": "daily", "module_name": module})
        assert response.status_code == 400
        assert "read only" in response.json["message"]

    response = client.post(sync_url, headers=HEADERS,
                           json={"direction": "receive", "enabled": True, "interval": "daily"})
    assert response.status_code == 200
    assert client.post(edit_url, headers=HEADERS, json={"read_only": False}).status_code == 200
    response = client.post(sync_url, headers=HEADERS,
                           json={"direction": "send", "enabled": True, "interval": "daily", "on_change": True})
    assert response.status_code == 200
    assert client.post(edit_url, headers=HEADERS, json={"read_only": True}).status_code == 200
    for read_only in (True, False):
        if not read_only:
            assert client.post(edit_url, headers=HEADERS, json={"read_only": False}).status_code == 200
        with app.app_context():
            schedules = ConnectorModel.get_misp_sync_schedules(case_id, link_id)
            assert schedules["send"]["enabled"] is False
            assert schedules["send"]["next_run_at"] is None
            assert schedules["receive"]["enabled"] is True
            assert schedules["receive"]["next_run_at"] is not None


def test_read_only_conflict_resolution_cannot_send(client, app, linked_instance):
    _, _, case_id, link_id = linked_instance
    with app.app_context():
        conflict = Case_Misp_Sync_Conflict(case_id=case_id, case_connector_instance_id=link_id,
                                          direction="send", item_type="event", local_snapshot={"details": []})
        db.session.add(conflict)
        db.session.commit()
        conflict_id = conflict.id
    url = f"/api/case/{case_id}/connectors/{link_id}/sync_conflicts/{conflict_id}/resolve"
    response = client.post(url, headers=HEADERS, json={"resolution": "prefer_flowintel"})
    assert response.status_code == 400
    assert "read only" in response.json["message"]
    with app.app_context():
        conflict = db.session.get(Case_Misp_Sync_Conflict, conflict_id)
        assert conflict.status == "pending"
        assert conflict.resolution is None
    response = client.post(url, headers=HEADERS, json={"resolution": "skip"})
    assert response.status_code == 200


def test_writable_instance_can_still_send(client, app, linked_instance, monkeypatch):
    connector_id, instance_id, case_id, link_id = linked_instance
    response = client.post(f"/api/connectors/{connector_id}/edit_instance/{instance_id}", headers=HEADERS,
                           json={"read_only": False})
    assert response.status_code == 200
    modules, _ = get_modules_list()
    handler = Mock(return_value={"synced_count": 1})
    monkeypatch.setattr(modules["misp_object_event"], "handler", handler)
    monkeypatch.setattr(CaseModel, "_misp_send_remote_change_guard", Mock(return_value=None))
    response = client.post(f"/api/case/{case_id}/call_module_case", headers=HEADERS,
                           json={"module": "misp_object_event", "instance_id": link_id})
    assert response.status_code == 200
    handler.assert_called_once()
    with app.app_context():
        assert Connector_Sync_Log.query.one().direction == "send"


def test_read_only_migration_preserves_existing_instances():
    migration_path = Path(__file__).resolve().parents[2] / "migrations/versions/b7e4c9a2d610_add_read_only_to_connector_instance.py"
    spec = importlib.util.spec_from_file_location("read_only_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    table = sa.Table(Connector_Instance.__tablename__, metadata,
                     sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(64)))
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(table.insert(), {"id": 1, "name": "Existing MISP"})
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            upgraded = sa.Table(table.name, sa.MetaData(), autoload_with=connection)
            assert connection.execute(sa.select(upgraded.c.read_only)).scalar_one() is False
            connection.execute(upgraded.insert(), {"id": 2, "name": "New MISP"})
            assert connection.execute(sa.select(upgraded.c.read_only).where(upgraded.c.id == 2)).scalar_one() is False
            migration.downgrade()
            assert "read_only" not in {column["name"] for column in sa.inspect(connection).get_columns(table.name)}
            assert connection.execute(sa.select(sa.func.count()).select_from(table)).scalar_one() == 2
            migration.upgrade()
    engine.dispose()
