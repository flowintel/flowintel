from flask import Flask, Blueprint, render_template
from flask_login import login_required, current_user

from ..db_class.db import Case, Task, Task_User, Case_Org, Status

home_blueprint = Blueprint(
    'home',
    __name__,
    template_folder='templates',
    static_folder='static'
)


@home_blueprint.route("/")
@login_required
def home():
    # case_stat = list()
    cases_open = Case.query.join(Case_Org, Case_Org.case_id==Case.id).where(Case_Org.org_id==current_user.org_id, Case.completed==False).all()
    # for case in cases_open:
    #     case_stat.append(case.to_json())

    cases_closed = Case.query.join(Case_Org, Case_Org.case_id==Case.id).where(Case_Org.org_id==current_user.org_id, Case.completed==True).all()

    tasks_open = Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==current_user.id, Task.completed==False).all()
    tasks_closed = Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==current_user.id, Task.completed ==True).all()


    all_cases_open = Case.query.filter_by(completed=False).all()
    all_cases_closed = Case.query.filter_by(completed=True).all()

    all_tasks_open = Task.query.filter_by(completed=False).all()
    all_tasks_closed = Task.query.filter_by(completed=True).all()
    
    return render_template("home.html", 
                           cases_open_len=len(cases_open), 
                           cases_closed_len=len(cases_closed), 
                           tasks_open_len=len(tasks_open), 
                           tasks_closed_len=len(tasks_closed),
                           all_cases_open=len(all_cases_open),
                           all_cases_closed=len(all_cases_closed),
                           all_tasks_open=len(all_tasks_open),
                           all_tasks_closed=len(all_tasks_closed))