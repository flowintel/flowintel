from .. import db
from ..db_class.db import Case, Task
from ..utils.utils import isUUID
import uuid

def get(id):
    if isUUID(id):
        case = Case.query.filter_by(uuid=id).first()
    elif id.isdigit():
        case = Case.query.get(id)
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