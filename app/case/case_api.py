from flask import Blueprint, request
from . import case_core as CaseModel
from . import case_core_api as CaseModelApi

from flask_restx import Api, Resource
from ..decorators import api_required, editor_required

api_case_blueprint = Blueprint('api_case', __name__)
api = Api(api_case_blueprint,
        title='Flowintel-cm API', 
        description='API to manage a case management instance.', 
        version='0.1', 
        default='GenericAPI', 
        default_label='Generic Flowintel-cm API', 
        doc='/doc'
    )



@api.route('/all')
@api.doc(description='Get all cases')
class GetCases(Resource):
    method_decorators = [api_required]
    def get(self):
        cases = CaseModel.get_all_cases()
        return {"cases": [case.to_json() for case in cases]}


@api.route('/<id>')
@api.doc(description='Get a case', params={'id': 'id of a case'})
class GetCase(Resource):
    method_decorators = [api_required]
    def get(self, id):
        case = CaseModel.get_case(id)
        if case:
            case_json = case.to_json()
            orgs = CaseModel.get_orgs_in_case(id)
            case_json["orgs"] = list()
            for org in orgs:
                case_json["orgs"].append({"id": org["id"], "uuid": org["uuid"], "name": org["name"]})
            
            return case_json
        return {"message": "Case not found"}


@api.route('/<id>/tasks')
@api.doc(description='Get all tasks for a case', params={'id': 'id of a case'})
class GetTasks(Resource):
    method_decorators = [api_required]
    def get(self, id):
        case = CaseModel.get_case(id)
            
        tasks = list()
        for task in case.tasks:
            users, flag = CaseModel.get_users_assign_task(task.id, CaseModelApi.get_user_api(request.headers["X-API-KEY"]))
            task.notes = CaseModel.markdown_notes(task.notes)
            tasks.append((task.to_json(), users, flag))

        return tasks


@api.route('/<id>/task/<tid>')
@api.doc(description='Get a specific task for a case', params={"id": "id of a case", "tid": "id of a task"})
class GetTask(Resource):
    method_decorators = [api_required]
    def get(self, id, tid):
        task = CaseModel.get_task(tid)
        if task:
            if id == task.case_id:
                return task.to_json()
            else:
                return {"message": "Task not in this case"}
        return {"message": "Task not found"}


@api.route('/<id>/delete')
@api.doc(description='Delete a case', params={'id': 'id of a case'})
class DeleteCase(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, id):
        if CaseModel.get_present_in_case(id, CaseModelApi.get_user_api(request.headers["X-API-KEY"])):
            if CaseModel.delete_case(id):
                return {"message": "Case deleted"}, 200
            else:
                return {"message": "Error case deleted"}
        return {"message": "Permission denied"}, 403


@api.route('/<id>/task/<tid>/delete')
@api.doc(description='Delete a specific task in a case', params={'id': 'id of a case', "tid": "id of a task"})
class DeleteTask(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, id, tid):
        if CaseModel.get_present_in_case(id, CaseModelApi.get_user_api(request.headers["X-API-KEY"])):
            task = CaseModel.get_task(tid)
            if task:
                if id == task.case_id:
                    if CaseModel.delete_task(tid):
                        return {"message": "Task deleted"}, 201
                    else:
                        return {"message": "Error task deleted"}, 201
                else:
                    return {"message": "Task not in this case"}
            return {"message": "Task not found"}
        return {"message": "Permission denied"}, 403
        

@api.route('/add', methods=['POST'])
@api.doc(description='Add a case')
class AddCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={"title": "Required. Title for a case", "description": "Description of a case", "dead_line_date": "Date(%Y-%m-%d)", "dead_line_time": "Time(%H-%M)"})
    def post(self):
        user = CaseModelApi.get_user_api(request.headers["X-API-KEY"])

        if request.json:
            verif_dict = CaseModelApi.verif_add_api(request.json)

            if "message" not in verif_dict:
                case = CaseModel.add_case_core(verif_dict, user)
                return {"message": f"Case created, id: {case.id}"}

            return verif_dict
        return {"message": "Please give data"}


