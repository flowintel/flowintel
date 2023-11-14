from flask import Blueprint, render_template, redirect, jsonify, request, flash
from .form import TaskEditForm, TaskForm
from flask_login import login_required, current_user
from . import case_core as CaseModel
from . import common_core as CommonModel
from . import task_core as TaskModel
from ..decorators import editor_required
from ..utils.utils import form_to_dict, check_tag
from ..db_class.db import Task_Template

task_blueprint = Blueprint(
    'task',
    __name__,
    template_folder='templates',
    static_folder='static'
)


@task_blueprint.route("/<cid>/create_task", methods=['GET', 'POST'])
@login_required
def create_task(cid):
    """View of a case"""
    if CommonModel.get_case(cid):
        present_in_case = CaseModel.get_present_in_case(cid, current_user)
        if present_in_case or current_user.is_admin():
            form = TaskForm()
            form.template_select.choices = [(template.id, template.title) for template in Task_Template.query.all()]
            form.template_select.choices.insert(0, (0," "))

            if form.validate_on_submit():
                if "tags_select" in request.form:
                    flag = True
                    tag_list = request.form.getlist("tags_select")
                    for tag in tag_list:
                        if not check_tag(tag):
                            flag = False
                    if not flag:
                        flash("tag doesn't exist")
                        return render_template("case/create_task.html", form=form)
                form_dict = form_to_dict(form)
                form_dict["tags"] = tag_list
                if TaskModel.create_task(form_dict, cid, current_user):
                    flash("Task created", "success")
                else:
                    flash("Error Task Created", "error")
                return redirect(f"/case/{cid}")
            return render_template("case/create_task.html", form=form)
        return redirect(f"/case/{cid}")
    return render_template("404.html")

