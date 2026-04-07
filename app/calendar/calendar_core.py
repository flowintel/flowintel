from ..db_class.db import Case, Task, Task_User, Case_Org

from datetime import datetime


def get_task_month_core(date_month, flag_dead_creation, user):
    # Convert "YYYY-MM" string into first day of month
    start = datetime.strptime(date_month, "%Y-%m")
    # Compute first day of next month
    if start.month == 12:
        end = start.replace(year=start.year+1, month=1, day=1)
    else:
        end = start.replace(month=start.month+1, day=1)

    if flag_dead_creation == 'true':
        return Task.query.join(Task_User, Task_User.task_id == Task.id).filter(
                Task_User.user_id == user.id,
                Task.deadline >= start,
                Task.deadline < end
            ).all()
    else:
        return Task.query.join(Task_User, Task_User.task_id == Task.id).filter(
                Task_User.user_id == user.id,
                Task.creation_date >= start,
                Task.creation_date < end
            ).all()


def get_case_month_core(date_month, flag_dead_creation, user):
    # Convert "YYYY-MM" string into first day of month
    start = datetime.strptime(date_month, "%Y-%m")
    # Compute first day of next month
    if start.month == 12:
        end = start.replace(year=start.year+1, month=1, day=1)
    else:
        end = start.replace(month=start.month+1, day=1)


    if flag_dead_creation == 'true':
        return Case.query.join(Case_Org, Case_Org.case_id==Case.id).filter(
            Case_Org.org_id == user.org_id,
            Case.deadline >= start,
            Case.deadline < end
        ).all()
    else:
        return Case.query.join(Case_Org, Case_Org.case_id==Case.id).filter(
            Case_Org.org_id == user.org_id,
            Case.creation_date >= start,
            Case.creation_date < end
        ).all()


def get_all_cases_for_user(user):
    """Get all cases for a user (for calendar feed)"""
    return Case.query.join(Case_Org, Case_Org.case_id==Case.id).filter(
        Case_Org.org_id == user.org_id
    ).all()


def get_all_tasks_for_user(user):
    """Get all tasks for a user (for calendar feed)"""
    return Task.query.join(Task_User, Task_User.task_id == Task.id).filter(
        Task_User.user_id == user.id
    ).all()


####################
# ICS Generation   #
####################

def _ics_escape(text):
    """Escape text for ICS fields per RFC 5545"""
    if not text:
        return ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\\', '\\\\')
    text = text.replace(';', '\\;')
    text = text.replace(',', '\\,')
    text = text.replace('\n', '\\n')
    return text


def _case_event(case, base_url, now, prefix=""):
    dtstart = case.deadline.strftime('%Y%m%d') if case.deadline else case.creation_date.strftime('%Y%m%d')
    description = _ics_escape(case.description)
    title = _ics_escape(case.title)
    url = f"{base_url}case/{case.id}"

    return f"""BEGIN:VEVENT
UID:case-{case.id}@flowintel
DTSTAMP:{now}
DTSTART;VALUE=DATE:{dtstart}
SUMMARY:{prefix}{title}
DESCRIPTION:{description}\\n\\nView case: {url}
URL:{url}
STATUS:CONFIRMED
END:VEVENT"""


def _task_event(task, base_url, now, prefix=""):
    dtstart = task.deadline.strftime('%Y%m%d') if task.deadline else task.creation_date.strftime('%Y%m%d')
    description = _ics_escape(task.description)
    title = _ics_escape(task.title)
    url = f"{base_url}case/{task.case_id}"

    return f"""BEGIN:VEVENT
UID:task-{task.id}@flowintel
DTSTAMP:{now}
DTSTART;VALUE=DATE:{dtstart}
SUMMARY:{prefix}{title}
DESCRIPTION:{description}\\n\\nView case: {url}
URL:{url}
STATUS:CONFIRMED
END:VEVENT"""


def _wrap_vcalendar(events):
    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Flowintel//Calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Flowintel Calendar
X-WR-TIMEZONE:UTC
X-WR-CALDESC:Cases and Tasks from Flowintel
{chr(10).join(events)}
END:VCALENDAR"""


def generate_full_calendar_feed(cases, tasks, base_url):
    """Generate a complete ICS calendar feed with all cases and tasks"""
    now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    events = []
    for case in cases:
        events.append(_case_event(case, base_url, now, prefix="[Case] "))
    for task in tasks:
        events.append(_task_event(task, base_url, now, prefix="[Task] "))
    return _wrap_vcalendar(events)


def generate_ics_for_case(case, base_url):
    """Generate ICS content for a single case"""
    now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    event = _case_event(case, base_url, now)
    return _wrap_vcalendar([event])


def generate_ics_for_task(task, base_url):
    """Generate ICS content for a single task"""
    now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    event = _task_event(task, base_url, now)
    return _wrap_vcalendar([event])
