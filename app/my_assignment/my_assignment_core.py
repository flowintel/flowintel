from ..db_class.db import Task, Task_User
from sqlalchemy import desc

def my_assignment_sort_by_status(user, completed, page):
    return Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==user.id, Task.completed==completed).paginate(page=page, per_page=20, max_per_page=50)


def my_assignment_sort_by_filter(user, completed, filter, page):
    return Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==user.id, Task.completed==completed).order_by(desc(filter)).paginate(page=page, per_page=20, max_per_page=50)

