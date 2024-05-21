import fnmatch
import importlib
import os
import glob
import json
import re
import sys
import uuid
import random
import string
import jsonschema
from ..db_class.db import User
from pytaxonomies import Taxonomies
from pymispgalaxies import Galaxies, Clusters
from conf.config import Config

MODULES = {}
MODULES_CONFIG = {}
MODULE_PATH = os.path.join(os.getcwd(), "app", "modules")
MISP_MODULES = Config.MISP_MODULES

manifest = os.path.join(os.getcwd(), "modules/misp-taxonomies/MANIFEST.json")

galaxies_list = []
root_dir_galaxies = os.path.join(os.getcwd(), 'modules/misp-galaxy/galaxies')
for galaxy_file in glob.glob(os.path.join(root_dir_galaxies, '*.json')):
    with open(galaxy_file, 'r') as f:
        galaxies_list.append(json.load(f))

clusters_list = []
root_dir_clusters = os.path.join(os.getcwd(), 'modules/misp-galaxy/clusters')
for galaxy_file in glob.glob(os.path.join(root_dir_clusters, '*.json')):
    with open(galaxy_file, 'r') as f:
        clusters_list.append(json.load(f))

taxonomies = Taxonomies(manifest_path=manifest)
galaxies = Galaxies(galaxies=galaxies_list)
clusters = Clusters(clusters=clusters_list)

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


def get_module_type():
    type_list = list()
    for dir in os.listdir(MODULE_PATH):
        type_list.append(dir)
    return type_list

def get_modules_list():
    modulename_list = list()
    sys.path.append(MODULE_PATH)
    for root, dirnames, filenames in os.walk(MODULE_PATH):
        if os.path.basename(root) == '__pycache__':
            continue
        if re.match(r'^\.', os.path.basename(root)):
            continue
        for filename in fnmatch.filter(filenames, '*.py'):
            if filename == '__init__.py':
                continue
            modulename = filename.split(".")[0]
            root_dir = os.path.basename(root)
            MODULES[modulename] = importlib.import_module(root_dir + '.' + modulename)
            MODULES_CONFIG[modulename] = {"type": root_dir, "config": MODULES[modulename].module_config}
            modulename_list.append(modulename)

    loc_elem = []
    for elem in MODULES_CONFIG:
        if elem not in modulename_list:
            loc_elem.append(elem)
    
    for elem in loc_elem:
        del MODULES_CONFIG[elem]
        del MODULES[elem]

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
        "clusters":{
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
        },
        "clusters":{
            "type": "array",
            "items": {"type": "string"},
        },
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
