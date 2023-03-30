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

@case_blueprint.route("/add", methods=['GET','POST'])
@login_required
@editor_required
def add_case():
    """Add a new case"""
    form = CaseForm()
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        case = CaseModel.add_case_core(form_dict, current_user)
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
            CaseModel.add_task_core(form_dict, id)
            return redirect(f"/case/view/{id}")
        return render_template("case/add_task.html", form=form)

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
            return redirect(f"/case/view/{id}")

        return render_template("case/add_orgs.html", form=form)
    return redirect(f"/case/view/{id}")



############
# Function #
#  Route   #
############

@case_blueprint.route("case/get_cases", methods=['GET'])
@login_required
def get_cases():
    """Return all cases"""
    cases = CaseModel.get_all_cases()
    role = CaseModel.get_role(current_user).to_json()
    return jsonify({"cases": [case.to_json() for case in cases], "role": role}), 201


@case_blueprint.route("/delete", methods=['POST'])
@login_required
@editor_required
def delete():
    """Delete the case"""
    id = request.json["id_case"]

    if CaseModel.get_present_in_case(id, current_user):
        if CaseModel.delete_case(id):
            return {"message": "Case deleted"}, 201
        else:
            return {"message": "Error case deleted"}, 201
    return {"message": "Not in case"}



@case_blueprint.route("view/get_case_info/<id>", methods=['GET'])
@login_required
def get_case_info(id):
    """Return all info of the case"""
    case = CaseModel.get_case(id)
    
    tasks = list()
    for task in case.tasks:
        users, flag = CaseModel.get_users_assign_task(task.id, current_user)
        task.notes = CaseModel.markdown_notes(task.notes)
        tasks.append((task.to_json(), users, flag))

    orgs_in_case = CaseModel.get_orgs_in_case(case.id)
    permission = CaseModel.get_role(current_user).to_json()

    present_in_case = CaseModel.get_present_in_case(id, current_user)

    return jsonify({"case": case.to_json(), "tasks": tasks, "orgs_in_case": orgs_in_case, "permission": permission, "present_in_case": present_in_case}), 201


@case_blueprint.route("/complete_task", methods=['POST'])
@login_required
@editor_required
def complete_task():
    """Complete the task"""
    id = request.json["id_task"]

    task = CaseModel.get_task(id)
    if CaseModel.get_present_in_case(task.case_id, current_user):
        if CaseModel.complete_task(id):
            return {"message": "Task completed"}, 201
        else:
            return {"message": "Error task completed"}, 201
    return {"message": "Not in case"}


@case_blueprint.route("/delete_task", methods=['POST'])
@login_required
@editor_required
def delete_task():
    """Delete the task"""
    id = request.json["id_task"]
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
    id = request.json["id_task"]

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