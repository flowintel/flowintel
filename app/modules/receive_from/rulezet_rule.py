import requests
import urllib3
urllib3.disable_warnings()

DATETIME_FORMAT = '%Y-%m-%dT%H:%M'

module_config = {
    "connector": "rulezet",
    "case_task": "case",
    "description": "Get a rule or a bundle from rulezet"
}


def handler(instance, case, user, case_model=None, db_session=None, payload=None):
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
    try:
        r = requests.get(instance["url"], verify=False, timeout=20)
    except Exception:
        return {"message": "Error connecting to Rulezet"}

    if not case_model or not db_session:
        return {"message": "Module requires case_model and db_session"}

    from app.case import common_core as CommonModel
    from app.db_class.db import Rulezet_Rule
    import datetime

    loc_json = requests.get(f'{instance["url"]}/api/rule/public/detail/{payload["query"]}', verify=False, timeout=20).json()

    title = loc_json.get("title")
    description = loc_json.get("description")
    format = loc_json.get("format")
    content = loc_json.get("to_string")
    version = loc_json.get("version")
    # store or update rule in DB
    try:
        remote_id = payload.get("query") if payload else None
    except Exception:
        remote_id = None

    if remote_id:
        existing = Rulezet_Rule.query.filter_by(remote_id=str(remote_id), instance_id=instance.get("id"), case_id=case.get("id")).first()
    else:
        existing = None

    if existing:
        existing.title = title
        existing.description = description
        existing.format = format
        existing.content = content
        existing.version = version
        existing.date_added = datetime.datetime.now(tz=datetime.timezone.utc)
        db_session.session.commit()
    else:
        new_rule = Rulezet_Rule(
            case_id=case.get("id"),
            instance_id=instance.get("id"),
            remote_id=str(remote_id) if remote_id else None,
            title=title,
            description=description,
            format=format,
            content=content,
            version=version,
            date_added=datetime.datetime.now(tz=datetime.timezone.utc)
        )
        db_session.session.add(new_rule)
        db_session.session.commit()

    CommonModel.update_last_modif(case["id"])


def introspection():
    return module_config
