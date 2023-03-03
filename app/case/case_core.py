from .. import db
from ..db_class.db import Case, Task
from ..utils.utils import isUUID
import uuid
import bleach
import markdown

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
        db.session.commit()
        return True
    return False

def delete_task(id):
    task = get_task(id)
    if task is not None:
        db.session.delete(task)
        db.session.commit()
        return True
    return False

def add_case_core(form):
    case = Case(
        title=form.title.data,
        description=form.description.data,
        uuid=str(uuid.uuid4()))
    db.session.add(case)
    db.session.commit()

    return case

def add_task_core(form, id):
    task = Task(
        uuid=str(uuid.uuid4()),
        title=form.title.data,
        description=form.description.data,
        case_id=id)
    db.session.add(task)
    db.session.commit()

    return task

def modif_note_core(id, notes):
    task = get_task(id)
    if task:
        task.notes = bleach.clean(notes)
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