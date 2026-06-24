from pymisp import MISPEvent, MISPObject, PyMISP, MISPAttribute
from pymisp.exceptions import InvalidMISPObjectAttribute, InvalidMISPObject, NewAttributeError
import time
import uuid
import conf.config_module as Config
import logging
import urllib3
urllib3.disable_warnings()

logger = logging.getLogger(__name__)

module_config = {
    "connector": "misp",
    "case_task": "case",
    "description": "Create or modify an event using misp-object present in the current case. Objects that use the MISP 'report' template are also pushed as MISP Event Reports."
}

# MISP 'report' object template UUID. Objects of this template are mirrored as
# MISP Event Reports in addition to being synced as regular MISP objects.
REPORT_TEMPLATE_UUID = "70a68471-df22-4e3f-aa1a-5a3be19f82df"

# Stable namespace used to derive deterministic UUIDs for the MISP Event Reports
# we create from report objects. Using a deterministic UUID keyed on the local
# object id allows us to update the matching EventReport on re-sync instead of
# accumulating duplicates.
_EVENT_REPORT_NAMESPACE = uuid.UUID("5a3be19f-82df-4e3f-aa1a-70a68471df22")


def bump_event_timestamp(event):
    """Set the event timestamp to the current epoch second."""
    event.timestamp = int(time.time())
    return event


def create_object(misp, object, event_id):
    misp_object = MISPObject(object["name"], standalone=False)
    attr_uuid_list = list()
    for attr in object["attributes"]:
        try:
            kwargs = {
                "to_ids": attr["ids_flag"],
                "comment": attr["comment"],
            }
            if attr.get("first_seen"):
                kwargs["first_seen"] = attr["first_seen"]
            if attr.get("last_seen"):
                kwargs["last_seen"] = attr["last_seen"]
            loc_attr = misp_object.add_attribute(
                attr["object_relation"], value=attr["value"], **kwargs
            )
        except NewAttributeError as e:
            # Value doesn't match the type expected by the object template.
            # Skip the attribute rather than aborting the entire export.
            logger.warning(
                "Skipped attribute %s (relation=%s, value=%r): %s",
                attr.get("id"), attr["object_relation"], attr["value"], e,
            )
            continue
        attr_uuid_list.append({
            "attribute_id": attr["id"],
            "uuid": loc_attr.uuid
        })         # Need to save uuid of attr for later update
    if not misp_object.attributes:
        # Every attribute was skipped — don't push an empty object to MISP.
        return misp_object, attr_uuid_list, {
            "errors": f"Object '{object['name']}' has no valid attributes after filtering"
        }
    res = misp.add_object(event_id, misp_object)
    return misp_object, attr_uuid_list, res

def manage_object_creation(misp, event, object, object_uuid_list):
    misp_object, attr_uuid_list, res = create_object(misp, object, event.id)
    if "errors" in res:
        return res, object_uuid_list
    object_uuid_list[object["id"]] = {      # Get uuid of object and attr to update later
        "attributes": attr_uuid_list,
        "uuid": misp_object.uuid
    }
    return "", object_uuid_list

def all_object_to_misp(misp, event, objects, object_uuid_list):
    details = []
    for object in objects:
        try:
            loc_object = event.get_object_by_uuid(object["uuid"])
            attr_uuid_list = list()
            for attr in object["attributes"]:
                try:
                    attribute = loc_object.get_attribute_by_uuid(attr["uuid"])
                    flag_modif = False
                    if not attr["value"] == attribute.value:
                        attribute.value = attr["value"]
                        flag_modif = True
                    if attribute.get("comment"):
                        if not attr["comment"] == attribute.comment:
                            attribute.comment = attr["comment"]
                            flag_modif = True
                    else:
                        if attr.get("comment"):
                            attribute.comment = attr["comment"]
                            flag_modif = True
                    if attribute.get("first_seen"):
                        if not attr["first_seen"] == attribute.first_seen:
                            attribute.first_seen = attr["first_seen"]
                            flag_modif = True
                    else:
                        if attr.get("first_seen"):
                            attribute.first_seen = attr["first_seen"]
                            flag_modif = True
                    if attribute.get("last_seen"):
                        if not attr["last_seen"] == attribute.last_seen:
                            attribute.last_seen = attr["last_seen"]
                            flag_modif = True
                    else:
                        if attr.get("last_seen"):
                            attribute.last_seen = attr["last_seen"]
                            flag_modif = True
                    if not attr["ids_flag"] == attribute.to_ids:
                        attribute.to_ids = attr["ids_flag"]
                        flag_modif = True

                    if flag_modif:
                        res = misp.update_attribute(attribute)
                        if "errors" in res:
                            details.append({"name": object.get("name", str(object.get("id", ""))), "status": "error", "error": str(res.get("errors", "update failed"))})
                            continue
                except (InvalidMISPObjectAttribute, NewAttributeError):
                    # Object exist but not this attribute, or value type mismatch
                    try:
                        loc_attr = loc_object.add_attribute(attr["object_relation"], value=attr["value"])
                    except NewAttributeError:
                        continue
                    attr_uuid_list.append({
                        "attribute_id": attr["id"],
                        "uuid": loc_attr.uuid
                    })
                    res = misp.update_object(loc_object)
                    if "errors" in res:
                        details.append({"name": object.get("name", str(object.get("id", ""))), "status": "error", "error": str(res.get("errors", "update failed"))})
                        continue
            if attr_uuid_list:
                object_uuid_list[object["id"]] = {
                    "attributes": attr_uuid_list,
                    "uuid": loc_object.uuid
                }
            details.append({"name": object.get("name", str(object.get("id", ""))), "status": "success", "error": None})
        except InvalidMISPObject:
            # Object not found or not exist, Create a new one
            res, object_uuid_list = manage_object_creation(misp, event, object, object_uuid_list)
            if "errors" in res:
                details.append({"name": object.get("name", str(object.get("id", ""))), "status": "error", "error": str(res.get("errors", "creation failed"))})
            else:
                details.append({"name": object.get("name", str(object.get("id", ""))), "status": "success", "error": None})
    return details, object_uuid_list


