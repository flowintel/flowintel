import ast
import json
from flask import Blueprint, render_template, redirect, jsonify, request, flash
from flask_login import login_required, current_user

from .form import CaseForm, CaseEditForm, RecurringForm
from .CaseCore import CaseModel
from . import common_core as CommonModel
from .TaskCore import TaskModel
from ..db_class.db import Case, Task_Template, Case_Template
from ..decorators import editor_required
from ..utils.utils import form_to_dict, get_object_templates
from ..utils.formHelper import prepare_tags

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
    return render_template("case/case_index.html")

@case_blueprint.route("/create_case", methods=['GET', 'POST'])
@login_required
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
                CaseModel.edit(form_dict, cid, current_user)
                flash("Case edited", "success")
                return redirect(f"/case/{cid}")
            else:
                case_modif = CommonModel.get_case(cid)
                form.title.data = case_modif.title
                form.deadline_date.data = case_modif.deadline
                form.deadline_time.data = case_modif.deadline
                form.time_required.data = case_modif.time_required
                form.is_private.data = case_modif.is_private
                form.ticket_id.data = case_modif.ticket_id

            return render_template("case/edit_case.html", form=form, description=case_modif.description)
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
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            tag_list = request.json["tags_select"]
            cluster_list = request.json["clusters_select"]
            custom_tags_list = request.json["custom_select"]
            if isinstance(CommonModel.check_tag(tag_list), bool):
                if isinstance(CommonModel.check_cluster(cluster_list), bool):
                    loc_dict = {
                        "tags": tag_list,
                        "clusters": cluster_list,
                        "custom_tags": custom_tags_list
                    }
                    CaseModel.edit_tags(loc_dict, cid, current_user)
                    return {"message": "Tags edited", "toast_class": "success-subtle"}, 200
                return {"message": "Error with Clusters", "toast_class": "warning-subtle"}, 400
            return {"message": "Error with Tags", "toast_class": "warning-subtle"}, 400
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
                        return {"message": "Orgs added", "toast_class": "success-subtle"}, 200
                    return {"message": "One Orgs doesn't exist", "toast_class": "danger-subtle"}, 404
                return {"message": "Need to pass 'org_id'", "toast_class": "warning-subtle"}, 400
            return {"message": "An error occur", "toast_class": "warning-subtle"}, 400
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
                        return {"message": "Owner changed", "toast_class": "success-subtle"}, 200
                    return {"message": "Org doesn't exist", "toast_class": "danger-subtle"}, 404
                return {"message": "Need to pass 'org_id'", "toast_class": "warning-subtle"}, 400
            return {"message": "An error occur", "toast_class": "warning-subtle"}, 400
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

