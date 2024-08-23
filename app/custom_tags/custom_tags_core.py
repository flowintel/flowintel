from .. import db
from ..db_class.db import Case_Custom_Tags, Case_Template_Custom_Tags, Custom_Tags, Task_Custom_Tags, Task_Template_Custom_Tags

def get_custom_tag(ctid):
    """Return a custom tag by id"""
    return Custom_Tags.query.get(ctid)

def get_custom_tags():
    """Return all custom tags"""
    return Custom_Tags.query.all()

def get_custom_tag_by_name(tag_name):
    """Return a custom tag by its name"""
    return Custom_Tags.query.filter_by(name=tag_name).first()

def change_status_core(ctid):
    """Active or disabled a tool"""
    ct = get_custom_tag(ctid)
    if ct:
        ct.is_active = not ct.is_active
        db.session.commit()
        return True
    return False

def change_config_core(request_json):
    """Change config for a custom_tag"""
    custom_tag = get_custom_tag(request_json["custom_tag_id"])
    if custom_tag:
        custom_tag.name = request_json["custom_tag_name"]
        custom_tag.icon = request_json["custom_tag_icon"]
        custom_tag.color = request_json["custom_tag_color"]
        db.session.commit()
        return True
    return False


def add_custom_tag_core(form_dict):
    """Add a custom tag into the db"""
    custom_tag = Custom_Tags(
        name=form_dict["name"],
        color=form_dict["color"],
        icon=form_dict["icon"]
    )
    db.session.add(custom_tag)
    db.session.commit()
    return True

def delete_custom_tag(ctid):
    """Delete a custom tag from db"""
    custom_tag = get_custom_tag(ctid)
    if custom_tag:
        Case_Custom_Tags.query.filter_by(custom_tag_id=ctid).delete()
        Task_Custom_Tags.query.filter_by(custom_tag_id=ctid).delete()
        Case_Template_Custom_Tags.query.filter_by(custom_tag_id=ctid).delete()
        Task_Template_Custom_Tags.query.filter_by(custom_tag_id=ctid).delete()
        db.session.delete(custom_tag)
        db.session.commit()
        return True
    return False