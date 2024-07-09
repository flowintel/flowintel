import ast
import json
from flask import Blueprint, render_template, redirect, jsonify, request, flash
from .form import CaseForm, CaseEditForm, RecurringForm
from flask_login import login_required, current_user
from . import case_core as CaseModel
from . import common_core as CommonModel
from . import task_core as TaskModel
from ..db_class.db import Task_Template, Case_Template
from ..decorators import editor_required
from ..utils.utils import form_to_dict
from ..utils.formHelper import prepare_tags_connectors
from ..custom_tags import custom_tags_core as CustomModel

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
        res = prepare_tags_connectors(request)
        if isinstance(res, dict):
            form_dict = form_to_dict(form)
            form_dict.update(res)
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
        present_in_case = CaseModel.get_present_in_case(cid, current_user)
        case_loc = case.to_json()
        case_loc["instances"] = list()
        for case_connector in CommonModel.get_case_connectors(case.id):
            case_loc["instances"].append(CommonModel.get_instance_with_icon(case_connector.instance_id, case_task=True, case_task_id=case.id))
        return render_template("case/case_view.html", case=case_loc, present_in_case=present_in_case)
    return render_template("404.html")


@case_blueprint.route("/edit/<cid>", methods=['GET','POST'])
@login_required
@editor_required
def edit_case(cid):
    """Edit the case"""
    if CommonModel.get_case(cid):
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            form = CaseEditForm()

            if form.validate_on_submit():
                res = prepare_tags_connectors(request)
                if isinstance(res, dict):
                    form_dict = form_to_dict(form)
                    form_dict.update(res)
                    CaseModel.edit_case(form_dict, cid, current_user)
                    flash("Case edited", "success")
                    return redirect(f"/case/{cid}")
                return render_template("case/edit_case.html", form=form)
            else:
                case_modif = CommonModel.get_case(cid)
                form.description.data = case_modif.description
                form.title.data = case_modif.title
                form.deadline_date.data = case_modif.deadline
                form.deadline_time.data = case_modif.deadline

            return render_template("case/edit_case.html", form=form)
        else:
            flash("Access denied", "error")
    else:
        return render_template("404.html")
    return redirect(f"/case/{id}")


@case_blueprint.route("/<cid>/add_orgs", methods=['GET', 'POST'])
@login_required
@editor_required
def add_orgs(cid):
    """Add orgs to the case"""
    if CommonModel.get_case(cid):
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
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
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
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
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
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

@case_blueprint.route("/get_cases_page", methods=['GET'])
@login_required
def get_cases():
    """Return all cases by page"""
    page = request.args.get('page', 1, type=int)
    tags = request.args.get('tags')
    taxonomies = request.args.get('taxonomies')
    or_and = request.args.get("or_and")

    cases = CaseModel.sort_by_status(page, tags, taxonomies, or_and, completed=False)
    role = CommonModel.get_role(current_user).to_json()

    loc = CaseModel.regroup_case_info(cases, current_user)
    return jsonify({"cases": loc["cases"], "role": role, "nb_pages": cases.pages}), 200

@case_blueprint.route("/get_case/<cid>", methods=['GET'])
@login_required
def get_case(cid):
    """Return all cases by page"""
    return CommonModel.get_case(cid).to_json()


