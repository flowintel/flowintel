import ast
from flask import Blueprint, render_template, redirect, jsonify, request, flash

from app.db_class.db import Case
from .form import TaskEditForm, TaskForm
from flask_login import login_required, current_user
from .CaseCore import CaseModel
from . import common_core as CommonModel
from .TaskCore import TaskModel
from ..decorators import editor_required
from ..utils.utils import form_to_dict
from ..utils.formHelper import prepare_tags

task_blueprint = Blueprint(
    'task',
    __name__,
    template_folder='templates',
    static_folder='static'
)


def check_user_private_case(case: Case, present_in_case: bool = None) -> bool:
    if not present_in_case:
        present_in_case = CommonModel.get_present_in_case(case.id, current_user)
    if case.is_private and not present_in_case and not current_user.is_admin():
        return False
    return True


@task_blueprint.route("/<cid>/create_task", methods=['GET', 'POST'])
@login_required
def create_task(cid):
    """View of a case"""
    if CommonModel.get_case(cid):
        present_in_case = CommonModel.get_present_in_case(cid, current_user)
        if present_in_case or current_user.is_admin():
            form = TaskForm()
            form.template_select.choices = [(template.id, template.title) for template in CommonModel.get_task_templates()]
            form.template_select.choices.insert(0, (0," "))

            if form.validate_on_submit():
                res = prepare_tags(request)
                if isinstance(res, dict):
                    form_dict = form_to_dict(form)
                    form_dict.update(res)
                    if TaskModel.create_task(form_dict, cid, current_user):
                        flash("Task created", "success")
                    else:
                        flash("Error Task Created", "error")
                    return redirect(f"/case/{cid}")
                return render_template("case/create_task.html", form=form)
            return render_template("case/create_task.html", form=form)
        return redirect(f"/case/{cid}")
    return render_template("404.html")

@task_blueprint.route("/<cid>/edit_task/<tid>", methods=['GET','POST'])
@login_required
@editor_required
def edit_task(cid, tid):
    """Edit the task"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            form = TaskEditForm()

            if form.validate_on_submit():
                res = prepare_tags(request)
                if isinstance(res, dict):
                    form_dict = form_to_dict(form)
                    form_dict.update(res)
                    TaskModel.edit_task_core(form_dict, tid, current_user)
                    flash("Task edited", "success")
                    return redirect(f"/case/{cid}")
                return render_template("case/edit_task.html", form=form)
            else:
                task_modif = CommonModel.get_task(tid)
                form.description.data = task_modif.description
                form.title.data = task_modif.title
                form.time_required.data = task_modif.time_required
                form.deadline_date.data = task_modif.deadline
                form.deadline_time.data = task_modif.deadline
            
            return render_template("case/edit_task.html", form=form)
        else:
            flash("Access denied", "error")
        return redirect(f"/case/{cid}")
    return render_template("404.html")


@task_blueprint.route("/complete_task/<tid>", methods=['GET'])
@login_required
@editor_required
def complete_task(tid):
    """Complete the task"""
    task = CommonModel.get_task(str(tid))
    if task:
        if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
            if TaskModel.complete_task(tid, current_user):
                return {"message": "Task completed", "toast_class": "success-subtle"}, 200
            return {"message": "Error task completed", "toast_class": "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    


@task_blueprint.route("/<cid>/delete_task/<tid>", methods=['GET'])
@login_required
@editor_required
def delete_task(cid, tid):
    """Delete the task"""
    if CommonModel.get_case(cid):
        if CommonModel.get_task(tid):
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if TaskModel.delete_task(tid, current_user):
                    return {"message": "Task deleted", "toast_class": "success-subtle"}, 200
                return {"message": "Error task deleted", "toast_class": "danger-subtle"}, 400
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
        return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/modif_note/<tid>", methods=['POST'])
@login_required
@editor_required
def modif_note(cid, tid):
    """Modify note of the task"""
    if CommonModel.get_case(cid):
        if CommonModel.get_task(tid):
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                notes = request.json["notes"]
                if "note_id" in request.args:
                    res_note = TaskModel.modif_note_core(tid, current_user, notes, request.args.get("note_id"))
                    if res_note and not type(res_note) == dict:
                        return {"note": res_note.to_json(), "message": "Note added", "toast_class": "success-subtle"}, 200
                    return {"message": "Error add/modify note", "toast_class": "danger-subtle"}, 400
                return {"message": "Need to pass a note id", "toast_class": "warning-subtle"}, 400
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
        return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

@task_blueprint.route("/<cid>/create_note/<tid>", methods=['GET'])
@login_required
@editor_required
def create_note(cid, tid):
    """Create note"""
    if CommonModel.get_case(cid):
        if CommonModel.get_task(tid):
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                res_note = TaskModel.create_note(tid, current_user)
                if res_note:
                    return {"note": res_note.to_json(), "message": "Note created", "toast_class": "success-subtle"}, 200
                return {"message": "Error create note", "toast_class": "danger-subtle"}, 400
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
        return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

@task_blueprint.route("/<cid>/delete_note/<tid>", methods=['GET'])
@login_required
@editor_required
def delete_note(cid, tid):
    """Create note"""
    if CommonModel.get_case(cid):
        if CommonModel.get_task(tid):
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if "note_id" in request.args:
                    if TaskModel.delete_note(tid, request.args.get("note_id"), current_user):
                        return {"message": "Note deleted", "toast_class": "success-subtle"}, 200
                    return {"message": "Error delete note", "toast_class": "danger-subtle"}, 400
                return {"message": "Need to pass a note id", "toast_class": "warning-subtle"}, 400
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
        return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/get_note/<tid>", methods=['GET'])
@login_required
def get_note(cid, tid):
    """Get not of a task in text format"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "permission denied", 'toast_class': "danger-subtle"}, 403
        
        task = CommonModel.get_task(tid)
        if task:
            if "note_id" in request.args:
                task_note = CommonModel.get_task_note(request.args.get("note_id"))
                return {"note": task_note.note}, 200
            return {"message": "Need to pass a note id", "toast_class": "warning-subtle"}, 400
        return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/take_task/<tid>", methods=['GET'])
