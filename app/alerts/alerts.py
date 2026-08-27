import importlib
import re

from flask import jsonify, request, redirect
from flask_login import login_required, current_user
import conf.config_module as ConfigModule
from app.decorators import admin_required

from app.alerts import alerts_core as AlertsCore
from . import alerts_blueprint

CONFIG_MODULE_PATH = "conf/config_module.py"
ALLOWED_CONFIG_KEYS = {
    "CASE_CREATE_ALERT_ENABLED": bool,
    "WEBHOOK_ENABLED": bool,
    "WEBHOOK_URL": str,
    "WEBHOOK_SECRET": str,
    "IMAP_SERVER": str,
    "IMAP_PORT": int,
    "IMAP_USE_SSL": bool,
    "IMAP_USER": str,
    "IMAP_PASSWORD": str,
}


def _config_value_to_python(value, expected_type):
    if expected_type is bool:
        if not isinstance(value, bool):
            raise ValueError("must be a boolean")
        return "True" if value else "False"
    if expected_type is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return str(value)
    if expected_type is str:
        if not isinstance(value, str):
            raise ValueError("must be a string")
        return repr(value)
    raise ValueError("has an unsupported type")


@alerts_blueprint.route("/")
@login_required
def index():
    return redirect("/notification/?tab=case-alerts")


@alerts_blueprint.route("/api/alerts")
@login_required
def api_alerts():
    return jsonify(AlertsCore.latest_alerts(current_user, limit=50))


@alerts_blueprint.route("/api/alerts/unread")
@login_required
def api_alerts_unread():
    return jsonify({"count": AlertsCore.unread_count(current_user)})


@alerts_blueprint.route("/api/alerts/<int:aid>/read", methods=["POST"])
@login_required
def api_alert_read(aid):
    AlertsCore.mark_alert_read(aid, current_user)
    return jsonify({"status": "ok"})


@alerts_blueprint.route("/api/alerts/read_all", methods=["POST"])
@login_required
def api_alerts_read_all():
    count = AlertsCore.mark_all_read(current_user)
    return jsonify({"status": "ok", "count": count})


@alerts_blueprint.route("/api/alerts/delete_read", methods=["POST"])
@login_required
def api_alerts_delete_read():
    count = AlertsCore.delete_read(current_user)
    return jsonify({"status": "ok", "count": count})


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
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    try:
        updates = {}
        for key, val in data.items():
            expected_type = ALLOWED_CONFIG_KEYS.get(key)
            if expected_type is None:
                return jsonify({"status": "error", "message": "Unsupported config key"}), 400
            try:
                updates[key] = _config_value_to_python(val, expected_type)
            except ValueError as exc:
                return jsonify({"status": "error", "message": f"{key} {exc}"}), 400

        with open(CONFIG_MODULE_PATH, "r") as f:
            content = f.read()

        for key, py_val in updates.items():
            pattern = rf"^{re.escape(key)}\s*=.*$"
            replacement = f"{key} = {py_val}"
            if re.search(pattern, content, flags=re.MULTILINE):
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            else:
                content += f"\n{replacement}\n"

        with open(CONFIG_MODULE_PATH, "w") as f:
            f.write(content)

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
    logs = AlertsCore.read_alert_log(100)
    return jsonify({"logs": logs})
