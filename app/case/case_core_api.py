from ..db_class.db import Case, User
from datetime import datetime
from . import case_core as CaseModel


def get_user_api(api_key):
    return User.query.filter_by(api_key=api_key).first()


def verif_set_recurring(data_dict):
    if "once" in data_dict:
        try:
            data_dict["once"] = datetime.strptime(data_dict["once"], '%Y-%m-%d') 
        except:
            return {"message": "once date bad format"}
    if "weekly" in data_dict:
        try:
            data_dict["weekly"] = datetime.strptime(data_dict["weekly"], '%Y-%m-%d') 
        except:
            return {"message": "weekly date bad format"}
    if "monthly" in data_dict:
        try:
            data_dict["monthly"] = datetime.strptime(data_dict["monthly"], '%Y-%m-%d') 
        except:
            return {"message": "monthly date bad format"}
    return data_dict


def verif_add_case_task(data_dict, isCase):
    if "title" not in data_dict:
        return {"message": "Please give a title to the case"}
    elif Case.query.filter_by(title=data_dict["title"]).first():
        return {"message": "Title already in use"}

    if "description" not in data_dict:
        data_dict["description"] = ""

    if "deadline_date" in data_dict:
        try:
            data_dict["deadline_date"] = datetime.strptime(data_dict["deadline_date"], '%Y-%m-%d') 
        except:
            return {"message": "date bad format"}
    else:
        data_dict["deadline_date"] = ""

    if "deadline_time" in data_dict:
        try:
            data_dict["deadline_time"] = datetime.strptime(data_dict["deadline_time"], '%H-%M') 
        except:
            return {"message": "time bad format"}
    else:
        data_dict["deadline_time"] = ""

    if not isCase:
        if "url" not in data_dict:
            data_dict["url"] = ""

    return data_dict



def common_verif(data_dict, case_task):
    if "description" not in data_dict:
        data_dict["description"] = case_task.description

    if "deadline_date" in data_dict:
        try:
            data_dict["deadline_date"] = datetime.strptime(data_dict["deadline_date"], '%Y-%m-%d') 
        except:
            return {"message": "date bad format"}
    elif case_task.dead_line:
        data_dict["deadline_date"] = case_task.dead_line.strftime('%Y-%m-%d')
    else:
        data_dict["deadline_date"] = ""

    if "deadline_time" in data_dict:
        try:
            data_dict["deadline_time"] = datetime.strptime(data_dict["deadline_time"], '%H-%M') 
        except:
            return {"message": "time bad format"}
    elif case_task.dead_line:
        data_dict["deadline_time"] = case_task.dead_line.strftime('%H-%M')
    else:
        data_dict["deadline_time"] = ""
    
    return data_dict


def verif_edit_case(data_dict, case_id):
    case = CaseModel.get_case(case_id)
    if "title" not in data_dict or data_dict["title"] == case.title:
        data_dict["title"] = case.title
    elif Case.query.filter_by(title=data_dict["title"]).first():
        return {"message": "Title already in use"}

    data_dict = common_verif(data_dict, case)

    return data_dict


def verif_edit_task(data_dict, task_id):
    task = CaseModel.get_task(task_id)
    if "title" not in data_dict or data_dict["title"] == task.title:
        data_dict["title"] = task.title

    data_dict = common_verif(data_dict, task)

    if "url" not in data_dict:
        data_dict["url"] = task.url

    return data_dict
=