@api.route('/<id>/add_task', methods=['POST'])
@api.doc(description='Add a task to a case', params={'id': 'id of a case'})
class AddTask(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={"title": "Required. Title for a task", "description": "Description of a task", "dead_line_date": "Date(%Y-%m-%d)", "dead_line_time": "Time(%H-%M)"})
    def post(self, id):
        if CaseModel.get_present_in_case(id, CaseModelApi.get_user_api(request.headers["X-API-KEY"])):
            if request.json:
                verif_dict = CaseModelApi.verif_add_api(request.json)

                if "message" not in verif_dict:
                    task = CaseModel.add_task_core(verif_dict, id)
                    return {"message": f"Task created for case id: {id}"}

                return verif_dict
            return {"message": "Please give data"}
        return {"message": "Permission denied"}, 403


@api.route('/<id>/edit', methods=['POST'])
@api.doc(description='Edit a case', params={'id': 'id of a case'})
class EditCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={"title": "Title for a case", "description": "Description of a case", "dead_line_date": "Date(%Y-%m-%d)", "dead_line_time": "Time(%H-%M)"})
    def post(self, id):
        if CaseModel.get_present_in_case(id, CaseModelApi.get_user_api(request.headers["X-API-KEY"])):
            if request.json:
                verif_dict = CaseModelApi.verif_edit_api(request.json, id)

                if "message" not in verif_dict:
                    CaseModel.edit_case_core(verif_dict, id)
                    return {"message": f"Case {id} edited"}

                return verif_dict
            return {"message": "Please give data"}
        return {"message": "Permission denied"}, 403


@api.route('/<id>/task/<tid>/edit', methods=['POST'])
@api.doc(description='Edit a task in a case', params={'id': 'id of a case', "tid": "id of a task"})
class EditTake(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={"title": "Title for a case", "description": "Description of a case", "dead_line_date": "Date(%Y-%m-%d)", "dead_line_time": "Time(%H-%M)"})
    def post(self, id, tid):
        if CaseModel.get_present_in_case(id, CaseModelApi.get_user_api(request.headers["X-API-KEY"])):
            if request.json:
                task = CaseModel.get_task(tid)
                if task:
                    if id == task.case_id:
                        verif_dict = CaseModelApi.verif_edit_api(request.json, tid)

                        if "message" not in verif_dict:
                            CaseModel.edit_task_core(verif_dict, tid)
                            return {"message": f"Task {tid} edited"}

                        return verif_dict
                    else:
                        return {"message": "Task not in this case"}
                else:
                    return {"message": "Task not found"}
            return {"message": "Please give data"}
        return {"message": "Permission denied"}, 403


@api.route('/<id>/task/<tid>/complete')
@api.doc(description='Complete a task in a case', params={'id': 'id of a case', "tid": "id of a task"})
class CompleteTake(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, id, tid):
        if CaseModel.get_present_in_case(id, CaseModelApi.get_user_api(request.headers["X-API-KEY"])):
            task = CaseModel.get_task(tid)
            if task:
                if id == task.case_id:
                    if CaseModel.complete_task(tid):
                        return {"message": f"Task {tid} completed"}
                    return {"message": f"Error task {tid} completed"}
                else:
                    return {"message": "Task not in this case"}
            return {"message": "Task not found"}
        return {"message": "Permission denied"}, 403


@api.route('/<id>/task/<tid>/get_note')
@api.doc(description='Get note of a task in a case', params={'id': 'id of a case', "tid": "id of a task"})
class GetNoteTask(Resource):
    method_decorators = [api_required]
    def get(self, id, tid):
        task = CaseModel.get_task(tid)
        if task:
            if id == task.case_id:
                note = CaseModel.get_note_text(tid)
                return {"note": note}
            else:
                return {"message": "Task not in this case"}
        return {"message": "Task not found"}


