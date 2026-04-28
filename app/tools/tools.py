from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, current_app
from flask_login import login_required, current_user
from . import tools_core as ToolsModel
from ..utils.note_variables import get_syntax_reference
from ..decorators import editor_required, admin_required, template_editor_required, misp_editor_required
from ..utils.utils import get_modules_list, reload_application
from ..utils.logger import flowintel_log
from ..case.common_core import get_all_cases as common_get_all_cases, get_case as common_get_case
from ..case.CaseCore import CaseModel, FILE_FOLDER
import base64
import csv
import io
import json
import os
import platform
import getpass
import re
import shutil
from pathlib import Path
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring

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
def importer_view():
    """Importer view"""
    can_import_cases = current_user.is_admin() or current_user.is_importer()
    can_import_templates = current_user.is_admin() or current_user.is_template_editor()
    return render_template("tools/importer.html",
                           can_import_cases=can_import_cases,
                           can_import_templates=can_import_templates)


@tools_blueprint.route("/importer", methods=['POST'])
@login_required
def importer():
    """Import case and task"""
    importer_type = request.args.get('type', 1, type=str)
    if importer_type:
        if importer_type == 'case':
            if not (current_user.is_admin() or current_user.is_importer()):
                flowintel_log("audit", 403, "Case import denied", User=current_user.email)
                abort(403)
        elif importer_type == 'template':
            if not (current_user.is_admin() or current_user.is_template_editor()):
                flowintel_log("audit", 403, "Template import denied", User=current_user.email)
                abort(403)
        else:
            return {"message": "Invalid import type", "toast_class": "warning-subtle"}, 400
        if len(request.files) > 0:
            # Create custom tags present in JSON if they don't exist
            create_custom_tags = request.form.get('create_custom_tags', 'false')
            create_custom_tags = True if str(create_custom_tags).lower() == 'true' else False
            message = ToolsModel.importer_core(request.files, current_user, importer_type, create_custom_tags)
            if message:
                message["toast_class"] = "danger-subtle"
                return message, 400
            flowintel_log("audit", 200, f"Import successful (type={importer_type})", User=current_user.email)
            return {"message": "All created", "toast_class": "success-subtle"}, 200
        return {"message": "Need to give a least a file", "toast_class": "warning-subtle"}, 400
    return {"message": "Need to give a type of import", "toast_class": "warning-subtle"}, 400
    
    
############
# Exporter #
############

@tools_blueprint.route("/exporter_view", methods=['GET'])
@login_required
def exporter_view():
    """Exporter view"""
    if not (current_user.is_admin() or current_user.is_case_admin()):
        abort(403)
    cases = common_get_all_cases(current_user)
    cases_list = [{"id": c.id, "title": c.title} for c in cases]
    return render_template("tools/exporter.html", cases=cases_list)


@tools_blueprint.route("/exporter", methods=['POST'])
@login_required
def exporter():
    """Export selected cases"""
    if not (current_user.is_admin() or current_user.is_case_admin()):
        abort(403)

    data = request.get_json()
    if not data:
        return {"message": "No data provided", "toast_class": "warning-subtle"}, 400

    case_ids = data.get("case_ids", [])
    export_format = data.get("format", "json")
    include_files = data.get("include_files", False) and export_format != "csv"

    if not case_ids:
        return {"message": "No cases selected", "toast_class": "warning-subtle"}, 400

    if export_format not in ("json", "csv", "xml"):
        return {"message": "Invalid export format", "toast_class": "warning-subtle"}, 400

    accessible_cases = common_get_all_cases(current_user)
    accessible_ids = {c.id for c in accessible_cases}

    export_data = []
    for cid in case_ids:
        case = common_get_case(cid)
        if not case or case.id not in accessible_ids:
            continue
        case_dict = case.download()
        tasks = list(case.tasks)
        case_dict["tasks"] = [t.download() for t in tasks]
        misp_objects = CaseModel.get_misp_object_by_case(cid)
        case_dict["misp-objects"] = [obj.download() for obj in misp_objects]
        if include_files:
            case_dict["files"] = _encode_files(case.files)
            for i, task in enumerate(tasks):
                case_dict["tasks"][i]["files"] = _encode_files(task.files)
        export_data.append(case_dict)

    if not export_data:
        return {"message": "No accessible cases found", "toast_class": "warning-subtle"}, 400

    flowintel_log("audit", 200, f"Bulk export ({export_format}, {len(export_data)} cases)", User=current_user.email)

    if export_format == "json":
        output = json.dumps(export_data, indent=4)
        mimetype = "application/json"
        filename = "cases_export.json"
    elif export_format == "csv":
        output = _cases_to_csv(export_data)
        mimetype = "text/csv"
        filename = "cases_export.csv"
    elif export_format == "xml":
        output = _cases_to_xml(export_data)
        mimetype = "application/xml"
        filename = "cases_export.xml"

    return output, 200, {
        "Content-Type": mimetype,
        "Content-Disposition": f"attachment; filename={filename}"
    }


