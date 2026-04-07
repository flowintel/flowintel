import json
import logging
import os
from pathlib import Path
from pymisp import MISPAttribute, MISPEvent, MISPGalaxy, MISPGalaxyCluster, MISPObject, MISPObjectReference, PyMISP
import uuid
from flask import current_app
import conf.config_module as Config
from .misp_object_event import all_object_to_misp, manage_object_creation
from app.case.CaseCore import FILE_FOLDER

logger = logging.getLogger(__name__)


module_config = {
    "connector": "misp",
    "case_task": "case",
    "description": "Create or modify an event using the current case. The event will include:\n\t- case's info as misp-object\n\t- tasks' info as misp-object\n\t- tasks' subtasks as text attributes\n\t- tasks' external references as link attributes\n\t- case and tasks notes as event report\n\t- file attachments (when MISP_EXPORT_FILES is enabled)"
}

def common_edit(case_task, attribute):
    if attribute.object_relation == 'title' and not attribute.value == case_task["title"]:
        attribute.value = case_task["title"]
    elif attribute.object_relation == 'description' and not attribute.value == case_task["description"]:
        attribute.value = case_task["description"]
    elif attribute.object_relation == 'deadline' and not attribute.value == case_task["deadline"]:
        attribute.value = case_task["deadline"]
    elif attribute.object_relation == 'finish-date' and not attribute.value == case_task["finish_date"]:
        attribute.value = case_task["finish_date"]
    elif attribute.object_relation == 'status' and not attribute.value == case_task["status"]:
        attribute.value = case_task["status"]
    elif attribute.object_relation == 'origin-url' and not attribute.value == Config.ORIGIN_URL:
        attribute.value = Config.ORIGIN_URL
    return attribute

def common_create(case_task, case_uuid, misp_object):
    title = misp_object.add_attribute('title', value=case_task["title"])
    for tag in case_task["tags"]:
        title.add_tag({'name': tag["name"], 'colour': tag["color"]})
    misp_object.add_attribute('case-uuid', value=case_uuid)
    misp_object.add_attribute('creation-date', value=case_task["creation_date"])
    misp_object.add_attribute('deadline', value=case_task["deadline"])
    misp_object.add_attribute('description', value=case_task["description"])
    misp_object.add_attribute('finish-date', value=case_task["finish_date"])
    misp_object.add_attribute('status', value=case_task["status"])
    misp_object.add_attribute('origin-url', value=Config.ORIGIN_URL)
    misp_object.add_attribute('flowintel-url', value=Config.ORIGIN_URL)
    return misp_object

def create_case(case):
    misp_object = MISPObject("flowintel-case", standalone=False)
    misp_object = common_create(case, case["uuid"], misp_object)
    
    misp_object.add_attribute('case-owner-org-name', value=case["org_name"])
    misp_object.add_attribute('case-owner-org-uuid', value=case["org_uuid"])
    misp_object.add_attribute('notes', value=case["notes"])
    misp_object.add_attribute('recurring-type', value=case["recurring_type"])
    return misp_object

def create_task(task, case_uuid):
    misp_object = MISPObject("flowintel-task", standalone=False)
    misp_object = common_create(task, case_uuid, misp_object)

    misp_object.add_attribute('task-uuid', value=task["uuid"])
    return misp_object

def create_task_note(note):
    misp_object = MISPObject("flowintel-task-note", standalone=False)

    misp_object.add_attribute('note', value=note["note"])
    misp_object.add_attribute('task-uuid', value=note["task_uuid"])
    misp_object.add_attribute('note-uuid', value=note["uuid"])
    misp_object.add_attribute('origin-url', value=Config.ORIGIN_URL)
    misp_object.add_attribute('flowintel-url', value=Config.ORIGIN_URL)
    return misp_object

def create_task_resource(resource):
    misp_object = MISPObject("flowintel-task-resource", standalone=False)

    misp_object.add_attribute('resource', value=resource["name"])
    misp_object.add_attribute('task-uuid', value=resource["task_uuid"])
    misp_object.add_attribute('resource-uuid', value=resource["uuid"])
    misp_object.add_attribute('origin-url', value=Config.ORIGIN_URL)
    misp_object.add_attribute('flowintel-url', value=Config.ORIGIN_URL)
    return misp_object