@login_required
@editor_required
def take_task(cid, tid):
    """Assign current user to the task"""
    if CommonModel.get_case(cid):
        if CommonModel.get_task(tid):
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if TaskModel.assign_task(tid, user=current_user, current_user=current_user, flag_current_user=True):
                    return {"message": "User Assigned", "toast_class": "success-subtle"}, 200
                return {"message": "Error assignment", "toast_class": "danger-subtle"}, 400
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
        return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404
    

@task_blueprint.route("/<cid>/assign_users/<tid>", methods=['POST'])
@login_required
@editor_required
def assign_user(cid, tid):
    """Assign a list of users to the task"""
    if CommonModel.get_case(cid):
        if "users_id" in request.json:
            users_list = request.json["users_id"]

            if CommonModel.get_task(tid):
                if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    for user in users_list:
                        TaskModel.assign_task(tid, user=user, current_user=current_user, flag_current_user=False)
                    return {"message": "Users Assigned", "toast_class": "success-subtle"}, 200
                return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
            return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
        return {"message": "'users_id' is missing", "toast_class": "danger-subtle"}, 400
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/remove_assignment/<tid>", methods=['GET'])
@login_required
@editor_required
def remove_assign_task(cid, tid):
    """Remove current user assignment to the task"""
    if CommonModel.get_case(cid):
        if CommonModel.get_task(tid):
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if TaskModel.remove_assign_task(tid, user=current_user, current_user=current_user, flag_current_user=True):
                    return {"message": "User Removed from assignment", "toast_class": "success-subtle"}, 200
                return {"message": "Error removed assignment", "toast_class": "danger-subtle"}, 400
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
        return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/remove_assigned_user/<tid>", methods=['POST'])
