from flask import Blueprint, render_template, redirect, jsonify, request, flash
from .form import CaseForm, TaskForm, CaseEditForm, AddOrgsCase
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

from .task import task_blueprint
case_blueprint.register_blueprint(task_blueprint)

##########
# Render #
##########


@case_blueprint.route("/", methods=['GET', 'POST'])
@login_required
def index():
    """List all cases"""
    form = CaseForm()
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        case = CaseModel.add_case_core(form_dict, current_user)
        flash("Case created", "success")
        return redirect(f"/case/view/{case.id}")
    return render_template("case/case_index.html", form=form)

@case_blueprint.route("/view/<id>", methods=['GET', 'POST'])
@login_required
def view(id):
    """View of a case"""
    case = CaseModel.get_case(id)
    
    if case:
        present_in_case = CaseModel.get_present_in_case(id, current_user)
        if present_in_case:
            form = TaskForm()
            if form.validate_on_submit():
                form_dict = form_to_dict(form)
                if CaseModel.add_task_core(form_dict, id):
                    flash("Task created", "success")
                else:
                    flash("Error File", "error")
                return redirect(f"/case/view/{id}")
        return render_template("case/case_view.html", id=id, case=case.to_json(), present_in_case=present_in_case, form=form)
    return render_template("404.html")


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
        return render_template("case/edit_case.html", form=form)

    return redirect(f"/case/view/{id}")


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
            CaseModel.add_orgs_case(form_dict, id, current_user)
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
    page = request.args.get('page', 1, type=int)
    cases = CaseModel.sort_by_ongoing_core(page)
    role = CaseModel.get_role(current_user).to_json()

    loc = CaseModel.regroup_case_info(cases, current_user)
    return jsonify({"cases": loc["cases"], "role": role, "nb_pages": cases.pages}), 201


@case_blueprint.route("/delete", methods=['POST'])
@login_required
@editor_required
def delete():
    """Delete the case"""
    cid = request.json["case_id"]

    if CaseModel.get_case(cid):
        if CaseModel.get_present_in_case(cid, current_user):
            if CaseModel.delete_case(cid, current_user):
                return {"message": "Case deleted", "toast_class": "success-subtle"}, 200
            else:
                return {"message": "Error case deleted", 'toast_class': "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
    return {"message": "Case no found", 'toast_class': "danger-subtle"}, 404


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
    if CaseModel.get_case(cid):
        if CaseModel.get_present_in_case(cid, current_user):
            if CaseModel.complete_case(cid, current_user):
                return {"message": "Case completed", "toast_class": "success-subtle"}, 200
            else:
                return {"message": "Error case completed", 'toast_class': "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
    return {"message": "Case no found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/remove_org/<oid>", methods=['GET'])
@login_required
@editor_required
def remove_org_case(cid, oid):
    """Remove an org to the case"""

    if CaseModel.get_case(cid):
        if CaseModel.get_present_in_case(cid, current_user):
            if CaseModel.remove_org_case(cid, oid, current_user):
                return {"message": "Org removed from case", "toast_class": "success-subtle"}, 200
            return {"message": "Error removing org from case", "toast_class": "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/change_status/<cid>", methods=['POST'])
@login_required
@editor_required
def change_status(cid):
    """Change the status of the case"""
    
    status = request.json["status"]
    case = CaseModel.get_case(cid)

    if CaseModel.get_case(cid):
        if CaseModel.get_present_in_case(cid, current_user):
            CaseModel.change_status_core(status, case)
            return {"message": "Status changed", "toast_class": "success-subtle"}, 200
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/get_status", methods=['GET'])
@login_required
def get_status():
    """Get status"""

    status = CaseModel.get_all_status()
    status_list = list()
    for s in status:
        status_list.append(s.to_json())
    return jsonify({"status": status_list}), 200


@case_blueprint.route("/sort_by_ongoing", methods=['GET'])
@login_required
def sort_by_ongoing():
    """Sort Case by living one"""
    page = request.args.get('page', 1, type=int)
    cases_list = CaseModel.sort_by_ongoing_core(page)
    return CaseModel.regroup_case_info(cases_list, current_user)



@case_blueprint.route("/sort_by_finished", methods=['GET'])
@login_required
def sort_by_finished():
    """Sort Case by finished one"""
    page = request.args.get('page', 1, type=int)
    cases_list = CaseModel.sort_by_finished_core(page)
    return CaseModel.regroup_case_info(cases_list, current_user)



@case_blueprint.route("/ongoing", methods=['GET'])
@login_required
def ongoing_sort_by_filter():
    """Sort by filter for living case"""
    data_dict = dict(request.args)
    page = request.args.get('page', 1, type=int)
    if "filter" in data_dict:
        cases_list = CaseModel.sort_by_filter(False, data_dict["filter"], page)
        return CaseModel.regroup_case_info(cases_list, current_user)
    return {"message": "No filter pass"}


@case_blueprint.route("/finished", methods=['GET'])
@login_required
def finished_sort_by_filter():
    """Sort by filter for finished task"""
    data_dict = dict(request.args)
    page = request.args.get('page', 1, type=int)
    if "filter" in data_dict:
        cases_list = CaseModel.sort_by_filter(True, data_dict["filter"], page)
        return CaseModel.regroup_case_info(cases_list, current_user)
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


@case_blueprint.route("/<cid>/get_assigned_users/<tid>", methods=['GET'])
@login_required
def get_assigned_users(cid, tid):
    """Get assigned users to the task"""

    if CaseModel.get_present_in_case(cid, current_user):
        users, _ = CaseModel.get_users_assign_task(tid, current_user)
        return users
    return {"message": "Not in Case"}


@case_blueprint.route("/download/<cid>", methods=['GET'])
@login_required
def download_case(cid):
    """Download a case"""

    case = CaseModel.get_case(cid)
    task_list = list()
    for task in case.tasks:
        task_list.append(task.to_json())
    return_dict = case.to_json()
    return_dict["tasks"] = task_list
    return jsonify(return_dict), 200, {'Content-Disposition': f'attachment; filename=case_{case.title}.json'}



@case_blueprint.route("/fork/<cid>", methods=['POST'])
@login_required
def fork_case(cid):
    """Assign current user to the task"""

    case_title_fork = request.json["case_title_fork"]

    new_case = CaseModel.fork_case_core(cid, case_title_fork, current_user)
    if type(new_case) == dict:
        return new_case
    return {"new_case_id": new_case.id}, 201


@case_blueprint.route("/get_all_case_title", methods=['GET'])
@login_required
def get_all_case_title():
    data_dict = dict(request.args)
    if CaseModel.get_case_by_title(data_dict["title"]):
        flag = True
    else:
        flag = False
    
    return {"title_already_exist": flag}


@case_blueprint.route("/create_template/<cid>", methods=['POST'])
@login_required
@editor_required
def create_template(cid):
    case_title_template = request.json["case_title_template"]

    new_case = CaseModel.create_template_from_case(cid, case_title_template)
    if type(new_case) == dict:
        return new_case
    return {"new_case_id": new_case.id}, 201


@case_blueprint.route("/get_all_case_template_title", methods=['GET'])
@login_required
def get_all_case_template_title():
    data_dict = dict(request.args)
    if CaseModel.get_case_template_by_title(data_dict["title"]):
        flag = True
    else:
        flag = False
    
    return {"title_already_exist": flag}