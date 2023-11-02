import os
import random
import string
from ..db_class.db import User
import uuid
import jsonschema
from pytaxonomies import Taxonomies

taxonomies = Taxonomies()

def isUUID(uid):
    try:
        uuid.UUID(str(uid))
        return True
    except ValueError:
        return False


def generate_api_key(length=60):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))



def get_user_api(api_key):
    return User.query.filter_by(api_key=api_key).first()


def verif_api_key(headers):
    if not "X-API-KEY" in headers:
        return {"message": "Error no API key pass"}, 403
    user = get_user_api(headers["X-API-KEY"])
    if not user:
        return {"message": "API key not found"}, 403
    return {}

def form_to_dict(form):
    loc_dict = dict()
    for field in form._fields:
        if field == "files_upload":
            loc_dict[field] = dict()
            loc_dict[field]["data"] = form._fields[field].data
            loc_dict[field]["name"] = form._fields[field].name
        elif not field == "submit" and not field == "csrf_token":
            loc_dict[field] = form._fields[field].data
    return loc_dict

def create_specific_dir(specific_dir):
    if not os.path.isdir(specific_dir):
        os.mkdir(specific_dir)


caseSchema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "uuid": {"type": "string"},
        "deadline:": {"type": "string"},
        "recurring_date:": {"type": "string"},
        "recurring_type:": {"type": "string"},
        "tasks": {
            "type": "array", 
            "items": {"type": "object"},
        },
        "tags":{
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ['title']
}

taskSchema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "uuid": {"type": "string"},
        "deadline:": {"type": "string"},
        "url:": {"type": "string"},
        "notes:": {"type": "string"},
        "tags":{
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ['title']
}

def validateCaseJson(json_data):
    try:
        jsonschema.validate(instance=json_data, schema=caseSchema)
    except jsonschema.exceptions.ValidationError as err:
        print(err)
        return False
    return True

def validateTaskJson(json_data):
    try:
        jsonschema.validate(instance=json_data, schema=taskSchema)
    except jsonschema.exceptions.ValidationError as err:
        print(err)
        return False
    return True

def check_tag(tag):
    try:
        name = tag.split(":")[0]
        return tag in taxonomies.get(name).machinetags()
    except:
        return False


def generate_palette_from_string(s, items):
    hue = str_to_num(s)
    saturation = 1
    steps = 80 / items
    results = []
    for i in range(items):
        value = (20 + (steps * (i + 1))) / 100
        rgb = hsv_to_rgb([hue, saturation, value])
        results.append(rgb)
    return results

def str_to_num(s):
    char_code_sum = 0
    for char in s:
        char_code_sum += ord(char)
    return (char_code_sum % 100) / 100

def hsv_to_rgb(hsv):
    H, S, V = hsv
    H = H * 6
    I = int(H)
    F = H - I
    M = V * (1 - S)
    N = V * (1 - S * F)
    K = V * (1 - S * (1 - F))
    rgb = []
    
    if I == 0:
        rgb = [V, K, M]
    elif I == 1:
        rgb = [N, V, M]
    elif I == 2:
        rgb = [M, V, K]
    elif I == 3:
        rgb = [M, N, V]
    elif I == 4:
        rgb = [K, M, V]
    elif I == 5 or I == 6:
        rgb = [V, M, N]
    return convert_to_hex(rgb)

def convert_to_hex(color_list):
    color = "#"
    for element in color_list:
        element = round(element * 255)
        element = format(element, '02x')
        if len(element) == 1:
            element = '0' + element
        color += element
    return color