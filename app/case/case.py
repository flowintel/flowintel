from flask import Blueprint, render_template, redirect, jsonify, request, flash
from .form import CaseForm, TaskForm, CaseEditForm, TaskEditForm, AddOrgsCase
from flask_login import login_required, current_user
from . import case_core as CaseModel
from ..db_class.db import Org, Case_Org
from ..decorators import editor_required
from ..utils.utils import form_to_dict

case_blueprint = Blueprint(
    'case',
    __name__,
    template_folder='templates',
    static_folder='static'
)


##########
# Render #
##########


@case_blueprint.route("/", methods=['GET'])
@login_required
def index():
    """List all cases"""
    return render_template("case/case_index.html")

@case_blueprint.route("/view/<id>", methods=['GET'])
@login_required
def view(id):
    """View of a case"""
    case = CaseModel.get_case(id)
    
    if case:
        present_in_case = CaseModel.get_present_in_case(id, current_user)
        return render_template("case/case_view.html", id=id, case=case.to_json(), present_in_case=present_in_case)
    return render_template("404.html")

@case_blueprint.route("/my_assignation", methods=['GET'])
@login_required
def my_assignation():
    """View of a assigned tasks"""
    return render_template("case/my_assignation.html")

@case_blueprint.route("/add", methods=['GET','POST'])
@login_required
@editor_required
def add_case():
    """Add a new case"""
    form = CaseForm()
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        case = CaseModel.add_case_core(form_dict, current_user)
        flash("Case created", "success")
        return redirect(f"/case/view/{case.id}")
    return render_template("case/add_case.html", form=form)

@case_blueprint.route("/edit/<id>", methods=['GET','POST'])
@login_required
@editor_required
def edit_case(id):
    """Edit the case"""
    if CaseModel.get_present_in_case(id, current_user):
        form = CaseEditForm()

        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            CaseModel.edit_case_core(form_dict, id)
            flash("Case edited", "success")
            return redirect(f"/case/view/{id}")
        else:
            case_modif = CaseModel.get_case(id)
            form.description.data = case_modif.description
            form.title.data = case_modif.title
            form.dead_line_date.data = case_modif.dead_line
            form.dead_line_time.data = case_modif.dead_line
        return render_template("case/add_case.html", form=form)

    return redirect(f"/case/view/{id}")

@case_blueprint.route("/<id>/add_task", methods=['GET','POST'])
@login_required
@editor_required
def add_task(id):
    """Add a task to the case"""
    if CaseModel.get_present_in_case(id, current_user):
        form = TaskForm()
        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            if CaseModel.add_task_core(form_dict, id):
                flash("Task created", "success")
            else:
                flash("Error File", "error")
            return redirect(f"/case/view/{id}")
        return render_template("case/add_task.html", form=form)
    else:
        flash("Access denied", "error")

    return redirect(f"/case/view/{id}")

@case_blueprint.route("view/<case_id>/edit_task/<id>", methods=['GET','POST'])
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
        
        return render_template("case/add_task.html", form=form)
    else:
        flash("Access denied", "error")
    
    return redirect(f"/case/view/{case_id}")

@case_blueprint.route("/view/<id>/add_orgs", methods=['GET', 'POST'])
@login_required
@editor_required
def add_orgs(id):
    """Add orgs to the case"""

    if CaseModel.get_present_in_case(id, current_user):
        form = AddOrgsCase()
        case_org = Case_Org.query.filter_by(case_id=id).all()

        org_list = list()

        for org in Org.query.order_by('name'):
            if case_org:
                flag = False
                for c_o in case_org:
                    if c_o.org_id == org.id:
                        flag = True
                if not flag:
                    org_list.append((org.id, f"{org.name}"))
            else:
                org_list.append((org.id, f"{org.name}"))

        form.org_id.choices = org_list
        form.case_id.data=id

        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            CaseModel.add_orgs_case(form_dict, id)
            flash("Orgs added", "success")
            return redirect(f"/case/view/{id}")

        return render_template("case/add_orgs.html", form=form)
    else:
        flash("Access denied", "error")
    return redirect(f"/case/view/{id}")



############
# Function #
#  Route   #
############

@case_blueprint.route("case/get_cases", methods=['GET'])
@login_required
def get_cases():
    """Return all cases"""
    cases = CaseModel.sort_by_ongoing_core()
    role = CaseModel.get_role(current_user).to_json()

    loc = CaseModel.regroup_case_info(cases, current_user)
    return jsonify({"cases": loc["cases"], "role": role}), 201


@case_blueprint.route("/delete", methods=['POST'])
@login_required
@editor_required
def delete():
    """Delete the case"""
    cid = request.json["case_id"]

    if CaseModel.get_present_in_case(cid, current_user):
        if CaseModel.delete_case(cid):
            return {"message": "Case deleted"}, 201
        else:
            return {"message": "Error case deleted"}, 201
    return {"message": "Not in case"}



