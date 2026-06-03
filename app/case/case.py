import ast
import json
from flask import Blueprint, render_template, redirect, jsonify, request, flash, current_app
from flask_login import login_required, current_user

from .form import CaseForm, CaseEditForm, RecurringForm
from .CaseCore import CaseModel
from . import common_core as CommonModel
from .TaskCore import TaskModel
from ..db_class.db import Case, Task_Template, Case_Template, File
from ..decorators import editor_required, template_editor_required
from ..utils.utils import form_to_dict
from ..utils.formHelper import prepare_tags
from ..utils.logger import flowintel_log

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
            form._case_id = int(cid)

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

@case_blueprint.route("/get_orgs", methods=['GET'])
@login_required
def get_orgs():
    """Get all orgs"""
    orgs = CommonModel.get_orgs()
    return [org.to_json() for org in orgs], 200

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
        
        return_dict = case.download()
        return_dict["tasks"] = [task.download() for task in case.tasks]
        return_dict["misp-objects"] = [obj.download() for obj in CaseModel.get_misp_object_by_case(cid)]
        return_dict["standalone_attributes"] = [attr.download() for attr in CaseModel.get_standalone_attributes_by_case(cid)]
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

        if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
            flowintel_log("audit", 403, "Merge case: Org not assigned to case", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403

        if case.privileged_case and not (current_user.is_admin() or current_user.is_case_admin()):
            flowintel_log("audit", 403, "Merge case: Privileged case requires admin permissions", User=current_user.email, CaseId=cid)
            return {"message": "Cannot merge privileged cases", 'toast_class': "danger-subtle"}, 403
        
        merging_case = CommonModel.get_case(ocid)
        if not merging_case:
            return {"message": "Target case not found", 'toast_class': "danger-subtle"}, 404

        if merging_case.id == case.id:
            flowintel_log("audit", 400, "Merge case: Cannot merge a case into itself", User=current_user.email, CaseId=cid)
            return {"message": "Cannot merge a case into itself", 'toast_class': "warning-subtle"}, 400

        if not check_user_private_case(merging_case):
            flowintel_log("audit", 403, "Merge case: Permission denied for target case", User=current_user.email, CaseId=cid, TargetCaseId=ocid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403

        if not (CommonModel.get_present_in_case(ocid, current_user) or current_user.is_admin()):
            flowintel_log("audit", 403, "Merge case: Org not assigned to target case", User=current_user.email, CaseId=cid, TargetCaseId=ocid)
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

        if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
            flowintel_log("audit", 403, "Create template from case: Org not assigned to case", User=current_user.email, CaseId=cid)
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


##############
#  History & #
# Audit Logs #
##############

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


@case_blueprint.route("/<cid>/download_history", methods=['GET'])
@login_required
def download_file(cid):
    """Download the file"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Download case history: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", "toast_class": "warning-subtle"}, 403
        if not (current_user.is_admin() or current_user.is_case_admin() or current_user.is_audit_viewer()):
            flowintel_log("audit", 403, "Download case history: Access restricted", User=current_user.email, CaseId=cid)
            return {"message": "Access restricted", "toast_class": "warning-subtle"}, 403
        flowintel_log("audit", 200, "Download case history", User=current_user.email, CaseId=cid)
        return CaseModel.download_history(case)
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/download_history_md", methods=['GET'])
@login_required
def download_history_md(cid):
    """Download the file"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Download case markdown: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", "toast_class": "warning-subtle"}, 403
        if not (current_user.is_admin() or current_user.is_case_admin() or current_user.is_audit_viewer()):
            flowintel_log("audit", 403, "Download case markdown: Access restricted", User=current_user.email, CaseId=cid)
            return {"message": "Access restricted", "toast_class": "warning-subtle"}, 403
        flowintel_log("audit", 200, "Download case markdown", User=current_user.email, CaseId=cid)
        return CaseModel.download_history_md(case)
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/download_audit_logs", methods=['GET'])
@login_required
def download_audit_logs(cid):
    """Download the audit logs as text file"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Download audit logs: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", "toast_class": "warning-subtle"}, 403
        if not (current_user.is_admin() or current_user.is_case_admin() or current_user.is_audit_viewer()):
            flowintel_log("audit", 403, "Download audit logs: Access restricted", User=current_user.email, CaseId=cid)
            return {"message": "Access restricted", "toast_class": "warning-subtle"}, 403
        flowintel_log("audit", 200, "Download audit logs", User=current_user.email, CaseId=cid)
        return CommonModel.download_audit_logs(case)
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/download_audit_logs_md", methods=['GET'])
@login_required
def download_audit_logs_md(cid):
    """Download the audit logs as markdown file"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Download audit logs markdown: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", "toast_class": "warning-subtle"}, 403
        if not (current_user.is_admin() or current_user.is_case_admin() or current_user.is_audit_viewer()):
            flowintel_log("audit", 403, "Download audit logs markdown: Access restricted", User=current_user.email, CaseId=cid)
            return {"message": "Access restricted", "toast_class": "warning-subtle"}, 403
        flowintel_log("audit", 200, "Download audit logs markdown", User=current_user.email, CaseId=cid)
        return CommonModel.download_audit_logs_md(case)
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


##############
# Taxonomies #
#  Galaxies  #
##############

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


###########
## Files ##
###########

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


  

# Register route modules — must be imported after case_blueprint is defined
from . import case_misp, case_modules, case_notes  # noqa: E402, F401
