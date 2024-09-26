from .utils import check_tag
from ..case import common_core as CommonModel

def creation_verification_tags_connectors(data_dict):
    if "tags" in data_dict:
        for tag in data_dict["tags"]:
            if not check_tag(tag):
                return {"message": f"Tag '{tag}' doesn't exist"}
    else:
        data_dict["tags"] = []

    if "clusters" in data_dict:
        loc = CommonModel.check_cluster(data_dict["clusters"])
        if not isinstance(loc, bool):
            return {"message": f"Cluster '{loc}' doesn't exist"}
    else:
        data_dict["clusters"] = []

    if "custom_tags" in data_dict:
        loc = CommonModel.check_custom_tags(data_dict["custom_tags"])
        if not isinstance(loc, bool):
            return {"message": f"Custom tag '{loc}' doesn't exist"}
    else:
        data_dict["custom_tags"] = []

    return data_dict

def edition_verification_tags_connectors(data_dict, case_task):
    if "tags" in data_dict:
        for tag in data_dict["tags"]:
            if not check_tag(tag):
                return {"message": f"Tag '{tag}' doesn't exist"}
    elif case_task.to_json()["tags"]:
        data_dict["tags"] = case_task.to_json()["tags"]
    else:
        data_dict["tags"] = []

    if "clusters" in data_dict:
        loc = CommonModel.check_cluster(data_dict["clusters"])
        if not isinstance(loc, bool):
            return {"message": f"Cluster '{loc}' doesn't exist"}
    elif case_task.to_json()["clusters"]:
        data_dict["clusters"] = case_task.to_json()["clusters"]
    else:
        data_dict["clusters"] = []
            
    if "custom_tags" in data_dict:
        loc = CommonModel.check_custom_tags(data_dict["custom_tags"])
        if not isinstance(loc, bool):
            return {"message": f"Custom tag '{loc}' doesn't exist"}
    elif case_task.to_json()["custom_tags"]:
        data_dict["custom_tags"] = case_task.to_json()["custom_tags"]
    else:
        data_dict["custom_tags"] = []

    return data_dict