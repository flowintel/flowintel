from flask import request
from . import my_assignment_core as AssignModel
from ..case.TaskCore import TaskModel

from flask_restx import Namespace, Resource
from ..decorators import api_required

my_assignment_ns = Namespace("my_assignment", description="Endpoints to manage assignments")

    
@my_assignment_ns.route('/user')
@my_assignment_ns.doc(description='Get all cases')
class MyAssignment(Resource):
    method_decorators = [api_required]
    def get(self):
        if "user_id" in request.args:
            if "page" in request.args:
                page = request.args.get("page")
            else:
                page = 1
            user = AssignModel.get_user(request.args.get("user_id"))

            tasks_list = AssignModel.my_assignment_sort_by_status(user=user, completed=False, page=page)
            return {"tasks": TaskModel.get_task_info(tasks_list, user), "nb_pages": tasks_list.pages}
        return {"message": "Need to pass a user id"}, 400
    