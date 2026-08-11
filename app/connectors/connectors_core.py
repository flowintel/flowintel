import datetime
import os
from .. import db
from ..db_class.db import Case, Case_Connector_Instance, Connector_Icon, Icon_File, Connector, Connector_Instance, User, User_Connector_Instance, Connector_Sync_Log, Case_Misp_Sync_Schedule, Case_Misp_Sync_Conflict, DATETIME_FORMAT_FULL
import uuid
from werkzeug.utils import secure_filename

ICON_FOLDER = os.path.join(os.getcwd(), "app", "static", "icons")
MISP_SYNC_DIRECTIONS = {"send", "receive"}
MISP_SYNC_INTERVALS = {"manual", "daily", "weekly", "monthly"}
MISP_SYNC_CONFLICT_STRATEGIES = {"ask", "prefer_flowintel", "prefer_misp"}
MISP_SYNC_RESOLUTIONS = {"prefer_flowintel", "prefer_misp", "skip"}


def as_utc_datetime(value):
    """Return a timezone-aware UTC datetime for DB/API comparisons."""
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


def format_misp_sync_datetime(value):
    loc_value = as_utc_datetime(value)
    return loc_value.strftime(DATETIME_FORMAT_FULL) if loc_value else None


def _misp_read_event_value(event, name):
    value = getattr(event, name, None)
    if value is None and hasattr(event, "get"):
        try:
            value = event.get(name)
        except Exception:
            value = None
    return value


def _misp_get_event_pythonified(loc_instance, api_key, event_identifier):
    if not event_identifier:
        return None, None
    try:
        from pymisp import PyMISP
        misp = PyMISP(loc_instance.url, api_key, ssl=False, timeout=20)
        event = misp.get_event(event_identifier, pythonify=True)
        if isinstance(event, dict) and "errors" in event:
            return None, {"message": "Event not found on MISP instance", "toast_class": "danger-subtle", "status": 404}
        return event, None
    except Exception as e:
        return None, {"message": f"Error connecting to MISP: {e}", "toast_class": "danger-subtle", "status": 500}


def _stringify_misp_conflict_value(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime.datetime):
        return format_misp_sync_datetime(value)
    return str(value)


def _remote_attr_to_snapshot(attr):
    return {
        "uuid": getattr(attr, "uuid", None),
        "value": _stringify_misp_conflict_value(getattr(attr, "value", None)),
        "type": _stringify_misp_conflict_value(getattr(attr, "type", None)),
        "object_relation": _stringify_misp_conflict_value(getattr(attr, "object_relation", None)),
        "comment": _stringify_misp_conflict_value(getattr(attr, "comment", None)),
        "first_seen": _stringify_misp_conflict_value(getattr(attr, "first_seen", None)),
        "last_seen": _stringify_misp_conflict_value(getattr(attr, "last_seen", None)),
        "ids_flag": _stringify_misp_conflict_value(getattr(attr, "to_ids", None)),
    }


def build_misp_event_conflict_details(local_case_snapshot, remote_event):
    """Compare mapped Flowintel values with the current MISP event and return side-specific diffs."""
    local_case_snapshot = local_case_snapshot or {}
    remote_event = remote_event or {}

    remote_objects = {getattr(obj, "uuid", None): obj for obj in getattr(remote_event, "objects", []) if getattr(obj, "uuid", None)}
    remote_attrs = {}
    for obj in getattr(remote_event, "objects", []):
        for attr in getattr(obj, "attributes", []) or []:
            if getattr(attr, "uuid", None):
                remote_attrs[attr.uuid] = _remote_attr_to_snapshot(attr)
    for attr in getattr(remote_event, "attributes", []) or []:
        if getattr(attr, "object_id", None) and int(getattr(attr, "object_id", 0) or 0) != 0:
            continue
        if getattr(attr, "uuid", None):
            remote_attrs[attr.uuid] = _remote_attr_to_snapshot(attr)

    local_details = []
    remote_details = []

    def add_diff(label, field, local_value, remote_value, ref):
        target_kind = "standalone_attribute" if str(label).startswith("Standalone /") else "attribute"
        local_text = _stringify_misp_conflict_value(local_value)
        remote_text = _stringify_misp_conflict_value(remote_value)
        if local_text == remote_text or (not local_text and not remote_text):
            return False
        local_details.append({
            "token": f"{ref}:{field}",
            "label": label,
            "field": field,
            "ref": ref,
            "target_kind": target_kind,
            "value": local_text or "(empty)",
            "other_value": remote_text or "(empty)"
        })
        remote_details.append({
            "token": f"{ref}:{field}",
            "label": label,
            "field": field,
            "ref": ref,
            "target_kind": target_kind,
            "value": remote_text or "(empty)",
            "other_value": local_text or "(empty)"
        })
        return True

    for obj in local_case_snapshot.get("objects", []) or []:
        remote_obj = remote_objects.get(obj.get("uuid")) if obj.get("uuid") else None
        if remote_obj:
            add_diff(
                obj.get("name") or "Object",
                "object_name",
                obj.get("name"),
                getattr(remote_obj, "name", None),
                obj.get("uuid")
            )
        for attr in obj.get("attributes", []) or []:
            remote_attr = remote_attrs.get(attr.get("uuid")) if attr.get("uuid") else None
            if not remote_attr:
                continue
            attr_label = f"{obj.get('name') or 'Object'} / {attr.get('object_relation') or attr.get('type') or 'attribute'}"
            attr_ref = attr.get("uuid") or obj.get("uuid")
            for field in ["value", "type", "object_relation", "comment", "first_seen", "last_seen", "ids_flag"]:
                added = add_diff(attr_label, field, attr.get(field), remote_attr.get(field), attr_ref)
                if added:
                    local_details[-1]["local_object_id"] = obj.get("id") or obj.get("object_id")
                    local_details[-1]["local_attribute_id"] = attr.get("id")
                    local_details[-1]["remote_object_uuid"] = obj.get("uuid")
                    local_details[-1]["remote_attribute_uuid"] = attr.get("uuid")
                    remote_details[-1]["local_object_id"] = obj.get("id") or obj.get("object_id")
                    remote_details[-1]["local_attribute_id"] = attr.get("id")
                    remote_details[-1]["remote_object_uuid"] = obj.get("uuid")
                    remote_details[-1]["remote_attribute_uuid"] = attr.get("uuid")

    for attr in local_case_snapshot.get("standalone_attributes", []) or []:
        remote_attr = remote_attrs.get(attr.get("uuid")) if attr.get("uuid") else None
        if not remote_attr:
            continue
        attr_label = f"Standalone / {attr.get('type') or 'attribute'}"
        attr_ref = attr.get("uuid")
        for field in ["value", "type", "comment", "first_seen", "last_seen", "ids_flag"]:
            added = add_diff(attr_label, field, attr.get(field), remote_attr.get(field), attr_ref)
            if added:
                local_details[-1]["local_attribute_id"] = attr.get("id")
                local_details[-1]["remote_attribute_uuid"] = attr.get("uuid")
                remote_details[-1]["local_attribute_id"] = attr.get("id")
                remote_details[-1]["remote_attribute_uuid"] = attr.get("uuid")

    return {
        "local": local_details[:25],
        "remote": remote_details[:25]
    }


