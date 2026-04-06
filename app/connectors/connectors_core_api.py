from ..db_class.db import Connector, Connector_Icon, Connector_Instance
from ..utils import utils

def verif_add_connector(data_dict):
    if "name" not in data_dict or not data_dict["name"]:
        return {"message": "Please give a name to your connector"}
    elif Connector.query.filter_by(name=data_dict["name"]).first():
        return {"message": "Name already exist"}
    
    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = ""

    if "icon_select" not in data_dict or not data_dict["icon_select"]:
        data_dict["icon_select"] = ""
    elif not Connector_Icon.query.get(data_dict["icon_select"]).first():
        return {"message": "Icon not found"}

    return data_dict

def verif_add_instance(data_dict):
    if "name" not in data_dict or not data_dict["name"]:
        return {"message": "Please give a name to your instance"}
    elif Connector_Instance.query.filter_by(name=data_dict["name"]).first():
        return {"message": "Name already exist"}
    
    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = ""

    # type is mandatory for creation
    if "type_select" not in data_dict or not data_dict["type_select"]:
        return {"message": "Please give a type to your instance"}
    elif data_dict["type_select"] not in utils.get_module_type():
        return {"message": "type selected unknown"}
    
    if "url" not in data_dict or not data_dict["url"]:
        return {"message": "Please give a url to your instance"}
    else:
        # basic URL validation and scheme sanitization
        from urllib.parse import urlparse
        parsed = urlparse(data_dict["url"].strip())
        scheme = (parsed.scheme or '').lower()
        if scheme not in ("http", "https"):
            return {"message": "URL must start with http:// or https://"}
        if not parsed.netloc:
            return {"message": "Invalid URL"}
    
    if "api_key" not in data_dict or not data_dict["api_key"]:
        data_dict["api_key"] = ""

    return data_dict

def verif_edit_connector(data_dict, cid):
    connector = Connector.query.get(cid)
    if "name" not in data_dict or data_dict["name"] == connector.name or not data_dict["name"]:
        data_dict["name"] = connector.name
    elif Connector.query.filter_by(name=data_dict["name"]).first():
        return {"message": "Name already exist"}
    
    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = connector.description

    if "icon_select" not in data_dict or not data_dict["icon_select"]:
        data_dict["icon_select"] = connector.icon_id

    return data_dict

def verif_edit_instance(data_dict, iid):
    instance = Connector_Instance.query.get(iid)
    if "name" not in data_dict or data_dict["name"] == instance.name or not data_dict["name"]:
        data_dict["name"] = instance.name
    elif Connector_Instance.query.filter_by(name=data_dict["name"]).first():
        return {"message": "Name already exist"}
    
    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = instance.description

    if "type_select" not in data_dict or not data_dict["type_select"]:
        data_dict["type_select"] = instance.type
    elif data_dict["type_select"] not in utils.get_module_type():
        return {"message": "type selected unknown"}

    if "url" not in data_dict or not data_dict["url"]:
        data_dict["url"] = instance.url
    else:
        from urllib.parse import urlparse
        parsed = urlparse(data_dict["url"].strip())
        scheme = (parsed.scheme or '').lower()
        if scheme not in ("http", "https"):
            return {"message": "URL must start with http:// or https://"}
        if not parsed.netloc:
            return {"message": "Invalid URL"}

    if "api_key" not in data_dict or not data_dict["api_key"]:
        data_dict["api_key"] = ""

    return data_dict