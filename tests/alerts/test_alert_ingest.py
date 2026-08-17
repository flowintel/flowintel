from app.alerting import alerting_core as AlertingCore
from app.db_class.db import (
    Case,
    Case_Connector_Instance,
    Case_Misp_Object,
    ExternalAlertAction,
    ExternalAlert,
    Misp_Attribute,
    Notification,
    User,
)
from app.case import common_core as CommonCase


ADMIN_KEY = "admin_api_key"
EDITOR_KEY = "editor_api_key"
ORGADMIN_MISP_KEY = "orgadmin_misp_editor_api_key"


def create_connector(client, name="Wazuh"):
    return client.post(
        "/api/connectors/add_connector",
        content_type="application/json",
        headers={"X-API-KEY": ADMIN_KEY},
        json={"name": name, "description": "Alert source"}
    )


def create_instance(client, connector_id, api_key="siem-source-key", sharing_scope="global", owner_key=ADMIN_KEY):
    return client.post(
        f"/api/connectors/{connector_id}/add_instance",
        content_type="application/json",
        headers={"X-API-KEY": owner_key},
        json={
            "name": f"{sharing_scope} alert source",
            "description": "Alert source instance",
            "url": "https://siem.example",
            "api_key": api_key,
            "sharing_scope": sharing_scope,
            "is_global_connector": sharing_scope in {"org", "global"},
        }
    )


def create_case_template(client, title="Alert Case Template"):
    return client.post(
        "/api/templating/create_case",
        content_type="application/json",
        headers={"X-API-KEY": ADMIN_KEY},
        json={"title": title, "description": "Template baseline"}
    )


def sample_alert():
    return {
        "Event": {
            "uuid": "11111111-2222-4333-8444-555555555555",
            "id": "wazuh-42",
            "info": "Suspicious PowerShell execution",
            "date": "2026-08-03",
            "threat_level_id": "1",
            "analysis": "0",
            "Orgc": {"name": "wazuh"},
            "Tag": [{"name": "tlp:amber"}, {"name": "source:wazuh"}],
            "Attribute": [
                {
                    "uuid": "aaaaaaaa-1111-4222-8333-000000000001",
                    "type": "ip-src",
                    "category": "Network activity",
                    "value": "203.0.113.10",
                    "comment": "source",
                    "to_ids": True,
                },
                {
                    "uuid": "aaaaaaaa-1111-4222-8333-000000000002",
                    "type": "link",
                    "category": "External analysis",
                    "value": "https://siem.example/alerts/wazuh-42",
                    "to_ids": False,
                },
            ],
            "Object": [
                {
                    "uuid": "bbbbbbbb-1111-4222-8333-000000000001",
                    "name": "file",
                    "template_uuid": "688c46fb-5edb-40a3-8273-1af7923e2215",
                    "Attribute": [
                        {
                            "uuid": "cccccccc-1111-4222-8333-000000000001",
                            "type": "filename",
                            "object_relation": "filename",
                            "value": "payload.ps1",
                            "to_ids": False,
                        },
                        {
                            "uuid": "cccccccc-1111-4222-8333-000000000002",
                            "type": "sha256",
                            "object_relation": "sha256",
                            "value": "44d88612fea8a8f36de82e1278abb02f",
                            "to_ids": True,
                        },
                    ],
                }
            ],
        }
    }


def sample_flat_misp_alert():
    return {
        "Event": {
            "uuid": "22222222-2222-4333-8444-555555555555",
            "info": "Flat MISP object attributes",
            "threat_level_id": "2",
            "Orgc": {"name": "misp"},
            "Attribute": [
                {
                    "uuid": "dddddddd-1111-4222-8333-000000000001",
                    "type": "ip-dst",
                    "value": "198.51.100.22",
                    "to_ids": True,
                },
                {
                    "uuid": "eeeeeeee-1111-4222-8333-000000000001",
                    "object_id": "99",
                    "type": "filename",
                    "object_relation": "filename",
                    "value": "dropper.exe",
                    "Object": {
                        "id": "99",
                        "uuid": "ffffffff-1111-4222-8333-000000000001",
                        "name": "file",
                        "template_uuid": "688c46fb-5edb-40a3-8273-1af7923e2215",
                    },
                },
                {
                    "uuid": "eeeeeeee-1111-4222-8333-000000000002",
                    "object_id": "99",
                    "type": "sha256",
                    "object_relation": "sha256",
                    "value": "1" * 64,
                    "to_ids": True,
                    "Object": {
                        "id": "99",
                        "uuid": "ffffffff-1111-4222-8333-000000000001",
                        "name": "file",
                        "template_uuid": "688c46fb-5edb-40a3-8273-1af7923e2215",
                    },
                },
            ],
        }
    }


