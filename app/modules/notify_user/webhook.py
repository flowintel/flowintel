import conf.config_module as Config
import requests
import json
import hashlib
import hmac
import datetime

module_config = {
    "case_task": "case"
}

ALERT_LOG_FILE = "logs/webhook_alerts.log"


def _sign_payload(payload: bytes) -> str:
    if Config.WEBHOOK_SECRET:
        return hmac.new(
            Config.WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
    return ""


def _update_alert_status(case_id, webhook_status, alert_status):
    """Update the alert record in the database"""
    try:
        from app import create_app
        from app.db_class.db import Alert, db
        app = create_app()
        with app.app_context():
            alert = Alert.query.filter_by(case_id=case_id).order_by(Alert.id.desc()).first()
            if alert:
                alert.webhook_status = webhook_status
                alert.status = alert_status
                db.session.commit()
    except Exception:
        pass


def handler(task, case, current_user, user):
    """
    task: dict
    case: dict of the case
    current_user: User who triggered
    user: User being notified
    Returns: int (HTTP status code) or None
    """
    if not Config.WEBHOOK_ENABLED or not Config.WEBHOOK_URL:
        return None

    payload = json.dumps({
        "event": "case_created",
        "case": case,
        "triggered_by": {
            "id": current_user.id,
            "email": current_user.email,
            "name": f"{current_user.first_name} {current_user.last_name}"
        },
        "timestamp": datetime.datetime.now().isoformat()
    }, indent=2, default=str)

    signature = _sign_payload(payload.encode())

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Flowintel-Webhook/1.0"
    }
    if signature:
        headers["X-Webhook-Signature"] = signature

    try:
        resp = requests.post(
            Config.WEBHOOK_URL,
            data=payload,
            headers=headers,
            timeout=10
        )
        with open(ALERT_LOG_FILE, "a") as f:
            f.write(f"[{datetime.datetime.now()}] Webhook sent to {Config.WEBHOOK_URL} - Status: {resp.status_code}\n")
        return resp.status_code
    except Exception as e:
        with open(ALERT_LOG_FILE, "a") as f:
            f.write(f"[{datetime.datetime.now()}] Webhook error: {e}\n")
        return None


def test_webhook():
    """Send a test payload to the webhook URL"""
    if not Config.WEBHOOK_ENABLED or not Config.WEBHOOK_URL:
        return {"status": "error", "message": "Webhook not configured"}

    payload = json.dumps({
        "event": "test",
        "message": "Flowintel webhook test",
        "timestamp": datetime.datetime.now().isoformat()
    })

    signature = _sign_payload(payload.encode())
    headers = {"Content-Type": "application/json", "User-Agent": "Flowintel-Webhook/1.0"}
    if signature:
        headers["X-Webhook-Signature"] = signature

    try:
        resp = requests.post(Config.WEBHOOK_URL, data=payload, headers=headers, timeout=10)
        return {"status": "ok", "status_code": resp.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def introspection():
    return module_config