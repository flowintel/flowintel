import json
from pymisp import MISPEvent, MISPObject, PyMISP
import uuid
from config import Config

module_config = {
    "connector": "misp",
    "case_task": "case"
}

def create_case(case):
    misp_object = MISPObject("flowintel-cm-case", standalone=False)
    title = misp_object.add_attribute('title', value=case["title"])
    for tag in case["tags"]:
        title.add_tag({'name': tag["name"], 'colour': tag["color"]})
    
    misp_object.add_attribute('case-owner-org-name', value=case["org_name"])
    misp_object.add_attribute('case-owner-org-uuid', value=case["org_uuid"])
    misp_object.add_attribute('case-uuid', value=case["uuid"])
    misp_object.add_attribute('creation-date', value=case["creation_date"])
    misp_object.add_attribute('deadline', value=case["deadline"])
    misp_object.add_attribute('description', value=case["description"])
    misp_object.add_attribute('finish-date', value=case["finish_date"])
    misp_object.add_attribute('recurring-type', value=case["recurring_type"])
    misp_object.add_attribute('status', value=case["status"])
    misp_object.add_attribute('origin-url', value=Config.ORIGIN_URL)
    return misp_object

def create_task(task, case_uuid):
    misp_object = MISPObject("flowintel-cm-task", standalone=False)

    title = misp_object.add_attribute('title', value=task["title"])
    for tag in task["tags"]:
        title.add_tag({'name': tag["name"], 'colour': tag["color"]})

    misp_object.add_attribute('creation-date', value=task["creation_date"])
    misp_object.add_attribute('deadline', value=task["deadline"])
    misp_object.add_attribute('description', value=task["description"])
    misp_object.add_attribute('finish-date', value=task["finish_date"])
    misp_object.add_attribute('notes', value=task["notes"])
    misp_object.add_attribute('status', value=task["status"])
    misp_object.add_attribute('origin-url', value=Config.ORIGIN_URL)
    misp_object.add_attribute('task-uuid', value=task["uuid"])
    misp_object.add_attribute('case-uuid', value=case_uuid)
    misp_object.add_attribute('url', value=task["url"])
    return misp_object


def handler(instance, case):
    """
    instance: name, url, description, uuid, connector_id, type, api_key, identifier

    case: id, uuid, title, description, creation_date, last_modif, status_id, status, completed, owner_org_id
          org_name, org_uuid, recurring_type, deadline, finish_date, tasks, clusters, connectors

    case["tasks"]: id, uuid, title, description, url, notes, creation_date, last_modif, case_id, status_id, status,
                   completed, deadline, finish_date, tags, clusters, connectors
    """
    try:
        misp = PyMISP(instance["url"], instance["api_key"], ssl=False)
    except:
        return {"message": "Error connecting to MISP"}
    flag = False
    if "identifier" in instance and instance["identifier"]:
        event = misp.get_event(instance["identifier"], pythonify=True)
        if 'errors' in event:
            flag = True

        else:
            misp_objects = event.get_objects_by_name("flowintel-cm-case")
            current_case_object = None
            for i in range(0, len(misp_objects)):
                for attribute in misp_objects[i].attributes:
                    if attribute.object_relation == 'case-uuid':
                        if attribute.value == case["uuid"]:
                            current_case_object = i
                            break
            ## Case exist in the event
            if not current_case_object == None:
                for attribute in misp_objects[current_case_object].attributes:
                    if attribute.object_relation == 'title' and not attribute.value == case["title"]:
                        attribute.value = case["title"]
                    elif attribute.object_relation == 'case-owner-org-name' and not attribute.value == case["org_name"]:
                        attribute.value = case["org_name"]
                    elif attribute.object_relation == 'case-owner-org-uuid' and not attribute.value == case["org_uuid"]:
                        attribute.value = case["org_uuid"]
                    elif attribute.object_relation == 'deadline' and not attribute.value == case["deadline"]:
                        attribute.value = case["deadline"]
                    elif attribute.object_relation == 'description' and not attribute.value == case["description"]:
                        attribute.value = case["description"]
                    elif attribute.object_relation == 'finish-date' and not attribute.value == case["finish_date"]:
                        attribute.value = case["finish_date"]
                    elif attribute.object_relation == 'origin-url' and not attribute.value == Config.ORIGIN_URL:
                        attribute.value = Config.ORIGIN_URL
                    elif attribute.object_relation == 'recurring-type' and not attribute.value == case["recurring_type"]:
                        attribute.value = case["recurring_type"]
                    elif attribute.object_relation == 'status' and not attribute.value == case["status"]:
                        attribute.value = case["status"]

                misp_objects = event.get_objects_by_name("flowintel-cm-task")
                for task in case["tasks"]:
                    current_object = None
                    for i in range(0, len(misp_objects)):
                        for attribute in misp_objects[i].attributes:
                            if attribute.object_relation == 'task-uuid':
                                if attribute.value == task["uuid"]:
                                    current_object = i
                                    break
                    ## Task exist in the event
                    if not current_object == None:
                        for attribute in misp_objects[current_object].attributes:
                            if attribute.object_relation == 'title' and not attribute.value == task["title"]:
                                attribute.value = task["title"]
                            elif attribute.object_relation == 'deadline' and not attribute.value == task["deadline"]:
                                attribute.value = task["deadline"]
                            elif attribute.object_relation == 'description' and not attribute.value == task["description"]:
                                attribute.value = task["description"]
                            elif attribute.object_relation == 'finish-date' and not attribute.value == task["finish_date"]:
                                attribute.value = task["finish_date"]
                            elif attribute.object_relation == 'notes' and not attribute.value == task["notes"]:
                                attribute.value = task["notes"]
                            elif attribute.object_relation == 'status' and not attribute.value == task["status"]:
                                attribute.value = task["status"]
                            elif attribute.object_relation == 'origin-url' and not attribute.value == Config.ORIGIN_URL:
                                attribute.value = Config.ORIGIN_URL
                            elif attribute.object_relation == 'url' and not attribute.value == task["url"]:
                                attribute.value = task["url"]
                    ## Task doesn't exist in the event
                    else:
                        misp_object = create_task(task, case["uuid"])
                        event.add_object(misp_object)
                event = misp.update_event(event, pythonify=True)
            ## Case doesn't exist in the event
            else:
                misp_object = create_case(case)
                event.add_object(misp_object)

                for task in case["tasks"]:
                    misp_object = create_task(task, case["uuid"])
                    event.add_object(misp_object)

                event = misp.update_event(event, pythonify=True)

    ## Case have no id for this connector or the event doesn't exist anymore  
    else: 
        flag = True

    ## Event doesn't exist or doesn't contains the case
    if flag:
        event = MISPEvent()
        event.uuid = str(uuid.uuid4())
        event.info = f"Case: {case['title']}"  # Required

        misp_object = create_case(case)

        event.add_object(misp_object)

        for task in case["tasks"]:
            misp_object = create_task(task, case["uuid"])
            event.add_object(misp_object)

        event = misp.add_event(event, pythonify=True)        
    
    return event.get("id")

def introspection():
    return module_config