def sample_xss_alert():
    return {
        "Event": {
            "uuid": "33333333-2222-4333-8444-555555555555",
            "info": "<img src=x onerror=alert(1)>",
            "threat_level_id": "2",
            "Orgc": {"name": "<script>alert(1)</script>"},
            "Attribute": [
                {
                    "uuid": "99999999-1111-4222-8333-000000000001",
                    "type": "link",
                    "value": "javascript:alert(1)",
                    "to_ids": False,
                },
                {
                    "uuid": "99999999-1111-4222-8333-000000000002",
                    "type": "url",
                    "value": "https://safe.example.test/report?id=1",
                    "to_ids": False,
                },
            ],
        }
    }


def login_user(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True


def test_ingest_alert_with_connector_key(client, app):
    connector = create_connector(client)
    instance = create_instance(client, connector.json["connector_id"], api_key="wazuh-ingest-key")

    assert connector.status_code == 200
    assert instance.status_code == 200

    response = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "wazuh-ingest-key"},
        json=sample_alert()
    )

    assert response.status_code == 201
    assert response.json["created"] is True

    with app.app_context():
        alert = ExternalAlert.query.get(response.json["alert_id"])
        assert alert is not None
        assert alert.to_json()["alert_type"] == "external"
        assert alert.title == "Suspicious PowerShell execution"
        assert alert.source == "wazuh"
        assert alert.severity == "high"
        assert alert.confidence is None
        assert alert.connector_instance_id == instance.json["connector_id"]
        assert alert.observables[0]["value"] == "203.0.113.10"
        assert alert.assets[0]["name"] == "file"
        assert alert.tags == ["tlp:amber", "source:wazuh"]


def test_ingest_new_alert_notifies_admins(client, app):
    connector = create_connector(client)
    create_instance(client, connector.json["connector_id"], api_key="notify-alert-key")

    response = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "notify-alert-key"},
        json=sample_alert()
    )

    assert response.status_code == 201

    with app.app_context():
        admin = User.query.filter_by(api_key=ADMIN_KEY).first()
        notif = Notification.query.filter_by(
            user_id=admin.id,
            category="alerting",
            notification_type="external_alert",
        ).first()

        assert notif is not None
        assert "New alert received from wazuh" in notif.message
        assert notif.target_url.startswith("/alerting/?alert_id=")


def test_ingest_deduplicated_alert_does_not_create_extra_notifications(client, app):
    connector = create_connector(client)
    create_instance(client, connector.json["connector_id"], api_key="notify-dedupe-key")

    first = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "notify-dedupe-key"},
        json=sample_alert()
    )
    second = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "notify-dedupe-key"},
        json=sample_alert()
    )

    assert first.status_code == 201
    assert second.status_code == 200

    with app.app_context():
        admin = User.query.filter_by(api_key=ADMIN_KEY).first()
        count = Notification.query.filter_by(
            user_id=admin.id,
            category="alerting",
            notification_type="external_alert",
        ).count()

        assert count == 1


