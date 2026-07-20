from .. import db
from ..db_class.db import Case_Custom_Tags, Case_Template_Custom_Tags, Custom_Tags, Task_Custom_Tags, Task_Template_Custom_Tags
from sqlalchemy.exc import SQLAlchemyError

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
        custom_tag.name = request_json["custom_tag_name"].strip()
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
    return custom_tag


def ensure_custom_tags_exist(custom_tags):
    """Ensure custom tags exist for a list of tags from JSON (dict or string)."""
    for custom_tag in custom_tags or []:
        if isinstance(custom_tag, dict):
            name = (custom_tag.get("name") or "").strip()
            color = custom_tag.get("color", "#000000")
            icon = custom_tag.get("icon", "")
        else:
            name = str(custom_tag).strip()
            color = "#000000"
            icon = ""

        if not name or get_custom_tag_by_name(name):
            continue

        try:
            add_custom_tag_core({"name": name, "color": color, "icon": icon})
        except SQLAlchemyError:
            db.session.rollback()
            # Ignore duplicate race conditions and continue import.
            continue


def ensure_custom_tags_for_case_payload(case_obj):
    """Ensure custom tags exist for case-level and nested task-level fields."""
    if not isinstance(case_obj, dict):
        return

    ensure_custom_tags_exist(case_obj.get("custom_tags", []))
    for task in case_obj.get("tasks", []) + case_obj.get("tasks_template", []):
        if isinstance(task, dict):
            ensure_custom_tags_exist(task.get("custom_tags", []))

def is_custom_tag_in_use(ctid):
    """Check if a custom tag is used in any case or task"""
    case_count = Case_Custom_Tags.query.filter_by(custom_tag_id=ctid).count()
    task_count = Task_Custom_Tags.query.filter_by(custom_tag_id=ctid).count()
    case_template_count = Case_Template_Custom_Tags.query.filter_by(custom_tag_id=ctid).count()
    task_template_count = Task_Template_Custom_Tags.query.filter_by(custom_tag_id=ctid).count()
    return (case_count + task_count + case_template_count + task_template_count) > 0

def get_cases_using_custom_tag(ctid):
    """Get all cases using a specific custom tag"""
    from ..db_class.db import Case
    cases = Case.query.join(Case_Custom_Tags, Case_Custom_Tags.case_id==Case.id)\
        .filter(Case_Custom_Tags.custom_tag_id==ctid).all()
    return [{"id": case.id, "title": case.title, "description": case.description} for case in cases]

def get_tasks_using_custom_tag(ctid):
    """Get all tasks using a specific custom tag"""
    from ..db_class.db import Task
    tasks = Task.query.join(Task_Custom_Tags, Task_Custom_Tags.task_id==Task.id)\
        .filter(Task_Custom_Tags.custom_tag_id==ctid).all()
    return [{"id": task.id, "title": task.title, "case_id": task.case_id} for task in tasks]

def get_case_templates_using_custom_tag(ctid):
    """Get all case templates using a specific custom tag"""
    from ..db_class.db import Case_Template
    case_templates = Case_Template.query.join(
        Case_Template_Custom_Tags,
        Case_Template_Custom_Tags.case_template_id == Case_Template.id
    ).filter(Case_Template_Custom_Tags.custom_tag_id == ctid).all()
    return [{"id": case_template.id, "title": case_template.title} for case_template in case_templates]

def get_task_templates_using_custom_tag(ctid):
    """Get all task templates using a specific custom tag"""
    from ..db_class.db import Task_Template
    task_templates = Task_Template.query.join(
        Task_Template_Custom_Tags,
        Task_Template_Custom_Tags.task_template_id == Task_Template.id
    ).filter(Task_Template_Custom_Tags.custom_tag_id == ctid).all()
    return [{"id": task_template.id, "title": task_template.title} for task_template in task_templates]

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