def _extract_report_fields(object):
    """Return (title, summary) from a 'report'-template object's attributes.

    Both values may be ``None`` if the corresponding attribute is missing.
    Multiple ``summary`` attributes are joined with two newlines, matching how
    MISP renders an event report (free-text markdown).
    """
    title = None
    summary_parts = []
    for attr in object.get("attributes", []) or []:
        relation = attr.get("object_relation")
        value = attr.get("value")
        if not value:
            continue
        if relation == "title" and title is None:
            title = value
        elif relation == "summary":
            summary_parts.append(value)
    summary = "\n\n".join(summary_parts) if summary_parts else None
    return title, summary


def _sync_report_event_reports(misp, event, objects):
    """Create or update a MISP EventReport for every report-template object.

    Called after the regular object sync so the event already exists on the MISP
    server. The function is best-effort: failures are logged but do not abort
    the surrounding sync, since the objects themselves have already been
    pushed successfully.
    """
    event_id = event.get("id") if event is not None else None
    if not event_id:
        logger.info("Skipping event report sync: no event id available")
        return

    report_objects = [o for o in objects if o.get("template_uuid") == REPORT_TEMPLATE_UUID]
    logger.info(
        "Event report sync: %d report-template object(s) out of %d total for event %s",
        len(report_objects), len(objects), event_id,
    )
    if not report_objects:
        return

    # Re-fetch the event so we see the up-to-date EventReport list (the
    # ``event`` object we received reflects state from before this sync run).
    try:
        fresh = misp.get_event(event_id, pythonify=True)
    except Exception as exc:
        logger.warning("Could not fetch MISP event %s to sync event reports: %s", event_id, exc)
        return
    if isinstance(fresh, dict) and fresh.get("errors"):
        logger.warning("Could not fetch MISP event %s to sync event reports: %s", event_id, fresh.get("errors"))
        return

    existing_by_uuid = {}
    for er in (getattr(fresh, "EventReport", None) or []):
        er_uuid = getattr(er, "uuid", None)
        if er_uuid:
            existing_by_uuid[er_uuid] = er

    for object in report_objects:
        title, summary = _extract_report_fields(object)
        if not title and not summary:
            logger.info("Skipping report object %s: no title and no summary", object.get("id"))
            continue

        target_uuid = str(uuid.uuid5(
            _EVENT_REPORT_NAMESPACE,
            f"flowintel-report-object-{object.get('id', object.get('uuid', ''))}"
        ))
        name = title or f"Report #{object.get('id', '')}"
        content = summary or ""

        if target_uuid in existing_by_uuid:
            er = existing_by_uuid[target_uuid]
            er.name = name
            er.content = content
            try:
                res = misp.update_event_report(er, event_id)
                logger.info("Updated MISP event report %s on event %s: %s", target_uuid, event_id, _summarize_misp_result(res))
            except Exception as exc:
                logger.warning("Could not update MISP event report %s: %s", target_uuid, exc)
        else:
            payload = {
                "uuid": target_uuid,
                "event_id": event_id,
                "name": name,
                "content": content,
            }
            try:
                res = misp.add_event_report(event_id, payload)
                logger.info("Created MISP event report %s on event %s: %s", target_uuid, event_id, _summarize_misp_result(res))
            except Exception as exc:
                logger.warning("Could not create MISP event report for object %s: %s", object.get("id"), exc)


def _summarize_misp_result(res):
    """Best-effort short string representation of a PyMISP add/update result."""
    if res is None:
        return "None"
    if isinstance(res, dict):
        if "errors" in res:
            return f"errors={res['errors']!r}"
        return "ok"
    return type(res).__name__


