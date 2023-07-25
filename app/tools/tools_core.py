from ..db_class.db import Case_Template, Task_Template, Case_Task_Template, Role, Case, Task, Case_Org
import bleach
import uuid
from .. import db
import datetime

def get_all_case_templates():
    return Case_Template.query.all()

def get_page_case_templates(page):
    return Case_Template.query.paginate(page=page, per_page=20, max_per_page=50)

def get_case_template(cid):
    return Case_Template.query.get(cid)

def get_all_task_templates():
    return Task_Template.query.all()

def get_page_task_templates(page):
    return Task_Template.query.paginate(page=page, per_page=20, max_per_page=50)

def get_task_template(tid):
    return Task_Template.query.get(tid)

def get_role(user):
    """Return role for the current user"""
    return Role.query.get(user.role_id)


def get_task_by_case(cid):
    case_task_template = Case_Task_Template.query.filter_by(case_id=cid).all()

    return [get_task_template(case_task.task_id) for case_task in case_task_template]


def add_case_template_core(form_dict):
    case_template = Case_Template(
        title=bleach.clean(form_dict["title"]),
        description=bleach.clean(form_dict["description"]),
        uuid=str(uuid.uuid4())
    )
    db.session.add(case_template)
    db.session.commit()

    for tid in form_dict["tasks"]:
        case_task_template = Case_Task_Template(
            case_id=case_template.id,
            task_id=tid
        )
        db.session.add(case_task_template)
        db.session.commit()
    return case_template

def add_task_template_core(form_dict):
    template = Task_Template(
        title=bleach.clean(form_dict["title"]),
        description=bleach.clean(form_dict["body"]),
        url=bleach.clean(form_dict["url"]),
        uuid=str(uuid.uuid4())
    )
    
    db.session.add(template)
    db.session.commit()
    return template


def add_task_case_template(form_dict, cid):
    if form_dict["tasks"]:
        for tid in form_dict["tasks"]:
            if not Case_Task_Template.query.filter_by(case_id=cid, task_id=tid).first():
                case_task_template = Case_Task_Template(
                    case_id=cid,
                    task_id=tid
                )
                db.session.add(case_task_template)
                db.session.commit()
    elif form_dict["title"]:
        template = add_task_template_core(form_dict)
        case_task_template = Case_Task_Template(
                case_id=cid,
                task_id=template.id
            )
        db.session.add(case_task_template)
        db.session.commit()
    else:
        return "No info"
    

def edit_task_template(form_dict, tid):
    template = get_task_template(tid)
    if not template.title == form_dict["title"]:
        if Task_Template.query.filter_by(title=form_dict["title"]).first():
            return "Title already exist"
        template.title=bleach.clean(form_dict["title"])

    template.description=bleach.clean(form_dict["body"])
    template.url=bleach.clean(form_dict["url"])
    db.session.commit()

def delete_case_template(cid):
    to_deleted = Case_Task_Template.query.filter_by(case_id=cid).all()
    for to_do in to_deleted:
        db.session.delete(to_do)
        db.session.commit()
    template = get_case_template(cid)
    db.session.delete(template)
    db.session.commit()
    return True

def remove_task_case(cid, tid):
    template = Case_Task_Template.query.filter_by(case_id=cid, task_id=tid).first()
    db.session.delete(template)
    db.session.commit()
    return True

def delete_task_template(tid):
    to_deleted = Case_Task_Template.query.filter_by(task_id=tid).all()
    for to_do in to_deleted:
        db.session.delete(to_do)
        db.session.commit()
    template = get_task_template(tid)
    db.session.delete(template)
    db.session.commit()
    return True


def create_case_from_template(cid, case_title_fork, user):
    case_title_stored = Case.query.filter_by(title=case_title_fork).first()
    if case_title_stored:
        return {"message": "Error, title already exist"}
    
    case_template = get_case_template(cid)

    case = Case(
        title=bleach.clean(case_title_fork),
        description=case_template.description,
        uuid=str(uuid.uuid4()),
        creation_date=datetime.datetime.now(),
        last_modif=datetime.datetime.now(),
        status_id=1,
        owner_org_id=user.org_id
    )
    db.session.add(case)
    db.session.commit()

    # Add the current user's org to the case
    case_org = Case_Org(
        case_id=case.id, 
        org_id=user.org_id
    )

    db.session.add(case_org)
    db.session.commit()

    task_case_template = get_task_by_case(cid)
    for task in task_case_template:
        t = Task(
            uuid=str(uuid.uuid4()),
            title=task.title,
            description=task.description,
            url=task.url,
            creation_date=datetime.datetime.now(),
            last_modif=datetime.datetime.now(),
            case_id=case.id,
            status_id=1
        )
        db.session.add(t)
        db.session.commit()
    
    return case