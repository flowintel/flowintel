import ast
import datetime
import json
import os
from flask import Blueprint, render_template, redirect, jsonify, request, flash, current_app, abort
from flask_login import login_required, current_user
import requests
import conf.config_module as ConfigModule

from .form import CaseForm, CaseEditForm, RecurringForm
from .CaseCore import CaseModel, FILE_FOLDER
from . import common_core as CommonModel
from .TaskCore import TaskModel
from ..db_class.db import Case, Task_Template, Case_Template, File, Case_Link_Case, Task_User, User
from ..decorators import editor_required, template_editor_required, admin_required, misp_editor_required
from ..utils.utils import form_to_dict, get_object_templates
from ..utils.formHelper import prepare_tags
from ..utils.logger import flowintel_log
from ..utils.file_converter import convert_file_to_note_content
from ..utils.gpg import sign_text
from ..utils.note_variables import resolve_variables, get_syntax_reference

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

def check_user_private_case(case: Case, present_in_case: bool = None) -> bool:
    if not present_in_case:
        present_in_case = CommonModel.get_present_in_case(case.id, current_user)
    if case.is_private and not present_in_case and not current_user.is_admin():
        return False
    return True


@case_blueprint.route("/", methods=['GET', 'POST'])
@login_required
def index():
    """List all cases"""
    flowintel_log("audit", 200, "List all cases", User=current_user.email)
    return render_template("case/case_index.html")

@case_blueprint.route("/create_case", methods=['GET', 'POST'])
@login_required
@editor_required
def create_case():
    """Create a case"""
    form = CaseForm()
    form.template_select.choices = [(template.id, template.title) for template in Case_Template.query.all()]
    form.template_select.choices.insert(0, (0," "))

    form.tasks_templates.choices = [(template.id, template.title) for template in Task_Template.query.all()]
    form.tasks_templates.choices.insert(0, (0," "))
    
    if form.validate_on_submit():
        res = prepare_tags(request)
        if isinstance(res, dict):
            form_dict = form_to_dict(form)
            form_dict.update(res)
            form_dict["description"] = request.form.get("description")
            case = CaseModel.create_case(form_dict, current_user)
            flowintel_log("audit", 200, "Case created", User=current_user.email, CaseId=case.id, CaseTitle=case.title, IsPrivate=case.is_private, IsPrivileged=case.privileged_case)
            flash("Case created", "success")
            return redirect(f"/case/{case.id}")
        return render_template("case/create_case.html", form=form)
    return render_template("case/create_case.html", form=form)

@case_blueprint.route("/<cid>", methods=['GET', 'POST'])
@login_required
def view(cid):
    """View of a case"""
    case = CommonModel.get_case(cid)
    if case:
        present_in_case = CommonModel.get_present_in_case(cid, current_user)
        if not check_user_private_case(case, present_in_case):
            flowintel_log("audit", 403, "View of a case: No access to private case", User=current_user.email, CaseId=cid)
            return render_template("404.html")
        return render_template("case/case_view.html", case=case.to_json(), present_in_case=present_in_case)
    return render_template("404.html")


