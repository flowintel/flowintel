import os

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc

from app.db_class.db import Case, Task_User, Task
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
    """Get stats for home page welcome header"""
    try:
        # Count open cases that user has access to
        all_open_cases = Case.query.filter_by(completed=False).all()
        accessible_cases = CommonModel.check_user_in_private_cases(all_open_cases, current_user)
        open_cases = len(accessible_cases)
        
        # Count tasks assigned to current user (not completed)
        # Get task IDs assigned to current user
        user_task_ids = [tu.task_id for tu in Task_User.query.filter_by(user_id=current_user.id).all()]
        assigned_tasks = Task.query.filter(
            Task.id.in_(user_task_ids),
            Task.completed == False
        ).count() if user_task_ids else 0
        
        # Count unread notifications
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

def open_closed(case):
    cp_open = 0
    cp_closed = 0
    for task in case.tasks:
        if task.completed:
            cp_closed += 1
        else:
            cp_open += 1
    return cp_open, cp_closed

@home_blueprint.route("/last_case")
@login_required
def last_case():
    # display 10 without private that cannot be seen
    cp = 0
    last_case = []
    all_case = Case.query.order_by(desc('last_modif')).all()
    misp_icon = CommonModel.get_misp_connector_icon() or ""
    for case in all_case:
        if cp < 10:
            if case.is_private:
                if CommonModel.get_present_in_case(case.id, current_user) or current_user.is_admin():
                    loc_case = CaseModel.regroup_case_info_core(case, current_user, misp_icon)
                    last_case.append(loc_case)
                    cp += 1
            else:
                loc_case = CaseModel.regroup_case_info_core(case, current_user, misp_icon)
                last_case.append(loc_case)
                cp += 1
            case.to_json()
    return {"cases": last_case}, 200


@home_blueprint.route("/version")
@login_required
def version():
    with open(os.path.join(os.getcwd(),"version")) as read_version:
        loc = read_version.readlines()
    return {"version": loc[0]}


@home_blueprint.route("/home_overview")
@login_required
def home_overview():
    """Side panels of the home page: the user's open tasks and the deadlines coming up"""
    import datetime

    now = datetime.datetime.now()
    horizon = now + datetime.timedelta(days=14)

    open_cases = CommonModel.check_user_in_private_cases(
        Case.query.filter_by(completed=False).all(), current_user)
    case_by_id = {c.id: c for c in open_cases}

    def fmt(value):
        return value.strftime('%Y-%m-%d %H:%M') if value else None

    # Open tasks assigned to the user, soonest deadline first (no deadline last)
    task_ids = [tu.task_id for tu in Task_User.query.filter_by(user_id=current_user.id).all()]
    my_tasks = []
    if task_ids:
        tasks = Task.query.filter(Task.id.in_(task_ids), Task.completed == False).all()
        tasks = [t for t in tasks if t.case_id in case_by_id]
        tasks.sort(key=lambda t: (t.deadline is None, t.deadline or now))
        for t in tasks[:6]:
            my_tasks.append({
                "id": t.id, "title": t.title, "case_id": t.case_id,
                "case_title": case_by_id[t.case_id].title,
                "deadline": fmt(t.deadline), "status_id": t.status_id,
            })

    # Deadlines of open cases and their open tasks in the next 14 days, and those missed
    # in the last 30 days (older ones are no longer "upcoming")
    since = now - datetime.timedelta(days=30)
    deadlines = []
    for c in open_cases:
        if c.deadline and since <= c.deadline <= horizon:
            deadlines.append({"kind": "case", "id": c.id, "case_id": c.id, "title": c.title,
                              "case_title": c.title, "deadline": fmt(c.deadline)})
    if case_by_id:
        due_tasks = Task.query.filter(Task.case_id.in_(list(case_by_id)), Task.completed == False,
                                      Task.deadline.isnot(None), Task.deadline >= since,
                                      Task.deadline <= horizon).all()
        for t in due_tasks:
            deadlines.append({"kind": "task", "id": t.id, "case_id": t.case_id, "title": t.title,
                              "case_title": case_by_id[t.case_id].title, "deadline": fmt(t.deadline)})
    deadlines.sort(key=lambda d: d["deadline"])

    week = now + datetime.timedelta(days=7)
    due_this_week = sum(1 for d in deadlines if d["deadline"] <= fmt(week))
    return {"my_tasks": my_tasks, "deadlines": deadlines[:8], "due_this_week": due_this_week}, 200