def event_report_note(case):
    loc_notes = ""
    if case["notes"]:
        loc_notes += f"# (Case) {case['title']}\n ---\n\n{case['notes']}\n ---\n\n"
    return loc_notes

def event_report_note_task(case):
    loc_notes = ""
    for task in case["tasks"]:
        if task["notes"]:
            loc_notes += f"## (Task) {task['title']}\n\n"
            cp = 0
            for note in task["notes"]:
                cp += 1
                loc_notes += f"#### #{cp}\n{note['note']}\n ---\n\n"
    return loc_notes

def create_galaxy_cluster(misp: PyMISP, event, clusters):
    for cluster in clusters:
        res = misp.get_galaxy(cluster["galaxy"]["uuid"])
        if "errors" in res:
            # Galaxy doesn't exist on this MISP instance
            galax_dict = {
                "description": cluster["galaxy"]["description"],
                "icon": cluster["icon"],
                "name": cluster["galaxy"]["name"],
                "namespace": "misp",
                "type": cluster["galaxy"]["type"],
                "uuid": cluster["galaxy"]["uuid"],
                "version": cluster["galaxy"]["version"]
            }
            m = MISPGalaxy()
            m.from_dict(**galax_dict)

            res_gal = misp._prepare_request(request_type='POST', url='galaxies/add', data=galax_dict)
            if "errors" in res_gal:
                # Galaxy creation failed
                return event
            else:
                clust_dict = {
                    "description": cluster["description"],
                    "uuid": cluster["uuid"],
                    "value": cluster["name"],
                    "type": cluster["galaxy"]["type"],
                    "meta": cluster["meta"],
                    "version": cluster["version"],
                    "collection_uuid":"",
                    "Galaxy": {
                        "uuid": cluster["galaxy"]["uuid"]
                    },
                    "published": True
                }

                cluster = MISPGalaxyCluster()
                cluster.from_dict(**clust_dict)
                cluster.parse_meta_as_elements()

                m.add_galaxy_cluster(**cluster.to_dict())

                loc_cluster = [{"GalaxyCluster": json.loads(cluster.to_json())}]
                misp._prepare_request(request_type='POST', url='galaxies/import', data=loc_cluster)
                event.add_galaxy(m)
        else:
            res_cluster = misp.get_galaxy_cluster(cluster["uuid"])
            if "errors" in res_cluster:
                # Cluster doesn't exist on this MISP instance
                galax_dict = {
                    "description": cluster["galaxy"]["description"],
                    "icon": cluster["icon"],
                    "name": cluster["galaxy"]["name"],
                    "namespace": "misp",
                    "type": cluster["galaxy"]["type"],
                    "uuid": cluster["galaxy"]["uuid"],
                    "version": cluster["galaxy"]["version"]
                }
                m = MISPGalaxy()
                m.from_dict(**galax_dict)
                
                clust_dict = {
                    "description": cluster["description"],
                    "uuid": cluster["uuid"],
                    "value": cluster["name"],
                    "type": cluster["galaxy"]["type"],
                    "meta": cluster["meta"],
                    "version": cluster["version"],
                    "collection_uuid":"",
                    "Galaxy": {
                        "uuid": cluster["galaxy"]["uuid"]
                    },
                    "published": True
                }

                cluster = MISPGalaxyCluster()
                cluster.from_dict(**clust_dict)
                cluster.parse_meta_as_elements()

                m.add_galaxy_cluster(**cluster.to_dict())
                loc_cluster = [{"GalaxyCluster": json.loads(cluster.to_json())}]
                misp._prepare_request(request_type='POST', url='galaxies/import', data=loc_cluster)
                event.add_galaxy(m)
                
            else:
                # Cluster and Galaxy exist on this MISP instance
                event.add_tag(cluster["tag"])

    return event

def _collect_files(case):
    """Return a list of (file_dict, origin_type, origin_uuid) tuples."""
    files = []
    for f in case.get("files", []):
        files.append((f, "case", case["uuid"]))
    for task in case.get("tasks", []):
        for f in task.get("files", []):
            files.append((f, "task", task["uuid"]))
    return files