@case_blueprint.route("/edit/<cid>", methods=['GET','POST'])
@login_required
@editor_required
def edit_case(cid):
    """Edit the case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            form = CaseEditForm()

            if form.validate_on_submit():
                form_dict = form_to_dict(form)
                form_dict["description"] = request.form.get("description")
                
                if not (current_user.is_admin() or current_user.is_case_admin()):
                    case_modif = CommonModel.get_case(cid)
                    form_dict["privileged_case"] = case_modif.privileged_case
                
                CaseModel.edit(form_dict, cid, current_user)
                case = CommonModel.get_case(cid)
                flowintel_log("audit", 200, "Case edited", User=current_user.email, CaseId=cid, CaseTitle=case.title, IsPrivate=form_dict.get("is_private", False), IsPrivileged=form_dict.get("privileged_case", False))
                flash("Case edited", "success")
                return redirect(f"/case/{cid}")
            else:
                case_modif = CommonModel.get_case(cid)
                form.title.data = case_modif.title
                form.deadline_date.data = case_modif.deadline
                form.deadline_time.data = case_modif.deadline
                form.time_required.data = case_modif.time_required
                form.is_private.data = case_modif.is_private
                form.privileged_case.data = case_modif.privileged_case
                form.ticket_id.data = case_modif.ticket_id

            return render_template("case/edit_case.html", form=form, description=case_modif.description, case_id=cid)
        else:
            flash("Access denied", "error")
    else:
        return render_template("404.html")
    return redirect(f"/case/{cid}")

@case_blueprint.route("/edit_tags/<cid>", methods=['GET','POST'])
@login_required
@editor_required
def edit_case_tags(cid):
    """Edit the case"""
    if CommonModel.get_case(cid):
        tag_list = request.json["tags_select"]
        cluster_list = request.json["clusters_select"]
        custom_tags_list = request.json["custom_select"]
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if isinstance(CommonModel.check_tag(tag_list), bool):
                if isinstance(CommonModel.check_cluster(cluster_list), bool):
                    loc_dict = {
                        "tags": tag_list,
                        "clusters": cluster_list,
                        "custom_tags": custom_tags_list
                    }
                    CaseModel.edit_tags(loc_dict, cid, current_user)
                    flowintel_log("audit", 200, "Case tags/galaxies edited", User=current_user.email, CaseId=cid, Tags=str(tag_list), Galaxies=str(cluster_list), CustomTags=str(custom_tags_list))
                    return {"message": "Tags edited", "toast_class": "success-subtle"}, 200
                return {"message": "Error with Clusters", "toast_class": "warning-subtle"}, 400
            return {"message": "Error with Tags", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Case tags/galaxies  edited: Access denied", User=current_user.email, CaseId=cid, Tags=str(tag_list), Galaxies=str(cluster_list), CustomTags=str(custom_tags_list))
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

@case_blueprint.route("/<cid>/add_orgs", methods=['GET', 'POST'])
@login_required
@editor_required
def add_orgs(cid):
    """Add orgs to the case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if request.json:
                if "org_id" in request.json:
                    if CaseModel.add_orgs_case(request.json, cid, current_user):
                        flowintel_log("audit", 200, "Orgs added to case", User=current_user.email, CaseId=cid, Orgs=str(request.json["org_id"]))
                        return {"message": "Orgs added", "toast_class": "success-subtle"}, 200
                    return {"message": "One Orgs doesn't exist", "toast_class": "danger-subtle"}, 404
                return {"message": "Need to pass 'org_id'", "toast_class": "warning-subtle"}, 400
            return {"message": "An error occur", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Add orgs to case: Permission denied", User=current_user.email, CaseId=cid)
        return {"message": "Permission denied", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

@case_blueprint.route("/<cid>/change_owner", methods=['GET', 'POST'])
@login_required
@editor_required
def change_owner(cid):
    """Change owner of a case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if request.json:
                if "org_id" in request.json:
                    if CaseModel.change_owner_core(request.json["org_id"], cid, current_user):
                        flowintel_log("audit", 200, "Owner of case changed", User=current_user.email, CaseId=cid, NewOwnerOrgId=request.json["org_id"])
                        return {"message": "Owner changed", "toast_class": "success-subtle"}, 200
                    return {"message": "Org doesn't exist", "toast_class": "danger-subtle"}, 404
                return {"message": "Need to pass 'org_id'", "toast_class": "warning-subtle"}, 400
            return {"message": "An error occur", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Change owner of case: Permission denied", User=current_user.email, CaseId=cid)
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

@case_blueprint.route("/<cid>/recurring", methods=['GET', 'POST'])
@login_required
@editor_required
def recurring(cid):
    """Recurring form"""

    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if case.privileged_case and not (current_user.is_admin() or current_user.is_case_admin()):
                flowintel_log("audit", 403, "Recurring: Privileged case requires admin permissions", User=current_user.email, CaseId=cid)
                flash("Cannot modify recurring settings for privileged cases", "warning")
                return redirect(f"/case/{cid}")
            
            form = RecurringForm()
            form.case_id.data = cid

            # List orgs and users in and verify if all users of an org are currently notify
            orgs_in_case = CommonModel.get_orgs_in_case(cid)
            orgs_to_return = CaseModel.prepare_recurring_form(cid, orgs_in_case)

            if form.validate_on_submit():
                form_dict = form_to_dict(form)
                if not CaseModel.change_recurring(form_dict, cid, current_user):
                    flash("Recurring empty", "error")
                    return redirect(f"/case/{cid}/recurring")
                if not form_dict["remove"]:
                    CaseModel.notify_user_recurring(request.form.to_dict(), cid, orgs_in_case)
                flowintel_log("audit", 200, "Recurring set for case", User=current_user.email, CaseId=cid, Recurring=str(form_dict))
                flash("Recurring set", "success")
                return redirect(f"/case/{cid}")
            
            return render_template("case/case_recurring.html", form=form, orgs=orgs_to_return)
        
        flash("Action not allowed", "warning")
        return redirect(f"/case/{cid}")
    
    return render_template("404.html")


############
# Function #
#  Route   #
############

@case_blueprint.route("/get_case/<cid>", methods=['GET'])
@login_required
def get_case(cid):
    """Return a case by id"""
    case = CommonModel.get_case(cid)
    if not check_user_private_case(case):
        return None, 200
    return case.to_json(), 200


@case_blueprint.route("/search", methods=['GET'])
@login_required
def search():
    """Return cases matching search terms"""
    text_search = ""
    if "text" in request.args:
        text_search = request.args.get("text")
    cases = CommonModel.search(text_search, current_user)
    flowintel_log("audit", 200, "Search cases", User=current_user.email, SearchText=text_search)
    if cases:
        return {"cases": [case.to_json() for case in cases]}, 200
    return {"message": "No case", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/delete", methods=['GET'])
@login_required
@editor_required
def delete(cid):
    """Delete the case"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if case.privileged_case and not (current_user.is_admin() or current_user.is_case_admin()):
                flowintel_log("audit", 403, "Delete case: Privileged case requires admin permissions", User=current_user.email, CaseId=cid)
                return {"message": "Cannot delete privileged cases", "toast_class": "danger-subtle"}, 403
            
            if CaseModel.delete_case(cid, current_user):
                flowintel_log("audit", 200, "Case deleted", User=current_user.email, CaseId=cid)
                return {"message": "Case deleted", "toast_class": "success-subtle"}, 200
            else:
                return {"message": "Error case deleted", 'toast_class': "danger-subtle"}, 400
        flowintel_log("audit", 403, "Case not deleted: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/get_case_info", methods=['GET'])
@login_required
def get_case_info(cid):
    """Return all info of the case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get case info: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "permission denied", 'toast_class': "danger-subtle"}, 403
        tasks_result = TaskModel.sort_tasks(case, current_user, completed=False)
        tasks = tasks_result["tasks"]

        o_in_c = CommonModel.get_orgs_in_case(case.id)
        orgs_in_case = [o_c.to_json() for o_c in o_in_c]
        permission = CommonModel.get_role(current_user).to_json()
        present_in_case = CommonModel.get_present_in_case(cid, current_user)

        try:
            files_list = [f.to_json() for f in case.files]
        except Exception:
            files_list = []

        case_json = case.to_json()
        case_json["misp_icon"] = CommonModel.get_misp_connector_icon() or ""
        case_json["has_misp_event"] = CommonModel.case_has_misp_event(case.id)

        return jsonify({"case": case_json, "tasks": tasks, "orgs_in_case": orgs_in_case, "permission": permission, "present_in_case": present_in_case, "current_user": current_user.to_json(), "files": files_list}), 200
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/complete_case", methods=['GET'])
@login_required
@editor_required
def complete_case(cid):
    """Mark a case as completed"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if case.privileged_case and not (current_user.is_admin() or current_user.is_case_admin()):
                operation = "revival" if case.completed else "completion"
                flowintel_log("audit", 403, f"Complete case: Privileged case {operation} denied", User=current_user.email, CaseId=cid)
                return {"message": "Insufficient permissions", 'toast_class': "danger-subtle"}, 403
            
            was_completed = case.completed
            
            if CaseModel.complete_case(cid, current_user):
                flash("Case Completed")
                if was_completed:
                    flowintel_log("audit", 200, "Case revived", User=current_user.email, CaseId=cid, CaseTitle=case.title)
                    return {"message": "Case revived", "toast_class": "success-subtle"}, 200
                else:
                    flowintel_log("audit", 200, "Case completed", User=current_user.email, CaseId=cid, CaseTitle=case.title)
                    return {"message": "Case completed", "toast_class": "success-subtle"}, 200
            else:
                if was_completed:
                    return {"message": "Error case revived", 'toast_class': "danger-subtle"}, 400
                return {"message": "Error case completed", 'toast_class': "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/remove_org/<oid>", methods=['GET'])
@login_required
@editor_required
def remove_org_case(cid, oid):
    """Remove an org to the case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.remove_org_case(cid, oid, current_user):
                flowintel_log("audit", 200, "Org removed from case", User=current_user.email, CaseId=cid, OrgId=oid)
                return {"message": "Org removed from case", "toast_class": "success-subtle"}, 200
            return {"message": "Error removing org from case", "toast_class": "danger-subtle"}, 400
        flowintel_log("audit", 403, "Remove org from case: Action not allowed", User=current_user.email, CaseId=cid, OrgId=oid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/change_status", methods=['POST'])
@login_required
@editor_required
def change_status(cid):
    """Change the status of the case"""
    status = request.json["status"]
    case = CommonModel.get_case(cid)

    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.change_status_core(status, case, current_user):
                status_obj = CommonModel.get_status(status)
                status_name = status_obj.name if status_obj else str(status)
                flowintel_log("audit", 200, "Case status changed", User=current_user.email, CaseId=cid, CaseTitle=case.title, Status=status_name)
                return {"message": "Status changed", "toast_class": "success-subtle"}, 200
            return {"message": "Invalid status", "toast_class": "danger-subtle"}, 400
        flowintel_log("audit", 403, "Change case status: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/get_status", methods=['GET'])
@login_required
def get_status():
    """Get all status"""
    status = CommonModel.get_all_status()
    status_list = list()
    for s in status:
        status_list.append(s.to_json())
    return jsonify({
        "status": status_list,
        "config": {
            "TASK_REQUESTED": current_app.config.get('TASK_REQUESTED', 7),
            "TASK_APPROVED": current_app.config.get('TASK_APPROVED', 8),
            "TASK_REJECTED": current_app.config.get('TASK_REJECTED', 5),
            "TASK_REQUEST_REVIEW": current_app.config.get('TASK_REQUEST_REVIEW', 9),
            "PRIVILEGED_CASE_ADD_ADMIN_ON_TASK_REQUEST": current_app.config.get('PRIVILEGED_CASE_ADD_ADMIN_ON_TASK_REQUEST', False)
        }
    }), 200


@case_blueprint.route("/sort_cases", methods=['GET'])
@login_required
def sort_cases():
    """Sort Cases"""
    page = request.args.get('page', 1, type=int)
    filter_by = request.args.get('filter')
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
    elif status == 'false':
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

    # optional title search filter
    title_q = request.args.get('q', None, type=str)

    cases_list, nb_pages = CaseModel.sort_cases(page=page, 
                                      completed=status,
                                      taxonomies=taxonomies, 
                                      galaxies=galaxies, 
                                      tags=tags, 
                                      clusters=clusters, 
                                      custom_tags=custom_tags,
                                      or_and_taxo=or_and_taxo, 
                                      or_and_galaxies=or_and_galaxies,
                                      filter=filter_by, 
                                      user=current_user,
                                      title_filter=title_q)
    
    return CaseModel.regroup_case_info(cases_list, current_user, nb_pages)


@case_blueprint.route("/<cid>/get_all_users", methods=['GET'])
@login_required
def get_all_users(cid):
    """Get all users in case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get all users in case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "permission denied", 'toast_class': "danger-subtle"}, 403
        users_list = list()
        orgs = CommonModel.get_all_org_case(case)
        for org in orgs:
            for user in org.users:
                if not user == current_user:
                    users_list.append(user.to_json())
        return {"users_list": users_list}
    return {"message": "Case not found"}, 404


@case_blueprint.route("/<cid>/get_assigned_users/<tid>", methods=['GET'])
@login_required
def get_assigned_users(cid, tid):
    """Get assigned users to the task"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get assigned users to task: Private case: Permission denied", User=current_user.email, CaseId=cid, TaskId=tid)
            return {"message": "permission denied", 'toast_class': "danger-subtle"}, 403
        
        users, _ = TaskModel.get_users_assign_task(tid, current_user)
        return users
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/download", methods=['GET'])
@login_required
def download_case(cid):
    """Download a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Download case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "permission denied", 'toast_class': "danger-subtle"}, 403
        
        task_list = [task.download() for task in case.tasks]

        misp_object_list = [obj.download() for obj in CaseModel.get_misp_object_by_case(cid)]
        return_dict = case.download()
        return_dict["tasks"] = task_list
        return_dict["misp-objects"] = misp_object_list
        flowintel_log("audit", 200, "Download case", User=current_user.email, CaseId=cid)
        return json.dumps(return_dict, indent=4), 200, {'Content-Disposition': f'attachment; filename=case_{case.title}.json'}
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404