@login_required
@editor_required
def remove_assigned_user(cid, tid):
    """Assign current user to the task"""
    if CommonModel.get_case(cid):
        if "user_id" in request.json:
            user_id = request.json["user_id"]
            if CommonModel.get_task(tid):
                if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    if TaskModel.remove_assign_task(tid, user=user_id, current_user=current_user, flag_current_user=False):
                        return {"message": "User Removed from assignment", "toast_class": "success-subtle"}, 200
                    return {"message": "Error removed assignment", "toast_class": "danger-subtle"}, 400
                return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
            return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
        return {"message": "'user_id' is missing", "toast_class": "danger-subtle"}, 400
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/change_task_status/<tid>", methods=['POST'])
@login_required
@editor_required
def change_task_status(cid, tid):
    """Change the status of the task"""
    if CommonModel.get_case(cid):
        if "status" in request.json:
            status = request.json["status"]
            task = CommonModel.get_task(tid)
            if task:
                if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    if TaskModel.change_task_status(status, task, current_user):
                        return {"message": "Status changed", "toast_class": "success-subtle"}, 200
                    return {"message": "Error changed status", "toast_class": "danger-subtle"}, 400
                return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
            return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
        return {"message": "'status' is missing", "toast_class": "danger-subtle"}, 400
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/task/<tid>/download_file/<fid>", methods=['GET'])
@login_required
@editor_required
def download_file(tid, fid):
    """Download the file"""
    task = CommonModel.get_task(tid)
    file = CommonModel.get_file(fid)
    if file and file in task.files:
        if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
            return TaskModel.download_file(file)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "File not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/task/<tid>/delete_file/<fid>", methods=['GET'])
@login_required
@editor_required
def delete_file(tid, fid):
    """Delete the file"""
    task = CommonModel.get_task(tid)
    file = CommonModel.get_file(fid)
    if file and file in task.files:
        if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
            if TaskModel.delete_file(file, task, current_user):
                return {"message": "File Deleted", "toast_class": "success-subtle"}, 200
            return {"message": "Error deleting file", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "File not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/add_files/<tid>", methods=['POST'])
@login_required
@editor_required
def add_files(cid, tid):
    """Add files to a task"""
    if CommonModel.get_case(cid):
        task = CommonModel.get_task(tid)
        if task:
            if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
                if len(request.files) > 0:
                    if TaskModel.add_file_core(task=task, files_list=request.files, current_user=current_user):
                        return {"message":"Files added", "toast_class": "success-subtle"}, 200
                    return {"message":"Something goes wrong adding files", "toast_class": "danger-subtle"}, 400
                return {"message":"No Files given", "toast_class": "warning-subtle"}, 400
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
        return {"message":"Task not found", "toast_class": "danger-subtle"}, 404
    return {"message":"Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/get_files/<tid>", methods=['GET'])
@login_required
@editor_required
def get_files(cid, tid):
    """Get files of a task"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        task = CommonModel.get_task(tid)
        if task:
            file_list = [file.to_json() for file in task.files]
            return {"files": file_list}, 200
        return {"message":"Task not found", "toast_class": "danger-subtle"}, 404
    return {"message":"Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/sort_tasks", methods=['GET'])
@login_required
def sort_tasks(cid):
    """Sort Tasks"""
    case = CommonModel.get_case(cid)

    if not check_user_private_case(case):
        return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
    
    filter = request.args.get('filter')
    status = request.args.get('status')
    tags = request.args.get('tags')
    taxonomies = request.args.get('taxonomies')
    or_and_taxo = request.args.get("or_and_taxo")

    galaxies = request.args.get('galaxies')
    clusters = request.args.get('clusters')
    or_and_galaxies = request.args.get("or_and_galaxies")

    custom_tags = request.args.get('custom_tags')

    if status == 'true':
        status = True
    elif status == 'false' or not status:
        status = False

    if tags:
        tags = ast.literal_eval(tags)
    if taxonomies:
        taxonomies = ast.literal_eval(taxonomies)

    if galaxies:
        galaxies = ast.literal_eval(galaxies)
    if clusters:
        clusters = ast.literal_eval(clusters)

    if custom_tags:
        custom_tags = ast.literal_eval(custom_tags)

    return TaskModel.sort_tasks(case, 
                                current_user, 
                                taxonomies, 
                                galaxies, 
                                tags, 
                                clusters,
                                custom_tags,
                                or_and_taxo, or_and_galaxies, 
                                completed=status,
                                filter=filter)


@task_blueprint.route("/<cid>/task/<tid>/notify_user", methods=['POST'])
@login_required
@editor_required
def notify_user(cid, tid):
    """Notify a user about a task"""
    if CommonModel.get_case(cid):
        if "user_id" in request.json:
            user = request.json["user_id"]
            task = CommonModel.get_task(tid)
            if task:
                if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    if CaseModel.notify_user(task, user):
                        return {"message":"User notified", "toast_class": "success-subtle"}, 200
                    return {"message":"Something goes wrong", "toast_class": "danger-subtle"}, 400
                return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
            return {"message":"Task not found", "toast_class": "danger-subtle"}, 404
        return {"message": "'user_id' is missing", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/task/<tid>/export_notes", methods=['GET'])
@login_required
def export_notes(cid, tid):
    """Export note of a task"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        if CommonModel.get_task(tid):
            if "type" in request.args:
                if "note_id" in request.args:
                    type_req = request.args.get("type")
                    note_id = request.args.get("note_id")
                    res = CommonModel.export_notes(case_task=False, case_task_id=tid, type_req=type_req, note_id=note_id)
                    CommonModel.delete_temp_folder()
                    return res
                return {"message": "'note_id' is missing", 'toast_class': "warning-subtle"}, 400
            return {"message": "'type' is missing", 'toast_class': "warning-subtle"}, 400
        return {"message": "Task not found", 'toast_class': "danger-subtle"}, 404
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@task_blueprint.route("/get_taxonomies_task/<tid>", methods=['GET'])
@login_required
def get_taxonomies_task(tid):
    """Get all taxonomies for a task"""
    task = CommonModel.get_task(tid)
    if task:
        if not check_user_private_case(CommonModel.get_case(task.case_id)):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        tags = CommonModel.get_task_tags_json(tid)
        taxonomies = []
        if tags:
            for tag in tags:
                if not tag["name"].split(":")[0] in taxonomies:
                    taxonomies.append(tag["name"].split(":")[0])
        return {"tags": tags, "taxonomies": taxonomies}
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@task_blueprint.route("/get_galaxies_task/<tid>", methods=['GET'])
@login_required
def get_galaxies_task(tid):
    """Get all galaxies for a task"""
    task = CommonModel.get_task(tid)
    if task:
        if not check_user_private_case(CommonModel.get_case(task.case_id)):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        clusters = CommonModel.get_task_clusters(tid)
        galaxies = []
        if clusters:
            for cluster in clusters:
                loc_g = CommonModel.get_galaxy(cluster.galaxy_id)
                if not loc_g in galaxies:
                    galaxies.append(loc_g.to_json())
                index = clusters.index(cluster)
                clusters[index] = cluster.to_json()
        return {"clusters": clusters, "galaxies": galaxies}
    return {"message": "task Not found", 'toast_class': "danger-subtle"}, 404


