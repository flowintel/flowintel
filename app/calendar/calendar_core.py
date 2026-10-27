from app.db_class.db import Case, Task, Task_User, Case_Org, Calendar_Event
from app.extensions import db

from datetime import date, datetime, timedelta, timezone
from sqlalchemy import and_, or_


def parse_event_datetime(value, all_day=False):
    if not isinstance(value, str) or not value:
        raise ValueError("A valid date is required")
    try:
        if all_day:
            return datetime.combine(date.fromisoformat(value), datetime.min.time())
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError("Timed events require a timezone")
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, OverflowError):
        raise ValueError("Invalid date or time (include a timezone for timed events)") from None


def validate_manual_event(data, user):
    if not isinstance(data, dict):
        raise ValueError("An event object is required")
    title = data.get('title')
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 255:
        raise ValueError("Title must contain between 1 and 255 characters")
    description = data.get('description', '')
    if not isinstance(description, str) or len(description.encode('utf-8')) > 60000:
        raise ValueError("Description must be text of at most 60000 bytes")
    all_day = data.get('all_day', True)
    if not isinstance(all_day, bool):
        raise ValueError("All day must be true or false")
    visibility = data.get('visibility', 'private')
    if visibility not in ('private', 'organisation'):
        raise ValueError("Visibility must be private or organisation")
    if visibility == 'organisation' and user.org_id is None:
        raise ValueError("An organisation is required to share this event")
    start = parse_event_datetime(data.get('start'), all_day)
    end_value = data.get('end')
    end = None if end_value in (None, '') else parse_event_datetime(end_value, all_day)
    if end is not None and end <= start:
        raise ValueError("End must be after start")
    if end is None:
        try:
            end = start + (timedelta(days=1) if all_day else timedelta(hours=1))
        except OverflowError:
            raise ValueError("Date is out of range") from None
    return dict(
        title=title.strip(), description=description, start=start, end=end,
        all_day=all_day, org_id=user.org_id if visibility == 'organisation' else None,
    )


def create_manual_event(data, user):
    values = validate_manual_event(data, user)
    event = Calendar_Event(user_id=user.id, **values)
    db.session.add(event)
    db.session.commit()
    return event


def manual_events_for_user(user):
    visibility = Calendar_Event.user_id == user.id
    if user.org_id is not None:
        visibility = or_(visibility, Calendar_Event.org_id == user.org_id)
    return Calendar_Event.query.filter(visibility)


def get_manual_events(start, end, user):
    # FullCalendar sends exclusive visible bounds, including adjacent month days.
    # All-day dates stay in the viewer's calendar timezone; timed events use UTC.
    day_start = parse_event_datetime(start[:10], all_day=True) if isinstance(start, str) else None
    day_end = parse_event_datetime(end[:10], all_day=True) if isinstance(end, str) else None
    start = parse_event_datetime(start)
    end = parse_event_datetime(end)
    if end <= start:
        raise ValueError("End must be after start")
    return manual_events_for_user(user).filter(
        or_(
            and_(Calendar_Event.all_day.is_(True), Calendar_Event.start < day_end, Calendar_Event.end > day_start),
            and_(Calendar_Event.all_day.is_(False), Calendar_Event.start < end, Calendar_Event.end > start),
        ),
    ).order_by(Calendar_Event.start, Calendar_Event.id).all()


def _tasks_visible_to_user_query(user):
    query = Task.query.join(Case, Case.id == Task.case_id)

    if user.is_admin():
        return query

    return (
        query
        .outerjoin(Task_User, Task_User.task_id == Task.id)
        .outerjoin(Case_Org, Case_Org.case_id == Case.id)
        .filter(or_(
            Task_User.user_id == user.id,
            Case_Org.org_id == user.org_id,
        ))
        .distinct()
    )


def _tasks_assigned_to_user_query(user):
    return Task.query.join(Task_User, Task_User.task_id == Task.id).filter(
        Task_User.user_id == user.id
    )


def get_task_month_core(date_month, flag_dead_creation, user, assigned_only=False):
    # Convert "YYYY-MM" string into first day of month
    start = datetime.strptime(date_month, "%Y-%m")
    # Compute first day of next month
    if start.month == 12:
        end = start.replace(year=start.year+1, month=1, day=1)
    else:
        end = start.replace(month=start.month+1, day=1)

    query = _tasks_assigned_to_user_query(user) if assigned_only else _tasks_visible_to_user_query(user)

    if flag_dead_creation == 'true':
        return query.filter(
                Task.deadline >= start,
                Task.deadline < end
            ).all()
    else:
        return query.filter(
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
    return _tasks_visible_to_user_query(user).all()


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
X-WR-CALDESC:Cases and Tasks and Events from Flowintel
{chr(10).join(events)}
END:VCALENDAR"""


def _manual_event(event, now, prefix=""):
    if event.all_day:
        dates = [f"DTSTART;VALUE=DATE:{event.start.strftime('%Y%m%d')}"]
        if event.end:
            dates.append(f"DTEND;VALUE=DATE:{event.end.strftime('%Y%m%d')}")
    else:
        dates = [f"DTSTART:{event.start.strftime('%Y%m%dT%H%M%SZ')}"]
        if event.end:
            dates.append(f"DTEND:{event.end.strftime('%Y%m%dT%H%M%SZ')}")
    return '\n'.join([
        'BEGIN:VEVENT',
        f'UID:event-{event.id}@flowintel',
        f'DTSTAMP:{now}',
        *dates,
        f'SUMMARY:{prefix}{_ics_escape(event.title)}',
        f'DESCRIPTION:{_ics_escape(event.description)}',
        'STATUS:CONFIRMED',
        'END:VEVENT',
    ])


def generate_ics_for_manual_event(event):
    now = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return _wrap_vcalendar([_manual_event(event, now)])


def generate_full_calendar_feed(cases, tasks, base_url, manual_events=()):
    """Generate a complete ICS calendar feed with cases, tasks and manual events."""
    now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    events = []
    for case in cases:
        events.append(_case_event(case, base_url, now, prefix="[Case] "))
    for task in tasks:
        events.append(_task_event(task, base_url, now, prefix="[Task] "))
    for event in manual_events:
        events.append(_manual_event(event, now, prefix="[Event] "))
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