@case_blueprint.route("/<cid>/fork", methods=['POST'])
@login_required
@editor_required
def fork_case(cid):
    """Fork a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Fork case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        if case.privileged_case and not (current_user.is_admin() or current_user.is_case_admin()):
            flowintel_log("audit", 403, "Fork case: Privileged case requires admin permissions", User=current_user.email, CaseId=cid)
            return {"message": "Cannot fork privileged cases", 'toast_class': "danger-subtle"}, 403
        
        if "case_title_fork" in request.json:
            case_title_fork = request.json["case_title_fork"]

            new_case = CaseModel.fork_case_core(cid, case_title_fork, current_user)
            if type(new_case) == dict:
                return new_case
            flowintel_log("audit", 201, "Case forked", User=current_user.email, OriginalCaseId=cid, NewCaseId=new_case.id, NewCaseTitle=case_title_fork)
            return {"new_case_id": new_case.id}, 201
        return {"message": "'case_title_fork' is missing", 'toast_class': "danger-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/merge/<ocid>", methods=['GET'])
@login_required
@editor_required
def merge_case(cid, ocid):
    """Merge a case to an other"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Merge case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        if case.privileged_case and not (current_user.is_admin() or current_user.is_case_admin()):
            flowintel_log("audit", 403, "Merge case: Privileged case requires admin permissions", User=current_user.email, CaseId=cid)
            return {"message": "Cannot merge privileged cases", 'toast_class': "danger-subtle"}, 403
        
        merging_case = CommonModel.get_case(ocid)
        if not merging_case:
            return {"message": "Target case not found", 'toast_class': "danger-subtle"}, 404
        
        if not check_user_private_case(merging_case):
            flowintel_log("audit", 403, "Merge case: Permission denied for target case", User=current_user.email, CaseId=cid, TargetCaseId=ocid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        if merging_case.privileged_case and not (current_user.is_admin() or current_user.is_case_admin()):
            flowintel_log("audit", 403, "Merge case: Target is a privileged case", User=current_user.email, CaseId=cid, TargetCaseId=ocid)
            return {"message": "Cannot merge into privileged cases", 'toast_class': "danger-subtle"}, 403
            
        if CaseModel.merge_case_core(case, merging_case, current_user):
            CaseModel.delete_case(cid, current_user)
            flowintel_log("audit", 200, "Cases merged", User=current_user.email, SourceCaseId=cid, TargetCaseId=ocid)
            flash("Merged successfully", "success")
            return {"message": "Case is merged", 'toast_class': "success-subtle"}, 200
        return {"message": "Error Merging", 'toast_class': "danger-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/check_case_title_exist", methods=['GET'])
@login_required
def check_case_title_exist():
    """Check if a title for a case exist"""
    data_dict = dict(request.args)
    if CommonModel.check_case_title(data_dict["title"]):
        return {"title_already_exist": True}
    return {"title_already_exist": False}


@case_blueprint.route("/<cid>/create_template", methods=['POST'])
@login_required
@template_editor_required
def create_template(cid):
    """Create a case template from a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Create template from case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        if case.privileged_case and not (current_user.is_admin() or current_user.is_case_admin()):
            flowintel_log("audit", 403, "Create template: Privileged case requires admin permissions", User=current_user.email, CaseId=cid)
            return {"message": "Cannot create template from privileged cases", 'toast_class': "danger-subtle"}, 403
        
        if "case_title_template" in request.json:
            case_title_template = request.json["case_title_template"]

            new_template = CaseModel.create_template_from_case(cid, case_title_template, current_user)
            if type(new_template) == dict:
                return new_template
            flowintel_log("audit", 201, "Case template created from case", User=current_user.email, CaseId=cid, TemplateId=new_template.id, TemplateTitle=case_title_template)
            return {"template_id": new_template.id}, 201
        return {"message": "'case_title_template' is missing", 'toast_class': "danger-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/check_case_template_title_exist", methods=['GET'])
@login_required
def check_case_template_title_exist():
    """Check if a title for a case template exist"""
    data_dict = dict(request.args)
    if CommonModel.get_case_template_by_title(data_dict["title"]):
        return {"title_already_exist": True}
    return {"title_already_exist": False}


@case_blueprint.route("/history/<cid>", methods=['GET'])
@login_required
def history(cid):
    """Get the history of a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get history: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        history = CommonModel.get_history(case.uuid)
        if history:
            return {"history": history}
        return {"history": None}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/audit_logs/<cid>", methods=['GET'])
@login_required
def audit_logs(cid):
    """Get the audit logs for a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get audit logs: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        audit_logs = CommonModel.get_audit_logs(cid)
        if audit_logs:
            return {"audit_logs": audit_logs}
        return {"audit_logs": []}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/get_taxonomies", methods=['GET'])
@login_required
def get_taxonomies():
    """Get all taxonomies"""
    loc_tax = CommonModel.get_taxonomies()
    return {"taxonomies": [t["name"] for t in loc_tax]}, 200

@case_blueprint.route("/get_tags", methods=['GET'])
@login_required
def get_tags():
    """Get all tags by taxonomies"""
    data_dict = dict(request.args)
    if "taxonomies" in data_dict:
        taxos = json.loads(data_dict["taxonomies"])
        return {"tags": CommonModel.get_tags(taxos)}, 200
    return {"message": "'taxonomies' is missing", 'toast_class': "warning-subtle"}, 400


@case_blueprint.route("/get_taxonomies_case/<cid>", methods=['GET'])
@login_required
def get_taxonomies_case(cid):
    """Get all taxonomies present in a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get taxonomies of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        tags = CommonModel.get_case_tags_json(case.id)
        taxonomies = []
        if tags:
            for tag in tags:
                if not tag["name"].split(":")[0] in taxonomies:
                    taxonomies.append(tag["name"].split(":")[0])
        return {"tags": tags, "taxonomies": taxonomies}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/get_galaxies", methods=['GET'])
@login_required
def get_galaxies():
    """Get all galaxies"""
    return {"galaxies": CommonModel.get_galaxies()}, 200


@case_blueprint.route("/get_clusters", methods=['GET'])
@login_required
def get_clusters():
    """Get all clusters by galaxies"""
    if "galaxies" in request.args:
        galaxies = request.args.get("galaxies")
        galaxies = json.loads(galaxies)
        return {"clusters": CommonModel.get_clusters_galaxy(galaxies)}, 200
    return {"message": "'galaxies' is missing", 'toast_class': "warning-subtle"}, 400


@case_blueprint.route("/get_galaxies_case/<cid>", methods=['GET'])
@login_required
def get_galaxies_case(cid):
    """Get all galaxies present in a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get galaxies of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        clusters = CommonModel.get_case_clusters(cid)
        galaxies = []
        seen_galaxy_ids = set()
        if clusters:
            for i, cluster in enumerate(clusters):
                loc_g = CommonModel.get_galaxy(cluster.galaxy_id)
                if loc_g.id not in seen_galaxy_ids:
                    seen_galaxy_ids.add(loc_g.id)
                    galaxies.append(loc_g.to_json())
                clusters[i] = cluster.to_json()
        return {"clusters": clusters, "galaxies": galaxies}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/get_case_modules", methods=['GET'])
@login_required
def get_case_modules():
    """Get all modules"""
    return {"modules": CommonModel.get_modules_by_case_task('case')}, 200


@case_blueprint.route("/<cid>/get_instance_module", methods=['GET'])
@login_required
def get_instance_module(cid):
    """Get all connectors instances by modules"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get instance module of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        if "module" in request.args:
            module = request.args.get("module")
        if "type" in request.args:
            type_module = request.args.get("type")
        else:
            return{"message": "Module type error", 'toast_class': "danger-subtle"}, 400
        return {"instances": CaseModel.get_instance_module_core(module, type_module, cid, current_user.id)}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/call_module_case", methods=['GET', 'POST'])
@login_required
@misp_editor_required
def call_module_case(cid):
    """Run a module"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Call module on case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        case_instance_id = request.get_json()["case_task_instance_id"]
        module = request.get_json()["module"]
        res = CaseModel.call_module_case(module, case_instance_id, case, current_user)
        if res:
            res["toast_class"] = "danger-subtle"
            return jsonify(res), 400
        flowintel_log("audit", 200, "Module called on case", User=current_user.email, CaseId=cid, Module=module)
        return {"message": "Connector used", 'toast_class': "success-subtle"}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/get_open_close/<cid>", methods=['GET'])
@login_required
def get_open_close(cid):
    """Get the numbers of open and closed tasks"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get open/close tasks of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        cp_open, cp_closed = CaseModel.open_closed(case)
        return {"open": cp_open, "closed": cp_closed}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/all_notes", methods=['GET'])
@login_required
def all_notes(cid):
    """Get all tasks notes for a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get all notes of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        notes = CaseModel.get_all_notes(case)
        flowintel_log("audit", 200, "Get all notes of a case", User=current_user.email, CaseId=cid)
        return {"notes": notes}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/modif_note_case", methods=['POST'])
@login_required
@editor_required
def modif_note(cid):
    """Modify note of the task"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            notes = request.json["notes"]
            if CaseModel.modify_note_core(cid, current_user, notes):
                flowintel_log("audit", 200, "Note modified", User=current_user.email, CaseId=cid)
                return {"message": "Note modified", "toast_class": "success-subtle"}, 200
            return {"message": "Error add/modify note", "toast_class": "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/export_notes", methods=['GET'])
@login_required
def export_notes(cid):
    """Export note of a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Export notes of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if "type" in request.args:
            res = CommonModel.export_notes(case_task=True, case_task_id=cid, type_req=request.args.get("type"))
            try:
                CommonModel.delete_temp_folder()
            except OSError:
                pass
            flowintel_log("audit", 200, "Export notes of a case", User=current_user.email, CaseId=cid, ExportType=request.args.get("type"))
            return res
        return {"message": "'type' is missing", 'toast_class': "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/run_computer_assistate_report", methods=['GET'])
@login_required
@editor_required
def run_computer_assistate_report(cid):
    """Create a report from all case information"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Run computer assisted report: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if not CaseModel.check_exist_task(case.uuid):
            flowintel_log("audit", 200, "Run computer assisted report", User=current_user.email, CaseId=cid)
            model = request.args.get('model') if request.args.get('model') else None
            prompt = request.args.get('prompt') if request.args.get('prompt') else None
            return CaseModel.generate_computer_assistate_report(case, current_user, model=model, prompt=prompt)
        return {"message": "There's already a generation going for this case", "toast_class": "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/status_computer_assistate_report", methods=['GET'])
@login_required
def status_computer_assistate_report(cid):
    """Create a report from all case information"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get status computer assisted report: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if CaseModel.get_status_computer_assistate_report(case.uuid):
            flowintel_log("audit", 200, "Get status computer assisted report", User=current_user.email, CaseId=cid)
            return {"report_status": "running"}, 200
        return {"report_status": "done", "message": "Report generation completed"}, 200
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/get_computer_assistate_report", methods=['GET'])
@login_required
def get_computer_assistate_report(cid):
    """Create a report from all case information"""
    case = CommonModel.get_case(cid)
    if case:
        flowintel_log("audit", 200, "Get computer assisted report", User=current_user.email, CaseId=cid)

        resp = {"report": case.computer_assistate_report}
        # Include persisted model/prompt if available
        try:
            if getattr(case, 'computer_assistate_model', None):
                resp["model"] = case.computer_assistate_model
            if getattr(case, 'computer_assistate_prompt', None):
                resp["prompt"] = case.computer_assistate_prompt
        except Exception:
            pass
        return resp
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/export_computer_assistate_report", methods=['GET'])
@login_required
def export_computer_assistate_report(cid):
    """Export note of a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Export computer assisted report of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if "type" in request.args:
            res = CommonModel.export_notes_core(case_task_id=None, 
                                                type_req=request.args.get("type"), 
                                                note=case.computer_assistate_report, 
                                                download_filename=f"case_{case.uuid}_computer_assistate_report")
            try:
                CommonModel.delete_temp_folder()
            except OSError:
                pass
            if isinstance(res, dict):
                return res, 400
            flowintel_log("audit", 200, "Export computer assisted report of a case", User=current_user.email, CaseId=cid, ExportType=request.args.get("type"))
            return res
        return {"message": "'type' is missing", 'toast_class': "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/list_ollama_models", methods=['GET'])
@login_required
def list_ollama_models():
    """Return a list of available models from the configured Ollama server"""
    if not ConfigModule.OLLAMA_URL:
        return {"message": "Ollama URL not configured", 'toast_class': "warning-subtle"}, 400

    url = f"{ConfigModule.OLLAMA_URL}/api/tags"
    headers = {}
    if getattr(ConfigModule, 'OLLAMA_KEY', None):
        headers["Authorization"] = f"Bearer {ConfigModule.OLLAMA_KEY}"

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        models = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    name = item.get('name') or item.get('model') or item.get('id')
                    if name:
                        models.append(name)
                elif isinstance(item, str):
                    models.append(item)
        elif isinstance(data, dict) and 'models' in data and isinstance(data['models'], list):
            for item in data['models']:
                if isinstance(item, dict):
                    name = item.get('name') or item.get('model') or item.get('id')
                    if name:
                        models.append(name)
        flowintel_log("audit", 200, "List ollama models", User=current_user.email)
        return {"models": models}, 200
    except requests.RequestException as e:
        flowintel_log("error", 500, f"Error listing ollama models: {e}", User=current_user.email)
        return {"message": "Unable to reach Ollama", 'toast_class': "danger-subtle"}, 500


@case_blueprint.route("/get_orgs", methods=['GET'])
@login_required
def get_orgs():
    """Get all orgs"""
    orgs = CommonModel.get_orgs()
    return [org.to_json() for org in orgs], 200

@case_blueprint.route("/get_custom_tags_case/<cid>", methods=['GET'])
@login_required
def get_custom_tags_case(cid):
    """Get all custom tags for a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get custom tags of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        return {"custom_tags": CommonModel.get_case_custom_tags_json(cid)}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/<cid>/download_history", methods=['GET'])
@login_required
def download_file(cid):
    """Download the file"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            flowintel_log("audit", 200, "Download case history", User=current_user.email, CaseId=cid)
            return CaseModel.download_history(case)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/download_history_md", methods=['GET'])
@login_required
def download_history_md(cid):
    """Download the file"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            flowintel_log("audit", 200, "Download case markdown", User=current_user.email, CaseId=cid)
            return CaseModel.download_history_md(case)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/download_audit_logs", methods=['GET'])
@login_required
def download_audit_logs(cid):
    """Download the audit logs as text file"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            return CommonModel.download_audit_logs(case)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/download_audit_logs_md", methods=['GET'])
