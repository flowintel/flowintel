import json
from pymisp import MISPEvent, MISPGalaxy, MISPGalaxyCluster, MISPObject, PyMISP
import uuid
import conf.config_module as Config
from .misp_object_event import all_object_to_misp, manage_object_creation

module_config = {
    "connector": "misp",
    "case_task": "case",
    "description": "Create or modify an event using the current case. The event will include:\n\t- case's info as misp-object\n\t- tasks' info as misp-object \n\t- misp-object\n\t- tasks\n\t- case and tasks notes as event report"
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
    except Exception:
        return {"message": "Error connecting to MISP"}, {}
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
                    return event, object_uuid_list

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
                    return event, object_uuid_list

            res, object_uuid_list = all_object_to_misp(misp, event, case["objects"], object_uuid_list)
            if "errors" in res:
                return res, object_uuid_list

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

        for object in case["objects"]:
            res, object_uuid_list = manage_object_creation(misp, event, object, object_uuid_list)
            if "errors" in res:
                return res, object_uuid_list
    
    if "errors" in event:
        return event, object_uuid_list
    return event.get("uuid"), object_uuid_list

def introspection():
    return module_config
