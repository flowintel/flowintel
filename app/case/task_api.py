from flask import request, current_app

from app.db_class.db import Case, User
from . import common_core as CommonModel
from .TaskCore import TaskModel
from . import validation_api as CaseModelApi
from ..utils import utils
from ..utils.logger import flowintel_log

from flask_restx import Namespace, Resource
from ..decorators import api_required, editor_required

task_ns = Namespace("task", description="Endpoints to manage tasks")


def check_user_private_case(case: Case, request_headers = None, current_user: User = None):
    if not current_user:
        current_user = utils.get_user_from_api(request_headers)
    if case.is_private and not CommonModel.get_present_in_case(case.id, current_user) and not current_user.is_admin():
        return False
    return True

@task_ns.route('/<tid>')
@task_ns.doc(description='Get a task by id', params={"tid": "id of a task"})
class GetTask(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if not check_user_private_case(CommonModel.get_case(task.case_id), current_user=current_user):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
            loc = dict()
            loc["users_assign"], loc["is_current_user_assign"] = TaskModel.get_users_assign_task(task.id, current_user)
            loc["task"] = task.to_json()
            return loc, 200
        return {"message": "Task not found"}, 404
    

@task_ns.route('/title', methods=["POST"])
@task_ns.doc(description='Get a task by title')
class GetTaskTitle(Resource):
    method_decorators = [api_required]
    @task_ns.doc(params={"title": "Title of a task"})
    def post(self):
        if "title" in request.json:
            current_user = utils.get_user_from_api(request.headers)
            task = CommonModel.get_task_by_title(request.json["title"], current_user)
            if task:
                return task.to_json(), 200
            return {"message": "Task not found"}, 404
        return {"message": "Need to pass a title"}, 404
    
    
@task_ns.route('/<tid>/edit', methods=['POST'])
@task_ns.doc(description='Edit a task', params={"tid": "id of a task"})
class EditTake(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={"title": "Title for a task", 
                     "description": "Description of a task", 
                     "deadline_date": "Date(%Y-%m-%d)", 
                     "deadline_time": "Time(%H-%M)",
                     "tags": "list of tags from taxonomies",
                     "clusters": "list of tags from galaxies",
                     "connectors": "List of name of connectors",
                     "galaxies": "list of galaxies name",
                     "identifier": "Dictionnary with connector as key and identifier as value",
                     "custom_tags" : "List of custom tags created on the instance",
                     "time_required": "Time required to realize the task"
                    })
    def post(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.is_task_restricted(task) and not TaskModel.can_edit_requested_task(current_user):
                    flowintel_log("audit", 403, "Task edit denied: Task in Requested or Rejected status", User=current_user.email, CaseId=task.case_id, TaskId=tid)
                    return {"message": "Task in Requested or Rejected status can only be edited by Admin, Case Admin or Queue Admin"}, 403
                
                if request.json:
                    verif_dict = CaseModelApi.verif_edit_task(request.json, tid)

                    if "message" not in verif_dict:
                        TaskModel.edit_task_core(verif_dict, tid, current_user)
                        return {"message": f"Task {tid} edited"}, 200

                    return verif_dict, 400
                return {"message": "Please give data"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task not found"}, 404

@task_ns.route('/<tid>/delete')
@task_ns.doc(description='Delete a task', params={"tid": "id of a task"})
class DeleteTask(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, tid):
        from ..utils.logger import flowintel_log
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.delete_task(tid, current_user):
                    flowintel_log("audit", 200, "Task deleted", User=current_user.email, CaseId=task.case_id, TaskId=tid)
                    return {"message": "Task deleted"}, 200
                return {"message": "Error task deleted"}, 400
            flowintel_log("audit", 403, "Task deletion denied", User=current_user.email, CaseId=task.case_id, TaskId=tid)
            return {"message": "Permission denied"}, 403
        return {"message": "Task not found"}, 404


@task_ns.route('/<tid>/complete')
@task_ns.doc(description='Complete a task', params={"tid": "id of a task"})
class CompleteTask(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.is_task_restricted(task) and not TaskModel.can_edit_requested_task(current_user):
                    flowintel_log("audit", 403, "Complete task denied: Task in Requested or Rejected status", User=current_user.email, CaseId=task.case_id, TaskId=tid)
                    return {"message": "Task in Requested or Rejected status can only be modified by Admin, Case Admin or Queue Admin"}, 403
                
                if TaskModel.complete_task(tid, current_user):
                    return {"message": f"Task {tid} completed"}, 200
                return {"message": f"Error task {tid} completed"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task not found"}, 404

    
@task_ns.route('/<tid>/get_all_notes')
@task_ns.doc(description='Get all notes of a task', params={"tid": "id of a task"})
class GetAllNotesTask(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            if not check_user_private_case(CommonModel.get_case(task.case_id), request.headers):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
            return {"notes": [note.to_json() for note in task.notes]}, 200
        return {"message": "Task not found"}, 404
    
@task_ns.route('/<tid>/get_note')
@task_ns.doc(description='Get note of a task', params={"note_id": "id of a note in task"})
class GetNoteTask(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            if not check_user_private_case(CommonModel.get_case(task.case_id), request.headers):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
            if "note_id" in request.args:
                task_note = CommonModel.get_task_note(request.args.get("note_id"))
                if task_note:
                    return {"note": task_note.note}, 200
                return {"message": "Note not found"}, 404
            return {"message": "Need to pass a note id"}, 400
        return {"message": "Task not found"}, 404


@task_ns.route('/<tid>/modif_note', methods=['POST'])
@task_ns.doc(description='Edit note of a task in a case', params={"tid": "id of a task"})
class ModifNoteTask(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={"note": "note to create or modify", "note_id": "id of the note"})
    def post(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.is_task_restricted(task) and not TaskModel.can_edit_requested_task(current_user):
                    flowintel_log("audit", 403, "Modify task note denied: Task in Requested or Rejected status", User=current_user.email, CaseId=task.case_id, TaskId=tid)
                    return {"message": "Task in Requested or Rejected status can only be modified by Admin, Case Admin or Queue Admin"}, 403
                
                if "note_id" in request.json:
                    if "note" in request.json:
                        res = TaskModel.modif_note_core(tid, current_user, request.json["note"], request.json["note_id"])
                        if type(res) == dict:
                            return res, 400
                        return {"message": f"Note for task {tid} edited"}, 200
                    return {"message": "Need to pass a note"}, 400
                return {"message": "Need to pass a note id"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task not found"}, 404
    
@task_ns.route('/<tid>/create_note', methods=['POST'])
@task_ns.doc(description='Create a new note for a task', params={"tid": "id of a task"})
class CreateNoteTask(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={"note": "note to create"})
    def post(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.is_task_restricted(task) and not TaskModel.can_edit_requested_task(current_user):
                    flowintel_log("audit", 403, "Create task note denied: Task in Requested or Rejected status", User=current_user.email, CaseId=task.case_id, TaskId=tid)
                    return {"message": "Task in Requested or Rejected status can only be modified by Admin, Case Admin or Queue Admin"}, 403
                
                if "note" in request.json:
                    res = TaskModel.modif_note_core(tid, current_user, request.json["note"], '-1')
                    if type(res) == dict:
                        return res, 400
                    return {"message": f"Note for task {tid} edited"}, 200
                return {"message": "Need to pass a note"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task not found"}, 404
    

@task_ns.route('/<tid>/delete_note')
@task_ns.doc(description='Delete a note of a task', params={"note_id": "id of a note in task"})
class GetNoteTask(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if "note_id" in request.args:
                    if TaskModel.delete_note(tid, request.args.get("note_id"), current_user):
                        return {"message": "Note deleted"}, 200
                return {"message": "Need to pass a note id"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task not found"}, 404


@task_ns.route('/<tid>/take_task', methods=['GET'])
@task_ns.doc(description='Assign current user to the task', params={"tid": "id of a task"})
class AssignTask(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.is_task_restricted(task) and not TaskModel.can_edit_requested_task(current_user):
                    flowintel_log("audit", 403, "Take task denied: Task in Requested or Rejected status", User=current_user.email, CaseId=task.case_id, TaskId=tid)
                    return {"message": "Task in Requested or Rejected status can only be modified by Admin, Case Admin or Queue Admin"}, 403
                
                if TaskModel.assign_task(tid, user=current_user, current_user=current_user, flag_current_user=True):
                    return {"message": f"Task Take"}, 200
                return {"message": f"Error Task Take"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task not found"}, 404


@task_ns.route('/<tid>/remove_assignment', methods=['GET'])
@task_ns.doc(description='Remove assigment of current user to the task', params={"tid": "id of a task"})
class RemoveOrgCase(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.is_task_restricted(task) and not TaskModel.can_edit_requested_task(current_user):
                    flowintel_log("audit", 403, "Remove assignment denied: Task in Requested or Rejected status", User=current_user.email, CaseId=task.case_id, TaskId=tid)
                    return {"message": "Task in Requested or Rejected status can only be modified by Admin, Case Admin or Queue Admin"}, 403
                
                if TaskModel.remove_assign_task(tid, user=current_user, current_user=current_user, flag_current_user=True):
                    return {"message": f"Removed from assignment"}, 200
                return {"message": f"Error Removed from assignment"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task not found"}, 404


@task_ns.route('/<tid>/assign_users', methods=['POST'])
@task_ns.doc(description='Assign users to a task', params={"tid": "id of a task"})
class AssignUsers(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={"users_id": "List of user id"})
    def post(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                users_list = request.json["users_id"]
                for user in users_list:
                    TaskModel.assign_task(tid, user=user, current_user=current_user, flag_current_user=False)
                return {"message": "Users Assigned"}, 200
            return {"message": "Permission denied"}, 403
        return {"message": "Task not found"}, 404


@task_ns.route('/<tid>/remove_assign_user', methods=['POST'])
@task_ns.doc(description='Remove an assign user to a task', params={"tid": "id of a task"})
class RemoveAssignUser(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={"user_id": "Id of a user"})
    def post(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                user_id = request.json["user_id"]
                if TaskModel.remove_assign_task(tid, user=user_id, current_user=current_user, flag_current_user=False):
                    return {"message": "User Removed from assignment"}, 200
                return {"message": "Error removing user from assignment"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task not found"}, 404
    

@task_ns.route('/list_status', methods=['GET'])
@task_ns.doc(description='List all status')
class ListStatus(Resource):
    method_decorators = [api_required]
    def get(self):
        return [status.to_json() for status in CommonModel.get_all_status()], 200

@task_ns.route('/<tid>/change_status', methods=['POST'])
@task_ns.doc(description='Change status of a task', params={"tid": "id of a task"})
class ChangeStatus(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={"status_id": "Id of the new status"})
    def post(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.change_task_status(request.json["status_id"], task, current_user):
                    return {"message": "Status changed"}, 200
                return {"message": "Error chnaging status"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task not found"}, 404


@task_ns.route('/<tid>/files')
@task_ns.doc(description='Get list of files', params={"tid": "id of a task"})
class DownloadFile(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            if not check_user_private_case(CommonModel.get_case(task.case_id), request.headers):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
            file_list = [file.to_json() for file in task.files]
            return {"files": file_list}, 200
        return {"message": "Task Not found"}, 404


@task_ns.route('/<tid>/upload_file')
@task_ns.doc(description='Upload a file')
class UploadFile(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={})
    def post(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.is_task_restricted(task) and not TaskModel.can_edit_requested_task(current_user):
                    flowintel_log("audit", 403, "Upload file denied: Task in Requested or Rejected status", User=current_user.email, CaseId=task.case_id, TaskId=tid)
                    return {"message": "Task in Requested or Rejected status can only be modified by Admin, Case Admin or Queue Admin"}, 403
                
                created_files = TaskModel.add_file_core(task, request.files, current_user)
                if created_files:
                    file_details = [f"{f.name} ({f.file_size} bytes, {f.file_type})" for f in created_files]
                    flowintel_log("audit", 200, "Files added to task", User=current_user.email, CaseId=task.case_id, TaskId=tid, FilesCount=len(created_files), Files="; ".join(file_details))
                    return {"message": "File added"}, 200
                return {"message": "Error file added"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task Not found"}, 404
    

@task_ns.route('/<tid>/download_file/<fid>')
@task_ns.doc(description='Download a file', params={"tid": "id of a task", "fid": "id of a file"})
class DownloadFile(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, tid, fid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                file = CommonModel.get_file(fid)
                if file and file in task.files:
                    return TaskModel.download_file(file)
            return {"message": "Permission denied"}, 403
        return {"message": "Task Not found"}, 404
    
@task_ns.route('/<tid>/delete_file/<fid>')
@task_ns.doc(description='Delete a file', params={"tid": "id of a task", "fid": "id of a file"})
class DeleteFile(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, tid, fid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                file = CommonModel.get_file(fid)
                if file and file in task.files:
                    file_name = file.name
                    file_size = file.file_size if file.file_size else 0
                    file_type = file.file_type if file.file_type else "unknown"
                    
                    if TaskModel.delete_file(file, task, current_user):
                        flowintel_log("audit", 200, "Task file deleted", User=current_user.email, CaseId=task.case_id, TaskId=tid, FileId=fid, FileName=file_name, FileSize=f"{file_size} bytes", FileType=file_type)
                        return {"message": "File Deleted"}, 200
                    return {"message": "Error File Deleted"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task Not found"}, 404


@task_ns.route('/<tid>/get_taxonomies_task', methods=['GET'])
@task_ns.doc(description='Get all tags and taxonomies in a task')
class GetTaxonomiesTask(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            if not check_user_private_case(CommonModel.get_case(task.case_id), request.headers):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
            tags = CommonModel.get_task_tags(tid)
            taxonomies = []
            if tags:
                taxonomies = [tag.split(":")[0] for tag in tags]
            return {"tags": tags, "taxonomies": taxonomies}
        return {"message": "Task Not found"}, 404


@task_ns.route('/<tid>/get_galaxies_task', methods=['GET'])
@task_ns.doc(description='Get all tags and taxonomies in a task')
class GetGalaxiesTask(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            if not check_user_private_case(CommonModel.get_case(task.case_id), request.headers):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
            clusters = CommonModel.get_task_clusters(tid)
            galaxies = []
            if clusters:
                for cluster in clusters:
                    loc_g = CommonModel.get_galaxy(cluster.galaxy_id)
                    if not loc_g.name in galaxies:
                        galaxies.append(loc_g.name)
                    index = clusters.index(cluster)
                    clusters[index] = cluster.tag
            return {"clusters": clusters, "galaxies": galaxies}
        return {"message": "Task Not found"}, 404


##############
# Connectors #
##############

@task_ns.route('/<tid>/get_connectors', methods=['GET'])
@task_ns.doc(description='Get all connectors for a task')
class GetConnectors(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            if not check_user_private_case(CommonModel.get_case(task.case_id), request.headers):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
            instance_list = []
            for task_instance in CommonModel.get_task_connectors(task.id):
                loc_instance = CommonModel.get_instance(task_instance.instance_id)
                instance_list.append({
                    "id": loc_instance.id,
                    "name": loc_instance.name,
                    "identifier": task_instance.identifier
                })
            return {"connectors": instance_list}, 200
        return {"message": "Task Not found"}, 404


@task_ns.route('/<tid>/add_connectors', methods=['POST'])
@task_ns.doc(description='Add connectors to a task')
class AddConnectorsTask(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={
        "connectors": "Required. List of connectors instance. Dict with 'name' and 'identifier' as keys."
    })
    def post(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.is_task_restricted(task) and not TaskModel.can_edit_requested_task(current_user):
                    flowintel_log("audit", 403, "Add connectors denied: Task in Requested or Rejected status", User=current_user.email, CaseId=task.case_id, TaskId=tid)
                    return {"message": "Task in Requested or Rejected status can only be modified by Admin, Case Admin or Queue Admin"}, 403
                
                if "connectors" in request.json:
                    if TaskModel.add_connector(tid, request.json):
                        return {"message": "Connector added"}, 200
                    return {"message": "Error Connector added"}, 400
                return {"message": "Please give a list of connectors"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task doesn't exist"}, 404
    
@task_ns.route('/<tid>/edit_connector/<ciid>', methods=['POST'])
@task_ns.doc(description='Edit connector')
class EditConnectorTask(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={
        "identifier": "Required. Identifier used by modules to identify where to send data."
    })
    def post(self, tid, ciid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if "identifier" in request.json:
                    if TaskModel.edit_connector(ciid, request.json):
                        return {"message": "Connector edited"}, 200
                    return {"message": "Error Connector edited"}, 400
                return {"message": "Please give a list of connectors"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task doesn't exist"}, 404
    
@task_ns.route('/<tid>/remove_connector/<ciid>', methods=['GET'])
@task_ns.doc(description='Remove a connector')
class RemoveConnectorTask(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, tid, ciid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.remove_connector(ciid):
                    return {"message": "Connector removed"}, 200
                return {"message": "Error Connector removed"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case doesn't exist"}, 404

###########
# Subtask #
###########

@task_ns.route('/<tid>/create_subtask', methods=['POST'])
@task_ns.doc(description='Create a subtask')
class CreateSubtask(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={
        'description': 'Required. Description of the subtask'
    })
    def post(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if "description" in request.json:
                    subtask = TaskModel.create_subtask(tid, request.json["description"], current_user)
                    if subtask:
                        return {"message": f"Subtask created, id: {subtask.id}", "subtask_id": subtask.id}, 201 
                return {"message": "Need to pass 'description'"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task Not found"}, 404
    
@task_ns.route('/<tid>/edit_subtask/<sid>', methods=['POST'])
@task_ns.doc(description='Edit a subtask')
class EditSubtask(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={
        'description': 'Required. Description of the subtask'
    })
    def post(self, tid, sid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if "description" in request.json:
                    subtask = TaskModel.edit_subtask(tid, sid, request.json["description"], current_user)
                    if subtask:
                        return {"message": f"Subtask edited"}, 200 
                return {"message": "Need to pass 'description'"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task Not found"}, 404
    
@task_ns.route('/<tid>/list_subtasks', methods=['GET'])
@task_ns.doc(description='List subtasks of a task')
class ListSubtask(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            if not check_user_private_case(CommonModel.get_case(task.case_id), request.headers):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
            return {"subtasks": [subtask.to_json() for subtask in task.subtasks]}, 200
        return {"message": "Task Not found"}, 404
    
@task_ns.route('/<tid>/subtask/<sid>', methods=['GET'])
@task_ns.doc(description='Get a subtask of a task')
class GetSubtask(Resource):
    method_decorators = [api_required]
    def get(self, tid, sid):
        task = CommonModel.get_task(tid)
        if task:
            if not check_user_private_case(CommonModel.get_case(task.case_id), request.headers):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
            subtask = TaskModel.get_subtask(sid)
            if subtask:
                return subtask.to_json()
        return {"message": "Task Not found"}, 404
    
@task_ns.route('/<tid>/complete_subtask/<sid>', methods=['GET'])
@task_ns.doc(description='Complete a subtask')
class CompleteSubtask(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, tid, sid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.complete_subtask(tid, sid, current_user):
                    return {"message": "Subtask completed"}, 200
                return {"message": "Subtask not found"}, 404
            return {"message": "Permission denied"}, 403
        return {"message": "Task Not found"}, 404
    
@task_ns.route('/<tid>/delete_subtask/<sid>', methods=['GET'])
@task_ns.doc(description='Delete a subtask')
class DeleteSubtask(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, tid, sid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.delete_subtask(tid, sid, current_user):
                    return {"message": "Subtask deleted"}, 200
                return {"message": "Subtask not found"}, 404
            return {"message": "Permission denied"}, 403
        return {"message": "Task Not found"}, 404
    

##############
# Urls/Tools #
##############

@task_ns.route('/<tid>/create_url_tool', methods=['POST'])
@task_ns.doc(description='Create a Url/Tool')
class CreateUrlTool(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={
        'name': 'Required. name of the url or tool'
    })
    def post(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if "name" in request.json:
                    url_tool = TaskModel.create_url_tool(tid, request.json["name"], current_user)
                    if url_tool:
                        return {"message": f"Url/Tool created, id: {url_tool.id}", "url_tool_id": url_tool.id}, 201 
                return {"message": "Need to pass 'name'"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task Not found"}, 404
    
@task_ns.route('/<tid>/edit_url_tool/<sid>', methods=['POST'])
@task_ns.doc(description='Edit a Url/Tool')
class EditUrlTool(Resource):
    method_decorators = [editor_required, api_required]
    @task_ns.doc(params={
        'name': 'Required. name of the url or tool'
    })
    def post(self, tid, sid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if "name" in request.json:
                    url_tool = TaskModel.edit_url_tool(tid, sid, request.json["name"], current_user)
                    if url_tool:
                        return {"message": f"Url/Tool edited"}, 200 
                return {"message": "Need to pass 'name'"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Task Not found"}, 404
    
@task_ns.route('/<tid>/list_urls_tools', methods=['GET'])
@task_ns.doc(description='List Urls/Tools of a task')
class ListUrlsTools(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task(tid)
        if task:
            if not check_user_private_case(CommonModel.get_case(task.case_id), request.headers):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
            return {"urls_tools": [url_tool.to_json() for url_tool in task.urls_tools]}, 200
        return {"message": "Task Not found"}, 404
    
@task_ns.route('/<tid>/url_tool/<utid>', methods=['GET'])
@task_ns.doc(description='Get a Url/Tool of a task')
class GetUrlTool(Resource):
    method_decorators = [api_required]
    def get(self, tid, utid):
        task = CommonModel.get_task(tid)
        if task:
            if not check_user_private_case(CommonModel.get_case(task.case_id), request.headers):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
            url_tool = TaskModel.get_url_tool(utid)
            if url_tool:
                return url_tool.to_json()
        return {"message": "Task Not found"}, 404
    
@task_ns.route('/<tid>/delete_url_tool/<utid>', methods=['GET'])
@task_ns.doc(description='Delete a Url/Tool')
class DeleteUrlTool(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, tid, utid):
        task = CommonModel.get_task(tid)
        if task:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if TaskModel.delete_url_tool(tid, utid, current_user):
                    return {"message": "Url/Tool deleted"}, 200
                return {"message": "Url/Tool not found"}, 404
            return {"message": "Permission denied"}, 403
        return {"message": "Task Not found"}, 404
    