## Connectors
def get_connectors():
    """Return all connectors"""
    return Connector.query.all()

def get_connector(cid):
    """Return a connector"""
    return Connector.query.get(cid)

def get_instances(cid):
    """Return all instances for a connector"""
    return Connector_Instance.query.filter_by(connector_id=cid).all()

def get_instance(iid):
    """Return an instance of a connector"""
    return Connector_Instance.query.get(iid)


def get_instance_sharing_scope(instance):
    """Return the visibility scope for a connector instance."""
    if getattr(instance, "sharing_scope", None) in {"personal", "org", "global"}:
        return instance.sharing_scope
    if instance.shared_org_id:
        return "org"
    if instance.global_api_key:
        return "global"
    return "personal"


def is_instance_visible_to_user(instance, user):
    """Return True if a connector instance is visible to the user."""
    if user.is_admin():
        return True

    scope = get_instance_sharing_scope(instance)
    if scope == "global":
        return True
    if scope == "org":
        return instance.shared_org_id == user.org_id
    return bool(get_user_instance_both(user_id=user.id, instance_id=instance.id))


def can_user_manage_instance(instance, user):
    """Return True if a user can edit/delete the connector instance."""
    scope = get_instance_sharing_scope(instance)
    if scope == "org":
        return user.is_org_admin() and user.is_misp_editor() and instance.shared_org_id == user.org_id
    if user.is_admin():
        return True
    if scope == "global":
        return user.is_admin()
    return bool(get_user_instance_both(user_id=user.id, instance_id=instance.id))


def normalize_instance_sharing_scope(form_dict, user):
    """Normalize legacy and current sharing scope inputs."""
    scope = form_dict.get("sharing_scope")
    if scope in {"personal", "org", "global"}:
        return scope

    if form_dict.get("is_global_connector"):
        if user.is_admin():
            return "global"
        if user.is_org_admin():
            return "org"
    return "personal"


def can_user_use_sharing_scope(user, sharing_scope):
    """Return True if the user can create or edit an instance with this scope."""
    if sharing_scope == "global":
        return user.is_admin()
    if sharing_scope == "org":
        return user.is_admin() or (user.is_org_admin() and user.is_misp_editor())
    return user.is_admin() or user.is_misp_editor()


def instance_has_links(instance_id):
    """Return True if instance is linked to a case or task."""
    case_link = Case_Connector_Instance.query.filter_by(instance_id=instance_id).first()
    if case_link:
        return True
    return False

def get_user_instance_by_instance(instance_id):
    """Return a user instance by instance id"""
    return User_Connector_Instance.query.filter_by(instance_id=instance_id).first()

def get_user_instance_by_user(user_id):
    """Return a user instance by user id"""
    return User_Connector_Instance.query.filter_by(user_id=user_id).all()

def get_user_instance_both(user_id, instance_id):
    return User_Connector_Instance.query.filter_by(user_id=user_id, instance_id=instance_id).all()

def get_connector_by_name(name):
    """Return a connector by its name"""
    return Connector.query.where(Connector.name.like(name)).first()

def get_icons():
    """Return all icons"""
    return Connector_Icon.query.all()


def connector_has_instances(connector_id):
    """Return True if connector has any instances."""
    return Connector_Instance.query.filter_by(connector_id=connector_id).count() > 0


def connector_has_linked_instances(connector_id):
    """Return True if any instance is linked to a case or task."""
    case_link = db.session.query(Case_Connector_Instance.id).join(
        Connector_Instance,
        Case_Connector_Instance.instance_id == Connector_Instance.id
    ).filter(Connector_Instance.connector_id == connector_id).first()
    if case_link:
        return True

    return False


def get_connectors_flags(connector_ids):
    """Return sets of connector ids with instances and with linked instances."""
    if not connector_ids:
        return set(), set()

    connectors_with_instances = {
        cid for (cid,) in db.session.query(Connector_Instance.connector_id)
        .filter(Connector_Instance.connector_id.in_(connector_ids))
        .distinct()
        .all()
    }

    case_linked = {
        cid for (cid,) in db.session.query(Connector_Instance.connector_id)
        .join(Case_Connector_Instance, Case_Connector_Instance.instance_id == Connector_Instance.id)
        .filter(Connector_Instance.connector_id.in_(connector_ids))
        .distinct()
        .all()
    }
    connectors_with_links = case_linked
    return connectors_with_instances, connectors_with_links


