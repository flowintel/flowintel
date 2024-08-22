from flask import Blueprint, redirect, render_template, request, session
from flask_login import current_user, login_required
from ..db_class.db import *
from ..utils.utils import form_to_dict
from ..decorators import editor_required
from . import analyzer_core as AnalyzerModel
from .form import AnalzyerForm

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


@analyzer_blueprint.route("/analyzer_result/<pid>", methods=['GET', 'POST'])
@login_required
def analyzer_result(pid):
    """Recieve result form analyzers"""
    session["pending_id"] = pid
    return render_template("analyzer/analyzer_result.html")


@analyzer_blueprint.route("/get_analyzer_results/<pid>", methods=['GET', 'POST'])
@login_required
def get_analyzer_results(pid):
    """Get result from analyzers"""
    p = AnalyzerModel.get_pending_result(pid)
    return p.to_json()


@analyzer_blueprint.route("/nextPage", methods=['GET', 'POST'])
@login_required
def nextPage():
    """Enrich notes from previous selection"""
    session["note_selected"] = request.form["note_selected"]
    return render_template("analyzer/nextPage.html")

@analyzer_blueprint.route("/get_note_selected", methods=['GET', 'POST'])
@login_required
def get_note_selected():
    """Get notes selected"""
    return session.get("note_selected")


@analyzer_blueprint.route("/manage_notes_selected", methods=['GET', 'POST'])
@login_required
@editor_required
def manage_notes_selected():
    """Manage notes selected"""
    case_id = AnalyzerModel.manage_notes_selected(request.json, current_user, session.get("pending_id"))
    session["note_selected"] = ""
    session["pending_id"] = ""
    return {"case_id": case_id}, 200

##########
# Config #
##########

@analyzer_blueprint.route("/config", methods=['GET'])
@login_required
@editor_required
def config():
    """Configure analyzers"""
    return render_template("analyzer/analyzer_config.html")


@analyzer_blueprint.route("/add_analyzer", methods=['GET', 'POST'])
@login_required
@editor_required
def add_analyzer():
    """Add a new analyzer"""
    form = AnalzyerForm()
    if form.validate_on_submit():
        if AnalyzerModel.add_analyzer_core(form_to_dict(form)):
            return redirect("/analyzer")
    return render_template("analyzer/add_analyzer.html", form=form)


@analyzer_blueprint.route("/<aid>/delete_analyzer", methods=['GET', 'POST'])
@login_required
@editor_required
def delete_analyzer(aid):
    """Delete an analyzer"""
    if AnalyzerModel.get_analyzer(aid):
        if AnalyzerModel.delete_analyzer(aid):
            return {"message": "Analyzer deleted", "toast_class": "success-subtle"}, 200
        return {"message": "Error analyzer deleted", 'toast_class': "danger-subtle"}, 400
    return {"message": "Analyzer not found", 'toast_class': "danger-subtle"}, 404


@analyzer_blueprint.route("/analyzers_data", methods=['GET'])
@login_required
def analyzers_data():
    """List all analyzers"""
    return [analyzer.to_json() for analyzer in AnalyzerModel.get_analyzers()]


@analyzer_blueprint.route("/change_status", methods=['GET', 'POST'])
@login_required
@editor_required
def change_status():
    """Active or disabled an analyzer"""
    if "analyzer_id" in request.args:
        res = AnalyzerModel.change_status_core(request.args.get("analyzer_id"))
        if res:
            return {'message': 'Analyzer status changed', 'toast_class': "success-subtle"}, 200
        return {'message': 'Something went wrong', 'toast_class': "danger-subtle"}, 400
    return {'message': 'Need to pass "analyzer_id"', 'toast_class': "warning-subtle"}, 400


@analyzer_blueprint.route("/change_config", methods=['GET', 'POST'])
@login_required
@editor_required
def change_config():
    """Change configuration for an analyzer"""
    if "analyzer_id" in request.json["result_dict"] and request.json["result_dict"]["analyzer_id"]:
        if "analyzer_name" in request.json["result_dict"] and request.json["result_dict"]["analyzer_name"]:
            if "analyzer_url" in request.json["result_dict"] and request.json["result_dict"]["analyzer_url"]:
                res = AnalyzerModel.change_config_core(request.json["result_dict"])
                if res:
                    return {'message': 'Config changed', 'toast_class': "success-subtle"}, 200
                return {'message': 'Something went wrong', 'toast_class': "danger-subtle"}, 400
            return {'message': 'Need to pass "analyzer_url"', 'toast_class': "warning-subtle"}, 400
        return {'message': 'Need to pass "analyzer_name"', 'toast_class': "warning-subtle"}, 400
    return {'message': 'Need to pass "analyzer_id"', 'toast_class': "warning-subtle"}, 400



###################
# Pending Results # 
###################

@analyzer_blueprint.route("/pending", methods=['GET'])
@login_required
def pending():
    """Pending page"""
    return render_template("analyzer/pending_index.html")


@analyzer_blueprint.route("/get_pending_result", methods=['GET'])
@login_required
def get_pending_result():
    """Get Pending result"""
    page = request.args.get('page', 1, type=int)
    pendings = AnalyzerModel.get_pending_results(page)
    return [pending.to_json() for pending in pendings]

@analyzer_blueprint.route("/get_len_pending_result", methods=['GET'])
@login_required
def get_len_pending_result():
    """Get length Pending result"""
    return {"len": AnalyzerModel.get_len_pending_results()}

@analyzer_blueprint.route("/delete_pending_result/<pid>", methods=['GET'])
@login_required
def delete_pending_result(pid):
    """Get length Pending result"""
    p = AnalyzerModel.get_pending_result(pid)
    if p:
        AnalyzerModel.delete_pending_result(pid)
        return {"message": "Pending result deleted", "toast_class": "success-subtle"}, 200
    return {"message": "Pending result not found", "toast_class": "danger-subtle"}, 404

