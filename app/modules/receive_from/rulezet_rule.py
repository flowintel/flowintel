import requests
import urllib3
from urllib.parse import quote
import conf.config_module as Config

# Default to True so existing deployments without RULEZET_VERIFY_SSL stay on the secure default.
VERIFY_SSL = getattr(Config, "RULEZET_VERIFY_SSL", True)

if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATETIME_FORMAT = '%Y-%m-%dT%H:%M'

module_config = {
    "connector": "rulezet",
    "case_task": "case",
    "description": "Get a rule or a bundle from rulezet"
}


def _rulezet_headers(api_key):
    if not api_key:
        return {}

    token = str(api_key).strip()
    auth_value = token if token.lower().startswith(("bearer ", "token ")) else f"Bearer {token}"
    return {
        "Authorization": auth_value,
        "X-API-KEY": token,
        "Accept": "application/json"
    }


def _rulezet_error_message(response):
    message = None
    try:
        data = response.json()
        if isinstance(data, dict):
            message = data.get("message") or data.get("error") or data.get("detail")
    except ValueError:
        message = response.text.strip() if getattr(response, "text", None) else None

    if message:
        return f"Rulezet returned {response.status_code}: {message}"
    return f"Rulezet returned HTTP {response.status_code}"


def handler(instance, case, user, case_model=None, db_session=None, payload=None):
    """
    instance: name, url, description, uuid, connector_id, api_key, identifier

    case: id, uuid, title, description, creation_date, last_modif, status_id, status, completed, owner_org_id
          org_name, org_uuid, recurring_type, deadline, finish_date, tasks, clusters, connectors

    case["tasks"]: id, uuid, title, description, url, notes, creation_date, last_modif, case_id, status_id, status,
                   completed, deadline, finish_date, tags, clusters, connectors

    user: id, first_name, last_name, email, role_id, password_hash, api_key, org_id

    case_model: CaseCore instance for DB helper access
    db_session: SQLAlchemy db session
    """
    headers = _rulezet_headers(instance.get("api_key"))
    base_url = instance["url"].rstrip("/")

    try:
        requests.get(base_url, headers=headers, verify=VERIFY_SSL, timeout=20)
    except Exception:
        return {"message": "Error connecting to Rulezet"}

    if not case_model or not db_session:
        return {"message": "Module requires case_model and db_session"}

    if not payload or not payload.get("query"):
        return {"message": "Need to give a query"}

    from app.case import common_core as CommonModel
    from app.db_class.db import Rulezet_Rule
    import datetime

    try:
        response = requests.get(
            f"{base_url}/api/rule/public/detail/{quote(str(payload['query']), safe='')}",
            headers=headers,
            verify=VERIFY_SSL,
            timeout=20
        )
    except Exception:
        return {"message": "Error connecting to Rulezet"}

    if response.status_code >= 400:
        return {"message": _rulezet_error_message(response)}

    try:
        loc_json = response.json()
    except ValueError:
        return {"message": "Rulezet returned invalid JSON"}

    title = loc_json.get("title")
    description = loc_json.get("description")
    rule_format = loc_json.get("format")
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
        existing.format = rule_format
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
            format=rule_format,
            content=content,
            version=version,
            date_added=datetime.datetime.now(tz=datetime.timezone.utc)
        )
        db_session.session.add(new_rule)
        db_session.session.commit()

    CommonModel.update_last_modif(case["id"])


def introspection():
    return module_config
