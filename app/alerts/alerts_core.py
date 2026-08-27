import os

from app import db
from app.case.common_core import check_user_in_private_cases
from app.db_class.db import Alert, Case
from app.modules.notify_user.webhook import ALERT_LOG_FILE as LOG_FILE


def case_notification_query():
    return Alert.query


def read_alert_log(lines=50):
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r") as f:
            all_lines = f.readlines()
        return [line.strip() for line in all_lines[-lines:]]
    except Exception:
        return []


def user_visible_alerts(alerts, user):
    case_ids = {alert.case_id for alert in alerts if alert.case_id}
    cases_by_id = {
        case.id: case for case in Case.query.filter(Case.id.in_(case_ids)).all()
    } if case_ids else {}
    allowed_case_ids = {
        case.id for case in check_user_in_private_cases(
            list(cases_by_id.values()),
            user,
        )
    }

    visible = []
    for alert in alerts:
        case = cases_by_id.get(alert.case_id)
        if case is None or case.id in allowed_case_ids:
            visible.append((alert, case))
    return visible


def alerts_to_json(alerts, user):
    result = []
    for alert, case in user_visible_alerts(alerts, user):
        item = alert.to_json()
        item["case_title"] = case.title if case else "(deleted)"
        item["case_uuid"] = case.uuid if case else ""
        result.append(item)
    return result


def latest_alerts(user, limit=50):
    alerts = case_notification_query().order_by(Alert.creation_date.desc()).limit(limit).all()
    return alerts_to_json(alerts, user)


def unread_count(user):
    unread = case_notification_query().filter_by(is_read=False).all()
    return len(user_visible_alerts(unread, user))


def mark_alert_read(alert_id, user):
    alert = Alert.query.get(alert_id)
    if not alert or not user_visible_alerts([alert], user):
        return False

    alert.is_read = True
    db.session.commit()
    return True


def mark_all_read(user):
    unread = case_notification_query().filter_by(is_read=False).all()
    visible = [alert for alert, _ in user_visible_alerts(unread, user)]
    for alert in visible:
        alert.is_read = True
    if visible:
        db.session.commit()
    return len(visible)


def delete_read(user):
    read_alerts = case_notification_query().filter_by(is_read=True).all()
    visible = [alert for alert, _ in user_visible_alerts(read_alerts, user)]
    for alert in visible:
        db.session.delete(alert)
    if visible:
        db.session.commit()
    return len(visible)
