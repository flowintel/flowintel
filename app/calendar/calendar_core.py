import os
from .. import db
from ..db_class.db import Case, Task, Task_User, User, Case_Org, Org, Status
from ..utils.utils import isUUID
import uuid
import datetime
from sqlalchemy import desc

def get_task_month_core(date_month, user):
    return Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==user.id, Task.dead_line.startswith(date_month) ).all()
