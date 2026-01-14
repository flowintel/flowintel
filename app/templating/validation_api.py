from ..db_class.db import Case_Template, Task_Template
from ..utils.datadictHelper import edition_verification_tags_connectors, creation_verification_tags_connectors


def common_creation(data_dict):
    if "time_required" not in data_dict or not data_dict["time_required"]:
        data_dict["time_required"] = ""
    return creation_verification_tags_connectors(data_dict)

def common_edit(data_dict, case_task):
    if "time_required" not in data_dict or not data_dict["time_required"]:
        data_dict["time_required"] = case_task.time_required
    return edition_verification_tags_connectors(data_dict, case_task)

def verif_create_case_template(data_dict):
    if "title" not in data_dict or not data_dict["title"]:
        return {"message": "Please give a title to the case"}
    elif Case_Template.query.filter_by(title=data_dict["title"]).first():
        return {"message": "Title already exist"}

    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = ""

    data_dict["tasks"] = []

    return common_creation(data_dict)

def verif_edit_case_template(data_dict, case_id):
    case_template = Case_Template.query.get(case_id)
    if "title" not in data_dict or not data_dict["title"]:
        data_dict["title"] = case_template.title
    
    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = case_template.description
    
    return common_edit(data_dict, case_template)


def verif_add_task_template(data_dict):
    if "title" not in data_dict or not data_dict["title"]:
        return {"message": "Please give a title to the case"}

    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = ""

    return common_creation(data_dict)

def verif_edit_task_template(data_dict, task_id):
    task_template = Task_Template.query.get(task_id)
    if "title" not in data_dict or not data_dict["title"]:
        data_dict["title"] = task_template.title
    
    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = task_template.description

    return common_edit(data_dict, task_template)