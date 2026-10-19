from flask_restx import Namespace, Resource, fields
from flask import request

from ..decorators import api_required, editor_required
from ..utils import utils
from ..utils.logger import flowintel_log

from . import calendar_core as CalendarModel

calendar_api = Namespace('calendar', description='Calendar operations')


manual_event_input = calendar_api.model('ManualCalendarEventInput', {
    'title': fields.String(required=True, min_length=1, max_length=255, description='Event title'),
    'description': fields.String(description='Optional description (up to 60000 UTF-8 bytes)', default=''),
    'start': fields.String(
        required=True,
        description='YYYY-MM-DD for all-day events; ISO 8601 with a timezone for timed events',
        example='2026-10-01',
    ),
    'end': fields.String(
        description='Optional exclusive end, in the same format as start. Omit or use null to default '
                    'to the following day for all-day events, or one hour later for timed events.',
        example='2026-10-02',
    ),
    'all_day': fields.Boolean(default=True, description='Whether the event lasts all day'),
    'visibility': fields.String(
        enum=['private', 'organisation'], default='private',
        description='Only the API key owner, or members of their organisation, can view the event',
    ),
})


@calendar_api.route('/events')
class ManualCalendarEvents(Resource):
    method_decorators = [editor_required, api_required]

    @calendar_api.doc(description='Create a standalone calendar event owned by the API key user. '
                                'Returns the saved event under the event key, including its id. '
                                'Timed dates in the response use UTC.')
    @calendar_api.expect(manual_event_input, validate=False)
    @calendar_api.response(201, 'Event created')
    @calendar_api.response(400, 'Invalid event data')
    @calendar_api.response(403, 'Invalid API key or read-only user')
    def post(self):
        """Create a manual calendar event."""
        user = utils.get_user_api(request.headers['X-API-KEY'])
        try:
            event = CalendarModel.create_manual_event(request.get_json(silent=True), user)
        except ValueError as exc:
            return {'message': str(exc)}, 400
        flowintel_log(
            'audit', 201, 'Manual calendar event created via API',
            User=user.email, EventId=event.id,
        )
        return {'event': event.to_json()}, 201


@calendar_api.route('/feed')
@calendar_api.doc(description='Get full calendar feed in ICS format for the authenticated user')
class CalendarFeed(Resource):
    """Get full calendar feed in ICS format"""
    method_decorators = [api_required]

    @calendar_api.doc(description='Download complete calendar feed (ICS format) for the authenticated user')
    def get(self):
        """Get calendar feed
        
        Returns an ICS calendar file containing cases, tasks and manual events visible to the current user.
        """
        current_user = utils.get_user_api(request.headers["X-API-KEY"])
        
        cases_list = CalendarModel.get_all_cases_for_user(current_user)
        tasks_list = CalendarModel.get_all_tasks_for_user(current_user)
        
        ics_content = CalendarModel.generate_full_calendar_feed(
            cases_list, tasks_list, request.host_url, CalendarModel.manual_events_for_user(current_user).all()
        )
        
        return ics_content, 200, {
            'Content-Type': 'text/calendar',
            'Content-Disposition': 'attachment; filename=flowintel_calendar.ics'
        }