def get_connectors_page(page, name=None):
    """Return connectors by page, optionally filtered by case-insensitive partial name match.

    Returns a list of connector dicts (same shape as `/get_connectors`).
    """
    nb = 25
    connectors = get_connectors()
    connector_ids = [connector.id for connector in connectors]
    connectors_with_instances, connectors_with_links = get_connectors_flags(connector_ids)

    connectors_list = []
    for connector in connectors:
        connector_loc = connector.to_json()
        icon_loc = get_icon(connector.icon_id)
        if icon_loc:
            icon_file = get_icon_file(icon_loc.file_icon_id)
            connector_loc["icon_filename"] = icon_file.name
            connector_loc["icon_uuid"] = icon_file.uuid
        else:
            connector_loc["icon_filename"] = None
            connector_loc["icon_uuid"] = None
        connector_loc["has_instances"] = connector.id in connectors_with_instances
        connector_loc["has_linked_instances"] = connector.id in connectors_with_links
        connectors_list.append(connector_loc)

    if name:
        name_l = name.lower()
        connectors_list = [c for c in connectors_list if name_l in c.get('name','').lower()]

    to_give = nb * page
    if to_give > len(connectors_list):
        limit = len(connectors_list)
    else:
        limit = to_give
    to_start = limit - nb

    out_list = list()
    for i in range(max(0, to_start), limit):
        out_list.append(connectors_list[i])
    return out_list


def get_nb_page_connectors(name=None):
    connectors_list = []
    for connector in get_connectors():
        connectors_list.append(connector.to_json())
    if name:
        name_l = name.lower()
        connectors_list = [c for c in connectors_list if name_l in c.get('name','').lower()]
    return int(len(connectors_list) / 25) + 1