def handler(instance, case, user, case_model=None, db_session=None, payload=None):
    """
    instance: name, url, description, uuid, connector_id, type, api_key, identifier

    case: id, uuid, title, description, creation_date, last_modif, status_id, status, completed, owner_org_id
          org_name, org_uuid, recurring_type, deadline, finish_date, tasks, clusters, connectors

    case["tasks"]: id, uuid, title, description, url, notes, creation_date, last_modif, case_id, status_id, status,
                   completed, deadline, finish_date, tags, clusters, connectors

    user: id, first_name, last_name, email, role_id, password_hash, api_key, org_id

    payload: optional dict; if payload["selected_objects"] is a list of local object IDs, only those are synced
    """
    try:
        misp = PyMISP(instance["url"], instance["api_key"], ssl=False, timeout=20)
    except Exception:
        return {"message": "Error connecting to MISP"}
    flag = False
    object_uuid_list = {}

    # Optional filter: only send objects whose id is in selected_objects
    objects = case["objects"]
    if payload and isinstance(payload.get("selected_objects"), list):
        selected_ids = set(str(i) for i in payload["selected_objects"])
        objects = [o for o in objects if str(o.get("object_id", o.get("id", ""))) in selected_ids]

    details = []
    if "identifier" in instance and instance["identifier"]:
        event = misp.get_event(instance["identifier"], pythonify=True)
        if 'errors' in event:
            flag = True
        else:
            details, object_uuid_list = all_object_to_misp(misp, event, objects, object_uuid_list)

    ## No identifier for this connector or the event doesn't exist anymore
    else: 
        flag = True

    ## Event doesn't exist
    if flag:
        event = MISPEvent()
        event.uuid = str(uuid.uuid4())
        event.info = f"Case: {case['title']}"  # Required
        event = misp.add_event(event, pythonify=True)

        for object in objects:
            res, object_uuid_list = manage_object_creation(misp, event, object, object_uuid_list)
            if "errors" in res:
                details.append({"name": object.get("name", ""), "status": "error", "error": str(res.get("errors", "creation failed"))})
            else:
                details.append({"name": object.get("name", ""), "status": "success", "error": None})

    if "errors" in event:
        return {"message": event.get("errors", "Error with MISP event")}

    # Mirror any 'report'-template objects as MISP EventReports on the same event.
    try:
        _sync_report_event_reports(misp, event, objects)
    except Exception as exc:
        logger.warning("Could not mirror report objects as MISP event reports: %s", exc)

    # Let the module handle its own DB storage
    if case_model and object_uuid_list:
        case_model.result_misp_object_module(object_uuid_list, instance["id"], case["id"])

    # Handle standalone attributes
    standalone_attr_uuid_list = []
    standalone_attrs = case.get("standalone_attributes", [])
    if payload and isinstance(payload.get("selected_standalone_attrs"), list):
        selected_sa_ids = set(str(i) for i in payload["selected_standalone_attrs"])
        standalone_attrs = [a for a in standalone_attrs if str(a.get("id", "")) in selected_sa_ids]

    for sa in standalone_attrs:
        try:
            misp_attr = MISPAttribute()
            misp_attr.type = sa["type"]
            misp_attr.value = sa["value"]
            misp_attr.comment = sa.get("comment") or ""
            misp_attr.to_ids = sa.get("ids_flag") or False
            misp_attr.disable_correlation = sa.get("disable_correlation") or False
            if sa.get("first_seen"):
                misp_attr.first_seen = sa["first_seen"]
            if sa.get("last_seen"):
                misp_attr.last_seen = sa["last_seen"]

            if sa.get("uuid"):
                # Try to find and update existing attribute
                existing = None
                for ev_attr in event.attributes:
                    if ev_attr.uuid == sa["uuid"]:
                        existing = ev_attr
                        break
                if existing:
                    flag_sa_modif = False
                    if existing.value != sa["value"]:
                        existing.value = sa["value"]
                        flag_sa_modif = True
                    if existing.comment != (sa.get("comment") or ""):
                        existing.comment = sa.get("comment") or ""
                        flag_sa_modif = True
                    if existing.to_ids != (sa.get("ids_flag") or False):
                        existing.to_ids = sa.get("ids_flag") or False
                        flag_sa_modif = True
                    if flag_sa_modif:
                        misp.update_attribute(existing)
                    standalone_attr_uuid_list.append({"attribute_id": sa["id"], "uuid": sa["uuid"]})
                    details.append({"name": f"attr:{sa['type']}", "status": "success", "error": None})
                    continue
            # Create new attribute on event
            res_attr = misp.add_attribute(event.id, misp_attr, pythonify=True)
            if "errors" in res_attr:
                details.append({"name": f"attr:{sa['type']}", "status": "error", "error": str(res_attr.get("errors", ""))})
                continue
            standalone_attr_uuid_list.append({"attribute_id": sa["id"], "uuid": res_attr.uuid})
            details.append({"name": f"attr:{sa['type']}", "status": "success", "error": None})
        except Exception as e:
            details.append({"name": f"attr:{sa.get('type','?')}", "status": "error", "error": str(e)})

    if case_model and standalone_attr_uuid_list:
        case_model.result_standalone_attr_module(standalone_attr_uuid_list, instance["id"], case["id"])

    synced = sum(1 for d in details if d["status"] == "success")
    failed = sum(1 for d in details if d["status"] == "error")
    return {
        "identifier": event.get("uuid"),
        "synced_count": synced,
        "failed_count": failed,
        "details": details
    }

def introspection():
    return module_config
