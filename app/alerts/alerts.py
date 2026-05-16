from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
import conf.config_module as ConfigModule
from app.db_class.db import Alert, Case, db
from app.decorators import admin_required
from app.case.common_core import check_user_in_private_cases
from app.modules.notify_user.webhook import ALERT_LOG_FILE as LOG_FILE
import os
import json

from . import alerts_blueprint


def read_alert_log(lines=50):
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r") as f:
            all_lines = f.readlines()
        return [line.strip() for line in all_lines[-lines:]]
    except Exception:
        return []


def _user_visible_alerts(alerts):
    case_ids = {a.case_id for a in alerts}
    cases_by_id = {
        c.id: c for c in Case.query.filter(Case.id.in_(case_ids)).all()
    } if case_ids else {}
    allowed_ids = {
        c.id for c in check_user_in_private_cases(
            list(cases_by_id.values()), current_user
        )
    }
    visible = []
    for a in alerts:
        case = cases_by_id.get(a.case_id)
        if case is None or case.id in allowed_ids:
            visible.append((a, case))
    return visible


def _alerts_to_json(alerts):
    result = []
    for a, case in _user_visible_alerts(alerts):
        item = a.to_json()
        item["case_title"] = case.title if case else "(deleted)"
        item["case_uuid"] = case.uuid if case else ""
        result.append(item)
    return result


@alerts_blueprint.route("/")
@login_required
def index():
    alert_logs = read_alert_log(50)
    alerts = Alert.query.order_by(Alert.creation_date.desc()).limit(50).all()
    alerts_json = _alerts_to_json(alerts)
    return render_template("alerts.html",
                           cfg=ConfigModule,
                           alert_logs=alert_logs,
                           alerts=alerts_json)


@alerts_blueprint.route("/api/alerts")
@login_required
def api_alerts():
    alerts = Alert.query.order_by(Alert.creation_date.desc()).limit(50).all()
    return jsonify(_alerts_to_json(alerts))


@alerts_blueprint.route("/api/alerts/unread")
@login_required
def api_alerts_unread():
    unread = Alert.query.filter_by(is_read=False).all()
    count = len(_user_visible_alerts(unread))
    return jsonify({"count": count})


@alerts_blueprint.route("/api/alerts/<int:aid>/read", methods=["POST"])
@login_required
def api_alert_read(aid):
    alert = Alert.query.get(aid)
    if alert:
        alert.is_read = True
        db.session.commit()
    return jsonify({"status": "ok"})


@alerts_blueprint.route("/api/alerts/read_all", methods=["POST"])
@login_required
def api_alerts_read_all():
    unread = Alert.query.filter_by(is_read=False).all()
    visible = [a for a, _ in _user_visible_alerts(unread)]
    for a in visible:
        a.is_read = True
    if visible:
        db.session.commit()
    return jsonify({"status": "ok", "count": len(visible)})


@alerts_blueprint.route("/api/alerts/delete_read", methods=["POST"])
@login_required
def api_alerts_delete_read():
    read_alerts = Alert.query.filter_by(is_read=True).all()
    visible = [a for a, _ in _user_visible_alerts(read_alerts)]
    for a in visible:
        db.session.delete(a)
    if visible:
        db.session.commit()
    return jsonify({"status": "ok", "count": len(visible)})


@alerts_blueprint.route("/config", methods=["POST"])
@login_required
@admin_required
def update_config():
    # explicit check for the 403 JSON response
    if not current_user.is_admin():
        return jsonify({"status": "error", "message": "Admin only"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    try:
        with open("conf/config_module.py", "r") as f:
            content = f.read()

        for key, val in data.items():
            if isinstance(val, bool):
                py_val = "True" if val else "False"
            elif isinstance(val, int):
                py_val = str(val)
            else:
                py_val = repr(val)
            import re
            content = re.sub(
                rf"^{key}\s*=.*",
                f'{key} = {py_val}',
                content,
                flags=re.MULTILINE
            )
            if key not in content:
                content += f"\n{key} = {py_val}\n"

        with open("conf/config_module.py", "w") as f:
            f.write(content)

        import importlib
        importlib.reload(ConfigModule)

        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@alerts_blueprint.route("/test/webhook", methods=["POST"])
@login_required
@admin_required
def test_webhook():
    try:
        from app.modules.notify_user.webhook import test_webhook as tw
        result = tw()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@alerts_blueprint.route("/test/imap", methods=["POST"])
@login_required
@admin_required
def test_imap():
    try:
        from app.modules.notify_user.email import test_imap
        result = test_imap()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@alerts_blueprint.route("/logs")
@login_required
@admin_required
def get_logs():
    logs = read_alert_log(100)
    return jsonify({"logs": logs})