@case_blueprint.route("view/get_case_info/<cid>", methods=['GET'])
@login_required
def get_case_info(cid):
    """Return all info of the case"""
    case = CaseModel.get_case(cid)
    
    tasks = CaseModel.sort_by_ongoing_task_core(case, current_user)

    orgs_in_case = CaseModel.get_orgs_in_case(case.id)
    permission = CaseModel.get_role(current_user).to_json()
    present_in_case = CaseModel.get_present_in_case(cid, current_user)

    return jsonify({"case": case.to_json(), "tasks": tasks, "orgs_in_case": orgs_in_case, "permission": permission, "present_in_case": present_in_case, "current_user": current_user.to_json()}), 201


@case_blueprint.route("/complete_case/<cid>", methods=['GET'])
@login_required
@editor_required
def complete_case(cid):
    """Complete the case"""

    if CaseModel.get_present_in_case(cid, current_user):
        if CaseModel.complete_case(cid):
            return {"message": "Case completed"}, 201
        else:
            return {"message": "Error case completed"}, 201
    return {"message": "Not in case"}


@case_blueprint.route("/complete_task/<tid>", methods=['GET'])
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


@case_blueprint.route("/delete_task", methods=['POST'])
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


@case_blueprint.route("/modif_note", methods=['POST'])
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


@case_blueprint.route("/get_note_text", methods=['GET'])
@editor_required
def get_note_text():
    """Get not of a task in text format"""

    data_dict = dict(request.args)
    note = CaseModel.get_note_text(data_dict["id"])

    return {"note": note}, 201


@case_blueprint.route("/get_note_markdown", methods=['GET'])
def get_note_markdown():
    """Get not of a task in markdown format"""

    data_dict = dict(request.args)
    note = CaseModel.get_note_markdown(data_dict["id"])

    return {"note": note}, 201


@case_blueprint.route("/take_task", methods=['POST'])
@login_required
@editor_required
def take_task():
    """Assign current user to the task"""

    id = request.json["task_id"]

    task = CaseModel.get_task(id)
    if CaseModel.get_present_in_case(task.case_id, current_user):
        CaseModel.assign_task(id, current_user)
        return {"message": "User Assigned"}, 201
    return {"message": "Not in Case"}


@case_blueprint.route("/remove_assign_task", methods=['POST'])
@login_required
@editor_required
def remove_assign_task():
    """Remove an assignation to the task"""
    
    id = request.json["task_id"]
    task = CaseModel.get_task(id)

    if CaseModel.get_present_in_case(task.case_id, current_user):
        CaseModel.remove_assign_task(id, current_user)
        return {"message": "User Removed from assignation"}, 201
    return {"message": "Not in Case"}


@case_blueprint.route("/<cid>/remove_org/<oid>", methods=['GET'])
@login_required
@editor_required
def remove_org_case(cid, oid):
    """Remove an org to the case"""

    if CaseModel.get_present_in_case(cid, current_user):
        if CaseModel.remove_org_case(cid, oid):
            return {"message": "Org removed from case"}
        return {"message", "Error removing org from case"}
    return {"message": "Not in Case"}


@case_blueprint.route("/change_status/<cid>", methods=['POST'])
@login_required
@editor_required
def change_status(cid):
    """Change the status of the case"""
    
    status = request.json["status"]
    case = CaseModel.get_case(cid)

    if CaseModel.get_present_in_case(cid, current_user):
        CaseModel.change_status_core(status, case)
        flash("Assignation changed", "success")
        return {"message": "Assignation changed"}, 201
    return {"message": "Not in Case"}


@case_blueprint.route("/change_status/task/<tid>", methods=['POST'])
@login_required
@editor_required
def change_status_task(tid):
    """Change the status of the task"""
    
    status = request.json["status"]
    task = CaseModel.get_task(tid)

    if CaseModel.get_present_in_case(task.case_id, current_user):
        CaseModel.change_status_task(status, task)
        flash("Assignation changed", "success")
        return {"message": "Assignation changed"}, 201
    return {"message": "Not in Case"}


@case_blueprint.route("/get_status", methods=['GET'])
@login_required
def get_status():
    """Get status"""

    status = CaseModel.get_all_status()
    status_list = list()
    for s in status:
        status_list.append(s.to_json())
    return jsonify({"status": status_list}), 200


@case_blueprint.route("/task/<tid>/download_file/<fid>", methods=['GET'])
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


@case_blueprint.route("/task/<tid>/delete_file/<fid>", methods=['GET'])
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


@case_blueprint.route("/add_files", methods=['POST'])
@login_required
@editor_required
def add_files():
    """Add files to a task"""
    if request.form.get("task_id"):
        
        task = CaseModel.get_task(request.form.get("task_id"))

        return_files_list = CaseModel.add_file_core(task=task, files_list=request.files)

        return return_files_list
    return []


@case_blueprint.route("/<cid>/sort_by_ongoing_task", methods=['GET'])
@login_required
def sort_by_ongoing_task(cid):
    """Sort Task by living one"""
    case = CaseModel.get_case(cid)
    if CaseModel.get_present_in_case(cid, current_user):
        return CaseModel.sort_by_ongoing_task_core(case, current_user)
    return {"message": "Not in Case"}


