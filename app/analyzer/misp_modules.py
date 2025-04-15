from flask import Blueprint, jsonify, redirect, render_template, request, session
from flask_login import current_user, login_required
from ..db_class.db import *
from ..decorators import editor_required
from . import session_class as SessionModel
from . import misp_modules_core as MispModuleModel

analyzer_blueprint = Blueprint(
    'analyzer',
    __name__,
    template_folder='templates',
    static_folder='static'
)

##########
# Render #
##########


@analyzer_blueprint.route("/misp-modules", methods=['GET'])
@login_required
def index():
    """Analyzer index page"""
    case_id = ""
    task_id = ""
    misp_object = ""
    if 'case_id' in request.args:
        case_id = request.args.get('case_id')
    if 'task_id' in request.args:
        task_id = request.args.get('task_id')
    if "misp_object" in request.args:
        misp_object = True
    return render_template("analyzer/misp_modules_index.html", case_id=case_id, task_id=task_id, misp_object=misp_object)

@analyzer_blueprint.route("/misp-modules/result_to_case", methods=['GET', 'POST'])
@login_required
def result_to_case():
    """Enrich notes from previous selection"""
    session["note_selected"] = request.form["note_selected"]
    return render_template("analyzer/misp_modules_result_to_case.html")

@analyzer_blueprint.route("/misp-modules/get_note_selected", methods=['GET', 'POST'])
@login_required
def get_note_selected():
    """Get notes selected"""
    return session.get("note_selected")


@analyzer_blueprint.route("/misp-modules/manage_notes_selected", methods=['GET', 'POST'])
@login_required
@editor_required
def manage_notes_selected():
    """Manage notes selected"""
    case_id = MispModuleModel.manage_notes_selected(request.json, current_user)
    session["note_selected"] = ""
    return {"case_id": case_id}, 200



@analyzer_blueprint.route("/misp-modules/get_list_misp_attributes")
@login_required
def get_list_misp_attributes():
    """Return all misp attributes for input and output"""
    res = MispModuleModel.get_list_misp_attributes()

    if "message" in res:
        return res, 404
    return res, 200

@analyzer_blueprint.route("/misp-modules/get_modules")
@login_required
def get_modules():
    """Return all modules available"""
    res = MispModuleModel.get_modules()

    if "message" in res:
        return res, 404
    return res, 200

@analyzer_blueprint.route("/misp-modules/run", methods=['POST'])
@login_required
@editor_required
def run_misp_modules():
    """Run modules"""
    if "query" in request.json:
        if "input" in request.json and request.json["input"]:
            if "modules" in request.json:
                session = SessionModel.Session_class(request.json, current_user)
                session.start()
                SessionModel.sessions.append(session)
                return jsonify(session.status()), 201
            return {"message": "Need a module type", 'toast_class': "warning-subtle"}, 400
        return {"message": "Need an input (misp attribute)", 'toast_class': "warning-subtle"}, 400
    return {"message": "Need to type something", 'toast_class': "warning-subtle"}, 400


##########
# Config #
##########

@analyzer_blueprint.route("/misp-modules/config", methods=['GET'])
@login_required
def misp_modules_config():
    """Configure misp-modules"""
    return render_template("analyzer/misp_modules_config.html")

@analyzer_blueprint.route("/misp-modules/modules_config_data")
@login_required
def modules_config_data():
    """List all modules for configuration"""

    modules_config = MispModuleModel.get_modules_config(current_user)
    return modules_config, 200

@analyzer_blueprint.route("/misp-modules/change_config", methods=["POST"])
@login_required
def misp_modules_change_config():
    """Change configuation for a misp-module"""
    if "module_name" in request.json["result_dict"]:
        res = MispModuleModel.change_config_core(request.json["result_dict"], current_user)
        if res:
            return {'message': 'Config changed', 'toast_class': "success-subtle"}, 200
        return {'message': 'Something went wrong', 'toast_class': "danger-subtle"}, 400
    return {'message': 'Need to pass "module_name"', 'toast_class': "warning-subtle"}, 400



###########
# Results #
###########

@analyzer_blueprint.route("/misp-modules/loading/<sid>", methods=["GET"])
@login_required
def misp_module_loading(sid):
    """Loading page waiting for results"""

    # l = {"query": ["circl.lu"], "input": "domain", "modules": ["circl_passivedns"]}
    # session = SessionModel.Session_class(l, current_user)
    # session.uuid = 12345
    # return render_template("analyzer/misp_modules_loading.html", sid=session.uuid)

    for s in SessionModel.sessions:
        if s.uuid == sid:
            return render_template("analyzer/misp_modules_loading.html", sid=sid)
    if MispModuleModel.get_misp_modules_result(sid):
        return redirect("/analyzer/misp-modules/result/"+sid)
    return render_template("404.html"), 404

@analyzer_blueprint.route("/misp-modules/loading_status/<sid>", methods=["GET"])
@login_required
def misp_module_loading_status(sid):
    """Loading page waiting for results"""
    # l = {"query": ["circl.lu"], "input": "domain", "modules": ["circl_passivedns"]}
    # session = SessionModel.Session_class(l, current_user)
    # session.uuid = 12345
    # return jsonify(session.status_for_test())

    for s in SessionModel.sessions:
        if s.uuid == sid:
            return jsonify(s.status)
    return {"message": "Session Not found", 'toast_class': "danger-subtle"}, 404


@analyzer_blueprint.route("/misp-modules/result_data/<sid>", methods=["GET"])
@login_required
def misp_module_result_data(sid):
    """Result page of misp-modules query"""
    res = MispModuleModel.get_misp_modules_result(sid)
    if res:
        return res.to_json()
    return render_template("404.html"), 404

@analyzer_blueprint.route("/misp-modules/result/<sid>", methods=['GET', 'POST'])
@login_required
def misp_module_result(sid):
    """Recieve result form analyzers"""
    return render_template("analyzer/misp_modules_result.html", sid=sid)


###########
# History #
###########

@analyzer_blueprint.route("/misp-modules/history", methods=['GET'])
@login_required
def misp_modules_history():
    """History of misp-modules"""
    return render_template("analyzer/misp_modules_history.html")

@analyzer_blueprint.route("/misp-modules/history_data", methods=['GET'])
@login_required
def misp_modules_history_data():
    """Get all history"""
    page = request.args.get('page', 1, type=int)
    histories, nb_pages = MispModuleModel.get_history(page)
    return {"history": histories, "nb_pages": nb_pages}

@analyzer_blueprint.route("/misp-modules/delete_history/<huuid>", methods=['GET'])
@login_required
def misp_modules_delete_history(huuid):
    """Delete history"""
    if MispModuleModel.delete_history(huuid, current_user):
        return {"message": "History deleted", "toast_class": "success-subtle"}, 200
    return {"message": "Error deleting History", "toast_class": "warning-subtle"}, 400