@task_blueprint.route("/<cid>/change_order/<tid>", methods=["GET",'POST'])
@login_required
@editor_required
def change_order(cid, tid):
    """Change the order of tasks"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            task = CommonModel.get_task(tid)
            if task:
                if task.case_id == case.id:
                    TaskModel.change_order(case, task, request.json)
                    return {"message": "Order changed", 'toast_class': "success-subtle"}, 200
                return {"message": "Task not in this case", 'toast_class': "danger-subtle"}, 400
            return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@task_blueprint.route("/get_task_modules", methods=['GET'])
@login_required
def get_task_modules():
    """Get all modules"""
    return {"modules": CommonModel.get_modules_by_case_task('task')}, 200

@task_blueprint.route("/<cid>/task/<tid>/get_instance_module", methods=['GET'])
@login_required
def get_instance_module(cid, tid):
    """Get all connectors instances by modules"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        if CommonModel.get_task(tid):
            if "module" in request.args:
                module = request.args.get("module")
            if "type" in request.args:
                type_module = request.args.get("type")
            else:
                return{"message": "Module type error", 'toast_class': "danger-subtle"}, 400
            return {"instances": TaskModel.get_instance_module_core(module, type_module, tid, current_user.id)}, 200
        return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404

@task_blueprint.route("/<cid>/task/<tid>/call_module_task", methods=['GET', 'POST'])
@login_required
@editor_required
def call_module_task(cid, tid):
    """Run a module"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            task = CommonModel.get_task(tid)
            if task:
                task_instance_id = request.get_json()["case_task_instance_id"]
                module = request.get_json()["module"]
                res = TaskModel.call_module_task(module, task_instance_id, case, task, current_user)
                if res:
                    res["toast_class"] = "danger-subtle"
                    return jsonify(res), 400
                return {"message": "Connector used", 'toast_class': "success-subtle"}, 200
            return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message":"Case not found", "toast_class": "danger-subtle"}, 404

@task_blueprint.route("/<cid>/task/<tid>/call_module_task_no_instance", methods=['GET', 'POST'])
@login_required
def call_module_task_no_instance(cid, tid):
    """Run a module"""
    case = CommonModel.get_case(cid)
    if not check_user_private_case(case):
        return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
    
    task = CommonModel.get_task(tid)
    if task:
        module = request.args.get("module")
        user_id = request.args.get("user_id")
        res = TaskModel.call_module_task_no_instance(module, task, case, current_user, user_id)
        if res:
            res["toast_class"] = "danger-subtle"
            return jsonify(res), 400
        return {"message": "Module used", 'toast_class': "success-subtle"}, 200
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@task_blueprint.route("/get_custom_tags_task/<tid>", methods=['GET'])
@login_required
def get_custom_tags_task(tid):
    """Get all custom tags for a task"""
    task = CommonModel.get_task(tid)
    if task:
        if not check_user_private_case(CommonModel.get_case(task.case_id)):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        return {"custom_tags": CommonModel.get_task_custom_tags_json(tid)}, 200
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404




##############
# Urls/Tools #
##############

@task_blueprint.route("/<cid>/task/<tid>/create_url_tool", methods=['POST'])
@login_required
@editor_required
def create_url_tool(cid,tid):
    """Create a new Url/Tool"""
    task = CommonModel.get_task(tid)
    if task:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "name" in request.json:
                url_tool = TaskModel.create_url_tool(tid, request.json["name"], current_user)
                if url_tool:
                    return {"message": f"Url/Tool created", "id": url_tool.id, 'toast_class': "success-subtle", "icon": "fas fa-plus"}, 200 
                return {"message": "Error creating Url/Tool", 'toast_class': "danger-subtle"}, 400
            return {"message": "Need to pass 'name", 'toast_class': "warning-subtle"}, 400
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@task_blueprint.route("/<cid>/task/<tid>/edit_url_tool/<utid>", methods=['POST'])
@login_required
@editor_required
def edit_url_tool(cid, tid, utid):
    """Edit a Url/Tool"""
    task = CommonModel.get_task(tid)
    if task:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "name" in request.json:
                if TaskModel.edit_url_tool(tid, utid, request.json["name"], current_user):
                    return {"message": "Url/Tool edited", 'toast_class': "success-subtle"}, 200 
                return {"message": "Url/Tool not found", 'toast_class': "danger-subtle"}, 404
            return {"message": "Need to pass 'name", 'toast_class': "warning-subtle"}, 400
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@task_blueprint.route("/<cid>/task/<tid>/delete_url_tool/<utid>", methods=['GET'])
@login_required
@editor_required
def delete_url_tool(cid, tid, utid):
    """Delete a Url/Tool"""
    task = CommonModel.get_task(tid)
    if task:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if TaskModel.delete_url_tool(tid, utid, current_user):
                return {"message": "Url/Tool deleted", 'toast_class': "success-subtle", "icon": "fas fa-trash"}, 200 
            return {"message": "Url/Tool not found", 'toast_class': "danger-subtle"}, 404
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404


###########
# Subtask #
###########

@task_blueprint.route("/<cid>/task/<tid>/create_subtask", methods=['POST'])
@login_required
@editor_required
def create_subtask(cid,tid):
    """Create a new subtask"""
    task = CommonModel.get_task(tid)
    if task:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "description" in request.json:
                subtask = TaskModel.create_subtask(tid, request.json["description"], current_user)
                if subtask:
                    return {"message": f"Subtask created", "id": subtask.id, 'toast_class': "success-subtle", "icon": "fas fa-plus"}, 200 
                return {"message": "Error creating subtask", 'toast_class': "danger-subtle"}, 400
            return {"message": "Need to pass 'description", 'toast_class': "warning-subtle"}, 400
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@task_blueprint.route("/<cid>/task/<tid>/edit_subtask/<sid>", methods=['POST'])
@login_required
@editor_required
def edit_subtask(cid, tid, sid):
    """Edit a subtask"""
    task = CommonModel.get_task(tid)
    if task:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "description" in request.json:
                if TaskModel.edit_subtask(tid, sid, request.json["description"], current_user):
                    return {"message": "Subtask edited", 'toast_class': "success-subtle"}, 200 
                return {"message": "Subtask not found", 'toast_class': "danger-subtle"}, 404
            return {"message": "Need to pass 'description", 'toast_class': "warning-subtle"}, 400
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@task_blueprint.route("/<cid>/task/<tid>/complete_subtask/<sid>", methods=['GET'])
@login_required
@editor_required
def complete_subtask(cid, tid, sid):
    """Complete a subtask"""
    task = CommonModel.get_task(tid)
    if task:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if TaskModel.complete_subtask(tid, sid, current_user):
                return {"message": "Subtask completed", 'toast_class': "success-subtle"}, 200 
            return {"message": "Subtask not found", 'toast_class': "danger-subtle"}, 404
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@task_blueprint.route("/<cid>/task/<tid>/delete_subtask/<sid>", methods=['GET'])
@login_required
@editor_required
def delete_subtask(cid, tid, sid):
    """Delete a subtask"""
    task = CommonModel.get_task(tid)
    if task:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if TaskModel.delete_subtask(tid, sid, current_user):
                return {"message": "Subtask deleted", 'toast_class': "success-subtle", "icon": "fas fa-trash"}, 200 
            return {"message": "Subtask not found", 'toast_class': "danger-subtle"}, 404
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@task_blueprint.route("/<cid>/task/<tid>/change_order_subtask/<sid>", methods=['GET'])
@login_required
@editor_required
def change_order_subtask(cid, tid, sid):
    """Change the order of tasks"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            task = CommonModel.get_task(tid)
            if task:
                subtask = TaskModel.get_subtask(sid)
                if subtask:
                    up_down = None
                    if "up_down" in request.args:
                        up_down = request.args.get("up_down")
                        TaskModel.change_order_subtask(task, subtask, up_down)
                        return {"message": "Order changed", 'toast_class': "success-subtle"}, 200
                    return {"message": "Need to pass up_down", 'toast_class': "danger-subtle"}, 400
                return {"message": "Subtask Not found", 'toast_class': "danger-subtle"}, 404
            return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


