from flask_restx import Namespace, Resource
from flask import request
from ..decorators import api_required
from . import calendar_core as CalendarModel
from ..utils import utils

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
        
        ics_content = CalendarModel.generate_full_calendar_feed(cases_list, tasks_list, request.host_url)
        
        return ics_content, 200, {
            'Content-Type': 'text/calendar',
            'Content-Disposition': 'attachment; filename=flowintel_calendar.ics'
        }
