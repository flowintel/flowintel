from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

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
    from ..account.settings_core import get_case_view
    # same default display as the case list (Settings → Cases → Default display)
    return render_template("my_assignment/my_assignment.html", default_view=get_case_view(current_user))


def is_it_true(value):
    return value.lower() == 'true'


@my_assignment_blueprint.route("/sort_tasks", methods=['GET'])
@login_required
def my_assignment_sort_tasks():
    """Sort tasks and optionally calculate statistics"""
    page = request.args.get('page', 1, type=int)
    show_completed = request.args.get('status', default=False, type=is_it_true)
    inactive_only = request.args.get('inactive', default=False, type=is_it_true)
    overdue_only = request.args.get('overdue', default=False, type=is_it_true)
    completed = not show_completed
    filter_value = request.args.get('filter', type=str)
    order = 'asc' if request.args.get('order') == 'asc' else 'desc'
    per_page = request.args.get('per_page', 20, type=int)
    title_q = request.args.get('q', None, type=str)
    due = request.args.get('due', None, type=str)
    # flat=true: one list with the case of each task (task_list component); otherwise the
    # former shape, tasks grouped by case title
    flat = request.args.get('flat', default=False, type=is_it_true)
    group_by_case = request.args.get('group', default=False, type=is_it_true)
    # tag filters (from the top bar search): "|"-separated names / cluster tags, all required
    tag_names = [t for t in request.args.get('tags', '', type=str).split('|') if t][:10]
    cluster_tags = [t for t in request.args.get('clusters', '', type=str).split('|') if t][:10]

    tasks_list = AssignModel.my_assignment_sort(
        user=current_user,
        completed=completed,
        page=page,
        filter=filter_value,
        inactive_only=inactive_only,
        overdue_only=overdue_only,
        order=order,
        per_page=per_page,
        title_filter=title_q,
        due=due,
        group_by_case=group_by_case,
        tag_names=tag_names,
        cluster_tags=cluster_tags,
    )

    stats = AssignModel.calculate_task_stats(current_user) if not completed and not inactive_only else None

    info = AssignModel.get_task_list_info if flat else AssignModel.get_task_info
    return {
        "tasks": info(tasks_list, current_user),
        "nb_pages": tasks_list.pages,
        "total": tasks_list.total,
        "stats": stats
    }
