from ..db_class.db import Subtask, Task, Task_User, User
from sqlalchemy import desc
from ..case import common_core as CommonModel
from ..case.TaskCore import TaskModel

def get_user(uid):
    return User.query.get(uid)

def my_assignment_sort(user, completed, page, filter=None):
    query = Task.query.join(Task_User, Task_User.task_id==Task.id)\
                      .where(Task_User.user_id==user.id, Task.completed==completed)
    if filter:
        query = query.order_by(desc(filter))
    query = query.paginate(page=page, per_page=20, max_per_page=50)
    return query


def get_task_info(tasks_list, user):
    tasks_by_case = {}
    for task in tasks_list:
        case = CommonModel.get_case(task.case_id)
        users, _ = TaskModel.get_users_assign_task(task.id, user)
        finalTask = task.to_json()
        finalTask["users"] = users
        finalTask["subtasks"] = []
        cp_open=0
        subtasks = Subtask.query.filter_by(task_id=task.id).order_by(Subtask.task_order_id).all()
        for subtask in subtasks:
            finalTask["subtasks"].append(subtask.to_json())
            if not subtask.completed:
                cp_open += 1
        finalTask["nb_open_subtasks"] = cp_open

        if not case.title in tasks_by_case:
            tasks_by_case[case.title] = []
        tasks_by_case[case.title].append(finalTask)
    return tasks_by_case