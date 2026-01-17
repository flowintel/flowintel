from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from . import calendar_core as CalendarModel
from datetime import datetime
from ..db_class.db import Case, Task

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

    data_dict = dict(request.args)
    date_month = data_dict["date"]
    flag_dead_creation = data_dict["dead_creation"]
    if date_month:
        tasks_list = list()
        tasks_month = CalendarModel.get_task_month_core(date_month, flag_dead_creation, current_user)
        for task in tasks_month:
            tasks_list.append(task.to_json())

        return {"tasks": tasks_list}
    return {"message": "No date"}


@calendar_blueprint.route("/get_case_month", methods=['GET'])
@login_required
def get_case_month():
    """Calendar info"""

    data_dict = dict(request.args)
    date_month = data_dict["date"]
    flag_dead_creation = data_dict["dead_creation"]
    if date_month:
        cases_list = list()
        cases_month = CalendarModel.get_case_month_core(date_month, flag_dead_creation, current_user)
        for case in cases_month:
            cases_list.append(case.to_json())

        return {"cases": cases_list}
    return {"message": "No date"}


@calendar_blueprint.route("/download_case_ics/<int:case_id>", methods=['GET'])
@login_required
def download_case_ics(case_id):
    """Download ICS file for a case"""
    case = Case.query.get(case_id)
    if not case:
        return {"message": "Case not found"}, 404
    
    ics_content = generate_ics_for_case(case, request.host_url)
    
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
    
    ics_content = generate_ics_for_task(task, request.host_url)
    
    response = Response(ics_content, mimetype='text/calendar')
    response.headers['Content-Disposition'] = f'attachment; filename=task_{task_id}.ics'
    return response


@calendar_blueprint.route("/calendar_feed", methods=['GET'])
@login_required
def calendar_feed():
    """Generate a complete calendar feed (ICS) for the current user"""
    cases_list = CalendarModel.get_all_cases_for_user(current_user)
    tasks_list = CalendarModel.get_all_tasks_for_user(current_user)
    
    ics_content = generate_full_calendar_feed(cases_list, tasks_list, request.host_url)
    
    response = Response(ics_content, mimetype='text/calendar')
    response.headers['Content-Disposition'] = 'attachment; filename=flowintel_calendar.ics'
    return response


def generate_full_calendar_feed(cases, tasks, base_url):
    """Generate a complete ICS calendar feed with all cases and tasks"""
    now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    
    events = []
    
    for case in cases:
        if case.deadline:
            dtstart = case.deadline.strftime('%Y%m%d')
        else:
            dtstart = case.creation_date.strftime('%Y%m%d')
        
        description = (case.description or '').replace('\n', '\\n').replace(',', '\\,')
        url = f"{base_url}case/{case.id}"
        
        event = f"""BEGIN:VEVENT
UID:case-{case.id}@flowintel
DTSTAMP:{now}
DTSTART;VALUE=DATE:{dtstart}
SUMMARY:[Case] {case.title}
DESCRIPTION:{description}\\n\\nView case: {url}
URL:{url}
STATUS:CONFIRMED
END:VEVENT"""
        events.append(event)
    
    for task in tasks:
        if task.deadline:
            dtstart = task.deadline.strftime('%Y%m%d')
        else:
            dtstart = task.creation_date.strftime('%Y%m%d')
        
        description = (task.description or '').replace('\n', '\\n').replace(',', '\\,')
        url = f"{base_url}case/{task.case_id}"
        
        event = f"""BEGIN:VEVENT
UID:task-{task.id}@flowintel
DTSTAMP:{now}
DTSTART;VALUE=DATE:{dtstart}
SUMMARY:[Task] {task.title}
DESCRIPTION:{description}\\n\\nView case: {url}
URL:{url}
STATUS:CONFIRMED
END:VEVENT"""
        events.append(event)
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Flowintel//Calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Flowintel Calendar
X-WR-TIMEZONE:UTC
X-WR-CALDESC:Cases and Tasks from Flowintel
{chr(10).join(events)}
END:VCALENDAR"""
    
    return ics_content


def generate_ics_for_case(case, base_url):
    """Generate ICS content for a case"""
    now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    
    if case.deadline:
        dtstart = case.deadline.strftime('%Y%m%d')
    else:
        dtstart = case.creation_date.strftime('%Y%m%d')
    
    description = (case.description or '').replace('\n', '\\n').replace(',', '\\,')
    
    url = f"{base_url}case/{case.id}"
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Flowintel//Calendar//EN
BEGIN:VEVENT
UID:case-{case.id}@flowintel
DTSTAMP:{now}
DTSTART;VALUE=DATE:{dtstart}
SUMMARY:{case.title}
DESCRIPTION:{description}\\n\\nView case: {url}
URL:{url}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
    
    return ics_content


def generate_ics_for_task(task, base_url):
    """Generate ICS content for a task"""
    now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    
    if task.deadline:
        dtstart = task.deadline.strftime('%Y%m%d')
    else:
        dtstart = task.creation_date.strftime('%Y%m%d')
    
    description = (task.description or '').replace('\n', '\\n').replace(',', '\\,')
    
    url = f"{base_url}case/{task.case_id}"
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Flowintel//Calendar//EN
BEGIN:VEVENT
UID:task-{task.id}@flowintel
DTSTAMP:{now}
DTSTART;VALUE=DATE:{dtstart}
SUMMARY:{task.title}
DESCRIPTION:{description}\\n\\nView case: {url}
URL:{url}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
    
    return ics_content
