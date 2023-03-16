from flask import Blueprint, request
from . import case_core as CaseModel
from . import case_core_api as CaseModelApi

from flask_restx import Api, Resource
from ..utils.utils import verif_api_key

api_case_blueprint = Blueprint('api_case', __name__)
api = Api(api_case_blueprint)



@api.route('/all')
class GetCases(Resource):
    def get(self):
        verif = verif_api_key(request.headers)
        if verif:
            return verif

        cases = CaseModel.getAll()
        return {"cases": [case.to_json() for case in cases]}


@api.route('/<id>')
class GetCase(Resource):
    def get(self, id):
        verif = verif_api_key(request.headers)
        if verif:
            return verif

        case = CaseModel.get(id)
        if case:
            return case.to_json()
        return {"message": "Case not found"}

@api.route('/<id>/tasks')
class GetTasks(Resource):
    def get(self, id):
        verif = verif_api_key(request.headers)
        if verif:
            return verif

        case = CaseModel.get(id)
            
        tasks = list()
        for task in case.tasks:
            users, flag = CaseModel.get_user_assign_task(task.id)
            task.notes = CaseModel.markdown_notes(task.notes)
            tasks.append((task.to_json(), users, flag))

        return tasks

@api.route('/<id>/task/<tid>')
class GetTask(Resource):
    def get(self, id, tid):
        verif = verif_api_key(request.headers)
        if verif:
            return verif

        task = CaseModel.get_task(tid)
        if task:
            return task.to_json()
        return {"message": "Task not found"}


@api.route('/<id>/delete')
class DeleteCase(Resource):
    def get(self, id):
        verif = verif_api_key(request.headers)
        if verif:
            return verif

        if CaseModel.delete(id):
            return {"message": "Case deleted"}, 200
        else:
            return {"message": "Error case deleted"}

@api.route('/<id>/task/<tid>/delete')
class DeleteTask(Resource):
    def get(self, id, tid):
        verif = verif_api_key(request.headers)
        if verif:
            return verif

        if CaseModel.delete_task(tid):
            return {"message": "Task deleted"}, 201
        else:
            return {"message": "Error task deleted"}, 201

@api.route('/add', methods=['POST'])
class AddCase(Resource):
    def post(self):
        verif = verif_api_key(request.headers)
        if verif:
            return verif

        if request.json:
            verif_dict = CaseModelApi.verif_add_api(request.json)

            if "message" not in verif_dict:
                case = CaseModelApi.add_case_core(verif_dict)
                return {"message": f"Case created, id: {case.id}"}

            return verif_dict
        return {"message": "Please give data"}


@api.route('/<id>/add_task', methods=['POST'])
class AddTask(Resource):
    def post(self, id):
        verif = verif_api_key(request.headers)
        if verif:
            return verif

        if request.json:
            verif_dict = CaseModelApi.verif_add_api(request.json)

            if "message" not in verif_dict:
                task = CaseModelApi.add_task_core(verif_dict, id)
                return {"message": f"Task created for case id: {id}"}

            return verif_dict
        return {"message": "Please give data"}


@api.route('/<id>/edit', methods=['POST'])
class EditCase(Resource):
    def post(self, id):
        verif = verif_api_key(request.headers)
        if verif:
            return verif

        if request.json:
            verif_dict = CaseModelApi.verif_edit_api(request.json, id)

            if "message" not in verif_dict:
                CaseModelApi.edit_case_core(verif_dict, id)
                return {"message": f"Case {id} edited"}

            return verif_dict
        return {"message": "Please give data"}

@api.route('/<id>/task/<tid>/edit', methods=['POST'])
class EditTake(Resource):
    def post(self, id, tid):
        verif = verif_api_key(request.headers)
        if verif:
            return verif

        if request.json:
            verif_dict = CaseModelApi.verif_edit_api(request.json, tid)

            if "message" not in verif_dict:
                CaseModelApi.edit_task_core(verif_dict, id)
                return {"message": f"Task {id} edited"}

            return verif_dict
        return {"message": "Please give data"}