def _encode_files(file_queryset):
    """Base64-encode files from disk"""
    result = []
    for f in file_queryset:
        entry = f.to_json()
        file_path = os.path.join(FILE_FOLDER, f.uuid)
        if os.path.exists(file_path):
            with open(file_path, "rb") as fh:
                entry["content_base64"] = base64.b64encode(fh.read()).decode("ascii")
        result.append(entry)
    return result


def _cases_to_csv(cases):
    """Build CSV from case and task data"""
    output = io.StringIO()
    fields = ["type", "uuid", "title", "description", "deadline", "time_required",
              "status", "tags", "recurring_type", "is_private", "ticket_id"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for case in cases:
        row = _csv_row(case, fields)
        row["type"] = "case"
        row["tags"] = _collect_tags(case)
        writer.writerow(row)
        for task in case.get("tasks", []):
            row = _csv_row(task, fields)
            row["type"] = "task"
            row["tags"] = _collect_tags(task)
            writer.writerow(row)
    return output.getvalue()


def _csv_row(source, fields):
    """Extract fields from a dict, converting None to empty string"""
    row = {}
    for f in fields:
        v = source.get(f)
        row[f] = v if v is not None else ""
    return row


def _collect_tags(entry):
    """Collect tags and custom tags into a semicolon-separated string"""
    items = list(entry.get("tags", []))
    items += [ct["name"] for ct in entry.get("custom_tags", [])]
    return "; ".join(items)


def _cases_to_xml(cases):
    """Build XML from case data"""
    root = Element("cases")
    for case in cases:
        _add_xml_element(root, "case", case)
    return tostring(root, encoding="unicode", xml_declaration=True)


def _add_xml_element(parent, tag, value):
    el = SubElement(parent, tag)
    if isinstance(value, dict):
        for k, v in value.items():
            _add_xml_element(el, k, v)
    elif isinstance(value, list):
        for item in value:
            _add_xml_element(el, "item", item)
    else:
        el.text = str(value) if value is not None else ""


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
    # Clear the cached modules so subsequent calls reload them from disk
    try:
        get_modules_list.cache_clear()
    except Exception:
        # If the function isn't cached for some reason, fall back to calling it
        pass
    get_modules_list()
    flowintel_log("audit", 200, "Modules reloaded", User=current_user.email)
    return {"message": "Modules reloaded", "toast_class": "success-subtle"}, 200


#########
# Stats #
#########
from ..db_class.db import Case, Case_Org
from ..case.common_core import check_user_in_private_cases

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
    cases = check_user_in_private_cases(cases, current_user)
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

@tools_blueprint.route("/tag_galaxy_stats")
@login_required
def get_tag_galaxy_stats():
    res = ToolsModel.get_tag_galaxy_top_stats(current_user)
    return res

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


@tools_blueprint.route("/note_variables_reference", methods=['GET'])
@login_required
def note_variables_reference_view():
    """Render the note variables syntax reference page"""
    reference = get_syntax_reference()
    return render_template("tools/note_variables_reference.html", reference=reference)

@tools_blueprint.route("/create_note_template_view", methods=['GET'])
@login_required
@template_editor_required
def create_note_template_view():
    return render_template("tools/create_note_template.html")

@tools_blueprint.route("/note_template_view/<int:nid>")
@login_required
def note_template_view(nid):
    return render_template("tools/note_template_view.html", note_template=ToolsModel.get_note_template(nid).to_json())

@tools_blueprint.route("/edit_note_template_view/<int:nid>")
@login_required
@template_editor_required
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
@template_editor_required
def create_note_template():
    if request.json:
        if "title" in request.json:
            if "content" in request.json:
                request.json.setdefault("description", "")
                note = ToolsModel.create_note_template(request.json, current_user)
                if note:
                    flowintel_log("audit", 201, "Note template created", User=current_user.email, NoteTemplateId=note.id, Title=note.title)
                    return {"message": "Note added correctly", "toast_class": "success-subtle"}, 201
                return {"message": "Error adding note", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'content'", "toast_class": "warning-subtle"}, 400
        return {"message": "Need to pass 'title'", "toast_class": "warning-subtle"}, 400
    return {"message": "An error occur", "toast_class": "warning-subtle"}, 400



@tools_blueprint.route("/note_template/<int:nid>/edit_content", methods=['POST'])
@login_required
@template_editor_required
def edit_content_note_template(nid):
    note = ToolsModel.get_note_template(nid)
    if note:
        if request.json:
            if "content" in request.json:
                result = ToolsModel.edit_content_note_template(nid, request.json)
                if result:
                    flowintel_log("audit", 200, "Note template content edited", User=current_user.email, NoteTemplateId=nid, Title=note.title)
                    return {"message": "Note edited correctly", "toast_class": "success-subtle", "version": result["version"]}, 200
                return {"message": "Error editing note", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'content'", "toast_class": "warning-subtle"}, 400
        return {"message": "An error occur", "toast_class": "warning-subtle"}, 400
    return {"message": "Note template not found", "toast_class": "warning-subtle"}, 404

@tools_blueprint.route("/note_template/<int:nid>/edit", methods=['POST'])
@login_required
@template_editor_required
def edit_note_template(nid):
    note = ToolsModel.get_note_template(nid)
    if note:
        if request.json:
            if "title" in request.json:
                if "description" in request.json:
                    result = ToolsModel.edit_note_template(nid, request.json)
                    if result:
                        flowintel_log("audit", 200, "Note template edited", User=current_user.email, NoteTemplateId=nid, Title=request.json.get("title"))
                        return {"message": "Note edited correctly", "toast_class": "success-subtle", "version": result["version"]}, 200
                    return {"message": "Error editing note", "toast_class": "danger-subtle"}, 400
                return {"message": "Need to pass 'description'", "toast_class": "warning-subtle"}, 400
            return {"message": "Need to pass 'title'", "toast_class": "warning-subtle"}, 400
        return {"message": "An error occur", "toast_class": "warning-subtle"}, 400
    return {"message": "Note template not found", "toast_class": "warning-subtle"}, 404


@tools_blueprint.route("/delete_note_template/<int:nid>", methods=['GET'])
@login_required
@template_editor_required
def delete_note_template(nid):
    note = ToolsModel.get_note_template(nid)
    if note:
        if ToolsModel.delete_note_template(nid):
            flowintel_log("audit", 200, "Note template deleted", User=current_user.email, NoteTemplateId=nid, Title=note.title)
            return {"message": "Note template deleted", "toast_class": "success-subtle"}, 200
    return {"message": "Error deleting note template", "toast_class": "danger-subtle"}, 400



########################
# Case from MISP Event #
########################

@tools_blueprint.route("/case_misp_event", methods=["GET", "POST"])
@login_required
def case_misp_event():
    can_use_misp = current_user.is_admin() or current_user.is_misp_editor()
    if request.method == 'POST':
        if not can_use_misp:
            return {"message": "Action not Allowed", "toast_class": "warning-subtle"}, 403
        res = ToolsModel.check_case_misp_event(request.json, current_user)
        if not type(res) == str:
            case = ToolsModel.create_case_misp_event(request.json, current_user)
            flowintel_log(
                "audit", 200, "Case created from MISP event",
                User=current_user.email, CaseId=case.id,
                MispInstanceId=request.json.get("misp_instance_id"),
                MispEventId=request.json.get("misp_event_id"),
            )
            return {"case_id": case.id}, 200
        else:
            return {"message": res, "toast_class": "warning-subtle"}, 400
    return render_template("tools/case_misp_event.html", can_use_misp=can_use_misp)


@tools_blueprint.route("/check_connection", methods=["GET"])
@login_required
@misp_editor_required
def check_connection():
    misp_instance_id = request.args.get('misp_instance_id', 1, type=int)
    res = ToolsModel.check_connection_misp(misp_instance_id, current_user)
    if not type(res) == str:
        return {"is_connection_okay": True}
    return {"is_connection_okay": False}

@tools_blueprint.route("/check_misp_event", methods=["GET"])
@login_required
@misp_editor_required
def check_misp_event():
    misp_instance_id = request.args.get('misp_instance_id', 1, type=int)
    misp_event_id = request.args.get('misp_event_id', 1, type=str)
    res = ToolsModel.check_event(misp_event_id, misp_instance_id, current_user)
    if not type(res) == str:
        return {"is_connection_okay": True, "event_details": ToolsModel.summarize_misp_event(res)}
    return {"is_connection_okay": False}


@tools_blueprint.route("/misp_connectors", methods=['GET'])
@login_required
def misp_connectors():
    """Return list of misp connectors"""
    return {"misp_connectors": ToolsModel.get_misp_connector_by_user(current_user.id)}, 200

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
    attr_value = request.args.get('value', '', type=str)
    start_date = request.args.get('start_date', None, type=str)
    end_date = request.args.get('end_date', None, type=str)

    res = ToolsModel.search_attr_with_value(attr_value, current_user, start_date=start_date, end_date=end_date)
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
    
    app_root = Path(__file__).parent.parent.parent
    installation_path = str(app_root)

    config_path = app_root / 'conf' / 'config.py'
    try:
        config_last_modified = datetime.fromtimestamp(config_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
    except OSError:
        config_last_modified = None

    process_user = getpass.getuser()
    try:
        process_uid = os.getuid()
    except AttributeError:
        process_uid = None
    
    os_name = platform.system()
    os_release = platform.release()
    python_version = platform.python_version()
    
    system_info = {
        # System
        'installation_path': installation_path,
        'os_name': os_name,
        'os_release': os_release,
        'python_version': python_version,
        'process_user': process_user,
        'process_uid': process_uid,
        'app_name': current_app.config.get('APP_NAME', 'Flowintel'),
        'config_last_modified': config_last_modified,

        # Configuration
        'flaskenv': flaskenv,
        'secret_key_set': current_app.config.get('SECRET_KEY', '') not in ('', 'SECRET_KEY_ENV_VAR_NOT_SET'),
        'debug': current_app.config.get('DEBUG', False),
        'session_type': current_app.config.get('SESSION_TYPE'),
        'valkey_ip': getattr(config_class, 'VALKEY_IP', '127.0.0.1'),
        'valkey_port': getattr(config_class, 'VALKEY_PORT', '6379'),
        'flask_url': getattr(config_class, 'FLASK_URL', None),
        'flask_port': getattr(config_class, 'FLASK_PORT', None),
        'misp_module': getattr(config_class, 'MISP_MODULE', None),
        'file_upload_max_size': current_app.config.get('FILE_UPLOAD_MAX_SIZE'),
        'behind_proxy': current_app.config.get('BEHIND_PROXY', False),
        'proxy_x_for': current_app.config.get('PROXY_X_FOR', 1),
        'proxy_x_proto': current_app.config.get('PROXY_X_PROTO', 1),
        'proxy_x_host': current_app.config.get('PROXY_X_HOST', 1),
        'proxy_x_prefix': current_app.config.get('PROXY_X_PREFIX', 0),
        'system_roles': current_app.config.get('SYSTEM_ROLES', [1, 2, 3]),

        # Setup
        'limit_user_view_to_org': current_app.config.get('LIMIT_USER_VIEW_TO_ORG'),
        'enforce_privileged_case': current_app.config.get('ENFORCE_PRIVILEGED_CASE', False),

        # Logging & theming
        'log_file': getattr(config_class, 'LOG_FILE', None),
        'audit_log_prefix': current_app.config.get('AUDIT_LOG_PREFIX', 'AUDIT'),
        'main_logo': current_app.config.get('MAIN_LOGO', ''),
        'topright_logo': current_app.config.get('TOPRIGHT_LOGO', ''),
        'welcome_text_top': current_app.config.get('WELCOME_TEXT_TOP', ''),
        'welcome_text_bottom': current_app.config.get('WELCOME_TEXT_BOTTOM', ''),
        'welcome_logo': current_app.config.get('WELCOME_LOGO', ''),
        'show_gdpr_notice': current_app.config.get('SHOW_GDPR_NOTICE', True),
        'gdpr_notice': current_app.config.get('GDPR_NOTICE', ''),

        # MISP
        'misp_export_files': current_app.config.get('MISP_EXPORT_FILES', False),
        'misp_event_threat_level': current_app.config.get('MISP_EVENT_THREAT_LEVEL', 4),
        'misp_event_analysis': current_app.config.get('MISP_EVENT_ANALYSIS', 0),
        'misp_add_local_tags_all_events': current_app.config.get('MISP_ADD_LOCAL_TAGS_ALL_EVENTS', ''),

        # Report signing
        'gpg_enabled': bool(current_app.config.get('GPG_KEY_ID')),
        'gpg_home': current_app.config.get('GPG_HOME', ''),
        'gpg_key_id': current_app.config.get('GPG_KEY_ID', ''),

        # Task status IDs
        'task_requested': current_app.config.get('TASK_REQUESTED', 7),
        'task_approved': current_app.config.get('TASK_APPROVED', 8),
        'task_rejected': current_app.config.get('TASK_REJECTED', 5),
        'task_request_review': current_app.config.get('TASK_REQUEST_REVIEW', 9),

        # Entra ID SSO
        'entra_id_enabled': current_app.config.get('ENTRA_ID_ENABLED', False),
        'entra_tenant_id': current_app.config.get('ENTRA_TENANT_ID', ''),
        'entra_client_id': current_app.config.get('ENTRA_CLIENT_ID', ''),
        'entra_group_admin': current_app.config.get('ENTRA_GROUP_ADMIN', ''),
        'entra_group_editor': current_app.config.get('ENTRA_GROUP_EDITOR', ''),
        'entra_group_readonly': current_app.config.get('ENTRA_GROUP_READONLY', ''),
        'entra_group_case_admin': current_app.config.get('ENTRA_GROUP_CASE_ADMIN', ''),
        'entra_role_case_admin': current_app.config.get('ENTRA_ROLE_CASE_ADMIN', ''),
        'entra_group_queue_admin': current_app.config.get('ENTRA_GROUP_QUEUE_ADMIN', ''),
        'entra_role_queue_admin': current_app.config.get('ENTRA_ROLE_QUEUE_ADMIN', ''),
        'entra_group_queuer': current_app.config.get('ENTRA_GROUP_QUEUER', ''),
        'entra_role_queuer': current_app.config.get('ENTRA_ROLE_QUEUER', ''),
        'entra_redirect_url': current_app.config.get('ENTRA_REDIRECT_URL', ''),

        # Database
        'db_type': db_type,
        'db_name': db_name,
        'db_host': db_host,
    }
    
    return render_template('tools/system_settings.html', system_info=system_info)


@tools_blueprint.route("/system_settings/save", methods=["POST"])
@login_required
@admin_required
def system_settings_save():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    key = data.get('key', '').upper()
    value = data.get('value')

    # Whitelist of editable keys with their expected types
    key_types = {
        'LIMIT_USER_VIEW_TO_ORG': 'bool',
        'ENFORCE_PRIVILEGED_CASE': 'bool',
        'MISP_EXPORT_FILES': 'bool',
        'SHOW_GDPR_NOTICE': 'bool',
        'TASK_REQUESTED': 'int',
        'TASK_APPROVED': 'int',
        'TASK_REJECTED': 'int',
        'MISP_EVENT_THREAT_LEVEL': 'int',
        'MISP_EVENT_ANALYSIS': 'int',
        'LOG_FILE': 'str',
        'AUDIT_LOG_PREFIX': 'str',
        'MAIN_LOGO': 'str',
        'TOPRIGHT_LOGO': 'str',
        'WELCOME_TEXT_TOP': 'str',
        'WELCOME_TEXT_BOTTOM': 'str',
        'WELCOME_LOGO': 'str',
        'GDPR_NOTICE': 'str',
        'MISP_ADD_LOCAL_TAGS_ALL_EVENTS': 'list',
    }

    if key not in key_types:
        return jsonify({"error": "Invalid configuration key"}), 400

    value_type = key_types[key]

    # Format value for Python source code
    if value_type == 'bool':
        py_value = 'True' if value else 'False'
    elif value_type == 'int':
        try:
            py_value = str(int(value))
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid integer value"}), 400
    elif value_type == 'list':
        items = [item.strip() for item in value.split(',') if item.strip()]
        py_value = repr(items)
    else:
        py_value = repr(str(value))

    app_root = Path(__file__).parent.parent.parent
    config_path = app_root / 'conf' / 'config.py'
    backup_path = config_path.parent / 'config.py.backup'

    # Create backup before modifying
    shutil.copy2(str(config_path), str(backup_path))

    content = config_path.read_text()
    pattern = re.compile(r'^(\s+' + re.escape(key) + r'\s*=\s*)(.*?)(\s*#.*)?$', re.MULTILINE)
    new_content, count = pattern.subn(lambda m: m.group(1) + py_value + (m.group(3) or ''), content, count=1)

    if count == 0:
        return jsonify({"error": f"Could not find {key} in config.py"}), 400

    config_path.write_text(new_content)

    # Update running config
    if value_type == 'bool':
        current_app.config[key] = bool(value)
    elif value_type == 'int':
        current_app.config[key] = int(value)
    elif value_type == 'list':
        current_app.config[key] = items
    else:
        current_app.config[key] = str(value)

    flowintel_log("audit", 200, "System setting changed", User=current_user.email, Setting=key, Value=py_value)

    return jsonify({"message": "Configuration saved", "backup_created": True})


@tools_blueprint.route("/system_settings/reload", methods=["POST"])
@login_required
@admin_required
def system_settings_reload():
    """Reload configuration by restarting gunicorn workers or refreshing in-process."""
    ok, message, status = reload_application()
    if not ok:
        return jsonify({"error": message}), status

    flowintel_log("audit", 200, "Application reload requested", User=current_user.email)
    return jsonify({"message": message}), status

