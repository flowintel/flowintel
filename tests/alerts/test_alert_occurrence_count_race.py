import copy
import threading
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
def test_concurrent_duplicate_ingests_count_every_occurrence(client, app, monkeypatch):
    setup_source(client)
    assert ingest(app).status_code == 201

    # Hold both requests between reading the existing alert and committing
    # the update, so both read the same occurrence_count.
    barrier = threading.Barrier(2, timeout=20)

    class PausingStatuses(set):
        def __contains__(self, value):
            barrier.wait()
            return set.__contains__(self, value)

    monkeypatch.setattr(
        AlertingCore,
        "TERMINAL_REVIEW_STATUSES",
        PausingStatuses(AlertingCore.TERMINAL_REVIEW_STATUSES),
    )

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
    assert [response.status_code for response in responses] == [200, 200]
    with app.app_context():
        alerts = ExternalAlert.query.filter_by(deduplication_key=EVENT["Event"]["uuid"]).all()
        assert len(alerts) == 1
        assert alerts[0].occurrence_count == 3
