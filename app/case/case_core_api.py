from .. import db
from ..db_class.db import Case, Task, Task_User, User, Case_Org
from ..utils.utils import isUUID
import uuid
import bleach
from flask_login import current_user
import datetime
from . import case_core as CaseModel


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


