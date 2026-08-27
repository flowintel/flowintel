import datetime
import json
import secrets
from urllib.parse import urlparse
import uuid

from app import db
from app.case import validation_api as CaseValidation
from app.case.CaseCore import CaseModel
from app.case import common_core as CommonCase
from app.case.common_core import check_user_in_private_cases, get_present_in_case
from app.connectors import connectors_core as ConnectorModel
from app.db_class.db import (
    Case,
    Case_Connector_Instance,
    Connector,
    Connector_Instance,
    ExternalAlert,
    ExternalAlertAction,
    Org,
    Role,
    User,
    User_Connector_Instance,
)
from app.templating import common_template_core as TemplateCommon
from app.templating.TemplateCase import TemplateModel
from app.utils.logger import flowintel_log


MISP_ALERT_SCHEMA = "misp.event"
FLOWINTEL_ALERT_SCHEMA = MISP_ALERT_SCHEMA
MAX_INGEST_BYTES = 512 * 1024
MAX_TEXT = 4000
MAX_DESCRIPTION = 12000
MAX_JSON_DEPTH = 6
MAX_JSON_KEYS = 80
MAX_JSON_LIST_ITEMS = 200
MAX_CASE_SUMMARY_ITEMS = 30
SAFE_EXTERNAL_URL_SCHEMES = {"http", "https"}

ALERT_TYPES = {"external", "case_notification"}
ALERT_REVIEW_STATUSES = {"new", "reviewing", "case_created", "false_positive", "dismissed"}
TERMINAL_REVIEW_STATUSES = {"case_created", "false_positive", "dismissed"}
ALERT_SEVERITIES = {"info", "low", "medium", "high", "critical"}
ALERT_TLPS = {"clear", "green", "amber", "amber+strict", "red"}
MISP_THREAT_LEVELS = {
    "1": "high",
    "2": "medium",
    "3": "low",
    "4": "info",
}
ALERT_ACTION_LABELS = {
    "new": "Reset to new",
    "reviewing": "Marked for review",
    "case_created": "Created case",
    "false_positive": "Marked false positive",
    "dismissed": "Dismissed",
}


def utcnow():
    return datetime.datetime.now(tz=datetime.timezone.utc)


def clean_string(value, max_len=MAX_TEXT):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=True, sort_keys=True)
    value = str(value).replace("\x00", "").strip()
    if len(value) > max_len:
        return value[:max_len] + "..."
    return value


def sanitize_external_url(value, max_len=2000):
    url = clean_string(value, max_len)
    if not url:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        return None

    parsed = urlparse(url)
    if parsed.scheme.lower() not in SAFE_EXTERNAL_URL_SCHEMES:
        return None
    if not parsed.netloc:
        return None
    return url