def test_review_alert_response_includes_actor_history(client, app):
    connector = create_connector(client)
    create_instance(client, connector.json["connector_id"], api_key="review-actor-key")
    response = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "review-actor-key"},
        json=sample_alert()
    )
    assert response.status_code == 201

    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        admin = User.query.filter_by(api_key=ADMIN_KEY).first()
        admin_id = admin.id
        admin_email = admin.email
        login_user(client, admin)

    review_response = client.post(
        f"/alerting/api/{response.json['alert_id']}/review",
        content_type="application/json",
        json={"review_status": "reviewing", "comment": "Taking ownership"}
    )

    assert review_response.status_code == 200
    alert_json = review_response.json["alert"]
    assert alert_json["review_status"] == "reviewing"
    assert alert_json["reviewed_by_name"] == "admin admin"
    assert alert_json["reviewed_by_email"] == admin_email
    assert len(alert_json["action_history"]) == 1
    assert alert_json["action_history"][0]["action"] == "reviewing"
    assert alert_json["action_history"][0]["action_label"] == "Marked for review"
    assert alert_json["action_history"][0]["user_name"] == "admin admin"
    assert alert_json["action_history"][0]["comment"] == "Taking ownership"

    with app.app_context():
        action = ExternalAlertAction.query.filter_by(
            alert_id=response.json["alert_id"],
            action="reviewing",
            user_id=admin_id,
        ).one()
        assert action.comment == "Taking ownership"


def test_ingest_keeps_only_standalone_attributes_in_attribute_section(client, app):
    connector = create_connector(client)
    create_instance(client, connector.json["connector_id"], api_key="flat-misp-key")

    response = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "flat-misp-key"},
        json=sample_flat_misp_alert()
    )

    assert response.status_code == 201

    with app.app_context():
        alert = ExternalAlert.query.get(response.json["alert_id"])
        assert [attr["value"] for attr in alert.observables] == ["198.51.100.22"]
        assert len(alert.assets) == 1
        assert alert.assets[0]["name"] == "file"
        assert [attr["value"] for attr in alert.assets[0]["attributes"]] == ["dropper.exe", "1" * 64]


def test_ingest_sanitizes_untrusted_alert_urls_and_keeps_text_inert(client, app):
    connector = create_connector(client)
    create_instance(client, connector.json["connector_id"], api_key="xss-alert-key")

    response = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "xss-alert-key"},
        json=sample_xss_alert()
    )

    assert response.status_code == 201

    with app.app_context():
        alert = ExternalAlert.query.get(response.json["alert_id"])
        assert alert.title == "<img src=x onerror=alert(1)>"
        assert alert.source == "<script>alert(1)</script>"
        assert [ref["url"] for ref in alert.external_references] == ["https://safe.example.test/report?id=1"]
        assert any(attr["value"] == "javascript:alert(1)" for attr in alert.observables)


def test_ingest_rejects_user_api_key_without_connector_instance(client):
    response = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": EDITOR_KEY},
        json=sample_alert()
    )

    assert response.status_code == 403


def test_ingest_deduplicates_by_connector_and_source_ref(client):
    connector = create_connector(client)
    create_instance(client, connector.json["connector_id"], api_key="dedupe-key")

    first = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "dedupe-key"},
        json=sample_alert()
    )
    second = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "dedupe-key"},
        json={**sample_alert(), "description": "Repeated alert"}
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json["alert_id"] == first.json["alert_id"]
    assert second.json["occurrence_count"] == 2


def test_org_scoped_alert_visibility(client, app):
    connector = create_connector(client, name="Org SIEM")
    instance = create_instance(
        client,
        connector.json["connector_id"],
        api_key="org-alert-key",
        sharing_scope="org",
        owner_key=ORGADMIN_MISP_KEY,
    )
    assert instance.status_code == 200

    response = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "org-alert-key"},
        json=sample_alert()
    )
    assert response.status_code == 201

    with app.app_context():
        owner = User.query.filter_by(api_key=ORGADMIN_MISP_KEY).first()
        other = User.query.filter_by(api_key=EDITOR_KEY).first()
        visible_to_owner = AlertingCore.query_visible_alerts(owner)
        visible_to_other = AlertingCore.query_visible_alerts(other)

        assert len(visible_to_owner) == 1
        assert visible_to_other == []


