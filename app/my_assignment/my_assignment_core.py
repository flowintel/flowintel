from ..db_class.db import Task, Task_User
from sqlalchemy import desc

def my_assignment_sort_by_status(user, completed):
    return Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==user.id, Task.completed==completed).all()


def my_assignment_sort_by_filter(user, completed, filter):
    return Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==user.id, Task.completed==completed).order_by(desc(filter)).all()

