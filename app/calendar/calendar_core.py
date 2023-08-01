import os
from .. import db
from ..db_class.db import Case, Task, Task_User, User, Case_Org, Org, Status
from ..utils.utils import isUUID
import uuid
import datetime
from sqlalchemy import desc

def get_task_month_core(date_month, flag_dead_creation, user):
    if flag_dead_creation == 'true':
        return Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==user.id, Task.deadline.startswith(date_month) ).all()
    else:
        return Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==user.id, Task.creation_date.startswith(date_month) ).all()


def get_case_month_core(date_month, flag_dead_creation, user):
    if flag_dead_creation == 'true':
        return Case.query.join(Case_Org, Case_Org.case_id==Case.id).where(Case_Org.org_id==user.org_id, Case.deadline.startswith(date_month) ).all()
    else:
        return Case.query.join(Case_Org, Case_Org.case_id==Case.id).where(Case_Org.org_id==user.org_id, Case.creation_date.startswith(date_month) ).all()