def test_create_case_from_alert_links_connector(client, app):
    connector = create_connector(client)
    instance = create_instance(client, connector.json["connector_id"], api_key="case-key")
    response = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "case-key"},
        json=sample_alert()
    )
    assert response.status_code == 201

    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        admin = User.query.filter_by(api_key=ADMIN_KEY).first()
        admin_id = admin.id
        with client.session_transaction() as session:
            session["_user_id"] = str(admin.id)
            session["_fresh"] = True

    case_response = client.post(
        f"/alerting/api/{response.json['alert_id']}/case",
        content_type="application/json",
        json={"title": "Escalated SIEM alert", "ticket_id": "WAZUH-42"}
    )

    assert case_response.status_code == 201
    case_id = case_response.json["case_id"]

    with app.app_context():
        case = Case.query.get(case_id)
        alert = ExternalAlert.query.get(response.json["alert_id"])
        action = ExternalAlertAction.query.filter_by(
            alert_id=response.json["alert_id"],
            action="case_created",
            user_id=admin_id,
        ).one()
        link = Case_Connector_Instance.query.filter_by(
            case_id=case_id,
            instance_id=instance.json["connector_id"],
        ).first()

        assert case.title == "Escalated SIEM alert"
        assert alert.case_id == case_id
        assert alert.review_status == "case_created"
        assert action.details["case_id"] == case_id
        assert case_response.json["alert"]["reviewed_by_name"] == "admin admin"
        assert case_response.json["alert"]["action_history"][0]["action"] == "case_created"
        assert link is not None
        assert link.identifier == "11111111-2222-4333-8444-555555555555"
        history = CommonCase.get_history(case.uuid)
        assert history
        assert any("Case created from alert 11111111-2222-4333-8444-555555555555" in line for line in history)
        assert case_response.json["imported"] == {"attributes": 2, "objects": 1}
        imported_object = Case_Misp_Object.query.filter_by(case_id=case_id, name="file").first()
        assert imported_object is not None
        object_attrs = imported_object.attributes.all()
        assert any(attr.type == "filename" and attr.value == "payload.ps1" for attr in object_attrs)
        sha_attr = next(attr for attr in object_attrs if attr.type == "sha256")
        assert sha_attr.value == "44d88612fea8a8f36de82e1278abb02f"
        assert sha_attr.ids_flag is True
        assert Misp_Attribute.query.filter_by(case_id=case_id, type="ip-src", value="203.0.113.10").count() == 1
        assert Misp_Attribute.query.filter_by(case_id=case_id, type="link", value="https://siem.example/alerts/wazuh-42").count() == 1


def test_create_case_from_alert_can_use_case_template(client, app):
    template = create_case_template(client)
    assert template.status_code == 201
    template_id = int(template.json["message"].split(": ")[1])

    connector = create_connector(client)
    create_instance(client, connector.json["connector_id"], api_key="template-case-key")
    response = client.post(
        "/api/alerts/ingest",
        content_type="application/json",
        headers={"X-API-KEY": "template-case-key"},
        json=sample_alert()
    )
    assert response.status_code == 201

    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        admin = User.query.filter_by(api_key=ADMIN_KEY).first()
        with client.session_transaction() as session:
            session["_user_id"] = str(admin.id)
            session["_fresh"] = True

    case_response = client.post(
        f"/alerting/api/{response.json['alert_id']}/case",
        content_type="application/json",
        json={
            "template_id": str(template_id),
            "title": "Templated alert case",
            "ticket_id": "TPL-42",
            "description": "Reviewer summary"
        }
    )

    assert case_response.status_code == 201
    case_id = case_response.json["case_id"]

    with app.app_context():
        case = Case.query.get(case_id)
        assert case.title == "Templated alert case"
        assert case.description == "Template baseline"
        assert case.ticket_id == "TPL-42"
        assert "Reviewer summary" in (case.notes or "")
        history = CommonCase.get_history(case.uuid)
        assert history
        assert any("Case created from alert 11111111-2222-4333-8444-555555555555" in line for line in history)
        assert Case_Misp_Object.query.filter_by(case_id=case_id, name="file").count() == 1
        assert Misp_Attribute.query.filter_by(case_id=case_id, type="ip-src", value="203.0.113.10").count() == 1


def test_alert_schema_endpoint_requires_user_api_key(client):
    response = client.get("/api/alerts/schema", headers={"X-API-KEY": ADMIN_KEY})

    assert response.status_code == 200
    assert response.json["schema"] == "misp.event"
    assert "Event" in response.json["example"]
