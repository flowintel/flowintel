from flask import jsonify, request, redirect
from flask_login import login_required, current_user
import conf.config_module as ConfigModule
from app.decorators import admin_required

from app.alerts import alerts_core as AlertsCore
from . import alerts_blueprint


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
    logs = AlertsCore.read_alert_log(100)
    return jsonify({"logs": logs})
