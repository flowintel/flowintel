from flask import Blueprint, flash, redirect, render_template, request
from flask_login import login_required, current_user
from . import tools_core as ToolsModel
from ..decorators import editor_required
from ..utils.utils import MODULES_CONFIG, get_modules_list

tools_blueprint = Blueprint(
    'tools',
    __name__,
    template_folder='templates',
    static_folder='static'
)

############
# Importer #
############

@tools_blueprint.route("/importer_view", methods=['GET'])
@login_required
@editor_required
def importer_view():
    """Importer view"""
    return render_template("tools/importer.html")


@tools_blueprint.route("/importer", methods=['POST'])
@login_required
@editor_required
def importer():
    """Import case and task"""
    if len(request.files) > 0:
        message = ToolsModel.read_json_file(request.files, current_user)
        if message:
            message["toast_class"] = "danger-subtle"
            return message, 400
        return {"message": "All created", "toast_class": "success-subtle"}, 200
    
###########
# Modules #
###########

@tools_blueprint.route("/module")
@login_required
def module():
    return render_template("tools/module_index.html")


@tools_blueprint.route("/get_modules")
@login_required
def get_modules():
    return {"modules": MODULES_CONFIG}, 200

@tools_blueprint.route("/reload_module")
@login_required
def reload():
    get_modules_list()
    return {"message": "Modules reloaded", "toast_class": "success-subtle"}, 200


#########
# Stats #
#########
from ..db_class.db import Case, Case_Org

@tools_blueprint.route("/stats")
@login_required
def stats():
    return render_template("tools/stats.html")

def chart_dict_constructor(input_dict):
    loc_dict = []
    for elem in input_dict:
        loc_dict.append({
            "calendar": elem,
            "count": input_dict[elem]
        })
    return loc_dict

@tools_blueprint.route("/case_stats")
@login_required
def case_stats():
    cases = Case.query.join(Case_Org, Case_Org.case_id==Case.id).where(Case_Org.org_id==current_user.org_id).all()
    res_dict = ToolsModel.stats_core(cases)

    return res_dict

@tools_blueprint.route("/admin_stats")
@login_required
def admin_stats():
    if current_user.is_admin():
        cases = Case.query.all()
        res_dict = ToolsModel.stats_core(cases)

        return res_dict
    return {}

@tools_blueprint.route("/case_tags_stats")
@login_required
def get_case_by_tags():
    res = ToolsModel.get_case_by_tags(current_user)
    if res:
        return res
    return {}



########################
# Case from MISP Event #
########################

@tools_blueprint.route("/case_misp_event", methods=["GET", "POST"])
@login_required
@editor_required
def case_misp_event():
    if request.method == 'POST':
        res = ToolsModel.check_case_misp_event(request.json, current_user)
        if not type(res) == str:
            case = ToolsModel.create_case_misp_event(request.json, current_user)
            return {"case_id": case.id}, 200
        else:
            return {"message": res, "toast_class": "warning-subtle"}, 400
    return render_template("tools/case_misp_event.html")


@tools_blueprint.route("/check_connection", methods=["GET"])
@login_required
@editor_required
def check_connection():
    misp_instance_id = request.args.get('misp_instance_id', 1, type=int)
    res = ToolsModel.check_connection_misp(misp_instance_id, current_user)
    if not type(res) == str:
        return {"is_connection_okay": True}
    return {"is_connection_okay": False}

@tools_blueprint.route("/check_misp_event", methods=["GET"])
@login_required
@editor_required
def check_misp_event():
    misp_instance_id = request.args.get('misp_instance_id', 1, type=int)
    misp_event_id = request.args.get('misp_event_id', 1, type=int)
    res = ToolsModel.check_event(misp_event_id, misp_instance_id, current_user)
    if not type(res) == str:
        return {"is_connection_okay": True, "event_info": res.info}
    return {"is_connection_okay": False}