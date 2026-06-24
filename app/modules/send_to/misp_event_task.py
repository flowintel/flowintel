from pymisp import MISPEvent, MISPObject, PyMISP
import uuid
from flask import current_app
import conf.config_module as Config
from .misp_object_event import bump_event_timestamp

module_config = {
    "connector": "misp",
    "case_task": "case",
    "description": "Create or modify an event using all tasks in the case. The event will include:\n\t- Each task's info as misp-object\n\t- An event report with notes from all tasks\n\t- file attachments (when MISP_EXPORT_FILES is enabled)"
}

def task_edit(task, attribute):
    if attribute.object_relation == 'title' and not attribute.value == task["title"]:
        attribute.value = task["title"]
    elif attribute.object_relation == 'description' and not attribute.value == task["description"]:
        attribute.value = task["description"]
    elif attribute.object_relation == 'deadline' and not attribute.value == task["deadline"]:
        attribute.value = task["deadline"]
    elif attribute.object_relation == 'finish-date' and not attribute.value == task["finish_date"]:
        attribute.value = task["finish_date"]
    elif attribute.object_relation == 'status' and not attribute.value == task["status"]:
        attribute.value = task["status"]
    elif attribute.object_relation == 'origin-url' and not attribute.value == Config.ORIGIN_URL:
        attribute.value = Config.ORIGIN_URL
    return attribute


def create_task(task, case_uuid):
    misp_object = MISPObject("flowintel-task", standalone=False)

    title = misp_object.add_attribute('title', value=task["title"])
    for tag in task["tags"]:
        title.add_tag({'name': tag["name"], 'colour': tag["color"]})
    misp_object.add_attribute('case-uuid', value=case_uuid)
    misp_object.add_attribute('creation-date', value=task["creation_date"])
    misp_object.add_attribute('deadline', value=task["deadline"])
    misp_object.add_attribute('description', value=task["description"])
    misp_object.add_attribute('finish-date', value=task["finish_date"])
    misp_object.add_attribute('status', value=task["status"])
    misp_object.add_attribute('origin-url', value=Config.ORIGIN_URL)
    misp_object.add_attribute('task-uuid', value=task["uuid"])
    return misp_object

def create_task_note(note):
    misp_object = MISPObject("flowintel-task-note", standalone=False)

    misp_object.add_attribute('note', value=note["note"])
    misp_object.add_attribute('task-uuid', value=note["task_uuid"])
    misp_object.add_attribute('note-uuid', value=note["uuid"])
    misp_object.add_attribute('origin-url', value=Config.ORIGIN_URL)
    return misp_object

def create_task_resource(resource):
    misp_object = MISPObject("flowintel-task-resource", standalone=False)

    misp_object.add_attribute('resource', value=resource["name"])
    misp_object.add_attribute('task-uuid', value=resource["task_uuid"])
    misp_object.add_attribute('resource-uuid', value=resource["uuid"])
    misp_object.add_attribute('origin-url', value=Config.ORIGIN_URL)
    return misp_object

def event_report_note_task(task):
    loc_notes = ""
    if task["notes"]:
        loc_notes += f"## (Task) {task['title']}\n\n"
        cp = 0
        for note in task["notes"]:
            cp += 1
            loc_notes += f"#### #{cp}\n{note['note']}\n ---\n\n"
    return loc_notes