@case_blueprint.route("/<cid>/recurring", methods=['GET', 'POST'])
@login_required
@editor_required
def recurring(cid):
    """Recurring form"""

    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
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
    if cases:
        return {"cases": [case.to_json() for case in cases]}, 200
    return {"message": "No case", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/delete", methods=['GET'])
@login_required
@editor_required
def delete(cid):
    """Delete the case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.delete_case(cid, current_user):
                return {"message": "Case deleted", "toast_class": "success-subtle"}, 200
            else:
                return {"message": "Error case deleted", 'toast_class': "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/get_case_info", methods=['GET'])
@login_required
def get_case_info(cid):
    """Return all info of the case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "permission denied", 'toast_class': "danger-subtle"}, 403
        tasks = TaskModel.sort_tasks(case, current_user, completed=False)

        o_in_c = CommonModel.get_orgs_in_case(case.id)
        orgs_in_case = [o_c.to_json() for o_c in o_in_c]
        permission = CommonModel.get_role(current_user).to_json()
        present_in_case = CommonModel.get_present_in_case(cid, current_user)

        case_json = case.to_json()
        case_json["misp_icon"] = "fe377a79-1950-407a-a02f-c5e1d990ca60"

        return jsonify({"case": case_json, "tasks": tasks, "orgs_in_case": orgs_in_case, "permission": permission, "present_in_case": present_in_case, "current_user": current_user.to_json()}), 200
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/complete_case", methods=['GET'])
@login_required
@editor_required
def complete_case(cid):
    """Mark a case as completed"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.complete_case(cid, current_user):
                flash("Case Completed")
                if request.args.get('revived', 1) == "true":
                    return {"message": "Case Revived", "toast_class": "success-subtle"}, 200
                return {"message": "Case completed", "toast_class": "success-subtle"}, 200
            else:
                if request.args.get('revived', 1) == "true":
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
                return {"message": "Org removed from case", "toast_class": "success-subtle"}, 200
            return {"message": "Error removing org from case", "toast_class": "danger-subtle"}, 400
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
            CaseModel.change_status_core(status, case, current_user)
            return {"message": "Status changed", "toast_class": "success-subtle"}, 200
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
    return jsonify({"status": status_list}), 200


@case_blueprint.route("/sort_cases", methods=['GET'])
@login_required
def sort_cases():
    """Sort Cases"""
    page = request.args.get('page', 1, type=int)
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

    cases_list, nb_pages = CaseModel.sort_cases(page=page, 
                                      completed=status,
                                      taxonomies=taxonomies, 
                                      galaxies=galaxies, 
                                      tags=tags, 
                                      clusters=clusters, 
                                      custom_tags=custom_tags,
                                      or_and_taxo=or_and_taxo, 
                                      or_and_galaxies=or_and_galaxies,
                                      filter=filter, 
                                      user=current_user)
    
    return CaseModel.regroup_case_info(cases_list, current_user, nb_pages)


@case_blueprint.route("/<cid>/get_all_users", methods=['GET'])
@login_required
def get_all_users(cid):
    """Get all users in case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
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
            return {"message": "permission denied", 'toast_class': "danger-subtle"}, 403
        
        task_list = [task.download() for task in case.tasks]

        misp_object_list = [obj.download() for obj in CaseModel.get_misp_object_by_case(cid)]
        return_dict = case.download()
        return_dict["tasks"] = task_list
        return_dict["misp-objects"] = misp_object_list
        return json.dumps(return_dict, indent=4), 200, {'Content-Disposition': f'attachment; filename=case_{case.title}.json'}
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404



@case_blueprint.route("/<cid>/fork", methods=['POST'])
@login_required
@editor_required
def fork_case(cid):
    """Assign current user to the task"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        if "case_title_fork" in request.json:
            case_title_fork = request.json["case_title_fork"]

            new_case = CaseModel.fork_case_core(cid, case_title_fork, current_user)
            if type(new_case) == dict:
                return new_case
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
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        merging_case = CommonModel.get_case(ocid)
        if merging_case:
            if not check_user_private_case(merging_case):
                return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
            
        if CaseModel.merge_case_core(case, merging_case, current_user):
            CaseModel.delete_case(cid, current_user)
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
@editor_required
def create_template(cid):
    """Create a case template from a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if "case_title_template" in request.json:
            case_title_template = request.json["case_title_template"]

            new_template = CaseModel.create_template_from_case(cid, case_title_template, current_user)
            if type(new_template) == dict:
                return new_template
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
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        clusters = CommonModel.get_case_clusters(cid)
        galaxies = []
        if clusters:
            for cluster in clusters:
                loc_g = CommonModel.get_galaxy(cluster.galaxy_id)
                if not loc_g in galaxies:
                    galaxies.append(loc_g.to_json())
                index = clusters.index(cluster)
                clusters[index] = cluster.to_json()
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
def call_module_case(cid):
    """Run a module"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        case_instance_id = request.get_json()["case_task_instance_id"]
        module = request.get_json()["module"]
        res = CaseModel.call_module_case(module, case_instance_id, case, current_user)
        if res:
            res["toast_class"] = "danger-subtle"
            return jsonify(res), 400
        return {"message": "Connector used", 'toast_class': "success-subtle"}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/get_open_close/<cid>", methods=['GET'])
@login_required
def get_open_close(cid):
    """Get the numbers of open and closed tasks"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
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
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        notes = CaseModel.get_all_notes(case)
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
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if "type" in request.args:
            res = CommonModel.export_notes(case_task=True, case_task_id=cid, type_req=request.args.get("type"))
            try:
                CommonModel.delete_temp_folder()
            except:
                pass
            return res
        return {"message": "'type' is missing", 'toast_class': "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/run_computer_assistate_report", methods=['GET'])
