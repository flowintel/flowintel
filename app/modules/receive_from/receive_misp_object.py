from pymisp import PyMISP
import urllib3
urllib3.disable_warnings()

module_config = {
    "connector": "misp",
    "case_task": "case",
    "description": "Update misp-object of current case from a misp event"
}


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
    
    event = misp.get_event(instance["identifier"], pythonify=True)
    if 'errors' in event:
        return {"message": "This Event doesn't exist"}
    else:
        return event


def introspection():
    return module_config
