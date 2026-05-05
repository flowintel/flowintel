from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
import conf.config_module as ConfigModule
from app.db_class.db import Alert, Case, db
import os
import json

from . import alerts_blueprint


LOG_FILE = "logs/webhook_alerts.log"


def read_alert_log(lines=50):
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r") as f:
            all_lines = f.readlines()
        return [line.strip() for line in all_lines[-lines:]]
    except Exception:
        return []


@alerts_blueprint.route("/")
@login_required
def index():
    alert_logs = read_alert_log(50)
    alerts = Alert.query.order_by(Alert.creation_date.desc()).limit(50).all()
    alerts_json = []
    for a in alerts:
        item = a.to_json()
        case = Case.query.get(a.case_id)
        item["case_title"] = case.title if case else "(deleted)"
        item["case_uuid"] = case.uuid if case else ""
        alerts_json.append(item)
    return render_template("alerts.html",
                           cfg=ConfigModule,
                           alert_logs=alert_logs,
                           alerts=alerts_json)


@alerts_blueprint.route("/api/alerts")
def api_alerts():
    alerts = Alert.query.order_by(Alert.creation_date.desc()).limit(50).all()
    result = []
    for a in alerts:
        item = a.to_json()
        case = Case.query.get(a.case_id)
        item["case_title"] = case.title if case else "(deleted)"
        item["case_uuid"] = case.uuid if case else ""
        result.append(item)
    return jsonify(result)


@alerts_blueprint.route("/api/alerts/unread")
def api_alerts_unread():
    count = Alert.query.filter_by(is_read=False).count()
    return jsonify({"count": count})


@alerts_blueprint.route("/api/alerts/<int:aid>/read")
def api_alert_read(aid):
    alert = Alert.query.get(aid)
    if alert:
        alert.is_read = True
        db.session.commit()
    return jsonify({"status": "ok"})


@alerts_blueprint.route("/config", methods=["POST"])
@login_required
def update_config():
    if not current_user.role_id == 1:
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


@alerts_blueprint.route("/test/webhook")
def test_webhook():
    try:
        from app.modules.notify_user.webhook import test_webhook as tw
        result = tw()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@alerts_blueprint.route("/test/imap")
def test_imap():
    try:
        from app.modules.notify_user.email import test_imap
        result = test_imap()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@alerts_blueprint.route("/logs")
def get_logs():
    logs = read_alert_log(100)
    return jsonify({"logs": logs})