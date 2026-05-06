"""
Test that when a case is deleted, all associated data is properly removed from the database.
This includes all models that hold a case_id without a cascading FK to the Case table.
"""

import io

API_KEY = "admin_api_key"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_case(client, title="Cleanup Test Case"):
    return client.post(
        "/api/case/create",
        content_type="application/json",
        headers={"X-API-KEY": API_KEY},
        json={"title": title},
    )


def delete_case(client, case_id):
    return client.get(f"/api/case/{case_id}/delete", headers={"X-API-KEY": API_KEY})


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_delete_case_cleans_up_all_features(client, app):
    """Deleting a fully-populated case must leave no orphaned rows behind."""

    # ── 1. Create the case ────────────────────────────────────────────────
    resp = create_case(client)
    assert resp.status_code == 201
    case_id = resp.json["case_id"]

    # ── 2. Add a task ─────────────────────────────────────────────────────
    resp = client.post(
        f"/api/case/{case_id}/create_task",
        content_type="application/json",
        headers={"X-API-KEY": API_KEY},
        json={"title": "Task to be deleted"},
    )
    assert resp.status_code == 201
    task_id = resp.json.get("task_id") or resp.json.get("id")

    # ── 3. Upload a file to the case ──────────────────────────────────────
    resp = client.post(
        f"/api/case/{case_id}/upload_file",
        content_type="multipart/form-data",
        headers={"X-API-KEY": API_KEY},
        data={"file": (io.BytesIO(b"hello"), "note.txt")},
    )
    assert resp.status_code == 200

    # ── 4. Create a second case and link it ───────────────────────────────
    resp2 = create_case(client, title="Linked Case")
    assert resp2.status_code == 201
    linked_case_id = resp2.json["case_id"]

    resp = client.post(
        f"/api/case/{case_id}/add_link",
        content_type="application/json",
        headers={"X-API-KEY": API_KEY},
        json={"case_id": [linked_case_id]},
    )
    assert resp.status_code == 200

    # ── 5. Insert remaining related rows directly into the DB ─────────────
    with app.app_context():
        from app import db
        from app.db_class.db import (
            Case_Tags,
            Case_Galaxy_Tags,
            Case_Custom_Tags,
            Case_Connector_Instance,
            Recurring_Notification,
            Case_Note_Template_Model,
            Rulezet_Rule,
            Alert,
            Case_Timeline_Event,
            Case_Timeline_Event_Link,
            Case_Misp_Object,
        )

        db.session.add(Case_Tags(tag_id=999, case_id=case_id))
        db.session.add(Case_Galaxy_Tags(cluster_id=999, case_id=case_id))
        db.session.add(Case_Custom_Tags(custom_tag_id=999, case_id=case_id))
        # Case_Org already contains a valid row from case creation; do not insert a
        # fake org_id here as the notification system would dereference it.
        db.session.add(Case_Connector_Instance(case_id=case_id, instance_id=999, identifier="test"))
        db.session.add(Recurring_Notification(user_id=999, case_id=case_id))
        db.session.add(Case_Note_Template_Model(case_id=case_id, note_template_id=999, values={}, content=""))
        db.session.add(Rulezet_Rule(case_id=case_id, instance_id=999, remote_id="rule-1"))
        db.session.add(Alert(case_id=case_id, message="pending alert", status="pending"))

        # Two timeline events linked to each other
        event_a = Case_Timeline_Event(case_id=case_id, date_text="2024-01-01", description="Event A")
        event_b = Case_Timeline_Event(case_id=case_id, date_text="2024-01-02", description="Event B")
        db.session.add(event_a)
        db.session.add(event_b)
        db.session.commit()

        tl_link = Case_Timeline_Event_Link(
            case_id=case_id,
            source_event_id=event_a.id,
            target_event_id=event_b.id,
            label="follows",
        )
        db.session.add(tl_link)
        db.session.commit()

    # ── 6. Delete the case ────────────────────────────────────────────────
    resp = delete_case(client, case_id)
    assert resp.status_code == 200
    assert b"Case deleted" in resp.data

    # ── 7. Verify every related table is now empty for this case ──────────
    with app.app_context():
        from app import db
        from app.db_class.db import (
            Case,
            Task,
            File,
            Case_Tags,
            Case_Galaxy_Tags,
            Case_Custom_Tags,
            Case_Org,
            Case_Connector_Instance,
            Case_Link_Case,
            Recurring_Notification,
            Case_Note_Template_Model,
            Rulezet_Rule,
            Alert,
            Case_Timeline_Event,
            Case_Timeline_Event_Link,
            Case_Misp_Object,
        )

        assert Case.query.get(case_id) is None, "Case record should be deleted"
        assert Task.query.filter_by(case_id=case_id).count() == 0, "Tasks should be deleted"
        assert File.query.filter_by(case_id=case_id).count() == 0, "Case files should be deleted"
        assert Case_Tags.query.filter_by(case_id=case_id).count() == 0, "Case_Tags should be deleted"
        assert Case_Galaxy_Tags.query.filter_by(case_id=case_id).count() == 0, "Case_Galaxy_Tags should be deleted"
        assert Case_Custom_Tags.query.filter_by(case_id=case_id).count() == 0, "Case_Custom_Tags should be deleted"
        assert Case_Org.query.filter_by(case_id=case_id).count() == 0, "Case_Org should be deleted"
        assert Case_Connector_Instance.query.filter_by(case_id=case_id).count() == 0, "Case_Connector_Instance should be deleted"
        assert Case_Link_Case.query.filter_by(case_id_1=case_id).count() == 0, "Case_Link_Case (side 1) should be deleted"
        assert Case_Link_Case.query.filter_by(case_id_2=case_id).count() == 0, "Case_Link_Case (side 2) should be deleted"
        assert Recurring_Notification.query.filter_by(case_id=case_id).count() == 0, "Recurring_Notification should be deleted"
        assert Case_Note_Template_Model.query.filter_by(case_id=case_id).count() == 0, "Case_Note_Template_Model should be deleted"
        assert Case_Misp_Object.query.filter_by(case_id=case_id).count() == 0, "Case_Misp_Object should be deleted"
        assert Rulezet_Rule.query.filter_by(case_id=case_id).count() == 0, "Rulezet_Rule should be deleted"
        assert Alert.query.filter_by(case_id=case_id).count() == 0, "Alert should be deleted"
        assert Case_Timeline_Event.query.filter_by(case_id=case_id).count() == 0, "Case_Timeline_Event should be deleted"
        assert Case_Timeline_Event_Link.query.filter_by(case_id=case_id).count() == 0, "Case_Timeline_Event_Link should be deleted"
