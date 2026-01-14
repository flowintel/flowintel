from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from ..case.TaskCore import TaskModel
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


def is_it_true(value):
  return value.lower() == 'true'
@my_assignment_blueprint.route("/sort_tasks", methods=['GET'])
@login_required
def my_assignment_sort_tasks():
    """Sort Task by living one"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', default=False, type=is_it_true)
    status = not status
    filter_value = request.args.get('filter', type=str)
    tasks_list = AssignModel.my_assignment_sort(user=current_user, completed=status, page=page, filter=filter_value)
    return {"tasks": AssignModel.get_task_info(tasks_list, current_user), "nb_pages": tasks_list.pages}
