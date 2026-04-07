import datetime
from pymisp import PyMISP
import urllib3
urllib3.disable_warnings()

DATETIME_FORMAT = '%Y-%m-%dT%H:%M'

module_config = {
    "connector": "misp",
    "case_task": "case",
    "description": "Update misp-object of current case from a misp event"
}


def handler(instance, case, user, case_model=None, db_session=None):
    """
    instance: name, url, description, uuid, connector_id, type, api_key, identifier

    case: id, uuid, title, description, creation_date, last_modif, status_id, status, completed, owner_org_id
          org_name, org_uuid, recurring_type, deadline, finish_date, tasks, clusters, connectors

    case["tasks"]: id, uuid, title, description, url, notes, creation_date, last_modif, case_id, status_id, status,
                   completed, deadline, finish_date, tags, clusters, connectors

    user: id, first_name, last_name, email, role_id, password_hash, api_key, org_id

    case_model: CaseCore instance for DB helper access
    db_session: SQLAlchemy db session
    """
    if not instance.get("identifier"):
        return {"message": "Need to give an identifier for this instance"}

    try:
        misp = PyMISP(instance["url"], instance["api_key"], ssl=False, timeout=20)
    except Exception:
        return {"message": "Error connecting to MISP"}

    event = misp.get_event(instance["identifier"], pythonify=True)
    if 'errors' in event:
        return {"message": "This Event doesn't exist"}

    if not case_model or not db_session:
        return {"message": "Module requires case_model and db_session"}

    from app.utils import misp_object_helper
    from app.case import common_core as CommonModel

    object_uuid_list = {}
    for obje in event.objects:
        # Check if object already exists for this instance
        object_exist = case_model.get_misp_object_instance_by_instance_uuid(obje.uuid, instance["id"], case["id"])
        if object_exist:
            db_misp_object = case_model.get_misp_object(object_exist.misp_object_id)
            if not db_misp_object.name == obje.name:
                db_misp_object.name = obje.name
                db_misp_object.last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
                db_session.session.commit()

            for attr in obje.attributes:
                attr_exist = case_model.get_misp_attribute_instance_by_instance_uuid(attr.uuid, instance["id"], case["id"])
                if attr_exist:
                    db_misp_attr = case_model.get_misp_attribute(attr_exist.misp_attribute_id)
                    flag = False
                    if not db_misp_attr.value == attr.value:
                        db_misp_attr.value = attr.value
                        flag = True
                    if not db_misp_attr.type == attr.type:
                        db_misp_attr.type = attr.type
                        flag = True
                    if not db_misp_attr.object_relation == attr.object_relation:
                        db_misp_attr.object_relation = attr.object_relation
                        flag = True
                    if not db_misp_attr.first_seen == attr.get("first_seen"):
                        if type(attr.first_seen) == datetime.datetime:
                            db_misp_attr.first_seen = attr.first_seen
                        else:
                            db_misp_attr.first_seen = datetime.datetime.strptime(attr.get("first_seen"), DATETIME_FORMAT)
                        flag = True
                    if not db_misp_attr.last_seen == attr.get("last_seen"):
                        if type(attr.last_seen) == datetime.datetime:
                            db_misp_attr.last_seen = attr.last_seen
                        else:
                            db_misp_attr.last_seen = datetime.datetime.strptime(attr.get("last_seen"), DATETIME_FORMAT)
                        flag = True
                    if not db_misp_attr.comment == attr.comment:
                        db_misp_attr.comment = attr.comment
                        flag = True
                    if not db_misp_attr.ids_flag == attr.to_ids:
                        db_misp_attr.ids_flag = attr.to_ids
                        flag = True

                    if flag:
                        db_misp_object.last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
                        db_session.session.commit()

        else:
            def append_dict(base, new):
                for key, value in new.items():
                    if key in base:
                        base[key]['attributes'].extend(value.get('attributes', []))
                    else:
                        base[key] = value
                return base
            loc = misp_object_helper.create_misp_object(case["id"], obje)
            object_uuid_list = append_dict(object_uuid_list, loc)

    case_model.result_misp_object_module(object_uuid_list, instance_id=instance["id"], case_id=case["id"])

    # Mark case as updated from MISP
    case_obj = CommonModel.get_case(case["id"])
    case_obj.is_updated_from_misp = True
    db_session.session.commit()

    CommonModel.update_last_modif(case["id"])


def introspection():
    return module_config