def _find_misp_object(event, origin_type, origin_uuid):
    """Find the flowintel-case or flowintel-task MISPObject"""
    if origin_type == "case":
        obj_name, relation = "flowintel-case", "case-uuid"
    else:
        obj_name, relation = "flowintel-task", "task-uuid"

    for obj in event.get_objects_by_name(obj_name):
        for attr in obj.attributes:
            if attr.object_relation == relation and attr.value == origin_uuid:
                return obj
    return None


def _existing_attr_values(event, attr_types, prefix=None):
    """Return a set of attribute values already on the MISP event."""
    values = set()
    if not isinstance(attr_types, tuple):
        attr_types = (attr_types,)
    for attr in event.Attribute:
        if attr.type in attr_types:
            if attr.value and (prefix is None or attr.value.startswith(prefix)):
                values.add(attr.value)
    return values


def add_case_task_references(misp, event, case):
    """Add 'includes' references from the flowintel-case object to each
    flowintel-task object.  Existing references are skipped."""
    case_obj = _find_misp_object(event, "case", case["uuid"])
    if not case_obj or not getattr(case_obj, "id", None):
        logger.debug("MISP export: case object not found, skipping task references")
        return

    # Collect UUIDs that already have a reference from this case object
    existing_refs = set()
    for ref in getattr(case_obj, "ObjectReference", []):
        ref_uuid = getattr(ref, "referenced_uuid", None)
        ref_type = getattr(ref, "relationship_type", None)
        if ref_uuid and ref_type == "includes":
            existing_refs.add(ref_uuid)

    task_objects = event.get_objects_by_name("flowintel-task")
    for task in case.get("tasks", []):
        for obj in task_objects:
            for attr in obj.attributes:
                if attr.object_relation == "task-uuid" and attr.value == task["uuid"]:
                    if obj.uuid in existing_refs:
                        break
                    if not getattr(obj, "id", None):
                        break
                    try:
                        ref = MISPObjectReference()
                        ref.object_uuid = case_obj.uuid
                        ref.object_id = case_obj.id
                        ref.referenced_uuid = obj.uuid
                        ref.relationship_type = "includes"
                        misp.add_object_reference(ref)
                        logger.info("MISP export: added 'includes' reference from case to task '%s'",
                                    task.get("title", task["uuid"]))
                    except Exception as e:
                        logger.warning("MISP export: failed to add case→task reference for '%s': %s",
                                       task.get("title", task["uuid"]), e)
                    break


def upload_files_to_event(misp, event, case):
    """Upload case & task files as MISP 'attachment' attributes."""
    if not current_app.config.get("MISP_EXPORT_FILES", False):
        return

    all_files = _collect_files(case)
    if not all_files:
        return

    existing = _existing_attr_values(event, ("attachment", "malware-sample"))

    for file_meta, origin_type, origin_uuid in all_files:
        if file_meta["name"] in existing:
            logger.debug("MISP export: file '%s' already attached, skipping", file_meta["name"])
            continue

        file_path = os.path.join(FILE_FOLDER, file_meta["uuid"])
        if not os.path.isfile(file_path):
            logger.warning("MISP export: file not found on disk: %s (%s)", file_meta["name"], file_path)
            continue

        try:
            attr = MISPAttribute()
            attr.type = "attachment"
            attr.value = file_meta["name"]
            attr.comment = "Uploaded from Flowintel"
            attr.data = Path(file_path)
            attr.distribution = 5

            result = misp.add_attribute(event, attr, pythonify=True)
            logger.info("MISP export: attached file '%s' to event %s", file_meta["name"], event.get("uuid", "?"))

            # Create a reference from the case/task object to the file attribute
            result_uuid = getattr(result, "uuid", None)
            if result_uuid:
                misp_obj = _find_misp_object(event, origin_type, origin_uuid)
                if misp_obj and getattr(misp_obj, "id", None):
                    try:
                        ref = MISPObjectReference()
                        ref.object_uuid = misp_obj.uuid
                        ref.object_id = misp_obj.id
                        ref.referenced_uuid = result_uuid
                        ref.relationship_type = "has-attachment"
                        misp.add_object_reference(ref)
                        logger.info("MISP export: added reference from %s object to file '%s'",
                                    origin_type, file_meta["name"])
                    except Exception as e:
                        logger.warning("MISP export: failed to add reference for file '%s': %s",
                                       file_meta["name"], e)
        except Exception as e:
            logger.error("MISP export: failed to attach file '%s': %s", file_meta["name"], e)


