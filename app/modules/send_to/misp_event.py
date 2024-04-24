from pymisp import MISPEvent, MISPObject, PyMISP
import uuid
import conf.config_module as Config

module_config = {
    "connector": "misp",
    "case_task": "case"
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
    return misp_object

def create_case(case):
    misp_object = MISPObject("flowintel-cm-case", standalone=False)
    misp_object = common_create(case, case["uuid"], misp_object)
    
    misp_object.add_attribute('case-owner-org-name', value=case["org_name"])
    misp_object.add_attribute('case-owner-org-uuid', value=case["org_uuid"])
    misp_object.add_attribute('notes', value=case["notes"])
    misp_object.add_attribute('recurring-type', value=case["recurring_type"])
    return misp_object

def create_task(task, case_uuid):
    misp_object = MISPObject("flowintel-cm-task", standalone=False)
    misp_object = common_create(task, case_uuid, misp_object)

    misp_object.add_attribute('task-uuid', value=task["uuid"])
    misp_object.add_attribute('url', value=task["url"])
    return misp_object

def create_task_note(note):
    misp_object = MISPObject("flowintel-cm-task-note", standalone=False)

    misp_object.add_attribute('note', value=note["note"])
    misp_object.add_attribute('task-uuid', value=note["task_uuid"])
    misp_object.add_attribute('note-uuid', value=note["uuid"])
    misp_object.add_attribute('origin-url', value=Config.ORIGIN_URL)
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
                    attribute = common_edit(case, attribute)
                    if attribute.object_relation == 'case-owner-org-name' and not attribute.value == case["org_name"]:
                        attribute.value = case["org_name"]
                    elif attribute.object_relation == 'case-owner-org-uuid' and not attribute.value == case["org_uuid"]:
                        attribute.value = case["org_uuid"]
                    elif attribute.object_relation == 'recurring-type' and not attribute.value == case["recurring_type"]:
                        attribute.value = case["recurring_type"]
                    elif attribute.object_relation == 'notes' and not attribute.value == case["notes"]:
                        attribute.value = case["notes"]
                    

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
                            attribute = common_edit(task, attribute)
                            if attribute.object_relation == 'url' and not attribute.value == task["url"]:
                                attribute.value = task["url"]

                        ## Task's notes
                        misp_objects_note = event.get_objects_by_name("flowintel-cm-task-note")
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
                                event.add_object(misp_note_object)
                        
                    ## Task doesn't exist in the event
                    else:
                        misp_object = create_task(task, case["uuid"])
                        event.add_object(misp_object)

                        ## Task's notes
                        for note in task["notes"]:
                            misp_object = create_task_note(note)
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

            ## Case doesn't exist in the event
            else:
                misp_object = create_case(case)
                event.add_object(misp_object)

                for task in case["tasks"]:
                    misp_object = create_task(task, case["uuid"])
                    event.add_object(misp_object)

                    for note in task["notes"]:
                        misp_object = create_task_note(note)
                        event.add_object(misp_object)

                event = misp.update_event(event, pythonify=True)

    ## Case have no id for this connector or the event doesn't exist anymore  
    else: 
        flag = True

    ## Event doesn't exist
    if flag:
        event = MISPEvent()
        event.uuid = str(uuid.uuid4())
        event.info = f"Case: {case['title']}"  # Required

        misp_object = create_case(case)
        event.add_object(misp_object)

        # Task
        for task in case["tasks"]:
            misp_object = create_task(task, case["uuid"])
            event.add_object(misp_object)

            ## Task's notes
            for note in task["notes"]:
                misp_object = create_task_note(note)
                event.add_object(misp_object)

        event = misp.add_event(event, pythonify=True)


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
    
    return event.get("id")

def introspection():
    return module_config
