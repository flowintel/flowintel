from ..db_class.db import Case, User
from datetime import datetime
from . import common_core as CommonModel
from ..utils.datadictHelper import edition_verification_tags_connectors, creation_verification_tags_connectors


def get_user_api(headers):
    if "MATRIX-ID" in headers:
        bot = User.query.filter_by(last_name="Bot", first_name="Matrix").first()
        if bot:
            if bot.api_key == headers["X-API-KEY"]:
                user = User.query.filter_by(matrix_id=headers["MATRIX-ID"]).first()
                if user:
                    return user
    return User.query.filter_by(api_key=headers["X-API-KEY"]).first()


def verif_set_recurring(data_dict):
    if "once" in data_dict:
        try:
            data_dict["once"] = datetime.strptime(data_dict["once"], '%Y-%m-%d') 
        except:
            return {"message": "once date bad format, YYYY-mm-dd"}
    if "weekly" in data_dict:
        try:
            data_dict["weekly"] = datetime.strptime(data_dict["weekly"], '%Y-%m-%d').date()
        except:
            return {"message": "weekly date bad format, YYYY-mm-dd"}
    if "monthly" in data_dict:
        try:
            data_dict["monthly"] = datetime.strptime(data_dict["monthly"], '%Y-%m-%d').date()
        except:
            return {"message": "monthly date bad format, YYYY-mm-dd"}
    return data_dict


def verif_create_case_task(data_dict, isCase):
    if "title" not in data_dict or not data_dict["title"]:
        return {"message": "Please give a title"}
    elif Case.query.filter_by(title=data_dict["title"]).first():
        return {"message": "Title already exist"}

    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = ""

    if "deadline_date" in data_dict:
        try:
            data_dict["deadline_date"] = datetime.strptime(data_dict["deadline_date"], '%Y-%m-%d') 
        except:
            return {"message": "deadline_date bad format"}
    else:
        data_dict["deadline_date"] = ""

    if "deadline_time" in data_dict:
        try:
            data_dict["deadline_time"] = datetime.strptime(data_dict["deadline_time"], '%H-%M') 
        except:
            return {"message": "deadline_time bad format"}
    else:
        data_dict["deadline_time"] = ""

    data_dict = creation_verification_tags_connectors(data_dict)

    if not isCase:
        if "url" not in data_dict or not data_dict["url"]:
            data_dict["url"] = ""

        if "connectors" in data_dict:
            loc = CommonModel.check_connector(data_dict["connectors"])
            if not isinstance(loc, bool):
                return {"message": f"Connector '{loc}' doesn't exist"}
        else:
            data_dict["connectors"] = []


    return data_dict



def common_verif(data_dict, case_task):
    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = case_task.description

    if "deadline_date" in data_dict:
        try:
            data_dict["deadline_date"] = datetime.strptime(data_dict["deadline_date"], '%Y-%m-%d') 
        except:
            return {"message": "date bad format"}
    elif case_task.deadline:
        data_dict["deadline_date"] = case_task.deadline.strftime('%Y-%m-%d')
    else:
        data_dict["deadline_date"] = ""

    if "deadline_time" in data_dict:
        try:
            data_dict["deadline_time"] = datetime.strptime(data_dict["deadline_time"], '%H-%M') 
        except:
            return {"message": "time bad format"}
    elif case_task.deadline:
        data_dict["deadline_time"] = case_task.deadline.strftime('%H-%M')
    else:
        data_dict["deadline_time"] = ""

    data_dict = edition_verification_tags_connectors(data_dict, case_task)
    
    return data_dict


def verif_edit_case(data_dict, case_id):
    case = CommonModel.get_case(case_id)
    if "title" not in data_dict or data_dict["title"] == case.title or not data_dict["title"]:
        data_dict["title"] = case.title
    elif Case.query.filter_by(title=data_dict["title"]).first():
        return {"message": "Title already exist"}

    data_dict = common_verif(data_dict, case)

    return data_dict


def verif_edit_task(data_dict, task_id):
    task = CommonModel.get_task(task_id)
    if "title" not in data_dict or data_dict["title"] == task.title or not data_dict["title"]:
        data_dict["title"] = task.title

    data_dict = common_verif(data_dict, task)

    if "url" not in data_dict or not data_dict["url"]:
        data_dict["url"] = task.url

    if "connectors" in data_dict:
        loc = CommonModel.check_connector(data_dict["connectors"])
        if not isinstance(loc, bool):
            return {"message": f"Connector '{loc}' doesn't exist"}
    elif task.to_json()["connectors"]:
        data_dict["connectors"] = task.to_json()["connectors"]
    else:
        data_dict["connectors"] = []

    return data_dict