def handler(instance, case, user, case_model=None, db_session=None, payload=None):
    """
    instance: name, url, description, uuid, connector_id, type, api_key, identifier

    case: id, uuid, title, description, creation_date, last_modif, status_id, status, completed, owner_org_id
          org_name, org_uuid, recurring_type, deadline, finish_date, tasks, clusters, connectors

    task: id, uuid, title, description, url, notes, creation_date, last_modif, case_id, status_id, status,
                   completed, deadline, finish_date, tags, clusters, connectors

    user: id, first_name, last_name, email, role_id, password_hash, api_key, org_id
    """
    try:
        misp = PyMISP(instance["url"], instance["api_key"], ssl=False, timeout=20)
    except Exception:
        return {"message": "Error connecting to MISP"}
    flag = False

    # If there's an identifier, attempt to fetch and update the event
    if "identifier" in instance and instance["identifier"]:
        event = misp.get_event(instance["identifier"], pythonify=True)
        if 'errors' in event:
            flag = True
        else:
            # Process each task in the case
            for task in case.get("tasks", []):
                misp_objects = event.get_objects_by_name("flowintel-task")
                current_object = None
                for i in range(0, len(misp_objects)):
                    for attribute in misp_objects[i].attributes:
                        if attribute.object_relation == 'task-uuid' and attribute.value == task.get("uuid"):
                            current_object = i
                            break
                    if current_object is not None:
                        break

                # Task exists in the event: update attributes/notes/resources
                if current_object is not None:
                    for attribute in misp_objects[current_object].attributes:
                        task_edit(task, attribute)

                    # Task's notes
                    misp_objects_note = event.get_objects_by_name("flowintel-task-note")
                    for note in task.get("notes", []):
                        current_note = None
                        for i in range(0, len(misp_objects_note)):
                            for attr in misp_objects_note[i].attributes:
                                if attr.object_relation == 'note-uuid' and attr.value == note.get("uuid"):
                                    current_note = i
                                    break
                            if current_note is not None:
                                break
                        # Note exists: update
                        if current_note is not None:
                            for attr in misp_objects_note[current_note].attributes:
                                if attr.object_relation == "note" and not attr.value == note.get("note"):
                                    attr.value = note.get("note")
                        # Note doesn't exist: create and reference
                        else:
                            misp_note_object = create_task_note(note)
                            misp_note_object.add_reference(misp_objects[current_object].uuid, relationship_type="note-for")
                            event.add_object(misp_note_object)

                    # Task's resources
                    misp_objects_resource = event.get_objects_by_name("flowintel-task-resource")
                    for resource in task.get("urls_tools", []):
                        current_resource = None
                        for i in range(0, len(misp_objects_resource)):
                            for attr in misp_objects_resource[i].attributes:
                                if attr.object_relation == 'resource-uuid' and attr.value == resource.get("uuid"):
                                    current_resource = i
                                    break
                            if current_resource is not None:
                                break
                        # Resource exists: update
                        if current_resource is not None:
                            for attr in misp_objects_resource[current_resource].attributes:
                                if attr.object_relation == "name" and not attr.value == resource.get("name"):
                                    attr.value = resource.get("name")
                        # Resource doesn't exist: create and reference
                        else:
                            misp_resource_object = create_task_resource(resource)
                            misp_resource_object.add_reference(misp_objects[current_object].uuid, relationship_type="resource-for")
                            event.add_object(misp_resource_object)

                # Task doesn't exist in the event: create object + notes + resources
                else:
                    loc_misp_task_object = create_task(task, case["uuid"])
                    event.add_object(loc_misp_task_object)

                    for note in task.get("notes", []):
                        misp_object = create_task_note(note)
                        misp_object.add_reference(loc_misp_task_object.uuid, relationship_type="note-for")
                        event.add_object(misp_object)

                    for resource in task.get("urls_tools", []):
                        misp_object = create_task_resource(resource)
                        misp_object.add_reference(loc_misp_task_object.uuid, relationship_type="resource-for")
                        event.add_object(misp_object)

            # Update aggregated tasks' notes report
            if event.EventReport:
                if len(event.EventReport) >= 2:
                    loc_event_report_case = event.EventReport[1]
                else:
                    loc_event_report_case = event.EventReport[0]

                loc_notes = ""
                for task in case.get("tasks", []):
                    loc_notes += event_report_note_task(task)

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

            
            event = bump_event_timestamp(event)
            event = misp.update_event(event, pythonify=True)

    # Case have no id for this connector or the event doesn't exist anymore
    else:
        flag = True

    # Event doesn't exist: create and add all tasks
    if flag:
        event = MISPEvent()
        event.uuid = str(uuid.uuid4())
        event.info = f"Case: {case['title']}"  # Required

        for task in case.get("tasks", []):
            loc_misp_task_object = create_task(task, case["uuid"])
            event.add_object(loc_misp_task_object)

            for note in task.get("notes", []):
                misp_object = create_task_note(note)
                misp_object.add_reference(loc_misp_task_object.uuid, relationship_type="note-for")
                event.add_object(misp_object)

            for resource in task.get("urls_tools", []):
                misp_object = create_task_resource(resource)
                misp_object.add_reference(loc_misp_task_object.uuid, relationship_type="resource-for")
                event.add_object(misp_object)

        event = misp.add_event(event, pythonify=True)

        # Tasks' notes event report (aggregated)
        loc_notes = ""
        for task in case.get("tasks", []):
            loc_notes += event_report_note_task(task)

        if loc_notes:
            event_report = {
                "uuid": str(uuid.uuid4()),
                "event_id": event.get("id"),
                "name": "Tasks notes",
                "content": loc_notes
            }
            misp.add_event_report(event.get("id"), event_report)

    if "errors" in event:
        return {"message": event.get("errors", "Error with MISP event")}

    local_tags = current_app.config.get("MISP_ADD_LOCAL_TAGS_ALL_EVENTS", "")
    if local_tags:
        if isinstance(local_tags, list):
            for tag in local_tags:
                misp.tag(event, tag, local=True)
        else:
            misp.tag(event, local_tags, local=True)

    return {"identifier": event.get("uuid")}

def introspection():
    return module_config