@case_blueprint.route("/<cid>/sort_by_finished_task", methods=['GET'])
@login_required
def sort_by_finished_task(cid):
    """Sort task by finished one"""
    case = CaseModel.get_case(cid)
    if CaseModel.get_present_in_case(cid, current_user):
        return CaseModel.sort_by_finished_task_core(case, current_user)
    return {"message": "Not in Case"}




@case_blueprint.route("/<cid>/tasks/ongoing", methods=['GET'])
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


@case_blueprint.route("/<cid>/tasks/finished", methods=['GET'])
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







@case_blueprint.route("/sort_by_ongoing", methods=['GET'])
@login_required
def sort_by_ongoing():
    """Sort Case by living one"""
    cases_list = CaseModel.sort_by_ongoing_core()
    return CaseModel.regroup_case_info(cases_list, current_user)



@case_blueprint.route("/sort_by_finished", methods=['GET'])
@login_required
def sort_by_finished():
    """Sort Case by finished one"""
    cases_list = CaseModel.sort_by_finished_core()
    return CaseModel.regroup_case_info(cases_list, current_user)



@case_blueprint.route("/ongoing", methods=['GET'])
@login_required
def ongoing_sort_by_filter():
    """Sort by filter for living case"""
    data_dict = dict(request.args)
    if "filter" in data_dict:
        cases_list = CaseModel.sort_by_filter(False, data_dict["filter"])
        return CaseModel.regroup_case_info(cases_list, current_user)
    return {"message": "No filter pass"}


@case_blueprint.route("/finished", methods=['GET'])
@login_required
def finished_sort_by_filter():
    """Sort by filter for finished task"""
    data_dict = dict(request.args)
    if "filter" in data_dict:
        cases_list = CaseModel.sort_by_filter(True, data_dict["filter"])
        return CaseModel.regroup_case_info(cases_list, current_user)
    return {"message": "No filter pass"}


@case_blueprint.route("/my_assignation_data", methods=['GET'])
@login_required
def my_assignation_data():
    """Get tasks assigned to current user"""
    tasks_list = CaseModel.my_assignation_sort_by_status(user=current_user, completed=False)
    return CaseModel.get_task_info(tasks_list, current_user)





@case_blueprint.route("/my_assignation/sort_by_ongoing", methods=['GET'])
@login_required
def my_assignation_sort_by_ongoing():
    """Sort Task by living one"""
    tasks_list = CaseModel.my_assignation_sort_by_status(user=current_user, completed=False)
    return CaseModel.get_task_info(tasks_list, current_user)



@case_blueprint.route("/my_assignation/sort_by_finished", methods=['GET'])
@login_required
def my_assignation_sort_by_finished():
    """Sort Task by finished one"""
    tasks_list = CaseModel.my_assignation_sort_by_status(user=current_user, completed=True)
    return CaseModel.get_task_info(tasks_list, current_user)


@case_blueprint.route("/my_assignation/tasks/ongoing", methods=['GET'])
@login_required
def my_assignation_ongoing_sort_by_filter():
    """Sort Task by living one"""
    data_dict = dict(request.args)
    if "filter" in data_dict:
        tasks_list = CaseModel.my_assignation_sort_by_filter(user=current_user, completed=False, filter=data_dict["filter"])
        return CaseModel.get_task_info(tasks_list, current_user)
    return {"message": "No filter pass"}


@case_blueprint.route("/my_assignation/tasks/finished", methods=['GET'])
@login_required
def my_assignation_finished_sort_by_filter():
    """Sort Task by finished one"""
    data_dict = dict(request.args)
    if "filter" in data_dict:
        tasks_list = CaseModel.my_assignation_sort_by_filter(user=current_user, completed=False, filter=data_dict["filter"])
        return CaseModel.get_task_info(tasks_list, current_user)
    return {"message": "No filter pass"}



@case_blueprint.route("/<cid>/get_all_users", methods=['GET'])
@login_required
def get_all_users(cid):
    """Sort Task by finished one"""
    users_list = list()
    case = CaseModel.get_case(cid)
    if CaseModel.get_present_in_case(cid, current_user):
        orgs = CaseModel.get_all_users_core(case)
        for org in orgs:
            for user in org.users:
                users_list.append(user.to_json())
        return {"users_list": users_list}
    return {"message": "Not in Case"}


@case_blueprint.route("/assign_users_task", methods=['POST'])
@login_required
@editor_required
def assign_user_task():
    """Assign current user to the task"""

    tid = request.json["task_id"]
    users_list = request.json["users_id"]

    task = CaseModel.get_task(tid)
    if CaseModel.get_present_in_case(task.case_id, current_user):
        for user in users_list:
            CaseModel.assign_task(tid, user)
        return {"message": "Users Assigned"}, 201
    return {"message": "Not in Case"}


@case_blueprint.route("/<cid>/get_assigned_users/<tid>", methods=['GET'])
@login_required
def get_assigned_users(cid, tid):
    """Get assigned users to the task"""

    if CaseModel.get_present_in_case(cid, current_user):
        users, _ = CaseModel.get_users_assign_task(tid, current_user)
        return users
    return {"message": "Not in Case"}