@login_required
def download_audit_logs_md(cid):
    """Download the audit logs as markdown file"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            return CommonModel.download_audit_logs_md(case)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

@case_blueprint.route("/<cid>/add_new_link", methods=['GET', 'POST'])
@login_required
@editor_required
def add_new_link(cid):
    """Add a new link to the case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if request.json:
                if "case_id" in request.json:
                    if CaseModel.add_new_link(request.json, cid, current_user):
                        flowintel_log("audit", 200, "Case link added", User=current_user.email, CaseId=cid, LinkedCaseId=request.json["case_id"])
                        return {"message": "Link added", "toast_class": "success-subtle"}, 200
                    return {"message": "A Case doesn't exist", "toast_class": "danger-subtle"}, 404
                return {"message": "Need to pass 'case_id'", "toast_class": "warning-subtle"}, 400
            return {"message": "An error occur", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Add case link: Permission denied", User=current_user.email, CaseId=cid)
        return {"message": "Permission denied", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

@case_blueprint.route("/<cid>/remove_case_link/<clid>", methods=['GET'])
@login_required
@editor_required
def remove_case_link(cid, clid):
    """Remove an org to the case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.remove_case_link(cid, clid, current_user):
                flowintel_log("audit", 200, "Case link removed", User=current_user.email, CaseId=cid, LinkId=clid)
                return {"message": "Link removed", "toast_class": "success-subtle"}, 200
            return {"message": "Error removing link from case", "toast_class": "danger-subtle"}, 400
        flowintel_log("audit", 403, "Remove case link: Action not allowed", User=current_user.email, CaseId=cid, LinkId=clid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/change_hedgedoc_url", methods=['POST'])
@login_required
@editor_required
def change_hedgedoc_url(cid):
    """Change hedgedoc url of the case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "hedgedoc_url" in request.json:
                if CaseModel.change_hedgedoc_url(request.json, cid, current_user):
                    flowintel_log("audit", 200, "HedgeDoc URL changed", User=current_user.email, CaseId=cid)
                    return {"message": "Link removed", "toast_class": "success-subtle"}, 200
                return {"message": "Error removing link from case", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'hedgedoc_url'", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Change HedgeDoc URL: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/<cid>/get_hedgedoc_notes", methods=['GET'])
@login_required
@editor_required
def get_hedgedoc_notes(cid):
    """Get hedgedoc notes of the case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            flowintel_log("audit", 200, "Get HedgeDoc notes", User=current_user.email, CaseId=cid)
            return CaseModel.get_hedgedoc_notes(cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


###############
# MISP Object #
###############
@case_blueprint.route("/<int:cid>/get_case_misp_object", methods=['GET'])
@login_required
def get_case_misp_object(cid):
    """Get case list of misp object"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get MISP objects of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        misp_object = CaseModel.get_misp_object_by_case(cid)
        loc_object = list()
        for object in misp_object:
            loc_attr_list = list()
            for attribute in object.attributes:
                res = CaseModel.check_correlation_attr(cid, attribute)
                loc_attr = attribute.to_json()
                loc_attr["correlation_list"] = res
                loc_attr_list.append(loc_attr)

            loc_object.append({
                "object_name": object.name,
                "attributes": loc_attr_list,
                "object_id": object.id,
                "object_uuid": object.template_uuid,
                "object_creation_date": object.creation_date.strftime('%Y-%m-%d %H:%M'),
                "object_last_modif": object.last_modif.strftime('%Y-%m-%d %H:%M')
            })
        return {"misp-object": loc_object}
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/<int:cid>/get_correlation_attr/<int:aid>", methods=['GET'])
@login_required
def get_correlation_attr(cid, aid):
    attribute = CaseModel.get_misp_attribute(aid)
    res = CaseModel.check_correlation_attr(cid, attribute)
    return {"correlation_list": res}, 200

@case_blueprint.route("/get_misp_object", methods=['GET'])
@login_required
def get_misp_object():
    """Get list of misp object"""
    return {"misp-object": get_object_templates()}, 200

@case_blueprint.route("/<cid>/create_misp_object", methods=['POST'])
@login_required
@editor_required
def create_misp_object(cid):
    """Create misp object"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "object-template" in request.json:
                if "attributes" in request.json:
                    CaseModel.create_misp_object(cid, request.json, current_user)
                    flowintel_log("audit", 200, "MISP object created", User=current_user.email, CaseId=cid, ObjectTemplate=request.json["object-template"])
                    return {"message": "Object created", "toast_class": "success-subtle"}, 200
                return {"message": "Need to pass 'attributes'", "toast_class": "warning-subtle"}, 400
            return {"message": "Need to pass 'object-template'", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Create MISP object: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/<cid>/delete_object/<oid>", methods=['GET'])
@login_required
@editor_required
def delete_object(cid, oid):
    """Delete an object from case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.delete_object(cid, oid, current_user):
                flowintel_log("audit", 200, "MISP object deleted", User=current_user.email, CaseId=cid, ObjectId=oid)
                return {"message": "Object deleted", "toast_class": "success-subtle"}, 200
            return {"message": "Object not found in this case", "toast_class": "warning-subtle"}, 404
        flowintel_log("audit", 403, "Delete MISP object: Action not allowed", User=current_user.email, CaseId=cid, ObjectId=oid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/<cid>/add_attributes/<oid>", methods=['POST'])
@login_required
@editor_required
def add_attributes(cid, oid):
    """Add attributes to an existing object"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "object-template" in request.json:
                if "attributes" in request.json:
                    if CaseModel.add_attributes_object(cid, oid, request.json):
                        flowintel_log("audit", 200, "Attributes added to MISP object", User=current_user.email, CaseId=cid, ObjectId=oid)
                        return {"message": "Receive", "toast_class": "success-subtle"}, 200
                    return {"message": "Object not found in this case", "toast_class": "warning-subtle"}, 404
                return {"message": "Need to pass 'attributes'", "toast_class": "warning-subtle"}, 400
            return {"message": "Need to pass 'object-template'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/misp_object/<oid>/edit_attr/<aid>", methods=['POST'])
@login_required
@editor_required
def edit_attr(cid, oid, aid):
    """Edit misp object"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "value" in request.json:
                if "type" in request.json:
                    flowintel_log("audit", 200, "Edit attribute of MISP object", User=current_user.email, CaseId=cid, ObjectId=oid, AttributeId=aid)
                    return CaseModel.edit_attr(cid, oid, aid, request.json)
                return {"message": "Need to pass 'value'", "toast_class": "warning-subtle"}, 400
            return {"message": "Need to pass 'type'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/misp_object/<oid>/delete_attribute/<aid>", methods=['GET'])
@login_required
@editor_required
def delete_attribute(cid, oid, aid):
    """Delete an object from case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            flowintel_log("audit", 200, "Delete attribute of MISP object", User=current_user.email, CaseId=cid, ObjectId=oid, AttributeId=aid)
            return CaseModel.delete_attribute(cid, oid, aid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/nb_objects", methods=['GET'])
@login_required
def nb_objects(cid):
    """Return nb of misp objects"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get number of MISP objects of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        return {"nb_objects": len(CaseModel.get_misp_object_by_case(cid))}, 200
    return {"message": "Case not found"}, 404



#############
# Connector #
#############

@case_blueprint.route("/<cid>/get_case_connectors", methods=['GET', 'POST'])
@login_required
@misp_editor_required
def get_case_connectors(cid):
    """Get all connectors for a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get connectors of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        instance_list = list()
        misp_connector = CommonModel.get_connector_by_name("MISP")
        for case_connector in CommonModel.get_case_connectors(cid, current_user):
            is_misp_connector = False
            if misp_connector:
                connect_instance = CommonModel.get_instance(case_connector.instance_id)
                if connect_instance and connect_instance.connector_id == misp_connector.id:
                    is_misp_connector = True
            instance_list.append({
                "case_task_instance_id": case_connector.id,
                "details": CommonModel.get_instance_with_icon(case_connector.instance_id),
                "identifier": case_connector.identifier,
                "is_updating_case": case_connector.is_updating_case,
                "is_misp_connector": is_misp_connector
            })
        return {"case_connectors": instance_list}, 200
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/add_connector", methods=['POST'])
@login_required
@misp_editor_required
def add_connector(cid):
    """Add MISP Connector"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "connectors" in request.json and CaseModel.add_connector(cid, request.json, current_user):
                flowintel_log("audit", 200, "Connector added to case", User=current_user.email, CaseId=cid)
                return {"message": "Connector added successfully", "toast_class": "success-subtle"}, 200
            return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Add connector to case: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/connectors/<ciid>/remove_connector", methods=['GET'])
@login_required
@misp_editor_required
def remove_connector(cid, ciid):
    """Remove a connector from case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.remove_connector(ciid):
                flowintel_log("audit", 200, "Connector removed from case", User=current_user.email, CaseId=cid, ConnectorInstanceId=ciid)
                return {"message": "Connector removed", 'toast_class': "success-subtle"}, 200
            return {"message": "Something went wrong", 'toast_class': "danger-subtle"}, 400
        flowintel_log("audit", 403, "Remove connector from case: Action not allowed", User=current_user.email, CaseId=cid, ConnectorInstanceId=ciid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/connectors/<ciid>/edit_connector", methods=['POST'])
@login_required
@misp_editor_required
def edit_connector(cid, ciid):
    """Edit Connector"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "identifier" in request.json:
                if CaseModel.edit_connector(ciid, request.json):
                    flowintel_log("audit", 200, "Connector edited", User=current_user.email, CaseId=cid, ConnectorInstanceId=ciid)
                    return {"message": "Connector edited successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Error editing connector", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Edit connector: Action not allowed", User=current_user.email, CaseId=cid, ConnectorInstanceId=ciid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/update_case/<iid>", methods=['GET'])
@login_required
@misp_editor_required
def update_case(cid, iid):
    """Update case from MISP connector"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            res = CaseModel.receive_from_misp(iid, cid, current_user)
            if not isinstance(res, dict):
                flowintel_log("audit", 200, "Case updated from MISP connector", User=current_user.email, CaseId=cid, ConnectorInstanceId=iid)
                flash("Objects updated successfully", "success")
                return {"message": "Connector removed", 'toast_class': "success-subtle"}, 200
            else:
                res["toast_class"] = "danger-subtle"
                return res, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404

#################
# Note Template #
#################

@case_blueprint.route("/<cid>/get_note_template", methods=['GET'])
@login_required
def get_note_template(cid):
    """Get note template of a case"""
    case_note_template = CaseModel.get_case_note_template(cid)
    if case_note_template:
        template = CaseModel.get_note_template_model(case_note_template.note_template_id)
        return {"case_note_template": case_note_template.to_json(), "current_template": template.to_json()}, 200
    return {"message": "No note template for the case"}, 404


@case_blueprint.route("/<cid>/create_note_template_case", methods=['POST'])
@login_required
@editor_required
def create_note_template_case(cid):
    """Create note template of a case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "values" in request.json and "template_id" in request.json:
                if CaseModel.create_note_template(cid, request.json, current_user):
                    flowintel_log("audit", 200, "Case note template created", User=current_user.email, CaseId=cid, TemplateId=request.json["template_id"])
                    return {"message": "Note template modified successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400
            return {"message": "Missing parameters", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Create case note template: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/modif_note_template_case", methods=['POST'])
@login_required
@editor_required
def modif_note_template_case(cid):
    """Modify note template of a case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "values" in request.json:
                if CaseModel.modif_note_template(cid, request.json, current_user):
                    flowintel_log("audit", 200, "Case note template modified", User=current_user.email, CaseId=cid)
                    return {"message": "Note template modified successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400
            return {"message": "No values passed", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Modify case note template: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/modif_note_template_content", methods=['POST'])
@login_required
@editor_required
def modif_note_template_content(cid):
    """Modify Content of note template of a case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "content" in request.json:
                if CaseModel.modif_content_note_template(cid, request.json, current_user):
                    flowintel_log("audit", 200, "Case note template content modified", User=current_user.email, CaseId=cid)
                    return {"message": "Note template modified successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400
            return {"message": "No content passed", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/export_notes_template", methods=['POST'])
@login_required
def export_notes_template(cid):
    """Export note of a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Export notes template of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if "type" in request.args:
            if "content" in request.json:
                res = CommonModel.export_notes_core(case_task_id=cid, type_req=request.args.get("type"), note=request.json["content"])
                try:
                    CommonModel.delete_temp_folder()
                except OSError:
                    pass
                flowintel_log("audit", 200, "Export notes template of a case", User=current_user.email, CaseId=cid, ExportType=request.args.get("type"))
                return res
            return {"message": "No content passed", "toast_class": "warning-subtle"}, 400
        return {"message": "'type' is missing", 'toast_class': "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/remove_note_template", methods=['GET'])
@login_required
@editor_required
def remove_note_template(cid):
    """Remove note template of a case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.remove_note_template(cid):
                flowintel_log("audit", 200, "Case note template removed", User=current_user.email, CaseId=cid)
                return {"message": "Note Template removed", "toast_class": "success-subtle"}, 200
            return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Remove case note template: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/add_files", methods=['POST'])
@login_required
@editor_required
def add_files(cid):
    """Add files to a case"""
    from ..utils.utils import validate_file_size
    
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            files_list = request.files
            if files_list:
                # Validate file sizes before processing
                for file_key in files_list:
                    file_obj = files_list[file_key]
                    if file_obj.filename:
                        is_valid, error_msg, file_size_mb = validate_file_size(file_obj)
                        if not is_valid:
                            flowintel_log("audit", 400, "Add files to case: File size too large", User=current_user.email, CaseId=cid, FileName=file_obj.filename, FileSizeMB=file_size_mb)
                            return {"message": error_msg, "toast_class": "danger-subtle"}, 400
                
                created_files = CaseModel.add_file_core(case, files_list, current_user)
                if created_files:
                    files_count = len(created_files)
                    total_size = sum(f.file_size for f in created_files)
                    file_names = ", ".join([f.name for f in created_files])
                    flowintel_log("audit", 200, "Files added to case", User=current_user.email, CaseId=cid, FilesCount=files_count, TotalSize=total_size, FileNames=file_names)
                    return {"message": f"{files_count} file(s) uploaded successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Error uploading files", "toast_class": "danger-subtle"}, 400
            return {"message": "No files provided", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Add files to case: Permission denied", User=current_user.email, CaseId=cid)
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/download_case_file/<fid>", methods=['GET'])
@login_required
def download_case_file(cid, fid):
    """Download a file from a case"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            file = File.query.get(fid)
            if file and file.case_id == int(cid):
                flowintel_log("audit", 200, "File downloaded from case", User=current_user.email, CaseId=cid, FileId=fid, FileName=file.name)
                return CaseModel.download_file(file)
            return {"message": "File not found", "toast_class": "danger-subtle"}, 404
        flowintel_log("audit", 403, "Download file from case: Permission denied", User=current_user.email, CaseId=cid, FileId=fid)
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/delete_case_file/<fid>", methods=['GET'])
@login_required
@editor_required
def delete_case_file(cid, fid):
    """Delete a file from a case"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            file = File.query.get(fid)
            if file and file.case_id == int(cid):
                file_name = file.name
                if CaseModel.delete_file(file, case, current_user):
                    flowintel_log("audit", 200, "File deleted from case", User=current_user.email, CaseId=cid, FileId=fid, FileName=file_name)
                    return {"message": "File deleted", "toast_class": "success-subtle"}, 200
                return {"message": "Error deleting file", "toast_class": "danger-subtle"}, 400
            return {"message": "File not found", "toast_class": "danger-subtle"}, 404
        flowintel_log("audit", 403, "Delete file from case: Permission denied", User=current_user.email, CaseId=cid, FileId=fid)
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


########
# Report
########

@case_blueprint.route("/<cid>/report", methods=['GET'])
@login_required
@admin_required
def case_report(cid):
    """Render the report builder page for a case"""
    case = CommonModel.get_case(cid)
    if not case:
        abort(404)
    return render_template("case/case_report.html", case=case)


@case_blueprint.route("/<cid>/report/generate", methods=['POST'])
@login_required
@admin_required
def case_report_generate(cid):
    """Generate and return the Markdown report text for a case"""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found"}, 404

    def _text_color(hex_color):
        h = (hex_color or '#888888').lstrip('#')
        try:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            return 'white'
        return 'white' if (299 * r + 587 * g + 114 * b) / 1000 < 128 else 'black'

    def _tag_badge(name, color):
        tc = _text_color(color or '#888888')
        bg = color or '#888888'
        return f'<span class="tag" style="background-color:{bg};color:{tc};">{name}</span>'

    def _cluster_badge(label):
        return f'<span class="cluster">{label}</span>'

    opts = request.json or {}
    tasks = case.tasks.all()

    try:
        ver_path = os.path.join(current_app.root_path, '..', 'version')
        with open(ver_path) as _vf:
            _version = _vf.read().strip()
    except Exception:
        _version = 'unknown'

    lines = []
    lines.append("# Case report")
    lines.append("")

    main_logo = current_app.config.get('MAIN_LOGO', '')
    topright_logo = current_app.config.get('TOPRIGHT_LOGO', '')
    logo_html = ''
    if main_logo:
        logo_html += f'<img src="{main_logo}" style="height:50px; margin-right:10px;">'
    if topright_logo:
        logo_html += f'<img src="{topright_logo}" style="height:50px; float:right;">'
    if logo_html:
        lines.append(logo_html)
        lines.append("")

    if opts.get("include_metadata", True):
        lines.append("---")
        lines.append("")
        lines.append("## Case information")

        lines.append(f"- **Case ID:** {case.id}")

        created = case.creation_date.strftime('%Y-%m-%d %H:%M') if case.creation_date else "—"
        lines.append(f"- **Date created:** {created}")

        owner_org = CommonModel.get_org(case.owner_org_id)
        lines.append(f"- **Owner:** {owner_org.name if owner_org else '—'}")

        orgs = CommonModel.get_orgs_in_case(case.id)
        if orgs:
            lines.append("- **Organisations:** " + ", ".join(o.name for o in orgs if o))
        else:
            lines.append("- **Organisations:** —")

        linked = Case.query.join(Case_Link_Case, Case_Link_Case.case_id_2 == Case.id)\
                            .filter(Case_Link_Case.case_id_1 == case.id).all()
        if linked:
            lines.append("- **Linked cases:** " + ", ".join(f"{lc.title} (#{lc.id})" for lc in linked))
        else:
            lines.append("- **Linked cases:** —")

        flags = []
        if case.privileged_case:
            flags.append("Privileged")
        if case.is_private:
            flags.append("Private")
        if flags:
            lines.append("- **Flags:** " + ", ".join(flags))

        if case.deadline:
            lines.append(f"- **Deadline:** {case.deadline.strftime('%Y-%m-%d %H:%M')}")
        if case.time_required:
            lines.append(f"- **Time required:** {case.time_required}")
        if case.ticket_id:
            lines.append(f"- **Ticket ID:** {case.ticket_id}")

        case_connectors = CommonModel.get_case_connectors_name(cid)
        if case_connectors:
            lines.append("- **Connectors:** " + ", ".join(case_connectors))

        total = len(tasks)
        done = sum(1 for t in tasks if t.completed)
        pct = int(done / total * 100) if total > 0 else 0
        lines.append(f"- **Completion:** {done}/{total} tasks ({pct}%)")

        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        user_label = f"{current_user.first_name} {current_user.last_name} ({current_user.email})"
        lines.append(f"- **Report generated on:** {now} by {user_label}")

        url = f"http://{current_app.config.get('FLASK_URL', '127.0.0.1')}:{current_app.config.get('FLASK_PORT', 7006)}"
        lines.append(f"- **Instance URL:** {url}")
        lines.append(f"- **Instance version:** {_version}")

        lines.append("")

    if opts.get("include_title", True):
        lines.append("---")
        lines.append("")
        lines.append(f"## Case: {case.title}")
        lines.append("")

    if opts.get("include_description", True):
        lines.append("---")
        lines.append("")
        lines.append("### Description")
        desc = (case.description or "—").replace("```", "")
        lines.append("```")
        lines.extend(desc.splitlines())
        lines.append("```")
        lines.append("")

    if opts.get("include_tasks", True):
        lines.append("---")
        lines.append("")
        lines.append("### Tasks")
        if tasks:
            for task in tasks:
                status_mark = "✓" if task.completed else "○"
                lines.append(f"#### [{status_mark}] {task.title}")
                if task.description:
                    lines.append(task.description)
                lines.append("")

                task_status = CommonModel.get_status(task.status_id)
                lines.append(f"- **Status:** {task_status.name if task_status else '—'}")

                user_ids = [tu.user_id for tu in Task_User.query.filter_by(task_id=task.id).all()]
                if user_ids:
                    owners = User.query.filter(User.id.in_(user_ids)).all()
                    owner_str = ", ".join(f"{u.first_name} {u.last_name} ({u.email})" for u in owners)
                    lines.append(f"- **Owner(s):** {owner_str}")
                else:
                    lines.append("- **Owner(s):** —")

                if task.deadline:
                    lines.append(f"- **Deadline:** {task.deadline.strftime('%Y-%m-%d %H:%M')}")
                if task.time_required:
                    lines.append(f"- **Time required:** {task.time_required}")

                task_tags_json = CommonModel.get_task_tags_json(task.id)
                task_clusters = CommonModel.get_task_clusters(task.id)
                task_galaxies = CommonModel.get_task_galaxies(task.id)

                if task_tags_json:
                    badges = " ".join(_tag_badge(t['name'], t['color']) for t in task_tags_json)
                    lines.append(f"- **Tags:** {badges}")
                if task_clusters:
                    badges = " ".join(_cluster_badge(c.tag) for c in task_clusters)
                    lines.append(f"- **Galaxy clusters:** {badges}")
                if task_galaxies:
                    lines.append("- **Galaxies:** " + ", ".join(g.name for g in task_galaxies))

                subtasks = task.subtasks.all()
                if subtasks:
                    lines.append("- **Subtasks:**")
                    for st in subtasks:
                        tick = "✓" if st.completed else "○"
                        lines.append(f"  - [{tick}] {st.description}")

                urls_tools = task.urls_tools.all()
                if urls_tools:
                    lines.append("- **URL/Tools:** " + ", ".join(ut.name for ut in urls_tools if ut.name))

                ext_refs = task.external_references.all()
                if ext_refs:
                    lines.append("- **External references:** " + ", ".join(er.url for er in ext_refs))

                task_connectors = CommonModel.get_task_connectors_name(task.id)
                if task_connectors:
                    lines.append("- **Connectors:** " + ", ".join(task_connectors))

                lines.append("")
        else:
            lines.append("No tasks.")
            lines.append("")

    if opts.get("include_notes", False):
        lines.append("---")
        lines.append("")
        lines.append("### Notes")
        lines.append("")
        has_notes = False

        if case.notes:
            has_notes = True
            lines.append("#### Case note")
            lines.append("")
            resolved_case_note = resolve_variables(case.notes, case_id=case.id)
            lines.append("```")
            lines.extend(line.replace("```", "") for line in resolved_case_note.splitlines())
            lines.append("```")
            lines.append("")

        task_note_sections = CaseModel.get_all_notes(case)
        if task_note_sections:
            has_notes = True
            lines.append("#### Task notes")
            lines.append("")
            for section in task_note_sections:
                section_text = section["text"] if isinstance(section, dict) else section
                task_id = section["task_id"] if isinstance(section, dict) else None
                resolved_section = resolve_variables(section_text, case_id=case.id, task_id=task_id)
                lines.append("```")
                lines.extend(line.replace("```", "") for line in resolved_section.splitlines())
                lines.append("```")
                lines.append("")

        if not has_notes:
            lines.append("No notes.")
            lines.append("")

    if opts.get("include_files", True):
        lines.append("---")
        lines.append("")
        lines.append("### Files")
        lines.append("")

        task_ids = [t.id for t in tasks]
        case_files = File.query.filter_by(case_id=case.id, task_id=None).all()
        task_files = File.query.filter(File.task_id.in_(task_ids)).all() if task_ids else []
        all_files = case_files + task_files

        if all_files:
            task_map = {t.id: t.title for t in tasks}
            lines.append("| Filename | Size | Type | Attached to |")
            lines.append("|---|---|---|---|")
            for f in all_files:
                size = f"{f.file_size:,} B" if f.file_size is not None else "Unknown"
                ftype = f.file_type or "Unknown"
                attached = "Case" if not f.task_id else f"Task: {task_map.get(f.task_id, 'Unknown')}"
                lines.append(f"| {f.name} | {size} | {ftype} | {attached} |")
        else:
            lines.append("No files.")
        lines.append("")

    case_tags_json = CommonModel.get_case_tags_json(cid)

    if opts.get("include_tags", True):
        lines.append("---")
        lines.append("")
        lines.append("### Tags and galaxies")

        if case_tags_json:
            badges = " ".join(_tag_badge(t['name'], t['color']) for t in case_tags_json)
            lines.append(f"**Tags:** {badges}")

        custom_tags = CommonModel.get_case_custom_tags_json(case.id)
        if custom_tags:
            badges = " ".join(_tag_badge(ct['name'], ct['color']) for ct in custom_tags)
            lines.append(f"**Custom tags:** {badges}")

        clusters = CommonModel.get_case_clusters(cid)
        if clusters:
            badges = " ".join(_cluster_badge(c.tag) for c in clusters)
            lines.append(f"**Galaxy clusters:** {badges}")

        lines.append("")

    if opts.get("include_objects", True):
        lines.append("---")
        lines.append("")
        lines.append("### Objects")
        objects = CaseModel.get_misp_object_by_case(cid)
        if objects:
            for obj in objects:
                lines.append(f"#### {obj.name}")
                for attr in obj.attributes:
                    lines.append(f"  - {attr.object_relation}: {attr.value}")
        else:
            lines.append("No objects.")
        lines.append("")

    if opts.get("include_taxonomies", False):
        lines.append("---")
        lines.append("")
        lines.append("### Appendix — Taxonomies")
        seen_taxo = {}
        for t in case_tags_json:
            name = t['name']
            taxo_name = name.split(":")[0] if ":" in name else name
            seen_taxo.setdefault(taxo_name, []).append(t)
        if seen_taxo:
            for taxo, tag_objs in sorted(seen_taxo.items()):
                lines.append(f"#### {taxo}")
                for t in tag_objs:
                    badge = _tag_badge(t['name'], t['color'])
                    lines.append(f"  - {badge}")
        else:
            lines.append("No taxonomy tags.")
        lines.append("")

    if opts.get("include_audit", False):
        lines.append("---")
        lines.append("")
        lines.append("### Audit logs")
        audit = CommonModel.get_audit_logs(case.id)
        if audit:
            for entry in audit:
                lines.append(f"- {entry}")
        else:
            lines.append("No audit logs found.")
        lines.append("")

    if opts.get("include_timeline", False):
        lines.append("---")
        lines.append("")
        lines.append("### Timeline")
        history = CommonModel.get_history(case.uuid)
        if history:
            for entry in history:
                lines.append(f"- {entry}")
        else:
            lines.append("No history recorded.")
        lines.append("")

    flowintel_log("audit", 200, "Case report generated",
                  User=current_user.email, CaseId=cid,
                  Options=", ".join(k for k, v in opts.items() if v))

    report_text = "\n".join(lines)
    result = {"report": report_text}

    try:
        sig = sign_text(report_text)
    except Exception as e:
        sig = {"error": str(e)}

    if sig and "error" not in sig:
        result["signature"] = sig["signature"]
        result["signed_by"] = sig["signed_by"]
        result["signed_at"] = sig["signed_at"]
    elif sig and "error" in sig:
        result["signature_error"] = sig["error"]

    return result


@case_blueprint.route("/<cid>/report/attach_pdf", methods=['POST'])
@login_required
@admin_required
def case_report_attach_pdf(cid):
    """Save the generated PDF report as a file attached to the case"""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

    if 'file' not in request.files or not request.files['file'].filename:
        return {"message": "No PDF provided", "toast_class": "warning-subtle"}, 400

    created_files = CaseModel.add_file_core(case, request.files, current_user)
    if created_files:
        names = ", ".join(f.name for f in created_files)
        flowintel_log("audit", 200, "Case report attached",
                      User=current_user.email, CaseId=cid, Files=names)
        return {"message": "Report attached to case", "toast_class": "success-subtle"}, 200
    return {"message": "Failed to attach PDF", "toast_class": "danger-subtle"}, 400
  
@case_blueprint.route("/<cid>/convert_case_file_to_note/<fid>", methods=['POST'])
@login_required
@editor_required
def convert_case_file_to_note(cid, fid):
    """Convert a file attached to a case into a case note"""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

    if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
        flowintel_log("audit", 403, "Convert case file to note: Permission denied", User=current_user.email, CaseId=cid, FileId=fid)
        return {"message": "Permission denied", "toast_class": "warning-subtle"}, 403

    file = CommonModel.get_file(fid)
    if not file or file.case_id != int(cid):
        return {"message": "File not found", "toast_class": "danger-subtle"}, 404

    file_extension = os.path.splitext(file.name)[1].lower().lstrip('.')
    if file_extension not in ['txt', 'csv', 'json']:
        return {"message": "Only TXT, CSV, and JSON files can be converted", "toast_class": "warning-subtle"}, 400

    file_path = os.path.join(FILE_FOLDER, file.uuid)
    success, content = convert_file_to_note_content(file_path, file_extension, file.name)

    if not success:
        flowintel_log("audit", 400, "Case file conversion failed", User=current_user.email, CaseId=cid, FileId=fid, FileName=file.name, Error=content)
        return {"message": f"Conversion failed: {content}", "toast_class": "danger-subtle"}, 400

    existing_notes = case.notes or ""
    new_notes = (existing_notes + "\n\n" + content).strip()
    if not CaseModel.modify_note_core(cid, current_user, new_notes):
        return {"message": "Error saving note", "toast_class": "danger-subtle"}, 400
    flowintel_log("audit", 200, "Case file converted to note", User=current_user.email, CaseId=cid, FileId=fid, FileName=file.name)
    return {"message": f"File '{file.name}' converted to note successfully", "toast_class": "success-subtle", "notes": new_notes}, 200


#####################
# Note Variables    #
#####################

@case_blueprint.route("/<cid>/resolve_note_variables", methods=['POST'])
@login_required
def resolve_note_variables(cid):
    """Resolve @-prefixed variable references in note text"""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404
    if not check_user_private_case(case):
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
    
    text = request.json.get("text", "")
    task_id = request.json.get("task_id", None)
    mark = request.json.get("mark", False)
    
    resolved = resolve_variables(text, case_id=int(cid), task_id=int(task_id) if task_id else None, mark=bool(mark))
    return {"resolved": resolved}, 200


@case_blueprint.route("/note_variables_reference", methods=['GET'])
@login_required
def note_variables_reference():
    """Return the complete syntax reference for note variables"""
    return {"reference": get_syntax_reference()}, 200