@case_blueprint.route("/search", methods=['GET'])
@login_required
def search():
    """Return cases matching search terms"""
    text_search = request.args.get("text")
    cases = CommonModel.search(text_search)
    if cases:
        return {"cases": [case.to_json() for case in cases]}, 200
    return {"message": "No case", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/delete", methods=['GET'])
@login_required
@editor_required
def delete(cid):
    """Delete the case"""
    if CommonModel.get_case(cid):
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.delete_case(cid, current_user):
                return {"message": "Case deleted", "toast_class": "success-subtle"}, 200
            else:
                return {"message": "Error case deleted", 'toast_class': "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/get_case_info", methods=['GET'])
@login_required
def get_case_info(cid):
    """Return all info of the case"""
    case = CommonModel.get_case(cid)
    if case:    
        tasks = TaskModel.sort_by_status_task_core(case, current_user, completed=False)

        o_in_c = CommonModel.get_orgs_in_case(case.id)
        orgs_in_case = [o_c.to_json() for o_c in o_in_c]
        permission = CommonModel.get_role(current_user).to_json()
        present_in_case = CaseModel.get_present_in_case(cid, current_user)

        return jsonify({"case": case.to_json(), "tasks": tasks, "orgs_in_case": orgs_in_case, "permission": permission, "present_in_case": present_in_case, "current_user": current_user.to_json()}), 200
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/complete_case", methods=['GET'])
@login_required
@editor_required
def complete_case(cid):
    """Mark a case as completed"""
    if CommonModel.get_case(cid):
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.complete_case(cid, current_user):
                flash("Case Completed")
                if request.args.get('revived', 1) == "true":
                    return {"message": "Case Revived", "toast_class": "success-subtle"}, 200
                return {"message": "Case completed", "toast_class": "success-subtle"}, 200
            else:
                if request.args.get('revived', 1) == "true":
                    return {"message": "Error case revived", 'toast_class': "danger-subtle"}, 400
                return {"message": "Error case completed", 'toast_class': "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/remove_org/<oid>", methods=['GET'])
@login_required
@editor_required
def remove_org_case(cid, oid):
    """Remove an org to the case"""
    if CommonModel.get_case(cid):
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.remove_org_case(cid, oid, current_user):
                return {"message": "Org removed from case", "toast_class": "success-subtle"}, 200
            return {"message": "Error removing org from case", "toast_class": "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/change_status", methods=['POST'])
@login_required
@editor_required
def change_status(cid):
    """Change the status of the case"""
    status = request.json["status"]
    case = CommonModel.get_case(cid)

    if case:
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            CaseModel.change_status_core(status, case, current_user)
            return {"message": "Status changed", "toast_class": "success-subtle"}, 200
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
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


@case_blueprint.route("/sort_by_ongoing", methods=['GET'])
@login_required
def sort_by_ongoing():
    """Sort Case by living one"""
    page = request.args.get('page', 1, type=int)
    tags = request.args.get('tags')
    taxonomies = request.args.get('taxonomies')
    or_and_taxo = request.args.get("or_and_taxo")

    galaxies = request.args.get('galaxies')
    clusters = request.args.get('clusters')
    or_and_galaxies = request.args.get("or_and_galaxies")

    cases_list = CaseModel.sort_by_status(page, taxonomies, galaxies, tags, clusters, or_and_taxo, or_and_galaxies, completed=False)
    return CaseModel.regroup_case_info(cases_list, current_user)



@case_blueprint.route("/sort_by_finished", methods=['GET'])
@login_required
def sort_by_finished():
    """Sort Case by finished one"""
    page = request.args.get('page', 1, type=int)
    tags = request.args.get('tags')
    taxonomies = request.args.get('taxonomies')
    or_and_taxo = request.args.get("or_and_taxo")

    galaxies = request.args.get('galaxies')
    clusters = request.args.get('clusters')
    or_and_galaxies = request.args.get("or_and_galaxies")

    cases_list = CaseModel.sort_by_status(page, taxonomies, galaxies, tags, clusters, or_and_taxo, or_and_galaxies, completed=True)
    return CaseModel.regroup_case_info(cases_list, current_user)


@case_blueprint.route("/ongoing", methods=['GET'])
@login_required
def ongoing_sort_by_filter():
    """Sort by filter for living case"""
    page = request.args.get('page', 1, type=int)
    filter = request.args.get('filter')
    tags = request.args.get('tags')
    taxonomies = request.args.get('taxonomies')
    or_and_taxo = request.args.get("or_and_taxo")

    galaxies = request.args.get('galaxies')
    clusters = request.args.get('clusters')
    or_and_galaxies = request.args.get("or_and_galaxies")

    if filter:
        cases_list, nb_pages = CaseModel.sort_by_filter(filter, page, taxonomies, galaxies, tags, clusters, or_and_taxo, or_and_galaxies, completed=False)
        return CaseModel.regroup_case_info(cases_list, current_user, nb_pages)
    return {"message": "No filter pass"}


@case_blueprint.route("/finished", methods=['GET'])
@login_required
def finished_sort_by_filter():
    """Sort by filter for finished task"""
    page = request.args.get('page', 1, type=int)
    filter = request.args.get('filter')
    tags = request.args.get('tags')
    taxonomies = request.args.get('taxonomies')
    or_and_taxo = request.args.get("or_and_taxo")

    galaxies = request.args.get('galaxies')
    clusters = request.args.get('clusters')
    or_and_galaxies = request.args.get("or_and_galaxies")

    if filter:
        cases_list, nb_pages = CaseModel.sort_by_filter(filter, page, taxonomies, galaxies, tags, clusters, or_and_taxo, or_and_galaxies, completed=True)
        return CaseModel.regroup_case_info(cases_list, current_user, nb_pages)
    return {"message": "No filter pass"}


@case_blueprint.route("/<cid>/get_all_users", methods=['GET'])
@login_required
def get_all_users(cid):
    """Get all users in case"""
    case = CommonModel.get_case(cid)
    if case:
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

    if CommonModel.get_case(cid):
        users, _ = TaskModel.get_users_assign_task(tid, current_user)
        return users
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/download", methods=['GET'])
@login_required
def download_case(cid):
    """Download a case"""
    case = CommonModel.get_case(cid)
    if case:
        task_list = list()
        for task in case.tasks:
            task_list.append(task.download())
        return_dict = case.download()
        return_dict["tasks"] = task_list
        return json.dumps(return_dict, indent=4), 200, {'Content-Disposition': f'attachment; filename=case_{case.title}.json'}
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404



@case_blueprint.route("/<cid>/fork", methods=['POST'])
@login_required
@editor_required
def fork_case(cid):
    """Assign current user to the task"""
    if CommonModel.get_case(cid):
        if "case_title_fork" in request.json:
            case_title_fork = request.json["case_title_fork"]

            new_case = CaseModel.fork_case_core(cid, case_title_fork, current_user)
            if type(new_case) == dict:
                return new_case
            return {"new_case_id": new_case.id}, 201
        return {"message": "'case_title_fork' is missing", 'toast_class': "danger-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/check_case_title_exist", methods=['GET'])
@login_required
def check_case_title_exist():
    """Check if a title for a case exist"""
    data_dict = dict(request.args)
    if CommonModel.get_case_by_title(data_dict["title"]):
        flag = True
    else:
        flag = False
    
    return {"title_already_exist": flag}


@case_blueprint.route("/<cid>/create_template", methods=['POST'])
@login_required
@editor_required
def create_template(cid):
    """Create a case template from a case"""
    if CommonModel.get_case(cid):
        if "case_title_template" in request.json:
            case_title_template = request.json["case_title_template"]

            new_template = CaseModel.create_template_from_case(cid, case_title_template)
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
        flag = True
    else:
        flag = False
    
    return {"title_already_exist": flag}


@case_blueprint.route("/history/<cid>", methods=['GET'])
@login_required
def history(cid):
    """Get the history of a case"""
    case = CommonModel.get_case(cid)
    if case:
        history = CommonModel.get_history(case.uuid)
        if history:
            return {"history": history}
        return {"history": None}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/get_taxonomies", methods=['GET'])
@login_required
def get_taxonomies():
    """Get all taxonomies"""
    return {"taxonomies": CommonModel.get_taxonomies()}, 200

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
        tags = CommonModel.get_case_tags(case.id)
        taxonomies = []
        if tags:
            taxonomies = [tag.split(":")[0] for tag in tags]
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
        clusters = CommonModel.get_case_clusters(case.id)
        galaxies = []
        if clusters:
            for cluster in clusters:
                loc_g = CommonModel.get_galaxy(cluster.galaxy_id)
                if not loc_g.name in galaxies:
                    galaxies.append(loc_g.name)
                index = clusters.index(cluster)
                clusters[index] = cluster.tag
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
    if CommonModel.get_case(cid):
        if "module" in request.args:
            module = request.args.get("module")
        if "type" in request.args:
            type_module = request.args.get("type")
        else:
            return{"message": "Module type error", 'toast_class': "danger-subtle"}, 400
        return {"instances": CaseModel.get_instance_module_core(module, type_module, cid, current_user.id)}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/get_connectors_case/<cid>", methods=['GET'])
@login_required
def get_connectors_case(cid):
    """Get all connectors instances for a case"""
    case = CommonModel.get_case(cid)
    if case:
        return {"connectors": [CommonModel.get_instance(case_instance.instance_id).name for case_instance in CommonModel.get_case_connectors(case.id) ]}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/get_connectors_case_id/<cid>", methods=['GET'])
@login_required
def get_connectors_case_id(cid):
    """Get identifier for a list of connectors instances"""
    case = CommonModel.get_case(cid)
    if case:
        loc = dict()
        instances = ast.literal_eval(request.args.get("instances"))
        for instance in instances:
            ident = CommonModel.get_case_connector_id(CommonModel.get_instance_by_name(instance).id, case.id)
            if ident:
                loc[instance] = ident.identifier
        return {"instances": loc}, 200
    return {"message": "case Not found", 'toast_class': "danger-subtle"}, 404



@case_blueprint.route("/<cid>/call_module_case", methods=['GET', 'POST'])
@login_required
def call_module_case(cid):
    """Run a module"""
    case = CommonModel.get_case(cid)
    if case:
        instances = request.get_json()["int_sel"]
        module = request.args.get("module")
        res = CaseModel.call_module_case(module, instances, case, current_user)
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
        cp_open = 0
        cp_closed = 0
        for task in case.tasks:
            if task.completed:
                cp_closed += 1
            else:
                cp_open += 1
        return {"open": cp_open, "closed": cp_closed}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/all_notes", methods=['GET'])
@login_required
def all_notes(cid):
    """Get all tasks notes for a case"""
    case = CommonModel.get_case(cid)
    if case:
        notes = CaseModel.get_all_notes(case)
        return {"notes": notes}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/modif_note_case", methods=['POST'])
@login_required
@editor_required
def modif_note(cid):
    """Modify note of the task"""
    if CommonModel.get_case(cid):
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            notes = request.json["notes"]
            if CaseModel.modif_note_core(cid, current_user, notes):
                return {"message": "Note modified", "toast_class": "success-subtle"}, 200
            return {"message": "Error add/modify note", "toast_class": "danger-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 401
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/export_notes", methods=['GET'])
@login_required
def export_notes(cid):
    """Export note of a case"""
    if CommonModel.get_case(cid):
        if "type" in request.args:
            res = CommonModel.export_notes(case_task=True, case_task_id=cid, type_req=request.args.get("type"))
            CommonModel.delete_temp_folder()
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
        return {"custom_tags": [CustomModel.get_custom_tag(c_t.custom_tag_id).name for c_t in CommonModel.get_case_custom_tags(case.id)]}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404