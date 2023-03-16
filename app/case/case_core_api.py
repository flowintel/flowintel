from .. import db
from ..db_class.db import Case, Task, Task_User, User, Case_User
from ..utils.utils import isUUID
import uuid
import bleach
from flask_login import current_user
import datetime
from . import case_core as CaseModel


def dead_line_check(date, time):
    dead_line = None
    if date and time:
        dead_line = datetime.datetime.combine(date, time)
    elif date:
        dead_line = date
    
    return dead_line

def get_user_api(api_key):
    return User.query.filter_by(api_key=api_key).first()


def verif_add_api(data_dict):
    if "title" not in data_dict:
        return {"message": "Please give a title to the case"}
    elif Case.query.filter_by(title=data_dict["title"]).first():
        return {"message": "Title already in use"}

    if "description" not in data_dict:
        data_dict["description"] = ""

    if "dead_line_date" in data_dict:
        if data_dict["dead_line_date"]:
            try:
                datetime_object = datetime.strptime(data_dict["dead_line_date"], '%Y-%m-%d') 
            except:
                return {"message": "date bad format"}
    else:
        data_dict["dead_line_date"] = ""

    if "dead_line_time" in data_dict:
        if data_dict["dead_line_time"]:
            try:
                datetime_object = datetime.strptime(data_dict["dead_line_time"], '%H-%M') 
            except:
                return {"message": "time bad format"}
    else:
        data_dict["dead_line_time"] = ""

    return data_dict


def verif_edit_api(data_dict, case_id):
    case = CaseModel.get(case_id)
    if "title" not in data_dict:
        data_dict["title"] = case.title

    if "description" not in data_dict:
        data_dict["description"] = case.description

    if "dead_line_date" in data_dict:
        if data_dict["dead_line_date"]:
            try:
                datetime_object = datetime.strptime(data_dict["dead_line_date"], '%Y-%m-%d') 
            except:
                return {"message": "date bad format"}
    elif case.dead_line:
        data_dict["dead_line_date"] = case.dead_line.strftime('%Y-%m-%d')
    else:
        data_dict["dead_line_date"] = ""

    if "dead_line_time" in data_dict:
        if data_dict["dead_line_time"]:
            try:
                datetime_object = datetime.strptime(data_dict["dead_line_time"], '%H-%M') 
            except:
                return {"message": "time bad format"}
    elif case.dead_line:
        data_dict["dead_line_time"] = case.dead_line.strftime('%H-%M')
    else:
        data_dict["dead_line_time"] = ""

    return data_dict


def add_case_core(data_dict):
    dead_line = dead_line_check(data_dict["dead_line_date"], data_dict["dead_line_time"])

    case = Case(
        title=bleach.clean(data_dict["title"]),
        description=bleach.clean(data_dict["description"]),
        uuid=str(uuid.uuid4()),
        creation_date=datetime.datetime.now(),
        last_modif=datetime.datetime.now(),
        dead_line=dead_line
    )
    db.session.add(case)
    db.session.commit()

    return case


def add_task_core(data_dict, id):
    dead_line = dead_line_check(data_dict["dead_line_date"], data_dict["dead_line_time"])

    task = Task(
        uuid=str(uuid.uuid4()),
        title=bleach.clean(data_dict["title"]),
        description=bleach.clean(data_dict["description"]),
        creation_date=datetime.datetime.now(),
        dead_line=dead_line,
        case_id=id
    )
    db.session.add(task)
    CaseModel.update_last_modif(id)
    db.session.commit()

    return task


def edit_case_core(data_dict, id):
    case = CaseModel.get(id)

    dead_line = dead_line_check(data_dict["dead_line_date"], data_dict["dead_line_time"])

    case.title = bleach.clean(data_dict["title"])
    case.description=bleach.clean(data_dict["description"])
    case.dead_line=dead_line

    CaseModel.update_last_modif(id)
    db.session.commit()


def edit_task_core(data_dict, id):
    task = CaseModel.get_task(id)
    dead_line = dead_line_check(data_dict["dead_line_date"], data_dict["dead_line_time"])

    task.title = bleach.clean(data_dict["title"])
    task.description=bleach.clean(data_dict["description"])
    task.dead_line=dead_line

    CaseModel.update_last_modif(task.case_id)
    db.session.commit()