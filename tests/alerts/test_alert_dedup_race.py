import copy
import threading
import uuid
import pytest

from app.alerting import alerting_core as AlertingCore
from app.db_class.db import ExternalAlert


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


def ingest(app):
    return app.test_client().post(
        "/api/alerts/ingest",
        headers={"X-API-KEY": SOURCE_KEY},
        json=copy.deepcopy(EVENT),
    )

@pytest.mark.concurrent_db
def test_concurrent_first_ingests_create_a_single_alert(client, app, monkeypatch):
    setup_source(client)

    # Hold both requests after their de-duplication lookup found nothing and
    # before either inserts, so both take the insert path.
    barrier = threading.Barrier(2, timeout=20)

    class PausingUuid:
        @staticmethod
        def uuid4():
            barrier.wait()
            return uuid.uuid4()

    monkeypatch.setattr(AlertingCore, "uuid", PausingUuid)

    responses = [None, None]
    errors = []

    def worker(index):
        try:
            responses[index] = ingest(app)
        except Exception as exc:  # pragma: no cover - surfaced by the assert below
            errors.append(repr(exc))

    threads = [threading.Thread(target=worker, args=(index,)) for index in (0, 1)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(60)

    assert not errors
    assert sorted(response.status_code for response in responses) == [200, 201]
    assert responses[0].json["alert_id"] == responses[1].json["alert_id"]
    with app.app_context():
        alerts = ExternalAlert.query.filter_by(deduplication_key=EVENT["Event"]["uuid"]).all()
        assert len(alerts) == 1
        assert alerts[0].occurrence_count == 2