@login_required
@editor_required
def run_computer_assistate_report(cid):
    """Create a report from all case informations"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if not CaseModel.check_exist_task(case.uuid):
            return CaseModel.generate_computer_assistate_report(case, current_user)
        return {"message": "There's already a generation going for this case", "toast_class": "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/status_computer_assistate_report", methods=['GET'])
@login_required
def status_computer_assistate_report(cid):
    """Create a report from all case informations"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if not CaseModel.check_exist_task(case.uuid):
            return {"message": "There's no generation going for this case", "toast_class": "warning-subtle"}, 400
        if CaseModel.get_status_computer_assistate_report(case.uuid):
            return {"report_status": "running"}, 200
        return {"report_status": "done"}, 200
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/get_computer_assistate_report", methods=['GET'])
@login_required
def get_computer_assistate_report(cid):
    """Create a report from all case informations"""
    case = CommonModel.get_case(cid)
    if case:
        return {"report": case.computer_assistate_report}
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/export_computer_assistate_report", methods=['GET'])
@login_required
def export_computer_assistate_report(cid):
    """Export note of a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if "type" in request.args:
            res = CommonModel.export_notes_core(case_task_id=None, 
                                                type_req=request.args.get("type"), 
                                                note=case.computer_assistate_report, 
                                                download_filename=f"case_{case.uuid}_computer_assistate_report")
            try:
                CommonModel.delete_temp_folder()
            except:
                pass
            if isinstance(res, dict):
                return res, 400
            return res
        return {"message": "'type' is missing", 'toast_class': "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


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
            return CaseModel.download_history_md(case)
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
                        return {"message": "Link added", "toast_class": "success-subtle"}, 200
                    return {"message": "A Case doesn't exist", "toast_class": "danger-subtle"}, 404
                return {"message": "Need to pass 'case_id'", "toast_class": "warning-subtle"}, 400
            return {"message": "An error occur", "toast_class": "warning-subtle"}, 400
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
                return {"message": "Link removed", "toast_class": "success-subtle"}, 200
            return {"message": "Error removing link from case", "toast_class": "danger-subtle"}, 400
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
                    return {"message": "Link removed", "toast_class": "success-subtle"}, 200
                return {"message": "Error removing link from case", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'hedgedoc_url'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/<cid>/get_hedgedoc_notes", methods=['GET'])
@login_required
@editor_required
def get_hedgedoc_notes(cid):
    """Get hedgedoc notes of the case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
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
                    return {"message": "Object created", "toast_class": "success-subtle"}, 200
                return {"message": "Need to pass 'attributes'", "toast_class": "warning-subtle"}, 400
            return {"message": "Need to pass 'object-template'", "toast_class": "warning-subtle"}, 400
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
                return {"message": "Object deleted", "toast_class": "success-subtle"}, 200
            return {"message": "Object not found in this case", "toast_class": "warning-subtle"}, 404
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
    """Create misp object"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "value" in request.json:
                if "type" in request.json:
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
            return CaseModel.delete_attribute(cid, oid, aid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/misp_object_connectors", methods=['GET'])
@login_required
def misp_object_connectors(cid):
    """Get MISP object connectors"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        instance_list = list()
        for object_connector in CaseModel.get_misp_object_connectors(cid):
            instance_list.append({
                "object_instance_id": object_connector.id,
                "details": CommonModel.get_instance_with_icon(object_connector.instance_id),
                "identifier": object_connector.identifier
            })
        return instance_list, 200
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/misp_connectors", methods=['GET'])
@login_required
def misp_connectors():
    """Return list of misp connectors"""
    return {"misp_connectors": CaseModel.get_misp_connector_by_user(current_user.id)}, 200