@task_blueprint.route("/<cid>/edit_task/<tid>", methods=['GET','POST'])
@login_required
@editor_required
def edit_task(cid, tid):
    """Edit the task"""
    if CommonModel.get_case(cid):
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            form = TaskEditForm()

            if form.validate_on_submit():
                if "tags_select" in request.form:
                    flag = True
                    tag_list = request.form.getlist("tags_select")
                    for tag in tag_list:
                        if not check_tag(tag):
                            flag = False
                    if not flag:
                        flash("tag doesn't exist")
                        return render_template("case/edit_task.html", form=form)
                form_dict = form_to_dict(form)
                form_dict["tags"] = tag_list
                TaskModel.edit_task_core(form_dict, tid, current_user)
                flash("Task edited", "success")
                return redirect(f"/case/{cid}")
            else:
                task_modif = CommonModel.get_task(tid)
                form.description.data = task_modif.description
                form.title.data = task_modif.title
                form.url.data = task_modif.url
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
        if CaseModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
            if TaskModel.complete_task(tid, current_user):
                return {"message": "Task completed", "toast_class": "success-subtle"}, 200
            return {"message": "Error task completed", "toast_class": "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
    return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    


@task_blueprint.route("/<cid>/delete_task/<tid>", methods=['GET'])
@login_required
@editor_required
def delete_task(cid, tid):
    """Delete the task"""
    if CommonModel.get_case(cid):
        if CommonModel.get_task(tid):
            if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if TaskModel.delete_task(tid, current_user):
                    return {"message": "Task deleted", "toast_class": "success-subtle"}, 200
                return {"message": "Error task deleted", "toast_class": "danger-subtle"}, 400
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
        return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/modif_note/<tid>", methods=['POST'])
@login_required
@editor_required
def modif_note(cid, tid):
    """Modify note of the task"""
    if CommonModel.get_case(cid):
        if CommonModel.get_task(tid):
            if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                notes = request.json["notes"]
                if TaskModel.modif_note_core(tid, current_user, notes):
                    return {"message": "Note added", "toast_class": "success-subtle"}, 200
                return {"message": "Error add/modify note", "toast_class": "danger-subtle"}, 400
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
        return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/get_note/<tid>", methods=['GET'])
@editor_required
def get_note(cid, tid):
    """Get not of a task in text format"""
    if CommonModel.get_case(cid):
        task = CommonModel.get_task(tid)
        if task:
            return {"note": task.notes}, 201
        return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/take_task/<tid>", methods=['GET'])
@login_required
@editor_required
def take_task(cid, tid):
    """Assign current user to the task"""
    if CommonModel.get_case(cid):
        if CommonModel.get_task(tid):
            if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if TaskModel.assign_task(tid, user=current_user, current_user=current_user, flag_current_user=True):
                    return {"message": "User Assigned", "toast_class": "success-subtle"}, 200
                return {"message": "Error assignment", "toast_class": "danger-subtle"}, 400
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
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
                if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    for user in users_list:
                        TaskModel.assign_task(tid, user=user, current_user=current_user, flag_current_user=False)
                    return {"message": "Users Assigned", "toast_class": "success-subtle"}, 200
                return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
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
            if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if TaskModel.remove_assign_task(tid, user=current_user, current_user=current_user, flag_current_user=True):
                    return {"message": "User Removed from assignment", "toast_class": "success-subtle"}, 200
                return {"message": "Error removed assignment", "toast_class": "danger-subtle"}, 400
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
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
                if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    if TaskModel.remove_assign_task(tid, user=user_id, current_user=current_user, flag_current_user=False):
                        return {"message": "User Removed from assignment", "toast_class": "success-subtle"}, 200
                    return {"message": "Error removed assignment", "toast_class": "danger-subtle"}, 400
                return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
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
                if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    if TaskModel.change_task_status(status, task, current_user):
                        return {"message": "Status changed", "toast_class": "success-subtle"}, 200
                    return {"message": "Error changed status", "toast_class": "danger-subtle"}, 400
                return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
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
        if CaseModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
            return TaskModel.download_file(file)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
    return {"message": "File not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/task/<tid>/delete_file/<fid>", methods=['GET'])
@login_required
@editor_required
def delete_file(tid, fid):
    """Delete the file"""
    task = CommonModel.get_task(tid)
    file = CommonModel.get_file(fid)
    if file and file in task.files:
        if CaseModel.get_present_in_case(task.case_id, current_user) or current_user.is_admin():
            if TaskModel.delete_file(file, task, current_user):
                return {"message": "File Deleted", "toast_class": "success-subtle"}, 200
            return {"message": "Error deleting file"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
    return {"message": "File not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/add_files/<tid>", methods=['POST'])
@login_required
@editor_required
def add_files(cid, tid):
    """Add files to a task"""
    if CommonModel.get_case(cid):
        task = CommonModel.get_task(tid)
        if task:
            if len(request.files) > 0:
                if TaskModel.add_file_core(task=task, files_list=request.files, current_user=current_user):
                    return {"message":"Files added", "toast_class": "success-subtle"}, 200
                return {"message":"Something goes wrong adding files", "toast_class": "danger-subtle"}, 400
            return {"message":"No Files given", "toast_class": "warning-subtle"}, 400
        return {"message":"Task not found", "toast_class": "danger-subtle"}, 404
    return {"message":"Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/get_files/<tid>", methods=['GET'])
@login_required
@editor_required
def get_files(cid, tid):
    """Get files of a task"""
    if CommonModel.get_case(cid):
        task = CommonModel.get_task(tid)
        if task:
            file_list = [file.to_json() for file in task.files]
            return {"files": file_list}, 200
        return {"message":"Task not found", "toast_class": "danger-subtle"}, 404
    return {"message":"Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/sort_by_ongoing_task", methods=['GET'])
@login_required
def sort_by_ongoing_task(cid):
    """Sort Task by living one"""
    if "tags" in request.args:
        tags = request.args.get('tags')
    else:
        tags = []
    case = CommonModel.get_case(cid)
    return TaskModel.sort_by_ongoing_task_core(case, current_user, tags)


@task_blueprint.route("/<cid>/sort_by_finished_task", methods=['GET'])
@login_required
def sort_by_finished_task(cid):
    """Sort task by finished one"""
    if "tags" in request.args:
        tags = request.args.get('tags')
    else:
        tags = []
    case = CommonModel.get_case(cid)
    return TaskModel.sort_by_finished_task_core(case, current_user, tags)


@task_blueprint.route("/<cid>/tasks/ongoing", methods=['GET'])
@login_required
def ongoing_tasks_sort_by_filter(cid):
    """Sort by filter for living task"""
    if "tags" in request.args:
        tags = request.args.get('tags')
    else:
        tags = []
    data_dict = dict(request.args)
    if "filter" in data_dict:
        case = CommonModel.get_case(cid)
        return TaskModel.sort_tasks_by_filter(case, current_user, False, data_dict["filter"], tags)
    return {"message": "No filter pass"}


@task_blueprint.route("/<cid>/tasks/finished", methods=['GET'])
@login_required
def finished_tasks_sort_by_filter(cid):
    """Sort by filter for finished task"""
    if "tags" in request.args:
        tags = request.args.get('tags')
    else:
        tags = []
    data_dict = dict(request.args)
    if "filter" in data_dict:
        case = CommonModel.get_case(cid)
        return TaskModel.sort_tasks_by_filter(case, current_user, True, data_dict["filter"], tags)
    return {"message": "No filter pass"}


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
                if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    if CaseModel.notify_user(task, user):
                        return {"message":"User notified", "toast_class": "success-subtle"}, 200
                    return {"message":"Something goes wrong", "toast_class": "danger-subtle"}, 400
                return {"message":"Action not Allowed", "toast_class": "warning-subtle"}, 400
            return {"message":"Task not found", "toast_class": "danger-subtle"}, 404
        return {"message": "'user_id' is missing", "toast_class": "danger-subtle"}, 404
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@task_blueprint.route("/<cid>/task/<tid>/export_notes", methods=['GET'])
@login_required
def export_notes(cid, tid):
    """Export note of a task as pdf"""

    case = CommonModel.get_case(cid)
    if case:
        task = CommonModel.get_task(tid)
        if task:
            data_dict = dict(request.args)
            if "type" in data_dict:
                type_req = data_dict["type"]
                res = TaskModel.export_notes(task, type_req)
                CommonModel.delete_temp_folder()
                return res
            return {"message": "'type' is missing", 'toast_class': "warning-subtle"}, 400
        return {"message": "Task not found", 'toast_class': "danger-subtle"}, 404
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@task_blueprint.route("/get_taxonomies_task/<tid>", methods=['GET'])
@login_required
def get_taxonomies_case(tid):
    task = CommonModel.get_task(tid)
    if task:
        tags = CommonModel.get_task_tags(task.id)
        taxonomies = []
        if tags:
            taxonomies = [tag.split(":")[0] for tag in tags]
        return {"tags": tags, "taxonomies": taxonomies}
    return {"message": "task Not found", 'toast_class': "danger-subtle"}, 404