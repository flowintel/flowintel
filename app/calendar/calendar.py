from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from . import calendar_core as CalendarModel
from ..db_class.db import Case, Task
from ..case.common_core import get_present_in_case

calendar_blueprint = Blueprint(
    'calendar',
    __name__,
    template_folder='templates',
    static_folder='static'
)


@calendar_blueprint.route("/", methods=['GET'])
@login_required
def calendar():
    """Calendar view"""
    return render_template("calendar/calendar.html")


@calendar_blueprint.route("/get_task_month", methods=['GET'])
@login_required
def get_task_month():
    """Calendar info"""
    date_month = request.args.get("date")
    flag_dead_creation = request.args.get("dead_creation")
    if not date_month or not flag_dead_creation:
        return {"message": "Missing date or dead_creation parameter"}, 400

    try:
        tasks_month = CalendarModel.get_task_month_core(date_month, flag_dead_creation, current_user)
    except ValueError:
        return {"message": "Invalid date format"}, 400

    tasks_list = [task.to_json() for task in tasks_month]
    return {"tasks": tasks_list}


@calendar_blueprint.route("/get_case_month", methods=['GET'])
@login_required
def get_case_month():
    """Calendar info"""
    date_month = request.args.get("date")
    flag_dead_creation = request.args.get("dead_creation")
    if not date_month or not flag_dead_creation:
        return {"message": "Missing date or dead_creation parameter"}, 400

    try:
        cases_month = CalendarModel.get_case_month_core(date_month, flag_dead_creation, current_user)
    except ValueError:
        return {"message": "Invalid date format"}, 400

    cases_list = [case.to_json() for case in cases_month]
    return {"cases": cases_list}


@calendar_blueprint.route("/download_case_ics/<int:case_id>", methods=['GET'])
@login_required
def download_case_ics(case_id):
    """Download ICS file for a case"""
    case = Case.query.get(case_id)
    if not case:
        return {"message": "Case not found"}, 404
    if case.is_private and not current_user.is_admin() and not get_present_in_case(case.id, current_user):
        return {"message": "Access denied"}, 403

    ics_content = CalendarModel.generate_ics_for_case(case, request.host_url)

    response = Response(ics_content, mimetype='text/calendar')
    response.headers['Content-Disposition'] = f'attachment; filename=case_{case_id}.ics'
    return response


@calendar_blueprint.route("/download_task_ics/<int:task_id>", methods=['GET'])
@login_required
def download_task_ics(task_id):
    """Download ICS file for a task"""
    task = Task.query.get(task_id)
    if not task:
        return {"message": "Task not found"}, 404
    case = Case.query.get(task.case_id)
    if case and case.is_private and not current_user.is_admin() and not get_present_in_case(case.id, current_user):
        return {"message": "Access denied"}, 403

    ics_content = CalendarModel.generate_ics_for_task(task, request.host_url)

    response = Response(ics_content, mimetype='text/calendar')
    response.headers['Content-Disposition'] = f'attachment; filename=task_{task_id}.ics'
    return response


@calendar_blueprint.route("/calendar_feed", methods=['GET'])
@login_required
def calendar_feed():
    """Generate a complete calendar feed (ICS) for the current user"""
    cases_list = CalendarModel.get_all_cases_for_user(current_user)
    tasks_list = CalendarModel.get_all_tasks_for_user(current_user)

    ics_content = CalendarModel.generate_full_calendar_feed(cases_list, tasks_list, request.host_url)

    response = Response(ics_content, mimetype='text/calendar')
    response.headers['Content-Disposition'] = 'attachment; filename=flowintel_calendar.ics'
    return response
