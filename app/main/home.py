import os

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc

from app.db_class.db import Case, Task_User, Task
from app.extensions import db
from app.notification import notification_core as NotifModel

from ..case import common_core as CommonModel
from ..case.CaseCore import CaseModel

home_blueprint = Blueprint(
    'home',
    __name__,
    template_folder='templates',
    static_folder='static'
)


@home_blueprint.route("/")
@login_required
def home():    
    return render_template("home.html")

@home_blueprint.route("/home_stats")
@login_required
def home_stats():
    """Stats of the home page header — counted in SQL (no case loaded)"""
    try:
        visible = CommonModel.visible_case_filter(current_user)
        open_cases = Case.query.filter(Case.completed.is_not(True), visible).count()
        assigned_tasks = Task.query.join(Task_User, Task_User.task_id == Task.id)\
            .join(Case, Case.id == Task.case_id)\
            .filter(Task_User.user_id == current_user.id, Task.completed.is_not(True), visible).count()
        notifications = len(NotifModel.get_user_notif(current_user, "true"))
        return jsonify({
            "open_cases": open_cases,
            "assigned_tasks": assigned_tasks,
            "notifications": notifications,
            "user": {
                "first_name": current_user.first_name,
                "last_name": current_user.last_name
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@home_blueprint.route("/last_case")
@login_required
def last_case():
    """The 10 most recently modified cases the user can see"""
    misp_icon = CommonModel.get_misp_connector_icon() or ""
    cases = Case.query.filter(CommonModel.visible_case_filter(current_user))\
        .order_by(desc(Case.last_modif), desc(Case.id)).limit(10).all()
    return {"cases": [CaseModel.regroup_case_info_core(case, current_user, misp_icon) for case in cases]}, 200


@home_blueprint.route("/version")
@login_required
def version():
    with open(os.path.join(os.getcwd(),"version")) as read_version:
        loc = read_version.readlines()
    return {"version": loc[0]}


@home_blueprint.route("/home_overview")
@login_required
def home_overview():
    """Side panels of the home page: the user's open tasks and the deadlines coming up.
    Everything is filtered, sorted and limited in SQL."""
    import datetime
    from sqlalchemy import and_

    now = datetime.datetime.now()
    horizon = now + datetime.timedelta(days=14)
    since = now - datetime.timedelta(days=30)   # missed in the last 30 days still shows
    visible = CommonModel.visible_case_filter(current_user)
    open_case = and_(Case.completed.is_not(True), visible)

    def fmt(value):
        return value.strftime('%Y-%m-%d %H:%M') if value else None

    # Open tasks assigned to the user, soonest deadline first (no deadline last)
    rows = db.session.query(Task, Case.title).join(Task_User, Task_User.task_id == Task.id)\
        .join(Case, Case.id == Task.case_id)\
        .filter(Task_User.user_id == current_user.id, Task.completed.is_not(True), open_case)\
        .order_by(Task.deadline.is_(None), Task.deadline, Task.id).limit(6).all()
    my_tasks = [{"id": t.id, "title": t.title, "case_id": t.case_id, "case_title": case_title,
                 "deadline": fmt(t.deadline), "status_id": t.status_id} for t, case_title in rows]

    # Deadlines of open cases and of their open tasks, from 30 days ago to 14 days ahead
    case_rows = Case.query.filter(open_case, Case.deadline >= since, Case.deadline <= horizon)\
        .order_by(Case.deadline).limit(8).all()
    task_rows = db.session.query(Task, Case.title).join(Case, Case.id == Task.case_id)\
        .filter(open_case, Task.completed.is_not(True), Task.deadline >= since, Task.deadline <= horizon)\
        .order_by(Task.deadline).limit(8).all()
    deadlines = [{"kind": "case", "id": c.id, "case_id": c.id, "title": c.title, "case_title": c.title,
                  "deadline": fmt(c.deadline)} for c in case_rows]
    deadlines += [{"kind": "task", "id": t.id, "case_id": t.case_id, "title": t.title, "case_title": case_title,
                   "deadline": fmt(t.deadline)} for t, case_title in task_rows]
    deadlines.sort(key=lambda d: d["deadline"])

    week = now + datetime.timedelta(days=7)
    due_this_week = Case.query.filter(open_case, Case.deadline >= since, Case.deadline <= week).count() + \
        db.session.query(Task.id).join(Case, Case.id == Task.case_id)\
        .filter(open_case, Task.completed.is_not(True), Task.deadline >= since, Task.deadline <= week).count()
    return {"my_tasks": my_tasks, "deadlines": deadlines[:8], "due_this_week": due_this_week}, 200
