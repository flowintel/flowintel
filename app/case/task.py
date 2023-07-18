from flask import Blueprint, render_template, redirect, jsonify, request, flash
from .form import TaskEditForm
from flask_login import login_required, current_user
from . import case_core as CaseModel
from ..decorators import editor_required
from ..utils.utils import form_to_dict

task_blueprint = Blueprint(
    'task',
    __name__,
    template_folder='templates',
    static_folder='static'
)



@task_blueprint.route("view/<case_id>/edit_task/<id>", methods=['GET','POST'])
@login_required
@editor_required
def edit_task(case_id, id):
    """Edit the task"""
    if CaseModel.get_present_in_case(case_id, current_user):
        form = TaskEditForm()

        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            CaseModel.edit_task_core(form_dict, id)
            flash("Task edited", "success")
            return redirect(f"/case/view/{case_id}")
        else:
            task_modif = CaseModel.get_task(id)
            form.description.data = task_modif.description
            form.title.data = task_modif.title
            form.url.data = task_modif.url
            form.dead_line_date.data = task_modif.dead_line
            form.dead_line_time.data = task_modif.dead_line
        
        return render_template("case/edit_task.html", form=form)
    else:
        flash("Access denied", "error")
    
    return redirect(f"/case/view/{case_id}")


@task_blueprint.route("/complete_task/<tid>", methods=['GET'])
@login_required
@editor_required
def complete_task(tid):
    """Complete the task"""

    task = CaseModel.get_task(str(tid))
    if CaseModel.get_present_in_case(task.case_id, current_user):
        if CaseModel.complete_task(tid):
            return {"message": "Task completed"}, 201
        else:
            return {"message": "Error task completed"}, 201
    return {"message": "Not in case"}


@task_blueprint.route("/delete_task", methods=['POST'])
@login_required
@editor_required
def delete_task():
    """Delete the task"""
    id = request.json["task_id"]
    task = CaseModel.get_task(id)
    if CaseModel.get_present_in_case(task.case_id, current_user):
        if CaseModel.delete_task(id):
            return {"message": "Task deleted"}, 201
        else:
            return {"message": "Error task deleted"}, 201
    return {"message": "Not in case"}


@task_blueprint.route("/modif_note", methods=['POST'])
@login_required
@editor_required
def modif_note():
    """Modify note of the task"""
    id = request.json["task_id"]

    task = CaseModel.get_task(id)
    if CaseModel.get_present_in_case(task.case_id, current_user):
        notes = request.json["notes"]
        
        if CaseModel.modif_note_core(id, notes):
            return {"message": "Note added"}, 201
        else:
            return {"message": "Error not added"}, 201

    return {"message": "Not in Case"}


@task_blueprint.route("/get_note_text", methods=['GET'])
@editor_required
def get_note_text():
    """Get not of a task in text format"""

    data_dict = dict(request.args)
    note = CaseModel.get_note_text(data_dict["id"])

    return {"note": note}, 201


@task_blueprint.route("/get_note_markdown", methods=['GET'])
def get_note_markdown():
    """Get not of a task in markdown format"""

    data_dict = dict(request.args)
    note = CaseModel.get_note_markdown(data_dict["id"])

    return {"note": note}, 201


@task_blueprint.route("/take_task", methods=['POST'])
@login_required
@editor_required
def take_task():
    """Assign current user to the task"""

    id = request.json["task_id"]

    task = CaseModel.get_task(id)
    if CaseModel.get_present_in_case(task.case_id, current_user):
        CaseModel.assign_task(id, current_user, flag_current_user=True)
        return {"message": "User Assigned"}, 201
    return {"message": "Not in Case"}


@task_blueprint.route("/remove_assign_task", methods=['POST'])
@login_required
@editor_required
def remove_assign_task():
    """Remove an assignment to the task"""
    
    id = request.json["task_id"]
    task = CaseModel.get_task(id)

    if CaseModel.get_present_in_case(task.case_id, current_user):
        CaseModel.remove_assign_task(id, current_user, flag_current_user=True)
        return {"message": "User Removed from assignment"}, 201
    return {"message": "Not in Case"}


