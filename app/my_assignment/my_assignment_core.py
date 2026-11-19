from datetime import datetime, timedelta

from sqlalchemy import asc, desc, func, or_

from app.db_class.db import Case, Case_Org, Status, Subtask, Task, Task_User, User

from ..case import common_core as CommonModel
from ..case.TaskCore import TaskModel

# Statuses that should not appear under "Ongoing Tasks"
_INACTIVE_STATUS_NAMES = ("Rejected", "Unavailable")


def get_user(uid):
    return User.query.get(uid)

def _inactive_status_ids():
    return [s.id for s in Status.query.filter(Status.name.in_(_INACTIVE_STATUS_NAMES)).all()]

def _visible_assignments(user, viewer):
    """Apply the public/private case visibility rule before pagination or counts."""
    query = Task.query.join(Task_User, Task_User.task_id==Task.id)\
                      .filter(Task_User.user_id==user.id)
    visible_case = Case.query.filter(Case.id==Task.case_id)
    if not viewer.is_admin():
        visibility = Case.is_private.is_not(True)
        if viewer.org_id is not None:
            membership = Case_Org.query.filter(
                Case_Org.case_id==Case.id, Case_Org.org_id==viewer.org_id
            ).exists()
            visibility = or_(visibility, membership)
        visible_case = visible_case.filter(visibility)
    return query.filter(visible_case.exists())


# Sort keys accepted from the client (never a raw column name in order_by)
SORT_COLUMNS = {
    "last_modif": Task.last_modif,
    "creation_date": Task.creation_date,
    "deadline": Task.deadline,
    "title": func.lower(Task.title),
    "status_id": Task.status_id,
    "case": Task.case_id,
}
PAGE_SIZES = (10, 25, 50, 100)


def my_assignment_sort(user, completed, page, filter=None, inactive_only=False, overdue_only=False, viewer=None,
                       order="desc", per_page=20, title_filter=None, due=None, group_by_case=False):
    """Tasks assigned to `user` that `viewer` may see, sorted and paginated.

    filter: a SORT_COLUMNS key (anything else keeps the database order); order: asc|desc,
    applied before pagination; title_filter: case-insensitive title search; due: a deadline
    window ("overdue", "24h", "7d", "30d", "none"); group_by_case: tasks of a case come
    together (most recently modified case first), the chosen sort applies inside each case."""
    viewer = viewer if viewer is not None else user
    query = _visible_assignments(user, viewer).filter(Task.completed==completed)
    inactive_ids = _inactive_status_ids()
    if inactive_only and inactive_ids:
        query = query.filter(Task.status_id.in_(inactive_ids))
    elif not completed and inactive_ids:
        query = query.filter(Task.status_id.notin_(inactive_ids))
    if overdue_only:
        query = query.filter(Task.deadline.isnot(None), Task.deadline < datetime.utcnow())
    if title_filter:
        query = query.filter(Task.title.ilike(f"%{title_filter}%"))
    now = datetime.utcnow()
    windows = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
    if due == "overdue":
        query = query.filter(Task.deadline.isnot(None), Task.deadline < now)
    elif due in windows:
        query = query.filter(Task.deadline >= now, Task.deadline < now + windows[due])
    elif due == "none":
        query = query.filter(Task.deadline.is_(None))
    if group_by_case:
        last_case_modif = Case.query.with_entities(Case.last_modif).filter(Case.id == Task.case_id).scalar_subquery()
        query = query.order_by(desc(last_case_modif), Task.case_id)
    if filter in SORT_COLUMNS:
        column = SORT_COLUMNS[filter]
        if filter == "deadline":
            # tasks without a deadline last, whatever the order
            query = query.order_by(Task.deadline.is_(None))
        query = query.order_by(asc(column) if order == "asc" else desc(column), Task.id)
    if per_page not in PAGE_SIZES and per_page != 20:
        per_page = 25
    query = query.paginate(page=page, per_page=per_page, max_per_page=100)
    return query


def get_task_info(tasks_list, user):
    tasks_by_case = {}
    for task in tasks_list:
        case = CommonModel.get_case(task.case_id)
        if not CommonModel.can_view_case(case, user):
            continue
        users, _ = TaskModel.get_users_assign_task(task.id, user)
        final_task = task.to_json()
        final_task["users"] = users
        final_task["subtasks"] = []
        cp_open=0
        subtasks = Subtask.query.filter_by(task_id=task.id).order_by(Subtask.task_order_id).all()
        for subtask in subtasks:
            final_task["subtasks"].append(subtask.to_json())
            if not subtask.completed:
                cp_open += 1
        final_task["nb_open_subtasks"] = cp_open

        if not case.title in tasks_by_case:
            tasks_by_case[case.title] = []
        tasks_by_case[case.title].append(final_task)
    return tasks_by_case


def get_task_list_info(tasks_list, user):
    """Flat list for the web page (task_list component): each task with its users, open
    subtasks and the case it belongs to (id, title, privileged, private)."""
    tasks = []
    cases = {}
    for task in tasks_list:
        if task.case_id not in cases:
            cases[task.case_id] = CommonModel.get_case(task.case_id)
        case = cases[task.case_id]
        if not CommonModel.can_view_case(case, user):
            continue
        users, _ = TaskModel.get_users_assign_task(task.id, user)
        loc = task.to_json()
        loc["users"] = users
        subtasks = Subtask.query.filter_by(task_id=task.id).order_by(Subtask.task_order_id).all()
        loc["subtasks"] = [s.to_json() for s in subtasks]
        loc["nb_open_subtasks"] = sum(1 for s in subtasks if not s.completed)
        loc["case"] = {"id": case.id, "title": case.title, "privileged_case": bool(case.privileged_case),
                       "is_private": bool(case.is_private)}
        tasks.append(loc)
    return tasks


def calculate_task_stats(user):
    base_query = _visible_assignments(user, user).filter(Task.completed==False)
    excluded = _inactive_status_ids()
    if excluded:
        base_query = base_query.filter(Task.status_id.notin_(excluded))
    
    total = base_query.count()
    
    now = datetime.utcnow()
    overdue = base_query.filter(Task.deadline < now).count()
    
    week_from_now = now + timedelta(days=7)
    due_this_week = base_query.filter(Task.deadline >= now, Task.deadline <= week_from_now).count()
    
    return {
        'total': total,
        'overdue': overdue,
        'due_this_week': due_this_week
    }
