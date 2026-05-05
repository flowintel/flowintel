from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from ..decorators import audit_viewer_required
from ..utils.logger import flowintel_log
from . import audit_logs_core as core


audit_logs_blueprint = Blueprint(
    "audit_logs",
    __name__,
    template_folder="templates",
)


def _log_filtered_access(view, row_count):
    """Audit-log a fetch when the user actually applied filters."""
    args = request.args
    if not core.has_active_filters(args):
        return
    flowintel_log(
        "audit", 200, "Audit logs filtered",
        User=current_user.email,
        View=view,
        Rows=row_count,
        StartDate=args.get("start_date") or "",
        EndDate=args.get("end_date") or "",
        UserFilter=args.get("user") or "",
        ActionFilter=args.get("action") or "",
        Exclude=args.get("exclude") or "",
    )


@audit_logs_blueprint.route("/", methods=["GET"], strict_slashes=False)
@login_required
@audit_viewer_required
def audit_logs_view():
    flowintel_log("audit", 200, "Audit logs page accessed",
                  User=current_user.email)
    return render_template("tools/audit_logs.html")


@audit_logs_blueprint.route("/data", methods=["GET"])
@login_required
@audit_viewer_required
def audit_logs_data():
    rows = core.collect_history_rows() + core.collect_login_rows()
    rows.sort(key=lambda r: r["timestamp"], reverse=True)
    rows = core.filter_rows(rows, request.args)
    _log_filtered_access("logs", len(rows))
    return jsonify({"rows": rows})


@audit_logs_blueprint.route("/audit", methods=["GET"])
@login_required
@audit_viewer_required
def audit_logs_audit():
    rows = core.collect_audit_rows()
    rows.sort(key=lambda r: r["timestamp"], reverse=True)
    rows = core.filter_rows(rows, request.args)
    _log_filtered_access("audit", len(rows))
    return jsonify({"rows": rows})


@audit_logs_blueprint.route("/export", methods=["GET"])
@login_required
@audit_viewer_required
def audit_logs_export():
    source = request.args.get("source", "logs")
    fmt = (request.args.get("format") or "csv").lower()
    if fmt not in ("csv", "json"):
        fmt = "csv"

    if source == "audit":
        rows = core.collect_audit_rows()
        fields = ["timestamp", "severity", "user", "action", "case_id", "extra"]
        base_name = "audit_log"
    else:
        rows = core.collect_history_rows() + core.collect_login_rows()
        fields = ["timestamp", "user", "action", "source", "case_id", "case_uuid"]
        base_name = "history_log"

    rows.sort(key=lambda r: r["timestamp"], reverse=True)
    rows = core.filter_rows(rows, request.args)

    if fmt == "json":
        body = core.rows_to_json(rows, fields)
        mimetype = "application/json"
        filename = f"{base_name}.json"
    else:
        body = core.rows_to_csv(rows, fields)
        mimetype = "text/csv; charset=utf-8"
        filename = f"{base_name}.csv"

    flowintel_log("audit", 200, "Audit logs exported",
                  User=current_user.email, Source=source, Format=fmt,
                  Rows=len(rows))

    return body, 200, {
        "Content-Type": mimetype,
        "Content-Disposition": f"attachment; filename={filename}",
    }
