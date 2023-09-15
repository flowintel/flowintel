from ..db_class.db import Case_Template, Task_Template, Case_Task_Template, Role, Case, Task, Case_Org
import bleach
import uuid
from .. import db
import datetime
from ..utils import utils
from ..case import case_core

def get_all_case_templates():
    return Case_Template.query.all()

def get_page_case_templates(page, title_filter):
    if title_filter == 'true':
        return Case_Template.query.order_by(('title')).paginate(page=page, per_page=20, max_per_page=50)
    return Case_Template.query.paginate(page=page, per_page=20, max_per_page=50)

def get_case_template(cid):
    return Case_Template.query.get(cid)

def get_all_task_templates():
    return Task_Template.query.all()

def get_page_task_templates(page, title_filter):
    if title_filter == 'true':
        return Task_Template.query.order_by(('title')).paginate(page=page, per_page=20, max_per_page=50)
    return Task_Template.query.paginate(page=page, per_page=20, max_per_page=50)

def get_task_template(tid):
    return Task_Template.query.get(tid)

def get_role(user):
    """Return role for the current user"""
    return Role.query.get(user.role_id)


def get_task_by_case(cid):
    case_task_template = Case_Task_Template.query.filter_by(case_id=cid).all()

    return [get_task_template(case_task.task_id) for case_task in case_task_template]


def create_case_template(form_dict):
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
    



def edit_case_template(form_dict, cid):
    template = get_case_template(cid)

    template.title=bleach.clean(form_dict["title"])
    template.description=bleach.clean(form_dict["description"])
    db.session.commit()

def edit_task_template(form_dict, tid):
    template = get_task_template(tid)

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
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
        last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
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
            creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
            last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
            case_id=case.id,
            status_id=1
        )
        db.session.add(t)
        db.session.commit()
    
    return case



def core_read_json_file(case, current_user):
    if utils.validateCaseJson(case):
        if Case.query.filter_by(title=case["title"]).first():
            return {"message": f"Case Title '{case['title']}' already exist"}
        if case["deadline"]:
            try:
                case["deadline_date"] = datetime.datetime.strptime(case["deadline"], "%Y-%m-%d")
                case["deadline_time"] = datetime.datetime.strptime(case["deadline"], "%H:%M")
            except:
                return {"message": f"'{case['title']}': deadline bad format, %Y-%m-%d %H:%M"}
        else:
            case["deadline_date"] = ""
            case["deadline_time"] = ""
        if case["recurring_date"]:
            if case["recurring_type"]:
                try:
                    datetime.datetime.strptime(case["recurring_date"], "%Y-%m-%d")
                except:
                    return {"message": f"'{case['title']}': recurring_date bad format, %Y-%m-%d"}
            else:
                return {"message": f"'{case['title']}': recurring_type is missing"}
        if case["recurring_type"] and not case["recurring_date"]:
            return {"message": f"'{case['title']}': recurring_date is missing"}
        if Case.query.filter_by(uuid=case["uuid"]).first():
            case["uuid"] = str(uuid.uuid4())

        case_created = case_core.create_case(case, current_user)

        for task in case["tasks"]:
            if utils.validateTaseJson(task):
                if Task.query.filter_by(uuid=task["uuid"]).first():
                    task["uuid"] = str(uuid.uuid4())

                if task["deadline"]:
                    try:
                        task["deadline_date"] = datetime.datetime.strptime(task["deadline"], "%Y-%m-%d")
                        task["deadline_time"] = datetime.datetime.strptime(task["deadline"], "%H:%M")
                    except:
                        return {"message": f"Task '{task['title']}': deadline bad format, %Y-%m-%d %H:%M"}
                else:
                    task["deadline_date"] = ""
                    task["deadline_time"] = ""

                task_created = case_core.create_task(task, case_created.id, current_user)
                if task["notes"]:
                    case_core.modif_note_core(task_created.id, current_user, task["notes"])
            else:
                return {"message": f"Task '{task['title']}' format not okay"}
    else:
        return {"message": f"Case '{case['title']}' format not okay"}
    

import json
def read_json_file(files_list, current_user):
    for file in files_list:
        if files_list[file].filename:
            try:
                file_data = json.loads(files_list[file].read().decode())
                if type(file_data) == list:
                    for case in file_data:
                        res = core_read_json_file(case, current_user)
                        if res: return res
                else:
                    return core_read_json_file(file_data, current_user)
            except Exception as e:
                print(e)
                return {"message": "Something went wrong"}