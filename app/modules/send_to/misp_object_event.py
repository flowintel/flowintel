from pymisp import MISPEvent, MISPObject, PyMISP, MISPAttribute
from pymisp.exceptions import InvalidMISPObjectAttribute, InvalidMISPObject, NewAttributeError
import uuid
import conf.config_module as Config
import logging
import urllib3
urllib3.disable_warnings()

logger = logging.getLogger(__name__)

module_config = {
    "connector": "misp",
    "case_task": "case",
    "description": "Create or modify an event using misp-object present in the current case"
}


def create_object(misp, object, event_id):
    misp_object = MISPObject(object["name"], standalone=False)
    attr_uuid_list = list()
    for attr in object["attributes"]:
        try:
            kwargs = {
                "to_ids": attr["ids_flag"],
                "comment": attr["comment"],
            }
            if attr.get("first_seen"):
                kwargs["first_seen"] = attr["first_seen"]
            if attr.get("last_seen"):
                kwargs["last_seen"] = attr["last_seen"]
            loc_attr = misp_object.add_attribute(
                attr["object_relation"], value=attr["value"], **kwargs
            )
        except NewAttributeError as e:
            # Value doesn't match the type expected by the object template.
            # Skip the attribute rather than aborting the entire export.
            logger.warning(
                "Skipped attribute %s (relation=%s, value=%r): %s",
                attr.get("id"), attr["object_relation"], attr["value"], e,
            )
            continue
        attr_uuid_list.append({
            "attribute_id": attr["id"],
            "uuid": loc_attr.uuid
        })         # Need to save uuid of attr for later update
    if not misp_object.attributes:
        # Every attribute was skipped — don't push an empty object to MISP.
        return misp_object, attr_uuid_list, {
            "errors": f"Object '{object['name']}' has no valid attributes after filtering"
        }
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
    details = []
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
                    if attribute.get("comment"):
                        if not attr["comment"] == attribute.comment:
                            attribute.comment = attr["comment"]
                            flag_modif = True
                    else:
                        if attr.get("comment"):
                            attribute.comment = attr["comment"]
                            flag_modif = True
                    if attribute.get("first_seen"):
                        if not attr["first_seen"] == attribute.first_seen:
                            attribute.first_seen = attr["first_seen"]
                            flag_modif = True
                    else:
                        if attr.get("first_seen"):
                            attribute.first_seen = attr["first_seen"]
                            flag_modif = True
                    if attribute.get("last_seen"):
                        if not attr["last_seen"] == attribute.last_seen:
                            attribute.last_seen = attr["last_seen"]
                            flag_modif = True
                    else:
                        if attr.get("last_seen"):
                            attribute.last_seen = attr["last_seen"]
                            flag_modif = True
                    if not attr["ids_flag"] == attribute.to_ids:
                        attribute.to_ids = attr["ids_flag"]
                        flag_modif = True

                    if flag_modif:
                        res = misp.update_attribute(attribute)
                        if "errors" in res:
                            details.append({"name": object.get("name", str(object.get("id", ""))), "status": "error", "error": str(res.get("errors", "update failed"))})
                            continue
                except (InvalidMISPObjectAttribute, NewAttributeError):
                    # Object exist but not this attribute, or value type mismatch
                    try:
                        loc_attr = loc_object.add_attribute(attr["object_relation"], value=attr["value"])
                    except NewAttributeError:
                        continue
                    attr_uuid_list.append({
                        "attribute_id": attr["id"],
                        "uuid": loc_attr.uuid
                    })
                    res = misp.update_object(loc_object)
                    if "errors" in res:
                        details.append({"name": object.get("name", str(object.get("id", ""))), "status": "error", "error": str(res.get("errors", "update failed"))})
                        continue
            if attr_uuid_list:
                object_uuid_list[object["id"]] = {
                    "attributes": attr_uuid_list,
                    "uuid": loc_object.uuid
                }
            details.append({"name": object.get("name", str(object.get("id", ""))), "status": "success", "error": None})
        except InvalidMISPObject:
            # Object not found or not exist, Create a new one
            res, object_uuid_list = manage_object_creation(misp, event, object, object_uuid_list)
            if "errors" in res:
                details.append({"name": object.get("name", str(object.get("id", ""))), "status": "error", "error": str(res.get("errors", "creation failed"))})
            else:
                details.append({"name": object.get("name", str(object.get("id", ""))), "status": "success", "error": None})
    return details, object_uuid_list


def handler(instance, case, user, case_model=None, db_session=None, payload=None):
    """
    instance: name, url, description, uuid, connector_id, type, api_key, identifier

    case: id, uuid, title, description, creation_date, last_modif, status_id, status, completed, owner_org_id
          org_name, org_uuid, recurring_type, deadline, finish_date, tasks, clusters, connectors

    case["tasks"]: id, uuid, title, description, url, notes, creation_date, last_modif, case_id, status_id, status,
                   completed, deadline, finish_date, tags, clusters, connectors

    user: id, first_name, last_name, email, role_id, password_hash, api_key, org_id

    payload: optional dict; if payload["selected_objects"] is a list of local object IDs, only those are synced
    """
    try:
        misp = PyMISP(instance["url"], instance["api_key"], ssl=False, timeout=20)
    except Exception:
        return {"message": "Error connecting to MISP"}
    flag = False
    object_uuid_list = {}

    # Optional filter: only send objects whose id is in selected_objects
    objects = case["objects"]
    if payload and isinstance(payload.get("selected_objects"), list):
        selected_ids = set(str(i) for i in payload["selected_objects"])
        objects = [o for o in objects if str(o.get("object_id", o.get("id", ""))) in selected_ids]

    details = []
    if "identifier" in instance and instance["identifier"]:
        event = misp.get_event(instance["identifier"], pythonify=True)
        if 'errors' in event:
            flag = True
        else:
            details, object_uuid_list = all_object_to_misp(misp, event, objects, object_uuid_list)

    ## No identifier for this connector or the event doesn't exist anymore
    else: 
        flag = True

    ## Event doesn't exist
    if flag:
        event = MISPEvent()
        event.uuid = str(uuid.uuid4())
        event.info = f"Case: {case['title']}"  # Required
        event = misp.add_event(event, pythonify=True)

        for object in objects:
            res, object_uuid_list = manage_object_creation(misp, event, object, object_uuid_list)
            if "errors" in res:
                details.append({"name": object.get("name", ""), "status": "error", "error": str(res.get("errors", "creation failed"))})
            else:
                details.append({"name": object.get("name", ""), "status": "success", "error": None})

    if "errors" in event:
        return {"message": event.get("errors", "Error with MISP event")}

    # Let the module handle its own DB storage
    if case_model and object_uuid_list:
        case_model.result_misp_object_module(object_uuid_list, instance["id"], case["id"])

    synced = sum(1 for d in details if d["status"] == "success")
    failed = sum(1 for d in details if d["status"] == "error")
    return {
        "identifier": event.get("uuid"),
        "synced_count": synced,
        "failed_count": failed,
        "details": details
    }

def introspection():
    return module_config