@api.route('/<id>/task/<tid>/modif_note', methods=['POST'])
@api.doc(description='Edit note of a task in a case', params={'id': 'id of a case', "tid": "id of a task"})
class ModifNoteTask(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={"note": "note to create or modify"})
    def post(self, id, tid):
        if CaseModel.get_present_in_case(id, CaseModelApi.get_user_api(request.headers["X-API-KEY"])):
            if "note" in request.json:
                task = CaseModel.get_task(tid)
                if task:
                    if id == task.case_id:
                        if CaseModel.modif_note_core(tid, request.json["note"]):
                            return {"message": f"Note for Task {tid} edited"}
                        return {"message": f"Error Note for Task {tid} edited"}
                    else:
                        return {"message": "Task not in this case"}
                return {"message": "Task not found"}
            return {"message": "Key 'note' not found"}
        return {"message": "Permission denied"}, 403



@api.route('/<id>/add_org', methods=['POST'])
@api.doc(description='Add an org to the case', params={'id': 'id of a case'})
class AddOrgCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={"name": "Name of the organisation", "oid": "id of the organisation"})
    def post(self, id):
        if CaseModel.get_present_in_case(id, CaseModelApi.get_user_api(request.headers["X-API-KEY"])):
            if "name" in request.json:
                org = CaseModel.get_org_by_name(request.json["name"])
            elif "id" in request.json:
                org = CaseModel.get_org(request.json["oid"])
            else:
                return {"message": "Required an id or a name of an Org"}

            if org:
                if not CaseModel.get_org_in_case(org.id, id):
                    if CaseModel.add_orgs_case({"org_id": [org.id]}, id):
                        return {"message": f"Org added for Case {id} edited"}
                    return {"message": f"Error Org added for Case {id} edited"}
                else:
                    return {"message": "Org already in case"}
            return {"message": "Org not found"}

        return {"message": "Permission denied"}, 403


@api.route('/<id>/remove_org/<oid>', methods=['GET'])
@api.doc(description='Add an org to the case', params={'id': 'id of a case', "oid": "id of an org"})
class RemoveOrgCase(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, id, oid):
        if CaseModel.get_present_in_case(id, CaseModelApi.get_user_api(request.headers["X-API-KEY"])):
            org = CaseModel.get_org(oid)

            if org:
                if CaseModel.get_org_in_case(org.id, id):
                    if CaseModel.remove_org_case(id, org.id):
                        return {"message": f"Org deleted for Case {id} edited"}
                    return {"message": f"Error Org deleted for Case {id} edited"}
                else:
                    return {"message": "Org not in case"}
            return {"message": "Org not found"}
        return {"message": "Permission denied"}, 403


@api.route('/<id>/take_task/<tid>', methods=['GET'])
@api.doc(description='Assign user to the task', params={'id': 'id of a case', "tid": "id of a task"})
class AssignTask(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, id, tid):
        if CaseModel.get_present_in_case(id, CaseModelApi.get_user_api(request.headers["X-API-KEY"])):
            task = CaseModel.get_task(tid)

            if task:
                if id == task.case_id:
                    user = CaseModelApi.get_user_api(request.headers["X-API-KEY"])
                    if CaseModel.assign_task(tid, user):
                        return {"message": f"Task Take"}
                    else:
                        return {"message": f"Error Task Take"}
                else:
                    return {"message": "Task not in this case"}
            return {"message": "Task not found"}
        return {"message": "Permission denied"}, 403


@api.route('/<id>/remove_assign_task/<tid>', methods=['GET'])
@api.doc(description='Assign user to the task', params={'id': 'id of a case', "tid": "id of a task"})
class RemoveOrgCase(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, id, tid):
        if CaseModel.get_present_in_case(id, CaseModelApi.get_user_api(request.headers["X-API-KEY"])):
            task = CaseModel.get_task(tid)

            if task:
                if id == task.case_id:
                    user = CaseModelApi.get_user_api(request.headers["X-API-KEY"])
                    if CaseModel.remove_assign_task(tid, user):
                        return {"message": f"User Removed from assignation"}
                    return {"message": f"Error User Removed from assignation"}
                else:
                    return {"message": "Task not in this case"}
            return {"message": "Task not found"}
        return {"message": "Permission denied"}, 403