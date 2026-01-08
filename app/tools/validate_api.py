from pymisp import PyMISP
from app.db_class.db import Case, Case_Template, Connector_Instance, User, User_Connector_Instance


def validate_case_from_misp(request_json: dict, current_user: User):
    print(request_json)
    if "case_title" not in request_json or not request_json["case_title"]:
        return {"message": "Please give a title"}
    elif Case.query.filter_by(title=request_json["case_title"]).first():
        return {"message": "Title already exist"}
    
    if "case_template_id" not in request_json or not request_json["case_template_id"]:
        return {"message": "Please give a case template id"}
    elif not Case_Template.query.get(int(request_json["case_template_id"])):
        return {"message": "Case template not found"}
    
    if "misp_instance_id" not in request_json or not request_json["misp_instance_id"]:
        return {"message": "Please give a misp instance id"}
    else:
        instance = Connector_Instance.query.get(int(request_json["misp_instance_id"]))
        if not instance:
            return {"message": "Instance not found"}
        
        user_connector_instance = User_Connector_Instance.query.filter_by(user_id=current_user.id,instance_id=instance.id).first()
        if not user_connector_instance:
            return {"message": "No config found for the instance"}
        
        try:
            misp = PyMISP(instance.url, user_connector_instance.api_key, ssl=False, timeout=20)
        except Exception:
            return {"message": "Error connecting to MISP"}        
            
    if "misp_event_id" not in request_json or not request_json["misp_event_id"]:
        return {"message": "Please give a misp event id"}
    else:
        instance = Connector_Instance.query.get(int(request_json["misp_instance_id"]))
        if not instance:
            return {"message": "Instance not found"}
        user_connector_instance = User_Connector_Instance.query.filter_by(user_id=current_user.id,instance_id=instance.id).first()
        if not user_connector_instance:
            return {"message": "No config found for the instance"}
        misp = PyMISP(instance.url, user_connector_instance.api_key, ssl=False, timeout=20)
        event = misp.get_event(request_json["misp_event_id"], pythonify=True)
        if 'errors' in event:
            return {"message": "Event not found on this MISP instance"}
        
    return {}