from flask import Blueprint, flash, redirect, render_template, request, current_app
from flask_login import login_required, current_user
from . import tools_core as ToolsModel
from ..decorators import editor_required, admin_required
from ..utils.utils import get_modules_list
from ..utils.logger import flowintel_log
import os
import platform
import getpass
from pathlib import Path

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
    flowintel_log("audit", 200, "Module list viewed", User=current_user.email)
    return render_template("tools/module_index.html")


@tools_blueprint.route("/get_modules")
@login_required
def get_modules():
    _, res = get_modules_list()
    return {"modules": res}, 200

@tools_blueprint.route("/reload_module")
@login_required
def reload():
    get_modules_list()
    flowintel_log("audit", 200, "Modules reloaded", User=current_user.email)
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

@tools_blueprint.route("/community_stats")
@login_required
def community_stats():
    if current_user.is_admin():
        res = ToolsModel.get_community_stats()
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

@tools_blueprint.route("/edit_note_template_view/<int:nid>")
@login_required
@editor_required
def edit_note_template_view(nid):
    return render_template("tools/edit_note_template.html", note_template=ToolsModel.get_note_template(nid).to_json())

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
                    note = ToolsModel.create_note_template(request.json, current_user)
                    if note:
                        flowintel_log("audit", 200, "Note template created", User=current_user.email, NoteTemplateId=note.id, NoteTemplateTitle=note.title)
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
    note = ToolsModel.get_note_template(nid)
    if note:
        if request.json:
            if "content" in request.json:
                result = ToolsModel.edit_content_note_template(nid, request.json)
                if result:
                    flowintel_log("audit", 200, "Note template content edited", User=current_user.email, NoteTemplateId=nid, NoteTemplateTitle=note.title)
                    return {"message": "Note edited correctly", "toast_class": "success-subtle", "version": result["version"]}, 200
                return {"message": "Error editing note", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'content'", "toast_class": "warning-subtle"}, 400
        return {"message": "An error occur", "toast_class": "warning-subtle"}, 400
    return {"message": "Note template not found", "toast_class": "warning-subtle"}, 404

@tools_blueprint.route("/note_template/<int:nid>/edit", methods=['POST'])
@login_required
@editor_required
def edit_note_template(nid):
    note = ToolsModel.get_note_template(nid)
    if note:
        if request.json:
            if "title" in request.json:
                if "description" in request.json:
                    result = ToolsModel.edit_note_template(nid, request.json)
                    if result:
                        flowintel_log("audit", 200, "Note template edited", User=current_user.email, NoteTemplateId=nid, NoteTemplateTitle=request.json["title"])
                        return {"message": "Note edited correctly", "toast_class": "success-subtle", "version": result["version"]}, 200
                    return {"message": "Error editing note", "toast_class": "danger-subtle"}, 400
                return {"message": "Need to pass 'description'", "toast_class": "warning-subtle"}, 400
            return {"message": "Need to pass 'title'", "toast_class": "warning-subtle"}, 400
        return {"message": "An error occur", "toast_class": "warning-subtle"}, 400
    return {"message": "Note template not found", "toast_class": "warning-subtle"}, 404


@tools_blueprint.route("/delete_note_template/<int:nid>", methods=['GET'])
@login_required
@editor_required
def delete_note_template(nid):
    note = ToolsModel.get_note_template(nid)
    if note:
        if ToolsModel.delete_note_template(nid):
            flowintel_log("audit", 200, "Note template deleted", User=current_user.email, NoteTemplateId=nid, NoteTemplateTitle=note.title)
            return {"message": "Note template deleted", "toast_class": "success-subtle"}, 200
    return {"message": "Error deleting note template", "toast_class": "danger-subtle"}, 400



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
    misp_event_id = request.args.get('misp_event_id', 1, type=str)
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


@tools_blueprint.route("/system_settings")
@login_required
@admin_required
def system_settings():
    from conf.config import config as app_config
    
    flaskenv = os.getenv('FLASKENV', 'development')
    config_class = app_config.get(flaskenv)
    
    db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri.startswith('postgresql'):
        db_type = 'PostgreSQL'
    elif db_uri.startswith('mysql'):
        db_type = 'MySQL/MariaDB'
    elif db_uri.startswith('sqlite'):
        db_type = 'SQLite'
    else:
        db_type = 'Unknown'
    
    db_name = getattr(config_class, 'db_name', None)
    db_host = getattr(config_class, 'db_host', None)
    
    installation_path = str(Path(__file__).parent.parent.parent)
    
    process_user = getpass.getuser()
    try:
        process_uid = os.getuid()
    except AttributeError:
        process_uid = None
    
    os_name = platform.system()
    os_release = platform.release()
    python_version = platform.python_version()
    
    system_info = {
        'flaskenv': flaskenv,
        'session_type': current_app.config.get('SESSION_TYPE'),
        'debug': current_app.config.get('DEBUG', False),
        'flask_url': getattr(config_class, 'FLASK_URL', None),
        'flask_port': getattr(config_class, 'FLASK_PORT', None),
        'misp_module': getattr(config_class, 'MISP_MODULE', None),
        'log_file': getattr(config_class, 'LOG_FILE', None),
        'installation_path': installation_path,
        'os_name': os_name,
        'os_release': os_release,
        'python_version': python_version,
        'process_user': process_user,
        'process_uid': process_uid,
        'db_type': db_type,
        'db_name': db_name,
        'db_host': db_host,
        'file_upload_max_size': current_app.config.get('FILE_UPLOAD_MAX_SIZE'),
        'limit_user_view_to_org': current_app.config.get('LIMIT_USER_VIEW_TO_ORG'),
        'enforce_privileged_case': current_app.config.get('ENFORCE_PRIVILEGED_CASE', False),
        'task_requested': current_app.config.get('TASK_REQUESTED', 7),
        'task_approved': current_app.config.get('TASK_APPROVED', 8),
        'task_rejected': current_app.config.get('TASK_REJECTED', 9)
    }
    
    return render_template('tools/system_settings.html', system_info=system_info)