def safe_markdown_text(value, max_len=MAX_TEXT):
    value = clean_string(value, max_len=max_len) or ""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def first_present(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def bounded_json(value, depth=0):
    if depth >= MAX_JSON_DEPTH:
        return clean_string(value, 500)
    if isinstance(value, dict):
        out = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_JSON_KEYS:
                out["_truncated"] = True
                break
            out[clean_string(key, 120) or ""] = bounded_json(item, depth + 1)
        return out
    if isinstance(value, list):
        out = [bounded_json(item, depth + 1) for item in value[:MAX_JSON_LIST_ITEMS]]
        if len(value) > MAX_JSON_LIST_ITEMS:
            out.append({"_truncated": True, "original_count": len(value)})
        return out
    if isinstance(value, str):
        return clean_string(value, MAX_TEXT)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return clean_string(value, MAX_TEXT)


def as_list(value):
    if value in (None, "", [], {}):
        return []
    if isinstance(value, list):
        return bounded_json(value)
    if isinstance(value, dict):
        return [bounded_json(value)]
    return [{"value": clean_string(value)}]


def as_dict(value):
    return value if isinstance(value, dict) else {}


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        loc_value = value
    else:
        try:
            if isinstance(value, (int, float)) or str(value).isdigit():
                loc_value = datetime.datetime.fromtimestamp(int(value), tz=datetime.timezone.utc)
            else:
                loc_value = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None
    if loc_value.tzinfo is None:
        return loc_value.replace(tzinfo=datetime.timezone.utc)
    return loc_value.astimezone(datetime.timezone.utc)


def normalize_severity(value):
    severity = clean_string(value, 20)
    if not severity:
        return "medium"
    severity = severity.lower().replace("informational", "info")
    if severity in {"notice", "debug"}:
        return "info"
    if severity in {"warn", "warning"}:
        return "medium"
    if severity in {"emergency", "fatal", "severe"}:
        return "critical"
    return severity if severity in ALERT_SEVERITIES else "medium"


def normalize_confidence(value):
    if value in (None, ""):
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if confidence > 1 and confidence <= 100:
        confidence = confidence / 100
    if confidence < 0 or confidence > 1:
        return None
    return confidence


def normalize_tlp(value):
    tlp = clean_string(value, 20)
    if not tlp:
        return None
    tlp = tlp.lower().replace("tlp:", "")
    return tlp if tlp in ALERT_TLPS else None


def unwrap_misp_event(payload):
    if not isinstance(payload, dict):
        return None
    event = payload.get("Event") if isinstance(payload.get("Event"), dict) else payload
    if not isinstance(event, dict):
        return None
    return event


def misp_tag_names(event):
    names = []
    for tag in as_list(event.get("Tag")) + as_list(event.get("tags")):
        if isinstance(tag, dict):
            name = tag.get("name")
        else:
            name = tag
        name = clean_string(name, 255)
        if name and name not in names:
            names.append(name)
    return names


def tlp_from_misp_tags(tag_names):
    for tag in tag_names:
        normalized = tag.lower().replace("tlp:", "")
        if normalized in ALERT_TLPS:
            return normalized
    return None


def misp_severity(event):
    return MISP_THREAT_LEVELS.get(clean_string(event.get("threat_level_id"), 20), "medium")


def misp_source(event, instance):
    orgc = event.get("Orgc") if isinstance(event.get("Orgc"), dict) else {}
    org = event.get("Org") if isinstance(event.get("Org"), dict) else {}
    connector = Connector.query.get(instance.connector_id) if instance else None
    return clean_string(first_present(
        orgc.get("name"),
        org.get("name"),
        connector.name if connector else None,
        instance.name if instance else None,
        "MISP event",
    ), 120)


def misp_event_title(event):
    return clean_string(first_present(
        event.get("info"),
        event.get("title"),
        event.get("uuid"),
        event.get("id"),
    ), 255)


def misp_attribute_payload(attribute):
    return {
        "uuid": clean_string(attribute.get("uuid"), 36),
        "value": clean_string(attribute.get("value"), MAX_TEXT),
        "type": clean_string(attribute.get("type"), 120) or "text",
        "object_relation": clean_string(attribute.get("object_relation"), 120) or "",
        "first_seen": clean_string(attribute.get("first_seen"), 80) or "",
        "last_seen": clean_string(attribute.get("last_seen"), 80) or "",
        "comment": clean_string(attribute.get("comment"), 1000) or "",
        "ids_flag": bool(attribute.get("to_ids") or attribute.get("ids_flag")),
        "disable_correlation": bool(attribute.get("disable_correlation")),
    }


def is_misp_object_attribute(attribute):
    if not isinstance(attribute, dict):
        return False
    object_id = attribute.get("object_id")
    if object_id not in (None, "", "0", 0):
        return True
    if attribute.get("object_relation") not in (None, ""):
        return True
    if isinstance(attribute.get("Object"), dict):
        return True
    return False


def misp_event_attributes(event):
    attributes = []
    for attribute in as_list(event.get("Attribute")) + as_list(event.get("attributes")):
        if isinstance(attribute, dict) and not is_misp_object_attribute(attribute):
            attributes.append(misp_attribute_payload(attribute))
    return [attr for attr in attributes if attr.get("value")]


def misp_object_attributes(misp_object):
    attributes = []
    for attribute in as_list(misp_object.get("Attribute")) + as_list(misp_object.get("attributes")):
        if isinstance(attribute, dict):
            attributes.append(misp_attribute_payload(attribute))
    return [attr for attr in attributes if attr.get("value")]


def misp_event_objects(event):
    objects = []
    object_ids_seen = set()
    for misp_object in as_list(event.get("Object")) + as_list(event.get("objects")):
        if not isinstance(misp_object, dict):
            continue
        name = clean_string(misp_object.get("name"), 120)
        attributes = misp_object_attributes(misp_object)
        if not name or not attributes:
            continue
        if misp_object.get("id") not in (None, ""):
            object_ids_seen.add(str(misp_object.get("id")))
        objects.append({
            "uuid": clean_string(misp_object.get("uuid"), 36),
            "name": name,
            "template_uuid": clean_string(first_present(
                misp_object.get("template_uuid"),
                misp_object.get("template_uuid_v4"),
            ), 36) or "",
            "meta_category": clean_string(misp_object.get("meta-category"), 120),
            "comment": clean_string(misp_object.get("comment"), 1000) or "",
            "attributes": attributes,
        })

    flat_objects = {}
    for attribute in as_list(event.get("Attribute")) + as_list(event.get("attributes")):
        if not is_misp_object_attribute(attribute):
            continue
        object_id = clean_string(first_present(attribute.get("object_id"), attribute.get("object_uuid")), 120)
        if object_id and object_id in object_ids_seen:
            continue
        object_data = attribute.get("Object") if isinstance(attribute.get("Object"), dict) else {}
        object_key = object_id or clean_string(first_present(
            object_data.get("uuid"),
            object_data.get("name"),
            attribute.get("object_relation"),
        ), 120) or "misp-object"
        current = flat_objects.setdefault(object_key, {
            "uuid": clean_string(first_present(object_data.get("uuid"), attribute.get("object_uuid")), 36),
            "name": clean_string(first_present(object_data.get("name"), attribute.get("object_name"), "misp-object"), 120),
            "template_uuid": clean_string(object_data.get("template_uuid"), 36) or "",
            "meta_category": clean_string(object_data.get("meta-category"), 120),
            "comment": clean_string(object_data.get("comment"), 1000) or "",
            "attributes": [],
        })
        payload = misp_attribute_payload(attribute)
        if payload.get("value") and payload not in current["attributes"]:
            current["attributes"].append(payload)

    objects.extend(obj for obj in flat_objects.values() if obj["attributes"])
    return objects


def misp_galaxy_items(event):
    items = []
    galaxy_sources = as_list(event.get("Galaxy")) + as_list(event.get("GalaxyCluster")) + as_list(event.get("galaxies"))
    for galaxy in galaxy_sources:
        if not isinstance(galaxy, dict):
            continue
        clusters = as_list(galaxy.get("GalaxyCluster")) or [galaxy]
        for cluster in clusters:
            if not isinstance(cluster, dict):
                continue
            value = clean_string(first_present(cluster.get("value"), cluster.get("tag_name"), cluster.get("uuid")), 255)
            if value:
                items.append({
                    "value": value,
                    "type": clean_string(first_present(galaxy.get("type"), cluster.get("type")), 120),
                    "uuid": clean_string(cluster.get("uuid"), 36),
                })
    return items


def misp_external_references(event):
    references = []
    for attribute in misp_event_attributes(event):
        if attribute.get("type") in {"link", "url"}:
            url = sanitize_external_url(attribute.get("value"))
            if url:
                references.append({"label": "MISP link", "url": url})
    return references


def connector_from_key(api_key):
    """Return connector identity for an external alert source API key."""
    if not api_key:
        return None

    global_instances = Connector_Instance.query.filter(Connector_Instance.global_api_key.isnot(None)).all()
    for instance in global_instances:
        if instance.global_api_key and secrets.compare_digest(instance.global_api_key, api_key):
            return {"instance": instance, "user": None}

    user_instances = User_Connector_Instance.query.filter(User_Connector_Instance.api_key.isnot(None)).all()
    for user_instance in user_instances:
        if user_instance.api_key and secrets.compare_digest(user_instance.api_key, api_key):
            instance = Connector_Instance.query.get(user_instance.instance_id)
            user = User.query.get(user_instance.user_id)
            if instance and user:
                return {"instance": instance, "user": user}

    return None


def connector_from_headers(headers):
    authorization = headers.get("Authorization", "")
    bearer = ""
    if authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()
    api_key = (
        headers.get("X-API-KEY")
        or headers.get("X-FLOWINTEL-ALERT-KEY")
        or headers.get("X-Flowintel-Alert-Key")
        or bearer
    )
    return connector_from_key(api_key)


def owner_scope_for_identity(identity):
    instance = identity["instance"]
    user = identity.get("user")
    scope = ConnectorModel.get_instance_sharing_scope(instance)
    if scope == "personal" and user:
        return user.id, user.org_id
    if scope == "org":
        return None, instance.shared_org_id
    return None, None


def source_name_for_instance(instance, source_data, source_value=None):
    connector = Connector.query.get(instance.connector_id) if instance else None
    return clean_string(first_present(
        source_data.get("tool"),
        source_data.get("name"),
        source_data.get("product"),
        source_value if isinstance(source_value, str) else None,
        connector.name if connector else None,
        instance.name if instance else None,
        "External tool",
    ), 120)


def normalize_alert_payload(payload, identity):
    event = unwrap_misp_event(payload)
    if not event:
        return None, {"message": "Alert payload must be a MISP event object or {'Event': {...}}"}

    if not (event.get("info") or event.get("uuid") or event.get("Attribute") or event.get("Object")):
        return None, {"message": "MISP event payload requires at least info, uuid, Attribute, or Object"}

    instance = identity["instance"]
    owner_user_id, owner_org_id = owner_scope_for_identity(identity)
    tag_names = misp_tag_names(event)
    event_attributes = misp_event_attributes(event)
    event_objects = misp_event_objects(event)
    source_ref = clean_string(first_present(event.get("uuid"), event.get("id")), 255)
    title = misp_event_title(event)

    if not title:
        return None, {"message": "MISP event payload requires an info, uuid, or id field"}

    event_time = parse_datetime(first_present(
        event.get("timestamp"),
        event.get("publish_timestamp"),
        event.get("date"),
    ))

    description = clean_string(first_present(
        event.get("info"),
        f"MISP event {source_ref}" if source_ref else None,
    ), MAX_DESCRIPTION) or ""

    return {
        "schema": MISP_ALERT_SCHEMA,
        "title": title,
        "description": description,
        "message": title,
        "severity": misp_severity(event),
        "confidence": None,
        "category": clean_string(first_present(event.get("analysis"), "misp-event"), 80),
        "tlp": tlp_from_misp_tags(tag_names),
        "source": misp_source(event, instance),
        "source_ref": source_ref,
        "source_url": None,
        "connector_instance_id": instance.id,
        "owner_user_id": owner_user_id,
        "owner_org_id": owner_org_id,
        "event_time": event_time,
        "last_seen": event_time or utcnow(),
        "deduplication_key": source_ref,
        "raw_payload": bounded_json(payload),
        "observables": event_attributes,
        "assets": event_objects,
        "external_references": misp_external_references(event),
        "mitre_attack": misp_galaxy_items(event),
        "recommended_actions": [],
        "tags": tag_names,
    }, None


def ingest_alert(payload, identity):
    normalized, error = normalize_alert_payload(payload, identity)
    if error:
        return None, False, error

    existing = None
    if normalized["deduplication_key"]:
        existing = ExternalAlert.query.filter_by(
            connector_instance_id=normalized["connector_instance_id"],
            deduplication_key=normalized["deduplication_key"],
        ).first()

    if existing:
        existing.occurrence_count = (existing.occurrence_count or 1) + 1
        existing.last_seen = normalized["last_seen"]
        existing.raw_payload = normalized["raw_payload"]
        existing.observables = normalized["observables"]
        existing.assets = normalized["assets"]
        existing.external_references = normalized["external_references"]
        existing.mitre_attack = normalized["mitre_attack"]
        existing.recommended_actions = normalized["recommended_actions"]
        existing.tags = normalized["tags"]
        if existing.review_status not in TERMINAL_REVIEW_STATUSES:
            for key in [
                "title", "description", "message", "severity", "confidence", "category",
                "tlp", "source", "source_ref", "source_url", "event_time"
            ]:
                setattr(existing, key, normalized[key])
            existing.is_read = False
        db.session.commit()
        return existing, False, None

    alert = ExternalAlert(
        uuid=str(uuid.uuid4()),
        title=normalized["title"],
        description=normalized["description"],
        message=normalized["message"],
        status="new",
        severity=normalized["severity"],
        confidence=normalized["confidence"],
        category=normalized["category"],
        tlp=normalized["tlp"],
        source=normalized["source"],
        source_ref=normalized["source_ref"],
        source_url=normalized["source_url"],
        connector_instance_id=normalized["connector_instance_id"],
        owner_user_id=normalized["owner_user_id"],
        owner_org_id=normalized["owner_org_id"],
        review_status="new",
        event_time=normalized["event_time"],
        last_seen=normalized["last_seen"],
        occurrence_count=1,
        deduplication_key=normalized["deduplication_key"],
        raw_payload=normalized["raw_payload"],
        observables=normalized["observables"],
        assets=normalized["assets"],
        external_references=normalized["external_references"],
        mitre_attack=normalized["mitre_attack"],
        recommended_actions=normalized["recommended_actions"],
        tags=normalized["tags"],
    )
    db.session.add(alert)
    db.session.commit()
    notify_external_alert_received(alert)
    return alert, True, None


def external_alert_notification_recipients(alert):
    recipients = {}

    admin_roles = Role.query.filter_by(admin=True).all()
    admin_role_ids = [role.id for role in admin_roles]
    if admin_role_ids:
        for user in User.query.filter(User.role_id.in_(admin_role_ids)).all():
            recipients[user.id] = user

    if alert.owner_user_id:
        owner = User.query.get(alert.owner_user_id)
        if owner:
            recipients[owner.id] = owner
    elif alert.owner_org_id:
        for user in User.query.filter_by(org_id=alert.owner_org_id).all():
            if not user.read_only():
                recipients[user.id] = user

    return list(recipients.values())


def notify_external_alert_received(alert):
    try:
        from app.notification import notification_core as NotifModel

        recipients = external_alert_notification_recipients(alert)
        source = alert.source or "External tool"
        title = alert.title or alert.message or f"Alert {alert.id}"
        message = clean_string(f"New alert received from {source}: {title}", 1000)
        return NotifModel.create_notification_for_users(
            message=message,
            users=recipients,
            html_icon="fa-solid fa-triangle-exclamation",
            category="alerting",
            notification_type="external_alert",
            target_url=f"/alerting/?alert_id={alert.id}"
        )
    except Exception as e:
        db.session.rollback()
        flowintel_log(
            "warn",
            500,
            "External alert notification failed",
            AlertId=getattr(alert, "id", None),
            Error=str(e),
        )
        return False


def can_user_view_alert(alert, user):
    if user.is_admin():
        return True

    if alert.owner_user_id:
        return alert.owner_user_id == user.id
    if alert.owner_org_id:
        return alert.owner_org_id == user.org_id

    if alert.case_id:
        case = Case.query.get(alert.case_id)
        if case and case.is_private:
            return get_present_in_case(case.id, user)
    return True


def visible_alert_pairs(alerts, user):
    case_ids = {alert.case_id for alert in alerts if alert.case_id}
    cases_by_id = {
        c.id: c for c in Case.query.filter(Case.id.in_(case_ids)).all()
    } if case_ids else {}
    visible_cases = {
        c.id for c in check_user_in_private_cases(list(cases_by_id.values()), user)
    }

    visible = []
    for alert in alerts:
        case = cases_by_id.get(alert.case_id)
        if case and case.id not in visible_cases:
            continue
        if can_user_view_alert(alert, user):
            visible.append((alert, case))
    return visible


def user_display_name(user):
    if not user:
        return ""
    name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    return name or user.nickname or user.email or f"User #{user.id}"


def action_label(action):
    return ALERT_ACTION_LABELS.get(action, action.replace("_", " ").title() if action else "Updated")


def action_to_json(action):
    payload = action.to_json()
    user = User.query.get(action.user_id) if action.user_id else None
    payload["action_label"] = action_label(action.action)
    payload["user_name"] = user_display_name(user)
    payload["user_email"] = user.email if user else ""
    return payload


def alert_action_history(alert):
    actions = ExternalAlertAction.query.filter_by(alert_id=alert.id).order_by(
        ExternalAlertAction.created_at.desc(),
        ExternalAlertAction.id.desc(),
    ).all()
    history = [action_to_json(action) for action in actions]

    if not history and alert.reviewed_by_id:
        user = User.query.get(alert.reviewed_by_id)
        history.append({
            "id": None,
            "alert_id": alert.id,
            "action": alert.review_status,
            "action_label": action_label(alert.review_status),
            "user_id": alert.reviewed_by_id,
            "user_name": user_display_name(user),
            "user_email": user.email if user else "",
            "comment": alert.review_comment,
            "details": {"legacy": True},
            "created_at": alert.reviewed_at.isoformat() if alert.reviewed_at else None,
        })

    return history


def alert_to_json(alert, case=None):
    item = alert.to_json()
    item["case_title"] = case.title if case else ""
    item["case_uuid"] = case.uuid if case else ""

    connector_instance = Connector_Instance.query.get(alert.connector_instance_id) if alert.connector_instance_id else None
    item["connector_instance_name"] = connector_instance.name if connector_instance else ""

    owner_user = User.query.get(alert.owner_user_id) if alert.owner_user_id else None
    owner_org = Org.query.get(alert.owner_org_id) if alert.owner_org_id else None
    reviewer = User.query.get(alert.reviewed_by_id) if alert.reviewed_by_id else None

    item["owner_user_name"] = user_display_name(owner_user)
    item["owner_user_email"] = owner_user.email if owner_user else ""
    item["owner_org_name"] = owner_org.name if owner_org else ""
    item["reviewed_by_name"] = user_display_name(reviewer)
    item["reviewed_by_email"] = reviewer.email if reviewer else ""
    item["action_history"] = alert_action_history(alert)
    return item


def record_alert_action(alert, action, user, comment=None, details=None):
    db.session.add(ExternalAlertAction(
        alert_id=alert.id,
        action=action,
        user_id=user.id if user else None,
        comment=clean_string(comment, 2000),
        details=bounded_json(details or {}),
        created_at=utcnow(),
    ))


def alerts_to_json(alerts, user):
    result = []
    for alert, case in visible_alert_pairs(alerts, user):
        result.append(alert_to_json(alert, case))
    return result


def query_visible_alerts(user, limit=200, review_status=None, alert_type=None):
    if alert_type and alert_type != "external":
        return []

    query = ExternalAlert.query
    if review_status:
        query = query.filter_by(review_status=review_status)
    return visible_alerts_from_query(user, query, limit=limit)


def visible_alerts_from_query(user, query, limit=200):
    alerts = query.order_by(ExternalAlert.creation_date.desc()).limit(limit).all()
    return alerts_to_json(alerts, user)


def update_review_status(alert, user, review_status, comment=None):
    if review_status not in ALERT_REVIEW_STATUSES:
        return {"message": "Invalid review status"}, 400
    if not can_user_view_alert(alert, user):
        return {"message": "Permission denied"}, 403

    alert.review_status = review_status
    alert.review_comment = clean_string(comment, 2000)
    alert.reviewed_by_id = user.id
    alert.reviewed_at = utcnow()
    alert.is_read = True
    if review_status in {"false_positive", "dismissed"}:
        alert.status = review_status
    record_alert_action(alert, review_status, user, comment=comment)
    db.session.commit()
    flowintel_log("audit", 200, "Alert review status updated", User=user.email, AlertId=alert.id, ReviewStatus=review_status)
    return {"message": "Alert updated", "alert": alert_to_json(alert)}, 200


def unique_case_title(base_title, alert_id):
    base_title = clean_string(base_title, 220) or f"Alert {alert_id}"
    title = base_title
    if not Case.query.filter_by(title=title).first():
        return title

    title = f"{base_title} (alert {alert_id})"
    if not Case.query.filter_by(title=title).first():
        return title

    suffix = 2
    while Case.query.filter_by(title=f"{base_title} (alert {alert_id}-{suffix})").first():
        suffix += 1
    return f"{base_title} (alert {alert_id}-{suffix})"


def format_object_for_case(item):
    if isinstance(item, dict):
        bits = []
        for key in ["type", "value", "name", "ip", "hostname", "user", "role"]:
            if item.get(key) not in (None, ""):
                bits.append(f"{key}: {safe_markdown_text(item.get(key), 500)}")
        if bits:
            return "; ".join(bits)
    return safe_markdown_text(item, 1000)


def build_case_description(alert, extra_description=None):
    lines = [
        "# Alert review",
        "",
        f"Source: {safe_markdown_text(alert.source or 'External tool', 200)}",
        f"Severity: {safe_markdown_text(alert.severity or 'medium', 40)}",
    ]
    if alert.confidence is not None:
        lines.append(f"Confidence: {round(alert.confidence * 100)}%")
    if alert.category:
        lines.append(f"Category: {safe_markdown_text(alert.category, 100)}")
    if alert.tlp:
        lines.append(f"TLP: {safe_markdown_text(alert.tlp.upper(), 40)}")
    if alert.source_ref:
        lines.append(f"Source reference: {safe_markdown_text(alert.source_ref, 300)}")
    if alert.event_time:
        lines.append(f"Event time: {alert.event_time.isoformat()}")
    if alert.source_url:
        lines.append(f"Source URL: {safe_markdown_text(alert.source_url, 1000)}")

    description = safe_markdown_text(extra_description or alert.description, MAX_DESCRIPTION)
    if description:
        lines.extend(["", "## Summary", "", description])

    if alert.assets:
        lines.extend(["", "## Assets"])
        for item in alert.assets[:MAX_CASE_SUMMARY_ITEMS]:
            lines.append(f"- {format_object_for_case(item)}")

    if alert.observables:
        lines.extend(["", "## Observables"])
        for item in alert.observables[:MAX_CASE_SUMMARY_ITEMS]:
            lines.append(f"- {format_object_for_case(item)}")

    if alert.mitre_attack:
        lines.extend(["", "## MITRE ATT&CK"])
        for item in alert.mitre_attack[:MAX_CASE_SUMMARY_ITEMS]:
            lines.append(f"- {format_object_for_case(item)}")

    if alert.recommended_actions:
        lines.extend(["", "## Suggested actions"])
        for item in alert.recommended_actions[:MAX_CASE_SUMMARY_ITEMS]:
            lines.append(f"- {format_object_for_case(item)}")

    lines.extend(["", f"Flowintel alert UUID: {alert.uuid}"])
    return "\n".join(lines)


def misp_event_from_alert(alert):
    return unwrap_misp_event(alert.raw_payload or {})


def import_misp_event_to_case(alert, case, user):
    event = misp_event_from_alert(alert)
    if not event:
        return {"objects": 0, "attributes": 0}

    instance_id = alert.connector_instance_id
    imported_objects = 0
    imported_attributes = 0
    object_uuid_map = {}
    standalone_uuid_list = []

    for attribute in misp_event_attributes(event):
        if not attribute.get("value") or not attribute.get("type"):
            continue
        attr = CaseModel.create_standalone_attribute(case.id, attribute, user)
        imported_attributes += 1
        if instance_id and attribute.get("uuid"):
            standalone_uuid_list.append({"attribute_id": attr.id, "uuid": attribute["uuid"]})

    if instance_id and standalone_uuid_list:
        CaseModel.result_standalone_attr_module(standalone_uuid_list, instance_id=instance_id, case_id=case.id)

    for misp_object in misp_event_objects(event):
        object_payload = {
            "object-template": {
                "uuid": misp_object.get("template_uuid") or misp_object.get("uuid") or "",
                "name": misp_object["name"],
            },
            "attributes": misp_object.get("attributes", []),
        }
        created = CaseModel.create_misp_object(case.id, object_payload, user)
        imported_objects += 1

        if instance_id and misp_object.get("uuid"):
            created_attrs = created.attributes.order_by("id").all()
            object_uuid_map[created.id] = {
                "uuid": misp_object["uuid"],
                "attributes": [],
            }
            for attr_payload, created_attr in zip(misp_object.get("attributes", []), created_attrs):
                if attr_payload.get("uuid"):
                    object_uuid_map[created.id]["attributes"].append({
                        "attribute_id": created_attr.id,
                        "uuid": attr_payload["uuid"],
                    })

    if instance_id and object_uuid_map:
        CaseModel.result_misp_object_module(object_uuid_map, instance_id=instance_id, case_id=case.id)

    return {"objects": imported_objects, "attributes": imported_attributes}


def create_empty_case_from_alert_payload(alert, user, payload, title, privileged_case):
    description = build_case_description(alert, payload.get("description"))
    case_payload = {
        "title": title,
        "description": description,
        "time_required": "",
        "is_private": bool(payload.get("is_private", False)),
        "privileged_case": privileged_case,
        "ticket_id": clean_string(payload.get("ticket_id"), 255) or alert.source_ref or "",
        "tags": [],
        "clusters": [],
        "custom_tags": [],
    }

    validated = CaseValidation.verif_create_case_task(case_payload)
    if "message" in validated:
        return None, validated, 400
    return CaseModel.create_case(validated, user), None, None


def create_template_case_from_alert_payload(template_id, alert, user, payload, title, privileged_case):
    template = TemplateCommon.get_case_template(template_id)
    if not template:
        return None, {"message": "Case template not found"}, 404

    case = TemplateModel.create_case_from_template(template_id, title, user, privileged_case=privileged_case)
    if isinstance(case, dict):
        return None, case, 400

    ticket_id = clean_string(payload.get("ticket_id"), 255) or alert.source_ref or ""
    if ticket_id:
        case.ticket_id = ticket_id
    if payload.get("description"):
        summary = build_case_description(alert, payload.get("description"))
        if case.notes:
            case.notes = f"{case.notes}\n\n{summary}"
        else:
            case.notes = summary
    db.session.commit()
    return case, None, None


def create_case_from_alert(alert, user, payload=None):
    payload = payload or {}
    if not can_user_view_alert(alert, user):
        return {"message": "Permission denied"}, 403
    if alert.case_id:
        return {"message": "Alert already linked to a case", "case_id": alert.case_id}, 400

    privileged_requested = bool(payload.get("privileged_case", False))
    from flask import current_app
    if privileged_requested or current_app.config.get("ENFORCE_PRIVILEGED_CASE", False):
        from app.decorators import check_privileged_case_permission
        error = check_privileged_case_permission(user, operation="creation from alert")
        if error:
            return error

    requested_title = clean_string(payload.get("title"), 220)
    title = unique_case_title(requested_title or f"[{alert.source or 'Alert'}] {alert.title or alert.message}", alert.id)
    template_id = clean_string(payload.get("template_id"), 40)
    if template_id:
        case, error, status_code = create_template_case_from_alert_payload(
            template_id,
            alert,
            user,
            payload,
            title,
            bool(payload.get("privileged_case", False)),
        )
    else:
        case, error, status_code = create_empty_case_from_alert_payload(
            alert,
            user,
            payload,
            title,
            bool(payload.get("privileged_case", False)),
        )
    if error:
        return error, status_code

    imported = import_misp_event_to_case(alert, case, user)
    alert.case_id = case.id
    alert.review_status = "case_created"
    alert.reviewed_by_id = user.id
    alert.reviewed_at = utcnow()
    alert.is_read = True
    alert.status = "case_created"
    record_alert_action(
        alert,
        "case_created",
        user,
        details={"case_id": case.id, "imported": imported},
    )

    if alert.connector_instance_id:
        existing = Case_Connector_Instance.query.filter_by(
            case_id=case.id,
            instance_id=alert.connector_instance_id,
        ).first()
        if not existing:
            db.session.add(Case_Connector_Instance(
                case_id=case.id,
                instance_id=alert.connector_instance_id,
                identifier=alert.source_ref,
                is_updating_case=False,
            ))

    db.session.commit()
    history_ref = alert.source_ref or alert.uuid or str(alert.id)
    CommonCase.save_history(
        case.uuid,
        user,
        f"Case created from alert {history_ref} ({alert.title or alert.message or 'MISP alert'})"
    )
    flowintel_log(
        "audit", 201, "Case created from MISP alert",
        User=user.email,
        AlertId=alert.id,
        CaseId=case.id,
        CaseTitle=case.title,
        MispObjects=imported["objects"],
        MispAttributes=imported["attributes"],
    )
    return {
        "message": "Case created from MISP alert",
        "case_id": case.id,
        "alert": alert_to_json(alert, case),
        "imported": imported,
    }, 201


def alert_schema_example():
    return {
        "Event": {
            "uuid": "11111111-2222-4333-8444-555555555555",
            "id": "4242",
            "info": "Possible SSH brute-force against srv-web-01",
            "date": "2026-08-03",
            "threat_level_id": "1",
            "analysis": "0",
            "Orgc": {"name": "Wazuh"},
            "Tag": [
                {"name": "tlp:amber"},
                {"name": "source:wazuh"},
            ],
            "Attribute": [
                {
                    "uuid": "aaaaaaaa-1111-4222-8333-000000000001",
                    "type": "ip-src",
                    "category": "Network activity",
                    "value": "203.0.113.77",
                    "comment": "Remote SSH client",
                    "to_ids": True,
                },
                {
                    "uuid": "aaaaaaaa-1111-4222-8333-000000000002",
                    "type": "link",
                    "category": "External analysis",
                    "value": "https://siem.example.local/alerts/demo-5715",
                    "comment": "Source alert",
                    "to_ids": False,
                },
            ],
            "Object": [
                {
                    "uuid": "bbbbbbbb-1111-4222-8333-000000000001",
                    "name": "file",
                    "template_uuid": "688c46fb-5edb-40a3-8273-1af7923e2215",
                    "Attribute": [
                        {
                            "uuid": "cccccccc-1111-4222-8333-000000000001",
                            "type": "filename",
                            "object_relation": "filename",
                            "value": "suspicious.ps1",
                            "to_ids": False,
                        },
                        {
                            "uuid": "cccccccc-1111-4222-8333-000000000002",
                            "type": "sha256",
                            "object_relation": "sha256",
                            "value": "0" * 64,
                            "to_ids": True,
                        },
                    ],
                }
            ],
        }
    }
