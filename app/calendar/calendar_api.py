from flask_restx import Namespace, Resource
from flask import request
from ..decorators import api_required
from . import calendar_core as CalendarModel
from ..utils import utils
from datetime import datetime

calendar_api = Namespace('calendar', description='Calendar operations')


@calendar_api.route('/feed')
class CalendarFeed(Resource):
    """Get full calendar feed in ICS format"""
    method_decorators = [api_required]

    @calendar_api.doc(description='Download complete calendar feed (ICS format) for the authenticated user')
    def get(self):
        """Get calendar feed
        
        Returns an ICS calendar file containing all cases and tasks for the current user.
        """
        current_user = utils.get_user_api(request.headers["X-API-KEY"])
        
        cases_list = CalendarModel.get_all_cases_for_user(current_user)
        tasks_list = CalendarModel.get_all_tasks_for_user(current_user)
        
        ics_content = generate_full_calendar_feed(cases_list, tasks_list, request.host_url)
        
        return ics_content, 200, {
            'Content-Type': 'text/calendar',
            'Content-Disposition': 'attachment; filename=flowintel_calendar.ics'
        }


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