def _add_attribute_with_reference(misp, event, task_obj, attr_type, value, comment, relationship):
    """Create a MISP attribute on the event and link it to *task_obj*."""
    attr = MISPAttribute()
    attr.type = attr_type
    attr.value = value
    attr.comment = comment
    attr.distribution = 5  # Inherit event distribution

    result = misp.add_attribute(event, attr, pythonify=True)
    result_uuid = getattr(result, "uuid", None)
    if result_uuid:
        ref = MISPObjectReference()
        ref.object_uuid = task_obj.uuid
        ref.object_id = task_obj.id
        ref.referenced_uuid = result_uuid
        ref.relationship_type = relationship
        misp.add_object_reference(ref)
    return result


def add_subtasks_to_event(misp, event, case):
    """Add task subtasks as MISP 'text' attributes with 'includes' references."""
    existing = _existing_attr_values(event, "text", prefix="Subtask: ")

    for task in case.get("tasks", []):
        task_obj = _find_misp_object(event, "task", task["uuid"])
        if not task_obj or not getattr(task_obj, "id", None):
            continue

        for subtask in task.get("subtasks", []):
            description = subtask.get("description", "")
            if not description:
                continue
            value = f"Subtask: {description}"
            if value in existing:
                continue

            try:
                _add_attribute_with_reference(
                    misp, event, task_obj,
                    attr_type="text", value=value,
                    comment=f"Subtask of task '{task.get('title', '')}'",
                    relationship="includes",
                )
                logger.info("MISP export: added subtask '%s'", value)
            except Exception as e:
                logger.warning("MISP export: failed to add subtask '%s': %s", value, e)


def add_external_references_to_event(misp, event, case):
    """Add task external references as MISP 'link' attributes with 'references' relations."""
    existing = _existing_attr_values(event, "link")

    for task in case.get("tasks", []):
        task_obj = _find_misp_object(event, "task", task["uuid"])
        if not task_obj or not getattr(task_obj, "id", None):
            continue

        for ext_ref in task.get("external_references", []):
            url = ext_ref.get("url", "")
            if not url or url in existing:
                continue

            try:
                _add_attribute_with_reference(
                    misp, event, task_obj,
                    attr_type="link", value=url,
                    comment=f"External reference of task '{task.get('title', '')}'",
                    relationship="references",
                )
                logger.info("MISP export: added external reference '%s'", url)
            except Exception as e:
                logger.warning("MISP export: failed to add external reference '%s': %s", url, e)


