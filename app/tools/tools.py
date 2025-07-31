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
    importer_type = request.args.get('type', 1, type=str)
    if importer_type:
        if len(request.files) > 0:
            message = ToolsModel.importer_core(request.files, current_user, importer_type)
            if message:
                message["toast_class"] = "danger-subtle"
                return message, 400
            return {"message": "All created", "toast_class": "success-subtle"}, 200
        return {"message": "Need to give a least a file", "toast_class": "warning-subtle"}, 400
    return {"message": "Need to give a type of import", "toast_class": "warning-subtle"}, 400
    
    
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



#################
# Note Template #
#################

@tools_blueprint.route("/note_template_index")
@login_required
def note_template_index():
    return render_template("tools/note_template_index.html")

@tools_blueprint.route("/create_note_template_view", methods=['GET'])
@login_required
@editor_required
def create_note_template_view():
    return render_template("tools/create_note_template.html")

@tools_blueprint.route("/note_template_view/<int:nid>")
@login_required
def note_template_view(nid):
    return render_template("tools/note_template_view.html", note_template=ToolsModel.get_note_template(nid).to_json())

@tools_blueprint.route("/note_template")
@login_required
def note_template():
    return [n.to_json() for n in ToolsModel.get_all_note_template()]

@tools_blueprint.route("/note_template/<int:nid>")
@login_required
def note_template_id(nid):
    return ToolsModel.get_note_template(nid).to_json()



@tools_blueprint.route("/note_template/get_by_page")
@login_required
def note_template_by_page():
    page = request.args.get('page', 1, type=int)
    notes = ToolsModel.get_note_template_by_page(page)
    if notes:
        notes_list = list()
        for note in notes:
            n = note.to_json()
            notes_list.append(n)
        return {"notes": notes_list, "nb_pages": notes.pages}
    return {"message": "No Notes"}, 404



@tools_blueprint.route("/create_note_template", methods=['POST'])
@login_required
@editor_required
def create_note_template():
    if request.json:
        if "title" in request.json:
            if "description" in request.json:
                if "content" in request.json:
                    if ToolsModel.create_note_template(request.json, current_user):
                        return {"message": "Note added correctly", "toast_class": "success-subtle"}, 201
                    return {"message": "Error adding note", "toast_class": "danger-subtle"}, 400
                return {"message": "Need to pass 'content'", "toast_class": "warning-subtle"}, 400
            return {"message": "Need to pass 'description'", "toast_class": "warning-subtle"}, 400
        return {"message": "Need to pass 'title'", "toast_class": "warning-subtle"}, 400
    return {"message": "An error occur", "toast_class": "warning-subtle"}, 400



@tools_blueprint.route("/note_template/<int:nid>/edit_content", methods=['POST'])
@login_required
@editor_required
def edit_content_note_template(nid):
    if ToolsModel.get_note_template(nid):
        if request.json:
            if "content" in request.json:
                if ToolsModel.edit_content_note_template(nid, request.json):
                    return {"message": "Note edited correctly", "toast_class": "success-subtle"}, 200
                return {"message": "Error editing note", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'content'", "toast_class": "warning-subtle"}, 400
        return {"message": "An error occur", "toast_class": "warning-subtle"}, 400
    return {"message": "Note template not found", "toast_class": "warning-subtle"}, 404

@tools_blueprint.route("/note_template/<int:nid>/edit", methods=['POST'])
@login_required
@editor_required
def edit_note_template():
    if request.json:
        if "title" in request.json:
            if "description" in request.json:
                if ToolsModel.edit_note_template(request.json, current_user):
                    return {"message": "Note eddited correctly", "toast_class": "success-subtle"}, 200
                return {"message": "Error editing note", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'description'", "toast_class": "warning-subtle"}, 400
        return {"message": "Need to pass 'title'", "toast_class": "warning-subtle"}, 400
    return {"message": "An error occur", "toast_class": "warning-subtle"}, 400



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


#####################
# Search Attr value #
#####################

@tools_blueprint.route("/search_attr", methods=["GET"])
@login_required
def search_attr():
    return render_template("tools/search_attr.html")


@tools_blueprint.route("/search_attr_with_value", methods=["GET"])
@login_required
def search_attr_with_value():
    attr_value = request.args.get('value', 1, type=str)
    res = ToolsModel.search_attr_with_value(attr_value, current_user)
    return res

