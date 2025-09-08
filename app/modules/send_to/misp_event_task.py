from pymisp import MISPEvent, MISPObject, PyMISP
import uuid
import conf.config_module as Config

module_config = {
    "connector": "misp",
    "case_task": "task"
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


def handler(instance, case, task, user):
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
    except:
        return {"message": "Error connecting to MISP"}
    flag = False
    if "identifier" in instance and instance["identifier"]:
        event = misp.get_event(instance["identifier"], pythonify=True)
        if 'errors' in event:
            flag = True
        else:                    
            misp_objects = event.get_objects_by_name("flowintel-task")
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
                    attribute = task_edit(task, attribute)
                    

                ## Task's notes
                misp_objects_note = event.get_objects_by_name("flowintel-task-note")
                for note in task["notes"]:
                    current_note = None
                    for i in range(0, len(misp_objects_note)):
                        for attr in misp_objects_note[i].attributes:
                            if attr.object_relation == 'note-uuid':
                                if attr.value == note["uuid"]:
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
                            if attr.object_relation == 'resource-uuid':
                                if attr.value == resource["uuid"]:
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
                ## Task' notes
                if len(event.EventReport) >= 2:
                    loc_event_report_case = event.EventReport[1]
                else:
                    loc_event_report_case = event.EventReport[0]
                loc_notes = event_report_note_task(task)

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

    ## Case have no id for this connector or the event doesn't exist anymore  
    else: 
        flag = True

    ## Event doesn't exist
    if flag:
        event = MISPEvent()
        event.uuid = str(uuid.uuid4())
        event.info = f"Case: {case['title']}"  # Required

        # Task
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

        ## Task's notes event report
        loc_notes = event_report_note_task(task)

        if loc_notes:
            event_report = {
                "uuid": str(uuid.uuid4()),
                "event_id": event.get("id"),
                "name": "Tasks notes",
                "content": loc_notes
            }   
            misp.add_event_report(event.get("id"), event_report)
    
    if "errors" in event:
        return event
    return event.get("uuid")

def introspection():
    return module_config
