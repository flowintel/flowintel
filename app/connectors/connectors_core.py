import os
from .. import db
from ..db_class.db import Connector_Icon, Icon_File, Connector, Connector_Instance, User_Connector_Instance
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

def get_user_instance_by_instance(instance_id):
    """Return a user instance by insatnce id"""
    return User_Connector_Instance.query.filter_by(instance_id=instance_id).first()

def get_user_instance_by_user(user_id):
    """Return a user instance by user id"""
    return User_Connector_Instance.query.filter_by(user_id=user_id).first()

def get_icons():
    """Return all icons"""
    return Connector_Icon.query.all()

def get_icon(iid):
    """Return an icon"""
    return Connector_Icon.query.get(iid)

def get_default_icon():
    """Return teh default icon"""
    return Connector_Icon.query.filter_by(name="default").first()

def get_icon_file(file_id):
    """Return a file"""
    return Icon_File.query.get(file_id)


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
    return True

def add_connector_instance_core(cid, form_dict, user_id):
    connector = Connector_Instance(
        name=form_dict["name"],
        description=form_dict["description"],
        url=form_dict["url"],
        uuid=str(uuid.uuid4()),
        connector_id=cid
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
    return True


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
        instance_db.name = form_dict["name"]
        instance_db.url = form_dict["url"]
        instance_db.description = form_dict["description"]
        if form_dict["api_key"]:
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
    instance = get_instance(iid)
    user_instance = get_user_instance_by_instance(iid)
    db.session.delete(user_instance)
    db.session.commit()
    db.session.delete(instance)
    db.session.commit()
    return True


def delete_icon_file(file_icon_id):
    """Delete an icon from disk from table Icon_File"""
    icon_file = get_icon_file(file_icon_id)

    try:
        os.remove(os.path.join(ICON_FOLDER, icon_file.uuid))
    except:
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