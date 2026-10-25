import copy
import threading
import pytest

from app import db
from app.alerting import alerting_core as AlertingCore
from app.db_class.db import Case, ExternalAlert, User


ADMIN_KEY = "admin_api_key"
SOURCE_KEY = "siem-source-key"
EVENT = {
    "Event": {
        "uuid": "11111111-2222-4333-8444-555555555555",
        "id": "wazuh-42",
        "info": "Suspicious PowerShell execution",
        "date": "2026-08-03",
        "Attribute": [],
    }
}


def setup_source(client):
    response = client.post(
        "/api/connectors/add_connector",
        headers={"X-API-KEY": ADMIN_KEY},
        json={"name": "Wazuh", "description": "Alert source"},
    )
    connector_id = response.json["connector_id"]
    response = client.post(
        f"/api/connectors/{connector_id}/add_instance",
        headers={"X-API-KEY": ADMIN_KEY},
        json={
            "name": "global alert source",
            "description": "Alert source instance",
            "url": "https://siem.example",
            "api_key": SOURCE_KEY,
            "sharing_scope": "global",
            "is_global_connector": True,
        },
    )
    assert response.status_code == 200, response.json

@pytest.mark.concurrent_db
def test_concurrent_case_creation_from_one_alert_creates_one_case(client, app, monkeypatch):
    setup_source(client)
    response = client.post(
        "/api/alerts/ingest",
        headers={"X-API-KEY": SOURCE_KEY},
        json=copy.deepcopy(EVENT),
    )
    assert response.status_code == 201
    alert_id = response.json["alert_id"]

    monkeypatch.setitem(app.config, 'WTF_CSRF_ENABLED', False)
    with app.app_context():
        admin_id = User.query.filter_by(api_key=ADMIN_KEY).first().id
        cases_before = Case.query.count()

    # Hold both requests after the "already linked" check and before either
    # creates its case, so both pass the check.
    barrier = threading.Barrier(2, timeout=20)
    original_unique_case_title = AlertingCore.unique_case_title

    def pausing_unique_case_title(base_title, alert_id):
        barrier.wait()
        return original_unique_case_title(base_title, alert_id)

    monkeypatch.setattr(AlertingCore, "unique_case_title", pausing_unique_case_title)

    responses = [None, None]
    errors = []

    def worker(index):
        try:
            user_client = app.test_client()
            with user_client.session_transaction() as session:
                session["_user_id"] = str(admin_id)
                session["_fresh"] = True
            responses[index] = user_client.post(
                f"/alerting/api/{alert_id}/case",
                json={"title": f"Escalated SIEM alert {index}"},
            )
        except Exception as exc:  # pragma: no cover - surfaced by the assert below
            errors.append(repr(exc))

    threads = [threading.Thread(target=worker, args=(index,)) for index in (0, 1)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(120)

    assert not errors
    assert sorted(response.status_code for response in responses) == [201, 400]
    winner = next(response for response in responses if response.status_code == 201)
    loser = next(response for response in responses if response.status_code == 400)
    assert loser.json["case_id"] == winner.json["case_id"]
    with app.app_context():
        assert Case.query.count() == cases_before + 1
        assert db.session.get(ExternalAlert, alert_id).case_id == winner.json["case_id"]
