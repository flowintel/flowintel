import os
from .. import db
from ..db_class.db import Case_Connector_Instance, Connector_Icon, Icon_File, Connector, Connector_Instance, Task_Connector_Instance, User_Connector_Instance
import uuid
from werkzeug.utils import secure_filename

ICON_FOLDER = os.path.join(os.getcwd(), "app", "static", "icons")


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


def instance_has_links(instance_id):
    """Return True if instance is linked to a case or task."""
    case_link = Case_Connector_Instance.query.filter_by(instance_id=instance_id).first()
    if case_link:
        return True
    task_link = Task_Connector_Instance.query.filter_by(instance_id=instance_id).first()
    return task_link is not None

def get_user_instance_by_instance(instance_id):
    """Return a user instance by instance id"""
    return User_Connector_Instance.query.filter_by(instance_id=instance_id).first()

def get_user_instance_by_user(user_id):
    """Return a user instance by user id"""
    return User_Connector_Instance.query.filter_by(user_id=user_id).all()

def get_user_instance_both(user_id, instance_id):
    return User_Connector_Instance.query.filter_by(user_id=user_id, instance_id=instance_id).all()

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

    task_link = db.session.query(Task_Connector_Instance.id).join(
        Connector_Instance,
        Task_Connector_Instance.instance_id == Connector_Instance.id
    ).filter(Connector_Instance.connector_id == connector_id).first()
    return task_link is not None


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
    task_linked = {
        cid for (cid,) in db.session.query(Connector_Instance.connector_id)
        .join(Task_Connector_Instance, Task_Connector_Instance.instance_id == Connector_Instance.id)
        .filter(Connector_Instance.connector_id.in_(connector_ids))
        .distinct()
        .all()
    }
    connectors_with_links = case_linked.union(task_linked)
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

    if form_dict["type_select"] and not form_dict["type_select"] == "None":
        type_select = form_dict["type_select"]
    else:
        type_select = ""

    connector = Connector_Instance(
        name=form_dict["name"],
        description=form_dict["description"],
        url=form_dict["url"],
        uuid=str(uuid.uuid4()),
        connector_id=cid,
        type=type_select,
        global_api_key=form_dict["api_key"] if form_dict["is_global_connector"] else None
    )
    db.session.add(connector)
    db.session.commit()

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
        if form_dict["type_select"] and not form_dict["type_select"] == "None":
            type_select = form_dict["type_select"]
        else:
            type_select = instance_db.type
        instance_db.name = form_dict["name"]
        instance_db.url = form_dict["url"]
        instance_db.description = form_dict["description"]
        instance_db.type = type_select
        if form_dict["api_key"]:
            if "is_global_connector" in form_dict and form_dict["is_global_connector"]:
                instance_db.global_api_key = form_dict["api_key"]
            else:
                user_instance = get_user_instance_by_instance(iid)
                user_instance.api_key = form_dict["api_key"]
                db.session.add(user_instance)
                db.session.commit()

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
    Case_Connector_Instance.query.filter_by(instance_id=iid).delete()
    Task_Connector_Instance.query.filter_by(instance_id=iid).delete()

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


def check_misp_connectivity(instance):
    """Check connectivity to a MISP instance"""
    # Check if API key is set
    if not instance.global_api_key:
        return {
            "success": False,
            "message": "API key is not configured for this instance",
            "is_api_key_missing": True
        }
    
    try:
        from pymisp import PyMISP
        import urllib3
        urllib3.disable_warnings()
        
        # Initialize MISP connection - if this succeeds, connectivity is verified
        misp = PyMISP(instance.url, instance.global_api_key, ssl=False, timeout=20)
        
        return {
            "success": True,
            "message": "Successfully connected to MISP instance"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error connecting to MISP: {str(e)}"
        }