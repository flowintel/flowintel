import os
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc

from ..db_class.db import Case, Task_User, Task, Notification

from ..case import common_core as CommonModel

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
        # Count open cases (status_id = 1 typically means open)
        open_cases = Case.query.filter_by(completed=False).count()
        
        # Count tasks assigned to current user (not completed)
        # Get task IDs assigned to current user
        user_task_ids = [tu.task_id for tu in Task_User.query.filter_by(user_id=current_user.id).all()]
        assigned_tasks = Task.query.filter(
            Task.id.in_(user_task_ids),
            Task.completed == False
        ).count() if user_task_ids else 0
        
        # Count unread notifications
        notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()
        
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
    # display 10 without private that cannot be seen
    cp = 0
    last_case = []
    all_case = Case.query.order_by(desc('last_modif')).all()
    for case in all_case:
        if cp < 10:
            if case.is_private:
                if CommonModel.get_present_in_case(case.id, current_user) or current_user.is_admin():
                    last_case.append(case.to_json())
                    cp += 1
            else:
                last_case.append(case.to_json())
                cp += 1
    return {"cases": last_case}, 200


@home_blueprint.route("/version")
@login_required
def version():
    with open(os.path.join(os.getcwd(),"version")) as read_version:
        loc = read_version.readlines()
    return {"version": loc[0]}