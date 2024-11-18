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
from ..db_class.db import Case, Case_Org, Task, Task_User

@tools_blueprint.route("/stats")
@login_required
def stats():
    cases_open = Case.query.join(Case_Org, Case_Org.case_id==Case.id).where(Case_Org.org_id==current_user.org_id, Case.completed==False).all()

    cases_closed = Case.query.join(Case_Org, Case_Org.case_id==Case.id).where(Case_Org.org_id==current_user.org_id, Case.completed==True).all()

    tasks_open = Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==current_user.id, Task.completed==False).all()
    tasks_closed = Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==current_user.id, Task.completed ==True).all()

    all_cases_open = Case.query.filter_by(completed=False).all()
    all_cases_closed = Case.query.filter_by(completed=True).all()

    all_tasks_open = Task.query.filter_by(completed=False).all()
    all_tasks_closed = Task.query.filter_by(completed=True).all()
    
    return render_template("tools/stats.html", 
                           cases_open_len=len(cases_open), 
                           cases_closed_len=len(cases_closed), 
                           tasks_open_len=len(tasks_open), 
                           tasks_closed_len=len(tasks_closed),
                           all_cases_open=len(all_cases_open),
                           all_cases_closed=len(all_cases_closed),
                           all_tasks_open=len(all_tasks_open),
                           all_tasks_closed=len(all_tasks_closed))

