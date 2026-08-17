import datetime

from app import db
from app.analyzer.session_class import SessionClass
from app.db_class.db import Misp_Module_Result, Notification, User
from app.notification import notification_core as NotifModel


def login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

def test_notification_api_returns_category_and_type_filters(client, app):
    with app.app_context():
        user = User.query.filter_by(api_key="editor_api_key").first()
        user_id = user.id
        NotifModel.create_notification_user(
            "You have been assigned to: '12-Review logs' of case '4-Incident'",
            4,
            user_id=user_id,
            html_icon="fa-solid fa-hand"
        )
        NotifModel.create_notification_user(
            "Password reset requested for user analyst@example.test",
            -3,
            user_id=user_id,
            html_icon="fa-solid fa-key"
        )

    login(client, user_id)
    response = client.get(
        "/notification/get_user_notifications?unread_read=true&category=task&notification_type=assignment"
    )

    assert response.status_code == 200
    assert len(response.json["notif"]) == 1
    assert response.json["notif"][0]["category"] == "task"
    assert response.json["notif"][0]["notification_type"] == "assignment"


def test_get_user_notif_can_sort_by_category_and_type(app):
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    with app.app_context():
        user = User.query.filter_by(api_key="editor_api_key").first()
        db.session.add_all([
            Notification(
                message="Task assigned",
                is_read=False,
                user_id=user.id,
                case_id=1,
                creation_date=now,
                html_icon="fa-solid fa-hand",
                category="task",
                notification_type="assignment",
            ),
            Notification(
                message="Password reset",
                is_read=False,
                user_id=user.id,
                case_id=-2,
                creation_date=now - datetime.timedelta(minutes=2),
                html_icon="fa-solid fa-key",
                category="admin",
                notification_type="password_reset",
            ),
            Notification(
                message="Reminder",
                is_read=False,
                user_id=user.id,
                case_id=3,
                creation_date=now - datetime.timedelta(minutes=1),
                html_icon="fa-solid fa-clock",
                category="deadline",
                notification_type="reminder",
            ),
        ])
        db.session.commit()

        by_category = [notif.category for notif in NotifModel.get_user_notif(user, True, sort="category")]
        by_type = [notif.notification_type for notif in NotifModel.get_user_notif(user, "true", sort="type")]

    assert by_category == ["admin", "deadline", "task"]
    assert by_type == ["assignment", "password_reset", "reminder"]


def test_analyser_save_info_notifies_requesting_user(app):
    with app.app_context():
        user = User.query.filter_by(api_key="misp_editor_api_key").first()
        session = SessionClass(
            {
                "query": ["203.0.113.10"],
                "input": "ip-src",
                "modules": ["dns"],
            },
            user
        )
        session.nb_errors = 1
        session.result = {"203.0.113.10": {"dns": {"results": []}}}
        session.save_info()

        saved = Misp_Module_Result.query.filter_by(uuid=session.uuid).first()
        notif = Notification.query.filter_by(
            user_id=user.id,
            category="analyzer",
            notification_type="analysis_completed",
        ).first()

        assert saved is not None
        assert notif is not None
        assert "Analyser run finished" in notif.message
        assert notif.target_url == f"/analyzer/misp-modules/result/{session.uuid}"
