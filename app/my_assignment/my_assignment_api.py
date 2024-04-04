from flask import Blueprint, request
from . import my_assignment_core as AssignModel
from ..case import task_core as TaskModel
from ..case import case_core_api as CaseModelApi

from flask_restx import Api, Resource
from ..decorators import api_required

api_assignment_blueprint = Blueprint('api_assignment', __name__)
api = Api(api_assignment_blueprint,
        title='Flowintel-cm API', 
        description='API to manage a case management instance.', 
        version='0.1', 
        default='GenericAPI', 
        default_label='Generic Flowintel-cm API', 
        doc='/doc'
    )

    
@api.route('/user')
@api.doc(description='Get all cases')
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
    