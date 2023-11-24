from ..db_class.db import Case_Template, User, Task_Template
from ..utils.utils import check_tag
from . import common_template_core as CommonModel


def get_user_api(api_key):
    return User.query.filter_by(api_key=api_key).first()

def verif_create_case_template(data_dict):
    if "title" not in data_dict or not data_dict["title"]:
        return {"message": "Please give a title to the case"}
    elif Case_Template.query.filter_by(title=data_dict["title"]).first():
        return {"message": "Title already exist"}

    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = ""

    data_dict["tasks"] = []

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

    return data_dict

def verif_edit_case_template(data_dict, case_id):
    case_template = Case_Template.query.get(case_id)
    if "title" not in data_dict or not data_dict["title"]:
        data_dict["title"] = case_template.title
    
    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = case_template.description

    if "tags" in data_dict:
        for tag in data_dict["tags"]:
            if not check_tag(tag):
                return {"message": f"Tag '{tag}' doesn't exist"}
    elif case_template.to_json()["tags"]:
        data_dict["tags"] = case_template.to_json()["tags"]
    else:
        data_dict["tags"] = []

    if "clusters" in data_dict:
        for cluster in data_dict["clusters"]:
            if not CommonModel.check_cluster_db(cluster):
                return {"message": f"Cluster '{cluster}' doesn't exist"}
    elif case_template.to_json()["clusters"]:
        data_dict["clusters"] = case_template.to_json()["clusters"]
    else:
        data_dict["clusters"] = []

    return data_dict


def verif_add_task_template(data_dict):
    if "title" not in data_dict or not data_dict["title"]:
        return {"message": "Please give a title to the case"}

    if "description" not in data_dict or not data_dict["description"]:
        data_dict["body"] = ""
    else:
        data_dict["body"] = data_dict["description"]

    if "url" not in data_dict or not data_dict["url"]:
        data_dict["url"] = ""

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

    return data_dict

def verif_edit_task_template(data_dict, task_id):
    task_template = Task_Template.query.get(task_id)
    if "title" not in data_dict or not data_dict["title"]:
        data_dict["title"] = task_template.title
    
    if "description" not in data_dict or not data_dict["description"]:
        data_dict["body"] = task_template.description

    if "url" not in data_dict or not data_dict["url"]:
        data_dict["url"] = task_template.url

    if "tags" in data_dict:
        for tag in data_dict["tags"]:
            if not check_tag(tag):
                return {"message": f"Tag '{tag}' doesn't exist"}
    elif task_template.to_json()["tags"]:
        data_dict["tags"] = task_template.to_json()["tags"]
    else:
        data_dict["tags"] = []

    if "clusters" in data_dict:
        for cluster in data_dict["clusters"]:
            if not CommonModel.check_cluster_db(cluster):
                return {"message": f"Cluster '{cluster}' doesn't exist"}
    elif task_template.to_json()["clusters"]:
        data_dict["clusters"] = task_template.to_json()["clusters"]
    else:
        data_dict["clusters"] = []

    return data_dict