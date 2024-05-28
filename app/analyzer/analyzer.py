from flask import Blueprint, render_template, request, session
from flask_login import login_required
from ..db_class.db import *
from ..utils.utils import MISP_MODULES

analyzer_blueprint = Blueprint(
    'analyzer',
    __name__,
    template_folder='templates',
    static_folder='static'
)

##########
# Render #
##########


@analyzer_blueprint.route("/", methods=['GET'])
@login_required
def index():
    """Analyzer index page"""
    case_id = ""
    task_id = ""
    if 'case_id' in request.args:
        case_id = request.args.get('case_id')
    if 'task_id' in request.args:
        task_id = request.args.get('task_id')
    return render_template("analyzer/analyzer_index.html", case_id=case_id, task_id=task_id)


@analyzer_blueprint.route("/recieve_result", methods=['GET', 'POST'])
@login_required
def recieve_result():
    """Recieve result form analyzers"""
    if "result" in request.form:
        session["misp_modules_res"] = request.form["result"]
    else:
        session["misp_modules_res"] = None
    return render_template("analyzer/analyzer_result.html")

@analyzer_blueprint.route("/get_misp_modules_result", methods=['GET', 'POST'])
@login_required
def get_misp_modules_result():
    """Get result from misp-modules"""
    return session.get("misp_modules_res")


@analyzer_blueprint.route("/nextPage", methods=['GET', 'POST'])
@login_required
def nextPage():
    """Get result from misp-modules"""
    session["note_selected"] = request.form["note_selected"]
    return render_template("analyzer/nextPage.html")

@analyzer_blueprint.route("/get_note_selected", methods=['GET', 'POST'])
@login_required
def get_note_selected():
    """Get result from misp-modules"""
    return session.get("note_selected")

@analyzer_blueprint.route("/misp-modules-url", methods=['GET', 'POST'])
@login_required
def misp_modules_url():
    """Get misp-modules url"""
    return {"url": MISP_MODULES}
