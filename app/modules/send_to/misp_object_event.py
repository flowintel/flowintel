from pymisp import MISPEvent, MISPObject, PyMISP, MISPAttribute
from pymisp.exceptions import InvalidMISPObjectAttribute, InvalidMISPObject
import uuid
import conf.config_module as Config
import urllib3
urllib3.disable_warnings()

module_config = {
    "connector": "misp",
    "case_task": "case",
    "description": "Create or modify an event using misp-object present in the current case"
}


def create_object(misp, object, event_id):
    misp_object = MISPObject(object["name"], standalone=False)
    attr_uuid_list = list()
    for attr in object["attributes"]:
        loc_attr = misp_object.add_attribute(attr["object_relation"], value=attr["value"],
                                             to_ids=attr["ids_flag"], 
                                             comment=attr["comment"], 
                                             first_seen=attr["first_seen"], 
                                             last_seen=attr["last_seen"])
        attr_uuid_list.append({
            "attribute_id": attr["id"],
            "uuid": loc_attr.uuid
        })         # Need to save uuid of attr for later update
    res = misp.add_object(event_id, misp_object)
    return misp_object, attr_uuid_list, res

def manage_object_creation(misp, event, object, object_uuid_list):
    misp_object, attr_uuid_list, res = create_object(misp, object, event.id)
    if "errors" in res:
        return res, object_uuid_list
    object_uuid_list[object["id"]] = {      # Get uuid of object and attr to update later
        "attributes": attr_uuid_list,
        "uuid": misp_object.uuid
    }
    return "", object_uuid_list

def all_object_to_misp(misp, event, objects, object_uuid_list):
    for object in objects:
        try:
            loc_object = event.get_object_by_uuid(object["uuid"])
            attr_uuid_list = list()
            for attr in object["attributes"]:
                try:
                    attribute = loc_object.get_attribute_by_uuid(attr["uuid"])
                    flag_modif = False
                    if not attr["value"] == attribute.value:
                        attribute.value = attr["value"]
                        flag_modif = True
                    if not attr["comment"] == attribute.comment:
                        attribute.comment = attr["comment"]
                        flag_modif = True
                    if not attr["first_seen"] == attribute.first_seen:
                        attribute.first_seen = attr["first_seen"]
                        flag_modif = True
                    if not attr["last_seen"] == attribute.last_seen:
                        attribute.last_seen = attr["last_seen"]
                        flag_modif = True
                    if not attr["ids_flag"] == attribute.to_ids:
                        attribute.to_ids = attr["ids_flag"]
                        flag_modif = True

                    if flag_modif:
                        res = misp.update_attribute(attribute)
                        if "errors" in res:
                            return res, object_uuid_list
                except InvalidMISPObjectAttribute as e:
                    # Object exist but not this attribute
                    loc_attr = loc_object.add_attribute(attr["object_relation"], value=attr["value"])
                    attr_uuid_list.append({
                        "attribute_id": attr["id"],
                        "uuid": loc_attr.uuid
                    })
                    res = misp.update_object(loc_object)
                    if "errors" in res:
                        return res, object_uuid_list
            if attr_uuid_list:
                object_uuid_list[object["id"]] = {
                    "attributes": attr_uuid_list,
                    "uuid": loc_object.uuid
                }
        except InvalidMISPObject as e:
            # Object not found or not exist, Create a new one
            res, object_uuid_list = manage_object_creation(misp, event, object, object_uuid_list)
            if "errors" in res:
                return res, object_uuid_list
    return "", object_uuid_list


def handler(instance, case, user):
    """
    instance: name, url, description, uuid, connector_id, type, api_key, identifier

    case: id, uuid, title, description, creation_date, last_modif, status_id, status, completed, owner_org_id
          org_name, org_uuid, recurring_type, deadline, finish_date, tasks, clusters, connectors

    case["tasks"]: id, uuid, title, description, url, notes, creation_date, last_modif, case_id, status_id, status,
                   completed, deadline, finish_date, tags, clusters, connectors

    user: id, first_name, last_name, email, role_id, password_hash, api_key, org_id
    """
    try:
        misp = PyMISP(instance["url"], instance["api_key"], ssl=False, timeout=20)
    except:
        return {"message": "Error connecting to MISP"}, {}
    flag = False
    object_uuid_list = {}
    
    if "identifier" in instance and instance["identifier"]:
        event = misp.get_event(instance["identifier"], pythonify=True)
        if 'errors' in event:
            flag = True
        else:
            res, object_uuid_list = all_object_to_misp(misp, event, case["objects"], object_uuid_list)
            if "errors" in res:
                return res, object_uuid_list

    ## No identifier for this connector or the event doesn't exist anymore
    else: 
        flag = True

    ## Event doesn't exist
    if flag:
        event = MISPEvent()
        event.uuid = str(uuid.uuid4())
        event.info = f"Case: {case['title']}"  # Required
        event = misp.add_event(event, pythonify=True)

        for object in case["objects"]:
            res, object_uuid_list = manage_object_creation(misp, event, object, object_uuid_list)
            if "errors" in res:
                return res, object_uuid_list

    if "errors" in event:
        return event, object_uuid_list
    return event.get("uuid"), object_uuid_list

def introspection():
    return module_config
