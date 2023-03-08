from .. import db
from ..db_class.db import Case, Task, Task_User, User, Case_User
from ..utils.utils import isUUID
import uuid
import bleach
import markdown
from flask_login import current_user
import datetime


def get(id):
    if isUUID(id):
        case = Case.query.filter_by(uuid=id).first()
    elif id.isdigit():
        case = Case.query.get(id)
    else:
        case = None
    return case

def get_task(id):
    if isUUID(id):
        case = Task.query.filter_by(uuid=id).first()
    elif id.isdigit():
        case = Task.query.get(id)
    else:
        case = None
    return case

def getAll():
    cases = Case.query.all()
    return cases


def delete(id):
    case = get(id)
    if case is not None:
        db.session.delete(case)
        Case_User.query.filter_by(case_id=case.id).delete()
        db.session.commit()
        return True
    return False

def update_last_modif(id):
    case = Case.query.get(id)
    case.last_modif = datetime.datetime.now()

def delete_task(id):
    task = get_task(id)
    if task is not None:
        db.session.delete(task)
        Task_User.query.filter_by(task_id=task.id).delete()

        update_last_modif(task.case_id)
        db.session.commit()
        return True
    return False

def add_case_core(form):
    dead_line = dead_line_check(form.dead_line_date.data, form.dead_line_time.data)

    case = Case(
        title=bleach.clean(form.title.data),
        description=bleach.clean(form.description.data),
        uuid=str(uuid.uuid4()),
        creation_date=datetime.datetime.now(),
        last_modif=datetime.datetime.now(),
        dead_line=dead_line
    )
    db.session.add(case)
    db.session.commit()

    return case

def edit_case_core(form, id):
    case = get(id)

    dead_line = dead_line_check(form.dead_line_date.data, form.dead_line_time.data)

    case.title = bleach.clean(form.title.data)
    case.description=bleach.clean(form.description.data)
    case.dead_line=dead_line

    update_last_modif(id)
    db.session.commit()
    

def add_task_core(form, id):
    dead_line = dead_line_check(form.dead_line_date.data, form.dead_line_time.data)

    task = Task(
        uuid=str(uuid.uuid4()),
        title=bleach.clean(form.title.data),
        description=bleach.clean(form.description.data),
        creation_date=datetime.datetime.now(),
        dead_line=dead_line,
        case_id=id
    )
    db.session.add(task)
    update_last_modif(id)
    db.session.commit()

    return task

def edit_task_core(form, id):
    task = get_task(id)
    dead_line = dead_line_check(form.dead_line_date.data, form.dead_line_time.data)

    task.title = bleach.clean(form.title.data)
    task.description=bleach.clean(form.description.data)
    task.dead_line=dead_line

    update_last_modif(task.case_id)
    db.session.commit()


def dead_line_check(date, time):
    dead_line = None
    if date and time:
        dead_line = datetime.datetime.combine(date, time)
    elif date:
        dead_line = date
    
    return dead_line


def modif_note_core(id, notes):
    task = get_task(id)
    if task:
        task.notes = bleach.clean(notes)
        update_last_modif(task.case_id)
        db.session.commit()
        return True
    return False

def get_note_text(id):
    task = get_task(id)
    if task:
        return task.notes
    else:
        return ""

def get_note_markdown(id):
    task = get_task(id)
    if task:
        return markdown.markdown(task.notes)
    else:
        return ""

def assign_task(id):
    task = get_task(id)
    task_user = Task_User(task_id=task.id, user_id=current_user.id)
    db.session.add(task_user)

    case_user = Case_User.query.filter_by(case_id=task.case_id, user_id=current_user.id).first()

    if not case_user:
        case_user = Case_User(case_id=task.case_id, user_id=current_user.id) 
        db.session.add(case_user)

    update_last_modif(task.case_id)

    db.session.commit()

def get_user_assign_task(task_id):
    task_users = Task_User.query.filter_by(task_id=task_id).all()
    users = list()
    flag = False
    for task_user in task_users:
        u = User.query.get(task_user.user_id)
        if u.id == current_user.id:
            flag = True
        users.append(u.to_json())
    return users, flag

def get_user_assign_case(case_id):
    case_user = Case_User.query.filter_by(case_id=case_id).all()
    users = list()

    for user in case_user:
        u = User.query.get(user.user_id)
        users.append(u.to_json())

    return users


def remove_assign_task(id):
    task = get_task(id)
    task_users = Task_User.query.filter_by(task_id=task.id, user_id=current_user.id).all()
    for task_user in task_users:
        db.session.delete(task_user)

    update_last_modif(task.case_id)
    
    db.session.commit()