@case_blueprint.route("/<cid>/add_misp_object_connector", methods=['POST'])
@login_required
@editor_required
def add_misp_object_connector(cid):
    """Add MISP Connector"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "connectors" in request.json:
                if CaseModel.add_misp_object_connector(cid, request.json, current_user):
                    return {"message": "Connector added successfully", "toast_class": "success-subtle"}, 200
            return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/<cid>/misp_object_connectors/<iid>/remove_connector", methods=['GET'])
@login_required
@editor_required
def remove_misp_connector(cid, iid):
    """Remove MISP Connector"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.remove_misp_connector(cid, iid, current_user):
                return {"message": "Connector removed successfully", "toast_class": "success-subtle"}, 200
            return {"message": "Error removing connector", "toast_class": "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/misp_object_connectors/<iid>/edit_connector", methods=['POST'])
@login_required
@editor_required
def edit_misp_connector(cid, iid):
    """Edit MISP Connector"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "identifier" in request.json:
                if CaseModel.edit_misp_connector(iid, request.json):
                    return {"message": "Connector edited successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Error editing connector", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/misp_object_connectors/<iid>/call_module_misp", methods=['GET'])
@login_required
@editor_required
def call_module_misp(cid, iid):
    """Remove MISP Connector"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            res = CaseModel.call_module_misp(iid, case, current_user)
            if res:
                res["toast_class"] = "danger-subtle"
                return jsonify(res), 400
            return {"message": "Connector used", 'toast_class': "success-subtle"}, 200
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/<cid>/nb_objects", methods=['GET'])
@login_required
def nb_objects(cid):
    """Return nb of misp objects"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        return {"nb_objects": len(CaseModel.get_misp_object_by_case(cid))}, 200
    return {"message": "Case not found"}, 404



#############
# Connector #
#############

@case_blueprint.route("/<cid>/get_case_connectors", methods=['GET', 'POST'])
@login_required
def get_case_connectors(cid):
    """Get all connectors for a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        instance_list = list()
        for case_connector in CommonModel.get_case_connectors(cid, current_user):
            connect = CommonModel.get_connector_by_name("MISP")
            connect_instance = CommonModel.get_instance(case_connector.instance_id)
            is_misp_connector = False
            if connect.id == connect_instance.connector_id:
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
@editor_required
def add_connector(cid):
    """Add MISP Connector"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "connectors" in request.json:
                if CaseModel.add_connector(cid, request.json, current_user):
                    return {"message": "Connector added successfully", "toast_class": "success-subtle"}, 200
            return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/connectors/<ciid>/remove_connector", methods=['GET'])
@login_required
@editor_required
def remove_connector(cid, ciid):
    """Remove a connector from case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.remove_connector(ciid):
                return {"message": "Connector removed", 'toast_class': "success-subtle"}, 200
            return {"message": "Something went wrong", 'toast_class': "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/<cid>/connectors/<ciid>/edit_connector", methods=['POST'])
@login_required
@editor_required
def edit_connector(cid, ciid):
    """Edit Connector"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "identifier" in request.json:
                if CaseModel.edit_connector(ciid, request.json):
                    return {"message": "Connector edited successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Error editing connector", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/update_case/<iid>", methods=['GET'])
@login_required
@editor_required
def update_case(cid, iid):
    """Remove a connector from case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            res = CaseModel.receive_from_misp(iid, cid, current_user)
            if not isinstance(res, dict):
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
                    return {"message": "Note template modified successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400
            return {"message": "Missing parameters", "toast_class": "warning-subtle"}, 400
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
                    return {"message": "Note template modified successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400
            return {"message": "No values passed", "toast_class": "warning-subtle"}, 400
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
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if "type" in request.args:
            if "content" in request.json:
                res = CommonModel.export_notes_core(case_task_id=cid, type_req=request.args.get("type"), note=request.json["content"])
                try:
                    CommonModel.delete_temp_folder()
                except:
                    pass
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
                return {"message": "Note Template removed", "toast_class": "success-subtle"}, 200
            return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404
