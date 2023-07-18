from flask import Blueprint, render_template, redirect, jsonify, request, flash
from flask_login import login_required, current_user
from ..case import case_core as CaseModel
from . import my_assignment_core as AssignModel

my_assignment_blueprint = Blueprint(
    'task',
    __name__,
    template_folder='templates',
    static_folder='static'
)


@my_assignment_blueprint.route("/", methods=['GET'])
@login_required
def my_assignment():
    """View of a assigned tasks"""
    return render_template("my_assignment/my_assignment.html")


@my_assignment_blueprint.route("/data", methods=['GET'])
@login_required
def my_assignment_data():
    """Get tasks assigned to current user"""
    tasks_list = AssignModel.my_assignment_sort_by_status(user=current_user, completed=False)
    return CaseModel.get_task_info(tasks_list, current_user)


@my_assignment_blueprint.route("/sort_by_ongoing", methods=['GET'])
@login_required
def my_assignment_sort_by_ongoing():
    """Sort Task by living one"""
    tasks_list = AssignModel.my_assignment_sort_by_status(user=current_user, completed=False)
    return CaseModel.get_task_info(tasks_list, current_user)



@my_assignment_blueprint.route("/sort_by_finished", methods=['GET'])
@login_required
def my_assignment_sort_by_finished():
    """Sort Task by finished one"""
    tasks_list = AssignModel.my_assignment_sort_by_status(user=current_user, completed=True)
    return CaseModel.get_task_info(tasks_list, current_user)


@my_assignment_blueprint.route("/tasks/ongoing", methods=['GET'])
@login_required
def my_assignment_ongoing_sort_by_filter():
    """Sort Task by living one"""
    data_dict = dict(request.args)
    if "filter" in data_dict:
        tasks_list = AssignModel.my_assignment_sort_by_filter(user=current_user, completed=False, filter=data_dict["filter"])
        return CaseModel.get_task_info(tasks_list, current_user)
    return {"message": "No filter pass"}


@my_assignment_blueprint.route("/tasks/finished", methods=['GET'])
@login_required
def my_assignment_finished_sort_by_filter():
    """Sort Task by finished one"""
    data_dict = dict(request.args)
    if "filter" in data_dict:
        tasks_list = AssignModel.my_assignment_sort_by_filter(user=current_user, completed=False, filter=data_dict["filter"])
        return CaseModel.get_task_info(tasks_list, current_user)
    return {"message": "No filter pass"}