def get_cases_for_instance(iid, page=1, per_page=10, current_user=None):
    """Return paginated cases linked to a connector instance.

    For non-admin users, private cases they are not a member of are excluded
    from the paginated list.  A separate ``private_count`` is returned so the
    caller can inform the user that additional private cases exist without
    revealing their titles.
    """
    from ..case.common_core import get_present_in_case

    all_cases = (
        db.session.query(Case)
        .join(Case_Connector_Instance, Case_Connector_Instance.case_id == Case.id)
        .filter(Case_Connector_Instance.instance_id == iid)
        .order_by(Case.last_modif.desc())
        .all()
    )

    visible = []
    private_count = 0
    for c in all_cases:
        if c.is_private and current_user is not None and not current_user.is_admin():
            if not get_present_in_case(c.id, current_user):
                private_count += 1
                continue
        visible.append(c)

    total = len(visible)
    nb_pages = max(1, (total + per_page - 1) // per_page)
    page_cases = visible[(page - 1) * per_page: page * per_page]
    return [
        {"id": c.id, "title": c.title, "uuid": c.uuid, "completed": c.completed, "is_private": c.is_private}
        for c in page_cases
    ], total, nb_pages, private_count


def get_icon(iid):
    """Return an icon"""
    return Connector_Icon.query.get(iid)

def get_default_icon():
    """Return the default icon"""
    return Connector_Icon.query.filter_by(name="default").first()

def get_icon_file(file_id):
    """Return a file"""
    return Icon_File.query.get(file_id)


def get_icons_page(page, name=None):
    """Return icons by page, optionally filtered by partial case-insensitive name."""
    nb = 25
    icons_list = []
    for icon in get_icons():
        icon_loc = icon.to_json()
        icon_file = get_icon_file(icon.file_icon_id)
        icon_loc["icon_filename"] = icon_file.name
        icon_loc["icon_uuid"] = icon_file.uuid
        icons_list.append(icon_loc)

    if name:
        name_l = name.lower()
        icons_list = [i for i in icons_list if name_l in i.get('name','').lower()]

    to_give = nb * page
    if to_give > len(icons_list):
        limit = len(icons_list)
    else:
        limit = to_give
    to_start = limit - nb

    out_list = list()
    for i in range(max(0, to_start), limit):
        out_list.append(icons_list[i])
    return out_list


def get_nb_page_icons(name=None):
    icons_list = [icon.to_json() for icon in get_icons()]
    if name:
        name_l = name.lower()
        icons_list = [i for i in icons_list if name_l in i.get('name','').lower()]
    return int(len(icons_list) / 25) + 1


def add_connector_core(form_dict):
    if not form_dict["icon_select"] or form_dict["icon_select"] == "None":
        icon_id = get_default_icon().id
    else:
        icon_id = form_dict["icon_select"]

    connector = Connector(
        name=form_dict["name"],
        description=form_dict["description"],
        uuid=str(uuid.uuid4()),
        icon_id=icon_id
    )
    db.session.add(connector)
    db.session.commit()
    return connector

def add_connector_instance_core(cid, form_dict, user_id):
    user = User.query.get(user_id)
    sharing_scope = normalize_instance_sharing_scope(form_dict, user)
    global_api_key = form_dict["api_key"] if sharing_scope in {"org", "global"} else None
    shared_org_id = user.org_id if sharing_scope == "org" else None

    connector = Connector_Instance(
        name=form_dict["name"],
        description=form_dict["description"],
        url=form_dict["url"],
        uuid=str(uuid.uuid4()),
        connector_id=cid,
        global_api_key=global_api_key,
        shared_org_id=shared_org_id,
        sharing_scope=sharing_scope
    )
    db.session.add(connector)
    db.session.commit()

    if sharing_scope == "personal":
        user_connector = User_Connector_Instance(
            user_id=user_id,
            instance_id=connector.id,
            api_key=form_dict["api_key"]
        )
        db.session.add(user_connector)
        db.session.commit()
    return connector


def add_icon_file(icon):
    uuid_loc = str(uuid.uuid4())
    try:
        with open(os.path.join(ICON_FOLDER, uuid_loc), "wb") as write_icon:
            write_icon.write(icon.data.read())
    except Exception as e:
        print(e)
        return False
    
    icon_file = Icon_File(
        name = secure_filename(icon.data.filename),
        uuid = uuid_loc
    )
    db.session.add(icon_file)
    db.session.commit()
    return icon_file.id

def add_icon_core(form_dict, icon):
    icon_file_id = add_icon_file(icon)
    
    icon = Connector_Icon(
        name = form_dict["name"],
        description = form_dict["description"],
        uuid = str(uuid.uuid4()),
        file_icon_id = icon_file_id
    )
    db.session.add(icon)
    db.session.commit()

    return True


def edit_connector_core(cid, form_dict):
    connector_db = get_connector(cid)
    if connector_db:
        if not form_dict["icon_select"] or form_dict["icon_select"] == "None":
            icon_id = get_default_icon().id
        else:
            icon_id = form_dict["icon_select"]
        connector_db.name = form_dict["name"]
        connector_db.description = form_dict["description"]
        connector_db.icon_id = icon_id

        db.session.add(connector_db)
        db.session.commit()
        return True
    return False

def edit_connector_instance_core(iid, form_dict):
    instance_db = get_instance(iid)
    if instance_db:
        user = User.query.get(form_dict["acting_user_id"])
        sharing_scope = normalize_instance_sharing_scope(form_dict, user)
        instance_db.name = form_dict["name"]
        instance_db.url = form_dict["url"]
        instance_db.description = form_dict["description"]
        instance_db.sharing_scope = sharing_scope
        if sharing_scope == "global":
            instance_db.shared_org_id = None
            if form_dict["api_key"]:
                instance_db.global_api_key = form_dict["api_key"]
        elif sharing_scope == "org":
            instance_db.shared_org_id = user.org_id
            if form_dict["api_key"]:
                instance_db.global_api_key = form_dict["api_key"]
        else:
            instance_db.shared_org_id = None
            instance_db.global_api_key = None
            user_instance = get_user_instance_by_instance(iid)
            if not user_instance:
                user_instance = User_Connector_Instance(
                    user_id=user.id,
                    instance_id=iid,
                    api_key=""
                )
            if form_dict["api_key"]:
                user_instance.api_key = form_dict["api_key"]
            db.session.add(user_instance)
            db.session.commit()

        if sharing_scope in {"org", "global"}:
            User_Connector_Instance.query.filter_by(instance_id=iid).delete()

        db.session.add(instance_db)
        db.session.commit()
        return True
    return False


def edit_icon_core(iid, form_dict, icon):
    icon_db = get_icon(iid)
    if icon_db:
        if icon.data:
            if not delete_icon_file(icon_db.file_icon_id):
                return False
            icon_db.file_icon_id = add_icon_file(icon)

        icon_db.name = form_dict["name"]
        icon_db.description = form_dict["description"]
        db.session.commit()
        return True
    return False


def delete_connector_core(cid):
    connector = get_connector(cid)
    for instance in connector.instances:
        delete_connector_instance_core(instance.id)
    db.session.delete(connector)
    db.session.commit()
    return True


def delete_connector_instance_core(iid):
    User_Connector_Instance.query.filter_by(instance_id=iid).delete()
    for ci in Case_Connector_Instance.query.filter_by(instance_id=iid).all():
        Connector_Sync_Log.query.filter_by(case_connector_instance_id=ci.id).delete()
    Case_Connector_Instance.query.filter_by(instance_id=iid).delete()

    instance = get_instance(iid)
    db.session.delete(instance)
    db.session.commit()
    return True


def delete_icon_file(file_icon_id):
    """Delete an icon from disk from table Icon_File"""
    icon_file = get_icon_file(file_icon_id)

    try:
        os.remove(os.path.join(ICON_FOLDER, icon_file.uuid))
    except OSError:
        return False
    
    db.session.delete(icon_file)
    db.session.commit()
    return True


def delete_icon_core(iid):
    """Delete the icon from the DB"""
    icon = get_icon(iid)
    if icon:
        if not delete_icon_file(icon.file_icon_id):
            return False

        default_icon = get_default_icon()
        for connector in Connector.query.filter_by(icon_id=icon.id).all():
            connector.icon_id = default_icon.id
            db.session.commit()

        db.session.delete(icon)
        db.session.commit()
        
        return True
    else:
        return False


####################
# MISP Core helpers #
####################

def misp_get_event_objects(loc_instance, api_key, event_identifier):
    """Fetch objects from a remote MISP event and return a preview list.

    Returns a tuple (result_dict, error_dict).  On success error_dict is None.
    result_dict has keys "objects" and "standalone_attributes".
    """
    try:
        from pymisp import PyMISP
        misp = PyMISP(loc_instance.url, api_key, ssl=False, timeout=20)
        event = misp.get_event(event_identifier, pythonify=True)
        if isinstance(event, dict) and "errors" in event:
            return None, {"message": "Event not found on MISP instance", "toast_class": "danger-subtle", "status": 404}
        objects = []
        for obj in event.objects:
            attrs = [{"relation": a.object_relation, "type": a.type, "value": str(a.value)[:80]}
                     for a in obj.attributes[:5]]
            objects.append({
                "uuid": obj.uuid,
                "name": obj.name,
                "attributes_preview": attrs,
                "attribute_count": len(obj.attributes)
            })
        standalone_attributes = []
        for ev_attr in getattr(event, 'attributes', []):
            if ev_attr.object_id and int(ev_attr.object_id) != 0:
                continue
            standalone_attributes.append({
                "uuid": ev_attr.uuid,
                "type": ev_attr.type,
                "value": str(ev_attr.value)[:80],
                "comment": getattr(ev_attr, 'comment', '') or ""
            })
        return {"objects": objects, "standalone_attributes": standalone_attributes}, None
    except Exception as e:
        return None, {"message": f"Error connecting to MISP: {e}", "toast_class": "danger-subtle", "status": 500}


def misp_get_event_reports(loc_instance, api_key, event_identifier):
    """Fetch event reports from a remote MISP event.

    Returns a tuple (note_content_str, error_dict).  On success error_dict is None.
    """
    try:
        from pymisp import PyMISP
        misp = PyMISP(loc_instance.url, api_key, ssl=False, timeout=20)
        event = misp.get_event(event_identifier, pythonify=True)
        if isinstance(event, dict) and "errors" in event:
            return None, {"message": "Event not found on MISP instance", "toast_class": "danger-subtle", "status": 404}
        reports = getattr(event, "event_reports", []) or []
        if not reports:
            return None, {"message": "No event reports found in this MISP event", "toast_class": "warning-subtle", "status": 404}
        now_str = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        parts = [f"# Imported from MISP: {loc_instance.name} \u2014 {now_str}\n"]
        for rpt in reports:
            name = getattr(rpt, "name", "Report")
            content = getattr(rpt, "content", "") or ""
            parts.append(f"## {name}\n\n{content}")
        return "\n\n---\n\n".join(parts), None
    except Exception as e:
        return None, {"message": f"Error importing event report: {e}", "toast_class": "danger-subtle", "status": 500}


def misp_get_event_metadata(loc_instance, api_key, event_identifier):
    """Fetch lightweight metadata for a remote MISP event."""
    if not event_identifier:
        return None, None
    try:
        event, error = _misp_get_event_pythonified(loc_instance, api_key, event_identifier)
        if error or not event:
            return None, error
        timestamp = _misp_read_event_value(event, "timestamp")
        timestamp_at = as_utc_datetime(timestamp)
        return {
            "id": _misp_read_event_value(event, "id"),
            "uuid": _misp_read_event_value(event, "uuid"),
            "info": _misp_read_event_value(event, "info"),
            "timestamp": str(timestamp) if timestamp is not None else None,
            "timestamp_at": format_misp_sync_datetime(timestamp_at),
            "published": bool(_misp_read_event_value(event, "published")),
        }, None
    except Exception as e:
        return None, {"message": f"Error connecting to MISP: {e}", "toast_class": "danger-subtle", "status": 500}


def get_connector_sync_logs(case_id, case_connector_instance_id, limit=50):
    """Return recent sync logs for a connector instance as a list of dicts."""
    logs = Connector_Sync_Log.query.filter_by(
        case_id=int(case_id), case_connector_instance_id=int(case_connector_instance_id)
    ).order_by(Connector_Sync_Log.timestamp.desc()).limit(limit).all()
    return [log.to_json() for log in logs]


MISP_SYNC_RUN_HOUR_UTC = 2
MISP_SYNC_RUN_MINUTE_UTC = 0


def calculate_misp_sync_next_run(interval, from_time=None):
    """Return the next UTC run date for a supported interval."""
    if interval == "manual":
        return None
    base = from_time or datetime.datetime.now(tz=datetime.timezone.utc)
    base = as_utc_datetime(base) or datetime.datetime.now(tz=datetime.timezone.utc)
    if interval == "daily":
        target = base + datetime.timedelta(days=1)
    elif interval == "weekly":
        target = base + datetime.timedelta(weeks=1)
    elif interval == "monthly":
        target = base + datetime.timedelta(days=30)
    else:
        return None
    return target.replace(
        hour=MISP_SYNC_RUN_HOUR_UTC,
        minute=MISP_SYNC_RUN_MINUTE_UTC,
        second=0,
        microsecond=0
    )


def default_misp_sync_schedule(case_id, case_connector_instance_id, direction):
    return {
        "id": None,
        "case_id": int(case_id),
        "case_connector_instance_id": int(case_connector_instance_id),
        "direction": direction,
        "enabled": False,
        "interval": "manual",
        "on_change": False,
        "module_name": "receive_misp_object" if direction == "receive" else "misp_object_event",
        "payload": {},
        "conflict_strategy": "ask",
        "last_run_at": None,
        "next_run_at": None,
        "last_seen_case_modif": None,
        "created_by_id": None,
        "updated_by_id": None,
        "created_at": None,
        "updated_at": None
    }


def sanitize_misp_sync_schedule(schedule):
    """Normalize legacy schedule values so removed merge options stay hidden."""
    loc_schedule = dict(schedule or {})
    if loc_schedule.get("conflict_strategy") == "merge":
        loc_schedule["conflict_strategy"] = "ask"
    loc_schedule.pop("auto_merge", None)
    return loc_schedule


def get_misp_sync_schedules(case_id, case_connector_instance_id):
    schedules = Case_Misp_Sync_Schedule.query.filter_by(
        case_id=int(case_id),
        case_connector_instance_id=int(case_connector_instance_id)
    ).all()
    by_direction = {schedule.direction: sanitize_misp_sync_schedule(schedule.to_json()) for schedule in schedules}
    for direction in sorted(MISP_SYNC_DIRECTIONS):
        by_direction.setdefault(direction, sanitize_misp_sync_schedule(default_misp_sync_schedule(case_id, case_connector_instance_id, direction)))
    return by_direction


def has_enabled_misp_sync_automation(case_id, case_connector_instance_id):
    return Case_Misp_Sync_Schedule.query.filter_by(
        case_id=int(case_id),
        case_connector_instance_id=int(case_connector_instance_id),
        enabled=True
    ).first() is not None


def normalize_misp_sync_schedule_payload(data):
    data = data or {}
    direction = data.get("direction")
    if direction not in MISP_SYNC_DIRECTIONS:
        return None, "Invalid sync direction"

    interval = data.get("interval") or "manual"
    if interval not in MISP_SYNC_INTERVALS:
        return None, "Invalid sync interval"

    conflict_strategy = data.get("conflict_strategy") or "ask"
    if conflict_strategy == "merge":
        conflict_strategy = "ask"
    if conflict_strategy not in MISP_SYNC_CONFLICT_STRATEGIES:
        return None, "Invalid conflict strategy"

    enabled = bool(data.get("enabled", False))
    on_change = bool(data.get("on_change", False))
    if enabled and interval == "manual" and not on_change:
        return None, "Enable a frequency or modification trigger before activating automation"

    module_name = (data.get("module_name") or ("receive_misp_object" if direction == "receive" else "misp_object_event")).strip()
    if not module_name:
        return None, "Module is required"

    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    return {
        "direction": direction,
        "enabled": enabled,
        "interval": interval,
        "on_change": on_change,
        "module_name": module_name[:128],
        "payload": payload,
        "conflict_strategy": conflict_strategy
    }, None


def upsert_misp_sync_schedule(case_id, case_connector_instance_id, data, user):
    normalized, error = normalize_misp_sync_schedule_payload(data)
    if error:
        return None, error

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    schedule = Case_Misp_Sync_Schedule.query.filter_by(
        case_id=int(case_id),
        case_connector_instance_id=int(case_connector_instance_id),
        direction=normalized["direction"]
    ).first()
    if not schedule:
        schedule = Case_Misp_Sync_Schedule(
            case_id=int(case_id),
            case_connector_instance_id=int(case_connector_instance_id),
            direction=normalized["direction"],
            created_by_id=user.id if user else None,
            created_at=now
        )
        db.session.add(schedule)

    old_interval = schedule.interval
    old_enabled = schedule.enabled
    schedule.enabled = normalized["enabled"]
    schedule.interval = normalized["interval"]
    schedule.on_change = normalized["on_change"]
    schedule.module_name = normalized["module_name"]
    schedule.payload = normalized["payload"]
    schedule.conflict_strategy = normalized["conflict_strategy"]
    schedule.updated_by_id = user.id if user else None
    schedule.updated_at = now

    if not schedule.enabled:
        schedule.next_run_at = None
    elif schedule.interval != "manual" and (old_interval != schedule.interval or not old_enabled or not schedule.next_run_at):
        schedule.next_run_at = calculate_misp_sync_next_run(schedule.interval, now)

    db.session.commit()
    return schedule, None


def mark_misp_sync_schedule_run(case_id, case_connector_instance_id, direction, case_last_modif=None, run_at=None):
    schedule = Case_Misp_Sync_Schedule.query.filter_by(
        case_id=int(case_id),
        case_connector_instance_id=int(case_connector_instance_id),
        direction=direction
    ).first()
    if not schedule:
        return None
    run_at = run_at or datetime.datetime.now(tz=datetime.timezone.utc)
    schedule.last_run_at = run_at
    schedule.last_seen_case_modif = case_last_modif
    schedule.next_run_at = calculate_misp_sync_next_run(schedule.interval, run_at) if schedule.enabled else None
    return schedule


def get_due_misp_sync_schedules(now=None, limit=50):
    """Return enabled schedules due by interval or because the case changed."""
    now = now or datetime.datetime.now(tz=datetime.timezone.utc)
    now = as_utc_datetime(now)
    candidates = Case_Misp_Sync_Schedule.query.filter_by(enabled=True).order_by(
        Case_Misp_Sync_Schedule.next_run_at.asc().nullslast(),
        Case_Misp_Sync_Schedule.updated_at.asc()
    ).limit(limit * 4).all()

    due = []
    for schedule in candidates:
        next_run_at = as_utc_datetime(schedule.next_run_at)
        interval_due = bool(next_run_at and next_run_at <= now)
        change_due = False
        if schedule.on_change:
            case = Case.query.get(schedule.case_id)
            if case and not case.completed:
                last_seen = as_utc_datetime(schedule.last_seen_case_modif or schedule.last_run_at or schedule.created_at)
                case_last_modif = as_utc_datetime(case.last_modif)
                change_due = bool(case_last_modif and (last_seen is None or case_last_modif > last_seen))
        if interval_due or (schedule.interval != "manual" and change_due):
            due.append(schedule)
        if len(due) >= limit:
            break
    return due


def _expand_misp_sync_conflicts(conflicts, include_resolved=False):
    expanded = []
    for conflict in conflicts:
        payload = conflict.to_json()
        if payload.get("item_type") == "event":
            local_details = payload.get("local_snapshot", {}).get("details") or []
            remote_details = payload.get("remote_snapshot", {}).get("details") or []
            resolved_tokens = set((payload.get("resolution_payload") or {}).get("resolved_details") or [])
            if local_details and remote_details:
                for index, local_detail in enumerate(local_details):
                    token = local_detail.get("token") or f"{payload['id']}:{index}"
                    is_resolved_detail = token in resolved_tokens
                    if include_resolved != is_resolved_detail:
                        continue
                    remote_detail = next((d for d in remote_details if (d.get("token") or "") == token), remote_details[index] if index < len(remote_details) else {})
                    detail_payload = dict(payload)
                    detail_payload["id"] = f"{payload['id']}:{index}"
                    detail_payload["parent_conflict_id"] = payload["id"]
                    detail_payload["item_type"] = local_detail.get("target_kind") or "attribute"
                    detail_payload["detail_token"] = token
                    detail_payload["local_ref"] = local_detail.get("label") or payload.get("local_ref")
                    detail_payload["remote_ref"] = remote_detail.get("label") or payload.get("remote_ref")
                    detail_payload["local_snapshot"] = {"details": [local_detail]}
                    detail_payload["remote_snapshot"] = {"details": [remote_detail]}
                    if is_resolved_detail:
                        detail_payload["resolved_resolution"] = payload.get("resolution")
                    expanded.append(detail_payload)
                continue
        if payload.get("item_type") == "event":
            continue
        if include_resolved == (payload.get("status") == "resolved"):
            expanded.append(payload)
    return expanded


def get_pending_misp_sync_conflicts(case_id, case_connector_instance_id):
    conflicts = Case_Misp_Sync_Conflict.query.filter_by(
        case_id=int(case_id),
        case_connector_instance_id=int(case_connector_instance_id),
        status="pending"
    ).order_by(Case_Misp_Sync_Conflict.created_at.desc()).all()
    return _expand_misp_sync_conflicts(conflicts, include_resolved=False)


def get_recent_misp_sync_conflict_history(case_id, case_connector_instance_id, limit=20):
    conflicts = Case_Misp_Sync_Conflict.query.filter_by(
        case_id=int(case_id),
        case_connector_instance_id=int(case_connector_instance_id)
    ).filter(
        Case_Misp_Sync_Conflict.status == "resolved"
    ).order_by(Case_Misp_Sync_Conflict.resolved_at.desc().nullslast(), Case_Misp_Sync_Conflict.created_at.desc()).limit(limit).all()
    history = _expand_misp_sync_conflicts(conflicts, include_resolved=True)
    history.sort(key=lambda item: item.get("resolved_at") or item.get("created_at") or "", reverse=True)
    return history[:limit]


def get_resolved_misp_event_conflict(case_id, case_connector_instance_id, direction, remote_ref, remote_timestamp):
    """Return the latest reviewed conflict for the same remote event timestamp."""
    if not remote_ref or not remote_timestamp:
        return None
    conflicts = Case_Misp_Sync_Conflict.query.filter_by(
        case_id=int(case_id),
        case_connector_instance_id=int(case_connector_instance_id),
        direction=direction,
        item_type="event",
        remote_ref=str(remote_ref),
        status="resolved"
    ).order_by(Case_Misp_Sync_Conflict.resolved_at.desc()).limit(10).all()
    for conflict in conflicts:
        remote_snapshot = conflict.remote_snapshot or {}
        if remote_snapshot.get("timestamp") == str(remote_timestamp) and conflict.resolution in {"prefer_flowintel", "prefer_misp", "skip"}:
            return conflict
    return None


def clear_pending_misp_event_sync_conflict(case_id, case_connector_instance_id, direction, local_ref, remote_ref):
    """Remove a pending event conflict placeholder when both sides are already aligned."""
    conflict = Case_Misp_Sync_Conflict.query.filter_by(
        case_id=int(case_id),
        case_connector_instance_id=int(case_connector_instance_id),
        direction=direction,
        item_type="event",
        local_ref=str(local_ref) if local_ref is not None else None,
        remote_ref=str(remote_ref) if remote_ref is not None else None,
        status="pending"
    ).first()
    if not conflict:
        return False
    db.session.delete(conflict)
    db.session.commit()
    return True


def upsert_misp_event_sync_conflict(case_id, case_connector_instance_id, direction, local_ref, remote_metadata, base_snapshot, local_snapshot):
    """Create a pending event-level MISP sync conflict, or reuse the existing one."""
    remote_metadata = remote_metadata or {}
    remote_ref = remote_metadata.get("uuid") or remote_metadata.get("id")
    existing = Case_Misp_Sync_Conflict.query.filter_by(
        case_id=int(case_id),
        case_connector_instance_id=int(case_connector_instance_id),
        direction=direction,
        item_type="event",
        local_ref=str(local_ref) if local_ref is not None else None,
        remote_ref=str(remote_ref) if remote_ref is not None else None,
        status="pending"
    ).first()
    if existing:
        existing.base_snapshot = base_snapshot
        existing.local_snapshot = local_snapshot
        existing.remote_snapshot = remote_metadata
        db.session.commit()
        return existing, False

    conflict = Case_Misp_Sync_Conflict(
        case_id=int(case_id),
        case_connector_instance_id=int(case_connector_instance_id),
        direction=direction,
        item_type="event",
        local_ref=str(local_ref) if local_ref is not None else None,
        remote_ref=str(remote_ref) if remote_ref is not None else None,
        status="pending",
        base_snapshot=base_snapshot,
        local_snapshot=local_snapshot,
        remote_snapshot=remote_metadata,
        created_at=datetime.datetime.now(tz=datetime.timezone.utc)
    )
    db.session.add(conflict)
    db.session.commit()
    return conflict, True


def resolve_misp_sync_conflict(conflict_id, resolution, resolution_payload, user):
    if resolution not in MISP_SYNC_RESOLUTIONS:
        return None, "Invalid conflict resolution"
    conflict = Case_Misp_Sync_Conflict.query.get(conflict_id)
    if not conflict:
        return None, "Conflict not found"
    resolution_payload = resolution_payload if isinstance(resolution_payload, dict) else {}
    detail_token = resolution_payload.get("detail_token")
    if conflict.item_type == "event" and detail_token:
        current_payload = dict(conflict.resolution_payload or {})
        resolved_details = list(current_payload.get("resolved_details") or [])
        if detail_token not in resolved_details:
            resolved_details.append(detail_token)
        current_payload["resolved_details"] = resolved_details
        current_payload["last_resolution"] = resolution
        conflict.resolution_payload = current_payload
        total_details = len((conflict.local_snapshot or {}).get("details") or [])
        conflict.status = "resolved" if total_details and len(resolved_details) >= total_details else "pending"
    else:
        conflict.status = "resolved"
        conflict.resolution_payload = resolution_payload
    conflict.resolution = resolution
    conflict.resolved_by_id = user.id if user else None
    conflict.resolved_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return conflict, None


def get_misp_conflict_followup_action(conflict, resolution, resolution_payload=None):
    """Return the sync action needed to align both sides after a manual resolution."""
    if not conflict or resolution not in MISP_SYNC_RESOLUTIONS:
        return None
    resolution_payload = resolution_payload if isinstance(resolution_payload, dict) else {}

    if conflict.direction != "send":
        return None
    if resolution not in {"prefer_flowintel", "prefer_misp"}:
        return None

    schedule_direction = "send" if resolution == "prefer_flowintel" else "receive"
    schedule = Case_Misp_Sync_Schedule.query.filter_by(
        case_id=int(conflict.case_id),
        case_connector_instance_id=int(conflict.case_connector_instance_id),
        direction=schedule_direction
    ).first()

    module_name = None
    payload = {}
    if schedule:
        module_name = schedule.module_name
        payload = dict(schedule.payload or {})

    if not module_name:
        module_name = "misp_object_event" if resolution == "prefer_flowintel" else "receive_misp_object"

    detail_token = resolution_payload.get("detail_token")
    detail = None
    if detail_token:
        details = (conflict.local_snapshot or {}).get("details") or []
        detail = next((d for d in details if d.get("token") == detail_token), None)

    if detail:
        # Drop any stored schedule-wide selectors so this resolution only targets
        # the conflicted attribute/object we rebuild just below.
        for key in [
            "selected_objects",
            "selected_standalone_attrs",
            "selected_object_attributes",
            "module",
            "case_task_instance_id",
            "force_conflict_resolution",
            "create_extended_event",
        ]:
            payload.pop(key, None)
        if resolution == "prefer_flowintel":
            module_name = "misp_object_event"
        else:
            module_name = "receive_misp_object"
        if resolution == "prefer_flowintel":
            if detail.get("target_kind") == "standalone_attribute" and detail.get("local_attribute_id"):
                payload["selected_standalone_attrs"] = [detail["local_attribute_id"]]
            elif detail.get("local_attribute_id"):
                payload["selected_object_attributes"] = [detail["local_attribute_id"]]
                if detail.get("local_object_id"):
                    payload["selected_objects"] = [detail["local_object_id"]]
        else:
            if detail.get("target_kind") == "standalone_attribute" and detail.get("remote_attribute_uuid"):
                payload["selected_standalone_attrs"] = [detail["remote_attribute_uuid"]]
            elif detail.get("remote_attribute_uuid"):
                payload["selected_object_attributes"] = [detail["remote_attribute_uuid"]]
                if detail.get("remote_object_uuid"):
                    payload["selected_objects"] = [detail["remote_object_uuid"]]

    payload["force_conflict_resolution"] = True
    payload["module"] = module_name
    payload["case_task_instance_id"] = conflict.case_connector_instance_id

    return {
        "direction": schedule_direction,
        "module_name": module_name,
        "payload": payload
    }


def check_misp_connectivity(instance, current_user=None):
    """Check connectivity to a MISP instance"""
    # Check if API key is set
    if current_user:
        user_api_key = User_Connector_Instance.query.filter_by(
            user_id=current_user.id, instance_id=instance.id
        ).first()
    else:
        user_api_key = get_user_instance_by_instance(instance.id)
    if not instance.global_api_key and (not user_api_key or not user_api_key.api_key):
        return {
            "success": False,
            "message": "API key is not configured for this instance",
            "is_api_key_missing": True
        }

    if instance.global_api_key:
        loc_api_key = instance.global_api_key
    else:
        loc_api_key = user_api_key.api_key
    try:
        from pymisp import PyMISP
        import urllib3
        urllib3.disable_warnings()
        
        # Initialize MISP connection - if this succeeds, connectivity is verified
        misp = PyMISP(instance.url, loc_api_key, ssl=False, timeout=20)
        
        return {
            "success": True,
            "message": "Successfully connected to MISP instance"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error connecting to MISP: {str(e)}"
        }


def search_misp_attributes(instance, current_user, query, api_key=None):
    """Search attributes in a MISP instance and return rows ready for UI rendering."""
    if not api_key:
        if current_user:
            user_api_key = User_Connector_Instance.query.filter_by(
                user_id=current_user.id, instance_id=instance.id
            ).first()
        else:
            user_api_key = get_user_instance_by_instance(instance.id)
        if not instance.global_api_key and (not user_api_key or not user_api_key.api_key):
            return {"success": False, "message": "API key is not configured for this instance"}
        api_key = instance.global_api_key or user_api_key.api_key

    try:
        from pymisp import PyMISP
        import urllib3
        urllib3.disable_warnings()

        misp = PyMISP(instance.url, api_key, ssl=False, timeout=30)
        search_value = query if "%" in query else f"%{query}%"
        response = misp.search(
            controller="attributes",
            value=search_value,
            to_ids=None,
            published=None,
            include_context=True,
            pythonify=False
        )
    except Exception as e:
        return {"success": False, "message": f"Error querying MISP: {str(e)}"}

    attributes = []
    if isinstance(response, dict):
        attributes = response.get("response", {}).get("Attribute") or response.get("Attribute") or []

    results = []
    for attr in attributes:
        event = attr.get("Event") or {}
        org = attr.get("Orgc") or event.get("Orgc") or event.get("Org") or {}
        org_name = org.get("name") if isinstance(org, dict) else org
        tags = [t.get("name") for t in (attr.get("Tag") or []) if isinstance(t, dict) and t.get("name")]
        results.append({
            "event_id": event.get("id"),
            "event_uuid": event.get("uuid"),
            "event_published": str(event.get("published")).lower() in ("1", "true"),
            "organisation": org_name,
            "event_info": event.get("info"),
            "date": event.get("date"),
            "attribute_type": attr.get("type"),
            "attribute_category": attr.get("category"),
            "attribute_value": attr.get("value"),
            "to_ids": str(attr.get("to_ids")).lower() in ("1", "true"),
            "comment": attr.get("comment"),
            "tags": tags,
        })

    return {"success": True, "results": results}
