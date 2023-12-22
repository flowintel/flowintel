from ..db_class.db import Case_Template, User, Task_Template
from ..utils.utils import check_tag
from . import common_template_core as CommonModel


def get_user_api(api_key):
    return User.query.filter_by(api_key=api_key).first()

def common_creation(data_dict):
    if "tags" in data_dict:
        for tag in data_dict["tags"]:
            if not check_tag(tag):
                return {"message": f"Tag '{tag}' doesn't exist"}
    else:
        data_dict["tags"] = []

    if "clusters" in data_dict:
        for cluster in data_dict["clusters"]:
            if not CommonModel.check_cluster_db(cluster):
                return {"message": f"Cluster '{cluster}' doesn't exist"}
    else:
        data_dict["clusters"] = []

    if "connectors" in data_dict:
        for connector in data_dict["connectors"]:
            if not CommonModel.check_connector(connector):
                return {"message": f"connector '{connector}' doesn't exist"}
    else:
        data_dict["connectors"] = []

    if "identifier" in data_dict:
        for connector in list(data_dict["identifier"].keys()):
            if not CommonModel.check_connector(connector):
                return {"message": f"Connector '{connector}' doesn't exist"}
    else:
        data_dict["identifier"] = []

    return data_dict

def common_edit(data_dict, case_task):
    if "tags" in data_dict:
        for tag in data_dict["tags"]:
            if not check_tag(tag):
                return {"message": f"Tag '{tag}' doesn't exist"}
    elif case_task.to_json()["tags"]:
        data_dict["tags"] = case_task.to_json()["tags"]
    else:
        data_dict["tags"] = []

    if "clusters" in data_dict:
        for cluster in data_dict["clusters"]:
            if not CommonModel.check_cluster_db(cluster):
                return {"message": f"Cluster '{cluster}' doesn't exist"}
    elif case_task.to_json()["clusters"]:
        data_dict["clusters"] = case_task.to_json()["clusters"]
    else:
        data_dict["clusters"] = []

    if "connectors" in data_dict:
        for connector in data_dict["connectors"]:
            if not CommonModel.check_connector(connector):
                return {"message": f"connector '{connector}' doesn't exist"}
    elif case_task.to_json()["connectors"]:
        data_dict["connectors"] = case_task.to_json()["connectors"]
    else:
        data_dict["connectors"] = []
    
    if "identifier" in data_dict:
        for connector in list(data_dict["identifier"].keys()):
            if not CommonModel.check_connector(connector):
                return {"message": f"connector '{connector}' doesn't exist"}
    else:
        data_dict["identifier"] = {}

    return data_dict


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
        data_dict["body"] = ""
    else:
        data_dict["body"] = data_dict["description"]

    if "url" not in data_dict or not data_dict["url"]:
        data_dict["url"] = ""

    return common_creation(data_dict)

def verif_edit_task_template(data_dict, task_id):
    task_template = Task_Template.query.get(task_id)
    if "title" not in data_dict or not data_dict["title"]:
        data_dict["title"] = task_template.title
    
    if "description" not in data_dict or not data_dict["description"]:
        data_dict["body"] = task_template.description

    if "url" not in data_dict or not data_dict["url"]:
        data_dict["url"] = task_template.url

    return common_edit(data_dict, task_template)