from flask import jsonify, render_template, request
from flask_login import current_user, login_required

from app.alerting import alerting_core as AlertingCore
from app.db_class.db import ExternalAlert, db
from app.decorators import editor_required
from app.templating import common_template_core as TemplateCommon

from . import alerting_blueprint


@alerting_blueprint.route("/")
@login_required
def index():
    alerts_json = AlertingCore.query_visible_alerts(
        current_user,
        limit=200,
    )
    case_templates = [
        {"id": template.id, "title": template.title}
        for template in TemplateCommon.get_all_case_templates()
    ]
    return render_template(
        "alerting.html",
        alerts=alerts_json,
        alert_schema_example=AlertingCore.alert_schema_example(),
        case_templates=case_templates,
    )


@alerting_blueprint.route("/api")
@login_required
def api_alerts():
    limit = min(request.args.get("limit", 200, type=int), 500)
    review_status = request.args.get("review_status")
    if review_status not in AlertingCore.ALERT_REVIEW_STATUSES:
        review_status = None
    return jsonify(AlertingCore.query_visible_alerts(
        current_user,
        limit=limit,
        review_status=review_status,
    ))


@alerting_blueprint.route("/api/unread")
@login_required
def api_alerts_unread():
    unread = ExternalAlert.query.filter_by(is_read=False).all()
    count = len(AlertingCore.visible_alert_pairs(unread, current_user))
    return jsonify({"count": count})


@alerting_blueprint.route("/api/<int:aid>/read", methods=["POST"])
@login_required
def api_alert_read(aid):
    alert = ExternalAlert.query.get(aid)
    if alert and AlertingCore.can_user_view_alert(alert, current_user):
        alert.is_read = True
        db.session.commit()
    return jsonify({"status": "ok"})


@alerting_blueprint.route("/api/read_all", methods=["POST"])
@login_required
def api_alerts_read_all():
    unread = ExternalAlert.query.filter_by(is_read=False).all()
    visible = [a for a, _ in AlertingCore.visible_alert_pairs(unread, current_user)]
    for a in visible:
        a.is_read = True
    if visible:
        db.session.commit()
    return jsonify({"status": "ok", "count": len(visible)})


@alerting_blueprint.route("/api/<int:aid>/review", methods=["POST"])
@login_required
@editor_required
def api_alert_review(aid):
    alert = ExternalAlert.query.get(aid)
    if not alert:
        return jsonify({"message": "Alert not found"}), 404
    data = request.get_json(silent=True) or {}
    response, status_code = AlertingCore.update_review_status(
        alert,
        current_user,
        data.get("review_status"),
        data.get("comment"),
    )
    return jsonify(response), status_code


@alerting_blueprint.route("/api/<int:aid>/case", methods=["POST"])
@login_required
@editor_required
def api_alert_create_case(aid):
    alert = ExternalAlert.query.get(aid)
    if not alert:
        return jsonify({"message": "Alert not found"}), 404
    data = request.get_json(silent=True) or {}
    response, status_code = AlertingCore.create_case_from_alert(alert, current_user, data)
    return jsonify(response), status_code
