from ..db_class.db import Custom_Tags
import re
from . import custom_tags_core as CustomModel

def verif_add_custom_tag(request_json):
    if "name" not in request_json or not request_json["name"]:
        return {"message": "Please give a name to your tag"}
    elif Custom_Tags.query.filter_by(name=request_json["name"]).first():
        return {"message": "Name already exist"}
    
    if "color" not in request_json or not request_json["color"]:
        return {"message": "Please give a color to your tag"}
    else:
        p = re.compile(r"^#[a-fA-F0-9]{6}")
        if not p.match(request_json["color"]):
            return {"message": "Bad format for color. #ffffff"}
    if "icon" not in request_json or not request_json["icon"]:
        request_json["icon"] = ""
    return request_json

def verif_edit_custom_tag(request_json, custom_tag_id):
    custom_tag = CustomModel.get_custom_tag(custom_tag_id)
    if "name" not in request_json or not request_json["name"] or request_json["name"] == custom_tag.name:
        request_json["name"] = custom_tag.name
    elif Custom_Tags.query.filter_by(name=request_json["name"]).first():
        return {"message": "Name already exist"}
    
    request_json["custom_tag_name"] = request_json["name"]
    
    if "color" not in request_json or not request_json["color"] or request_json["color"] == custom_tag.color:
        request_json["color"] = custom_tag.color
    else:
        p = re.compile(r"^#[a-fA-F0-9]{6}")
        if not p.match(request_json["color"]):
            return {"message": "Bad format for color. #ffffff"}
    
    request_json["custom_tag_color"] = request_json["color"]
    
    if "icon" not in request_json or not request_json["icon"] or request_json["icon"] == custom_tag.icon:
        request_json["icon"] = custom_tag.icon
    else:
        request_json["icon"] = ""

    request_json["custom_tag_icon"] = request_json["icon"]

    request_json["custom_tag_id"] = custom_tag_id

    return request_json