from flask import jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.alerting import alerting_core as AlertingCore
from app.db_class.db import Case, ExternalAlert, db
from app.decorators import editor_required
from app.templating import common_template_core as TemplateCommon

from . import alerting_blueprint


@alerting_blueprint.route("/")
@login_required
def index():
    case_templates = [
        {"id": template.id, "title": template.title}
        for template in TemplateCommon.get_all_case_templates()
    ]
    return render_template(
        "alerting.html",
        alert_schema_example=AlertingCore.alert_schema_example(),
        case_templates=case_templates,
    )


@alerting_blueprint.route("/api")
@login_required
def api_alerts():
    limit = max(0, min(request.args.get("limit", 200, type=int), 500))
    review_status = request.args.get("review_status")
    if review_status not in AlertingCore.ALERT_REVIEW_STATUSES:
        review_status = None
    return jsonify(AlertingCore.query_visible_alerts(
        current_user,
        limit=limit,
        review_status=review_status,
    ))


def parse_queue_filters(params):
    status = params.get("review_status", "active")
    statuses = AlertingCore.ALERT_REVIEW_STATUSES | AlertingCore.ALERT_REVIEW_GROUPS.keys() | {"all"}
    if not isinstance(status, str) or status not in statuses:
        raise ValueError("Invalid review status filter")
    severity = params.get("severity")
    if severity is not None and (not isinstance(severity, str) or severity not in AlertingCore.ALERT_SEVERITIES | {""}):
        raise ValueError("Invalid severity filter")
    term = params.get("q", "")
    if not isinstance(term, str):
        raise ValueError("Invalid search term")
    return {"review_status": status, "severity": severity, "term": term.replace("\x00", "").strip()}


@alerting_blueprint.route("/api/queue")
@login_required
def api_alert_queue():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = max(1, min(request.args.get("per_page", 25, type=int), AlertingCore.MAX_BULK_ALERTS))
    try:
        filters = parse_queue_filters(request.args)
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    return jsonify(AlertingCore.paginated_alerts(current_user, page, per_page, **filters))


@alerting_blueprint.route("/api/<int:aid>")
@login_required
def api_alert_detail(aid):
    if aid > 2**31 - 1:
        return jsonify({"message": "Alert not found"}), 404
    row = AlertingCore.visible_alert_query(current_user).filter(ExternalAlert.id == aid).outerjoin(
        Case, Case.id == ExternalAlert.case_id,
    ).add_entity(Case).first()
    if row is None:
        return jsonify({"message": "Alert not found"}), 404
    alert, linked_case = row
    return jsonify(AlertingCore.alert_to_json(alert, linked_case))


@alerting_blueprint.route("/api/unread")
@login_required
def api_alerts_unread():
    count = AlertingCore.visible_alert_query(current_user).filter(ExternalAlert.is_read.is_(False)).with_entities(
        func.count(ExternalAlert.id),
    ).scalar()
    return jsonify({"count": count})


@alerting_blueprint.route("/api/<int:aid>/read", methods=["POST"])
@login_required
def api_alert_read(aid):
    if aid <= 2**31 - 1:
        AlertingCore.visible_alert_query(current_user).filter(ExternalAlert.id == aid, ExternalAlert.is_read.is_not(True)).update(
            {"is_read": True}, synchronize_session=False,
        )
        db.session.commit()
    return jsonify({"status": "ok"})


@alerting_blueprint.route("/api/read_all", methods=["POST"])
@login_required
def api_alerts_read_all():
    count = AlertingCore.visible_alert_query(current_user).filter(ExternalAlert.is_read.is_(False)).update(
        {"is_read": True}, synchronize_session=False,
    )
    db.session.commit()
    return jsonify({"status": "ok", "count": count})


@alerting_blueprint.route("/api/bulk_review", methods=["POST"])
@login_required
@editor_required
def api_alerts_bulk_review():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"message": "Expected a JSON object"}), 400
    review_status = data.get("review_status")
    if not isinstance(review_status, str) or review_status not in AlertingCore.BULK_REVIEW_STATUSES:
        return jsonify({"message": "Invalid bulk review status"}), 400
    if "filters" in data:
        params = data["filters"]
        if (
            "alert_ids" in data
            or not isinstance(params, dict)
            or "review_status" not in params
            or params.keys() - {"review_status", "severity", "q"}
        ):
            return jsonify({"message": "Specify valid filters for all matching alerts"}), 400
        try:
            selection = {"filters": parse_queue_filters(params)}
        except ValueError as error:
            return jsonify({"message": str(error)}), 400
    else:
        ids = data.get("alert_ids")
        if not isinstance(ids, list) or not 1 <= len(ids) <= AlertingCore.MAX_BULK_ALERTS or any(
            type(alert_id) is not int or not 0 < alert_id <= 2**31 - 1 for alert_id in ids
        ):
            return jsonify({"message": f"Select between 1 and {AlertingCore.MAX_BULK_ALERTS} valid alerts"}), 400
        selection = {"alert_ids": set(ids)}
    response, status_code = AlertingCore.bulk_update_review_status(current_user, review_status, **selection)
    return jsonify(response), status_code


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
