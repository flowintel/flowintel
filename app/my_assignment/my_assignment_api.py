from flask import request

from flask_restx import Namespace, Resource

from ..decorators import api_required
from ..utils import utils

from . import my_assignment_core as AssignModel


my_assignment_ns = Namespace("my_assignment", description="Endpoints to manage assignments")
    
@my_assignment_ns.route('/user')
@my_assignment_ns.doc(description='Get all task assignments for a user')
class MyAssignment(Resource):
    method_decorators = [api_required]
    @my_assignment_ns.doc(params={"user_id": "Required. Id of the user whose assignments to retrieve", "page": "Page number for pagination (default: 1)"})
    def get(self):
        user_id = request.args.get("user_id")
        if not user_id:
            return {"message": "Need to pass a user id"}, 400

        page = request.args.get("page", default=1, type=int)
        user = AssignModel.get_user(user_id)
        if not user:
            return {"message": "User not found"}, 404

        tasks_list = AssignModel.my_assignment_sort(user=user, completed=False, page=page)
        return {"tasks": AssignModel.get_task_info(tasks_list, user), "nb_pages": tasks_list.pages}


@my_assignment_ns.route('/me')
@my_assignment_ns.doc(description='Get all task assignments for the authenticated API user')
class MyAssignmentMe(Resource):
    method_decorators = [api_required]
    @my_assignment_ns.doc(params={"page": "Page number for pagination (default: 1)"})
    def get(self):
        page = request.args.get("page", default=1, type=int)
        current_user = utils.get_user_from_api(request.headers)
        if not current_user:
            return {"message": "Current user not found"}, 403

        tasks_list = AssignModel.my_assignment_sort(user=current_user, completed=False, page=page)
        return {"tasks": AssignModel.get_task_info(tasks_list, current_user), "nb_pages": tasks_list.pages}
    