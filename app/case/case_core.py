from .. import db
from ..db_class.db import Case, Task
from ..utils.utils import isUUID
import uuid

def get(id):
    if isUUID(id):
        case = db.session.execute(db.select(Case).filter_by(uuid=id)).first()
    elif id.isdigit():
        case = db.session.execute(db.select(Case).filter_by(id=id)).first()
    else:
        case = None
    return case

def getAll():
    cases = db.session.execute(db.select(Case)).scalars()
    return cases

def case_uuid_route_core(sid):
    tasks = db.session.execute(db.select(Task).filter_by(uuid_case=sid)).scalars()
    return tasks

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