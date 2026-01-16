from ..db_class.db import Case
from datetime import datetime
from . import common_core as CommonModel
from ..utils.datadictHelper import edition_verification_tags_connectors, creation_verification_tags_connectors

DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H-%M'


def verif_set_recurring(data_dict):
    if "once" in data_dict:
        try:
            data_dict["once"] = datetime.strptime(data_dict["once"], DATE_FORMAT) 
        except ValueError:
            return {"message": "once date bad format, YYYY-mm-dd"}
    if "weekly" in data_dict:
        try:
            data_dict["weekly"] = datetime.strptime(data_dict["weekly"], DATE_FORMAT).date()
        except ValueError:
            return {"message": "weekly date bad format, YYYY-mm-dd"}
    if "monthly" in data_dict:
        try:
            data_dict["monthly"] = datetime.strptime(data_dict["monthly"], DATE_FORMAT).date()
        except ValueError:
            return {"message": "monthly date bad format, YYYY-mm-dd"}
    return data_dict


def verif_create_case_task(data_dict):
    if "title" not in data_dict or not data_dict["title"]:
        return {"message": "Please give a title"}
    elif Case.query.filter_by(title=data_dict["title"]).first():
        return {"message": "Title already exist"}

    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = ""

    if "deadline_date" in data_dict:
        try:
            data_dict["deadline_date"] = datetime.strptime(data_dict["deadline_date"], DATE_FORMAT) 
        except ValueError:
            return {"message": "deadline_date bad format"}
    else:
        data_dict["deadline_date"] = ""

    if "deadline_time" in data_dict:
        try:
            data_dict["deadline_time"] = datetime.strptime(data_dict["deadline_time"], TIME_FORMAT) 
        except ValueError:
            return {"message": "deadline_time bad format"}
    else:
        data_dict["deadline_time"] = ""

    data_dict = creation_verification_tags_connectors(data_dict)

    if "time_required" not in data_dict or not data_dict["time_required"]:
        data_dict["time_required"] = ""

    if "is_private" not in data_dict or not data_dict["is_private"]:
        data_dict["is_private"] = False
    elif not isinstance(data_dict["is_private"], bool):
        return {"message": "'is_private' need a bool"}
    
    if "ticket_id" not in data_dict or not data_dict["ticket_id"]:
        data_dict["ticket_id"] = ""


    return data_dict



def common_verif(data_dict, case_task):
    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = case_task.description

    if "deadline_date" in data_dict:
        try:
            data_dict["deadline_date"] = datetime.strptime(data_dict["deadline_date"], DATE_FORMAT) 
        except ValueError:
            return {"message": "date bad format"}
    elif case_task.deadline:
        data_dict["deadline_date"] = case_task.deadline.strftime(DATE_FORMAT)
    else:
        data_dict["deadline_date"] = ""

    if "deadline_time" in data_dict:
        try:
            data_dict["deadline_time"] = datetime.strptime(data_dict["deadline_time"], TIME_FORMAT) 
        except ValueError:
            return {"message": "time bad format"}
    elif case_task.deadline:
        data_dict["deadline_time"] = case_task.deadline.strftime(TIME_FORMAT)
    else:
        data_dict["deadline_time"] = ""

    if "time_required" not in data_dict or not data_dict["time_required"]:
        data_dict["time_required"] = case_task.time_required

    data_dict = edition_verification_tags_connectors(data_dict, case_task)
    
    return data_dict


def verif_edit_case(data_dict, case_id):
    case = CommonModel.get_case(case_id)
    if "title" not in data_dict or data_dict["title"] == case.title or not data_dict["title"]:
        data_dict["title"] = case.title
    elif Case.query.filter_by(title=data_dict["title"]).first():
        return {"message": "Title already exist"}
    
    if "is_private" not in data_dict or not data_dict["is_private"]:
        data_dict["is_private"] = case.is_private

    if "ticket_id" not in data_dict or not data_dict["ticket_id"]:
        data_dict["ticket_id"] = case.ticket_id

    data_dict = common_verif(data_dict, case)

    return data_dict


def verif_edit_task(data_dict, task_id):
    task = CommonModel.get_task(task_id)
    if "title" not in data_dict or data_dict["title"] == task.title or not data_dict["title"]:
        data_dict["title"] = task.title

    data_dict = common_verif(data_dict, task)

    return data_dict