def handler(instance, case, user, case_model=None, db_session=None):
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
    except Exception:
        return {"message": "Error connecting to MISP"}
    flag = False
    object_uuid_list = {}
    if "identifier" in instance and instance["identifier"]:
        event = misp.get_event(instance["identifier"], pythonify=True)
        if 'errors' in event:
            flag = True
        else:
            misp_objects = event.get_objects_by_name("flowintel-case")
            current_case_object = None
            for i in range(0, len(misp_objects)):
                for attribute in misp_objects[i].attributes:
                    if attribute.object_relation == 'case-uuid' and attribute.value == case["uuid"]:
                        current_case_object = i
                        break
            ## Case exist in the event
            if not current_case_object == None:
                event = create_galaxy_cluster(misp, event, case["clusters"])
                
                for attribute in misp_objects[current_case_object].attributes:
                    attribute = common_edit(case, attribute)
                    if attribute.object_relation == 'case-owner-org-name' and not attribute.value == case["org_name"]:
                        attribute.value = case["org_name"]
                    elif attribute.object_relation == 'case-owner-org-uuid' and not attribute.value == case["org_uuid"]:
                        attribute.value = case["org_uuid"]
                    elif attribute.object_relation == 'recurring-type' and not attribute.value == case["recurring_type"]:
                        attribute.value = case["recurring_type"]
                    elif attribute.object_relation == 'notes' and not attribute.value == case["notes"]:
                        attribute.value = case["notes"]
                    

                misp_objects = event.get_objects_by_name("flowintel-task")
                for task in case["tasks"]:
                    current_object = None
                    for i in range(0, len(misp_objects)):
                        for attribute in misp_objects[i].attributes:
                            if attribute.object_relation == 'task-uuid' and attribute.value == task["uuid"]:
                                current_object = i
                                break
                    ## Task exist in the event
                    if not current_object == None:
                        for attribute in misp_objects[current_object].attributes:
                            attribute = common_edit(task, attribute)

                        ## Task's notes
                        misp_objects_note = event.get_objects_by_name("flowintel-task-note")
                        for note in task["notes"]:
                            current_note = None
                            for i in range(0, len(misp_objects_note)):
                                for attr in misp_objects_note[i].attributes:
                                    if attr.object_relation == 'note-uuid' and attr.value == note["uuid"]:
                                        current_note = i
                                        break
                            ## Note exist in the event
                            if not current_note == None:
                                for attr in misp_objects_note[current_note].attributes:
                                    if attr.object_relation == "note" and not attribute.value == note["note"]:
                                        attr.value = note["note"]
                            ## Note doesn't exist in the event
                            else:
                                misp_note_object = create_task_note(note)
                                misp_note_object.add_reference(misp_objects[current_object].uuid, relationship_type="note-for")
                                event.add_object(misp_note_object)

                        ## Task's resources
                        misp_objects_resource = event.get_objects_by_name("flowintel-task-resource")
                        for resource in task["urls_tools"]:
                            current_resource = None
                            for i in range(0, len(misp_objects_resource)):
                                for attr in misp_objects_resource[i].attributes:
                                    if attr.object_relation == 'resource-uuid' and attr.value == resource["uuid"]:
                                        current_resource = i
                                        break
                            ## Resource exist in the event
                            if not current_resource == None:
                                for attr in misp_objects_resource[current_resource].attributes:
                                    if attr.object_relation == "name" and not attribute.value == resource["name"]:
                                        attr.value = resource["name"]
                            ## Resource doesn't exist in the event
                            else:
                                misp_resource_object = create_task_resource(resource)
                                misp_resource_object.add_reference(misp_objects[current_object].uuid, relationship_type="resource-for")
                                event.add_object(misp_resource_object)

                    ## Task doesn't exist in the event
                    else:
                        loc_misp_task_object = create_task(task, case["uuid"])
                        event.add_object(loc_misp_task_object)

                        ## Task's notes
                        for note in task["notes"]:
                            misp_object = create_task_note(note)
                            misp_object.add_reference(loc_misp_task_object.uuid, relationship_type="note-for")
                            event.add_object(misp_object)

                        ## Task's resources
                        for resource in task["urls_tools"]:
                            misp_object = create_task_resource(resource)
                            misp_object.add_reference(loc_misp_task_object.uuid, relationship_type="resource-for")
                            event.add_object(misp_object)

                if event.EventReport:
                    ## Case's notes
                    loc_notes = event_report_note(case)
                    loc_event_report_case = event.EventReport[0]

                    if loc_event_report_case:
                        loc_event_report_case["content"] = loc_notes
                        misp.update_event_report(loc_event_report_case, event.get("id"))
                    else:
                        if loc_notes:
                            event_report = {
                                "uuid": str(uuid.uuid4()),
                                "event_id": event.get("id"),
                                "name": "Case's notes",
                                "content": loc_notes
                            }   
                            misp.add_event_report(event.get("id"), event_report)

                    ## Tasks' notes
                    if len(event.EventReport) >= 2:
                        loc_notes = event_report_note_task(case)
                        loc_event_report_case = event.EventReport[1]

                        if loc_event_report_case:
                            loc_event_report_case["content"] = loc_notes
                            misp.update_event_report(loc_event_report_case, event.get("id"))
                        else:
                            if loc_notes:
                                event_report = {
                                    "uuid": str(uuid.uuid4()),
                                    "event_id": event.get("id"),
                                    "name": "Tasks' notes",
                                    "content": loc_notes
                                }   
                                misp.add_event_report(event.get("id"), event_report)
                
                event = misp.update_event(event, pythonify=True)
                if "errors" in event:
                    return {"message": event.get("errors", "Error updating event")}

                add_case_task_references(misp, event, case)

            ## Case doesn't exist in the event
            else:
                misp_object = create_case(case)
                event.add_object(misp_object)

                for tag in case["tags"]:
                    event.add_tag({'name': tag["name"], 'colour': tag["color"]})

                event = create_galaxy_cluster(misp, event, case["clusters"])

                for task in case["tasks"]:
                    loc_misp_task_object = create_task(task, case["uuid"])
                    event.add_object(loc_misp_task_object)

                    for note in task["notes"]:
                        misp_object = create_task_note(note)
                        misp_object.add_reference(loc_misp_task_object.uuid, relationship_type="note-for")
                        event.add_object(misp_object)

                    ## Task's resources
                    for resource in task["urls_tools"]:
                        misp_object = create_task_resource(resource)
                        misp_object.add_reference(loc_misp_task_object.uuid, relationship_type="resource-for")
                        event.add_object(misp_object)

                event = misp.update_event(event, pythonify=True)
                if "errors" in event:
                    return {"message": event.get("errors", "Error updating event")}

                add_case_task_references(misp, event, case)

            upload_files_to_event(misp, event, case)

            add_subtasks_to_event(misp, event, case)
            add_external_references_to_event(misp, event, case)

            res, object_uuid_list = all_object_to_misp(misp, event, case["objects"], object_uuid_list)
            if "errors" in res:
                return {"message": res.get("errors", "Error syncing objects")}

    ## Case have no id for this connector or the event doesn't exist anymore  
    else: 
        flag = True

    ## Event doesn't exist
    if flag:
        event = MISPEvent()
        event.uuid = str(uuid.uuid4())
        event.info = f"Case: {case['title']}"  # Required
        event.threat_level_id = current_app.config.get("MISP_EVENT_THREAT_LEVEL", 4)
        event.analysis = current_app.config.get("MISP_EVENT_ANALYSIS", 0)

        misp_object = create_case(case)
        event.add_object(misp_object)

        for tag in case["tags"]:
            event.add_tag({'name': tag["name"], 'colour': tag["color"]})

        event = create_galaxy_cluster(misp, event, case["clusters"])

        # Task
        loc_misp_task_object = None
        for task in case["tasks"]:
            loc_misp_task_object = create_task(task, case["uuid"])
            event.add_object(loc_misp_task_object)

            ## Task's notes
            for note in task["notes"]:
                misp_object = create_task_note(note)
                misp_object.add_reference(loc_misp_task_object.uuid, relationship_type="note-for")
                event.add_object(misp_object)

            ## Task's resources
            for resource in task["urls_tools"]:
                misp_object = create_task_resource(resource)
                misp_object.add_reference(loc_misp_task_object.uuid, relationship_type="resource-for")
                event.add_object(misp_object)

        event = misp.add_event(event, pythonify=True)

        add_case_task_references(misp, event, case)

        ## Get all notes from task to create an event report
        ## Case's notes event report
        loc_notes = event_report_note(case)
        if loc_notes:
            event_report = {
                "uuid": str(uuid.uuid4()),
                "event_id": event.get("id"),
                "name": "Case notes",
                "content": loc_notes
            }   
            misp.add_event_report(event.get("id"), event_report)

        ## Tasks' notes event report
        loc_notes = event_report_note_task(case)

        if loc_notes:
            event_report = {
                "uuid": str(uuid.uuid4()),
                "event_id": event.get("id"),
                "name": "Tasks notes",
                "content": loc_notes
            }   
            misp.add_event_report(event.get("id"), event_report)

        upload_files_to_event(misp, event, case)

        add_subtasks_to_event(misp, event, case)
        add_external_references_to_event(misp, event, case)

        for object in case["objects"]:
            res, object_uuid_list = manage_object_creation(misp, event, object, object_uuid_list)
            if "errors" in res:
                return {"message": res.get("errors", "Error creating object")}
    
    if "errors" in event:
        return {"message": event.get("errors", "Error with MISP event")}

    local_tags = current_app.config.get("MISP_ADD_LOCAL_TAGS_ALL_EVENTS", "")
    if local_tags:
        if isinstance(local_tags, list):
            for tag in local_tags:
                misp.tag(event, tag, local=True)
        else:
            misp.tag(event, local_tags, local=True)

    # Let the module handle its own DB storage
    if case_model and object_uuid_list:
        case_model.result_misp_object_module(object_uuid_list, instance["id"], case["id"])

    return {"identifier": event.get("uuid")}

def introspection():
    return module_config