##############
# Connectors #
##############

@task_blueprint.route("/get_connectors", methods=['GET'])
@login_required
def get_connectors():
    """Get all connectors and instances"""
    connectors_list = CommonModel.get_connectors()
    connectors_dict = dict()
    for connector in connectors_list:
        loc = list()
        for instance in connector.instances:
            if CommonModel.get_user_instance_both(user_id=current_user.id, instance_id=instance.id):
                loc.append(instance.to_json())
        if loc:
            connectors_dict[connector.name] = loc
    
    return jsonify({"connectors": connectors_dict}), 200

@task_blueprint.route("/get_task_connectors/<tid>", methods=['GET'])
@login_required
def get_task_connectors(tid):
    """Get all connectors for a task"""
    task = CommonModel.get_task(tid)
    if task:
        if not check_user_private_case(CommonModel.get_case(task.case_id)):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        instance_list = list()
        for task_connector in CommonModel.get_task_connectors(tid):
            instance_list.append({
                "case_task_instance_id": task_connector.id,
                "details": CommonModel.get_instance_with_icon(task_connector.instance_id),
                "identifier": task_connector.identifier
            })
        return {"task_connectors": instance_list}, 200
    return {"message": "Task not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/task/<tid>/add_connector", methods=['POST'])
@login_required
@editor_required
def add_connector(tid):
    """Add Connector"""
    task = CommonModel.get_task(tid)
    if task:
        if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
            if "connectors" in request.json:
                if TaskModel.add_connector(tid, request.json, current_user):
                    return {"message": "Connector added successfully", "toast_class": "success-subtle"}, 200
            return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Task not found", 'toast_class': "danger-subtle"}, 404

@task_blueprint.route("/task/<tid>/remove_connector/<ciid>", methods=['GET'])
@login_required
@editor_required
def remove_connector(tid, ciid):
    """Remove a connector from task"""
    task = CommonModel.get_task(tid)
    if task:
        if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
            if TaskModel.remove_connector(ciid):
                return {"message": "Connector removed", 'toast_class': "success-subtle"}, 200
            return {"message": "Something went wrong", 'toast_class': "danger-subtle"}, 400
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Task not found", 'toast_class': "danger-subtle"}, 404

@task_blueprint.route("/task/<tid>/edit_connector/<ciid>", methods=['POST'])
@login_required
@editor_required
def edit_connector(tid, ciid):
    """Edit Connector"""
    task = CommonModel.get_task(tid)
    if task:
        if CommonModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
            if "identifier" in request.json:
                if TaskModel.edit_connector(ciid, request.json):
                    return {"message": "Connector edited successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Error editing connector", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400
        return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Task not found", 'toast_class': "danger-subtle"}, 404

