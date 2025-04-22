from flask import Blueprint, render_template, request
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