@task_blueprint.route("/change_status/task/<tid>", methods=['POST'])
@login_required
@editor_required
def change_status_task(tid):
    """Change the status of the task"""
    
    status = request.json["status"]
    task = CaseModel.get_task(tid)

    if CaseModel.get_present_in_case(task.case_id, current_user):
        CaseModel.change_status_task(status, task)
        flash("Assignment changed", "success")
        return {"message": "Assignment changed"}, 201
    return {"message": "Not in Case"}


@task_blueprint.route("/task/<tid>/download_file/<fid>", methods=['GET'])
@login_required
@editor_required
def download_file(tid, fid):
    """Download the file"""
    task = CaseModel.get_task(tid)
    file = CaseModel.get_file(fid)
    if file and file in task.files:
        if CaseModel.get_present_in_case(task.case_id, current_user):
            return CaseModel.download_file(file.name)
        return {"message": "Not in Case"}
    return {"message": "File not found"}


@task_blueprint.route("/task/<tid>/delete_file/<fid>", methods=['GET'])
@login_required
@editor_required
def delete_file(tid, fid):
    """Delete the file"""
    task = CaseModel.get_task(tid)
    file = CaseModel.get_file(fid)
    if file and file in task.files:
        if CaseModel.get_present_in_case(task.case_id, current_user):
            if CaseModel.delete_file(file):
                return {"message": "File Deleted"}
            return {"message": "Error deleting file"}, 404
        return {"message": "Not in Case"}, 404
    return {"message": "File not found"}, 404


@task_blueprint.route("/add_files", methods=['POST'])
@login_required
@editor_required
def add_files():
    """Add files to a task"""
    if request.form.get("task_id"):
        
        task = CaseModel.get_task(request.form.get("task_id"))

        return_files_list = CaseModel.add_file_core(task=task, files_list=request.files)

        return return_files_list
    return []


@task_blueprint.route("/<cid>/sort_by_ongoing_task", methods=['GET'])
@login_required
def sort_by_ongoing_task(cid):
    """Sort Task by living one"""
    case = CaseModel.get_case(cid)
    if CaseModel.get_present_in_case(cid, current_user):
        return CaseModel.sort_by_ongoing_task_core(case, current_user)
    return {"message": "Not in Case"}


@task_blueprint.route("/<cid>/sort_by_finished_task", methods=['GET'])
@login_required
def sort_by_finished_task(cid):
    """Sort task by finished one"""
    case = CaseModel.get_case(cid)
    if CaseModel.get_present_in_case(cid, current_user):
        return CaseModel.sort_by_finished_task_core(case, current_user)
    return {"message": "Not in Case"}




@task_blueprint.route("/<cid>/tasks/ongoing", methods=['GET'])
@login_required
def ongoing_tasks_sort_by_filter(cid):
    """Sort by filter for living task"""
    data_dict = dict(request.args)
    if "filter" in data_dict:
        case = CaseModel.get_case(cid)
        if CaseModel.get_present_in_case(cid, current_user):
            return CaseModel.sort_tasks_by_filter(case, current_user, False, data_dict["filter"])
        return {"message": "Not in Case"}
    return {"message": "No filter pass"}


@task_blueprint.route("/<cid>/tasks/finished", methods=['GET'])
@login_required
def finished_tasks_sort_by_filter(cid):
    """Sort by filter for finished task"""
    data_dict = dict(request.args)
    if "filter" in data_dict:
        case = CaseModel.get_case(cid)
        if CaseModel.get_present_in_case(cid, current_user):
            return CaseModel.sort_tasks_by_filter(case, current_user, True, data_dict["filter"])
        return {"message": "Not in Case"}
    return {"message": "No filter pass"}
