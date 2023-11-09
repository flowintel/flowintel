from ..db_class.db import *
import uuid
import ast
import json
from .. import db
import datetime
from ..utils import utils
from ..case import case_core

def get_all_case_templates():
    return Case_Template.query.all()

def get_page_case_templates(page, title_filter, tags=[]):
    if tags:
        tags = ast.literal_eval(tags)
        if title_filter == 'true':
            return Case_Template.query.join(Case_Template_Tags, Case_Template_Tags.case_id==Case_Template.id).join(Tags, Case_Template_Tags.tag_id==Tags.id)\
                            .where(Tags.name.in_(list(tags)))\
                            .order_by(('title'))\
                            .paginate(page=page, per_page=20, max_per_page=50)
        return Case_Template.query.join(Case_Template_Tags, Case_Template_Tags.case_id==Case_Template.id).join(Tags, Case_Template_Tags.tag_id==Tags.id)\
                            .where(Tags.name.in_(list(tags)))\
                            .paginate(page=page, per_page=20, max_per_page=50)
    else:
        if title_filter == 'true':
            return Case_Template.query.order_by(('title')).paginate(page=page, per_page=20, max_per_page=50)
        return Case_Template.query.paginate(page=page, per_page=20, max_per_page=50)

def get_case_template(cid):
    return Case_Template.query.get(cid)

def get_all_task_templates():
    return Task_Template.query.all()

def get_page_task_templates(page, title_filter, tags=[]):
    if tags:
        tags = ast.literal_eval(tags)
        if title_filter == 'true':
            return Task_Template.query.join(Task_Template_Tags, Task_Template_Tags.task_id==Task_Template.id).join(Tags, Task_Template_Tags.tag_id==Tags.id)\
                            .where(Tags.name.in_(list(tags)))\
                            .order_by(('title'))\
                            .paginate(page=page, per_page=20, max_per_page=50)
        return Task_Template.query.join(Task_Template_Tags, Task_Template_Tags.task_id==Task_Template.id).join(Tags, Task_Template_Tags.tag_id==Tags.id)\
                            .where(Tags.name.in_(list(tags)))\
                            .paginate(page=page, per_page=20, max_per_page=50)
    else:
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


def get_case_template_tags(cid):
    return [tag.name for tag in Tags.query.join(Case_Template_Tags, Case_Template_Tags.tag_id==Tags.id).filter_by(case_id=cid).all()]

def get_task_template_tags(tid):
    return [tag.name for tag in Tags.query.join(Task_Template_Tags, Task_Template_Tags.tag_id==Tags.id).filter_by(task_id=tid).all()]

def get_tag(tag):
    return Tags.query.filter_by(name=tag).first()


def create_case_template(form_dict):
    case_template = Case_Template(
        title=form_dict["title"],
        description=form_dict["description"],
        uuid=str(uuid.uuid4())
    )
    db.session.add(case_template)
    db.session.commit()

    for tag in form_dict["tags"]:
        tag = get_tag(tag)
        
        case_tag = Case_Template_Tags(
            tag_id=tag.id,
            case_id=case_template.id
        )
        db.session.add(case_tag)
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
        title=form_dict["title"],
        description=form_dict["body"],
        url=form_dict["url"],
        uuid=str(uuid.uuid4())
    )
    db.session.add(template)
    db.session.commit()

    for tag in form_dict["tags"]:
        tag = get_tag(tag)
        
        task_tag = Task_Template_Tags(
            tag_id=tag.id,
            task_id=template.id
        )
        db.session.add(task_tag)
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

    template.title=form_dict["title"]
    template.description=form_dict["description"]

    case_tag_db = Case_Template_Tags.query.filter_by(case_id=template.id).all()

    for tag in form_dict["tags"]:
        tag = get_tag(tag)

        if not tag in case_tag_db:
            case_tag = Case_Template_Tags(
                tag_id=tag.id,
                case_id=template.id
            )
            db.session.add(case_tag)
            db.session.commit()
    
    for c_t_db in case_tag_db:
        if not c_t_db in form_dict["tags"]:
            Case_Template_Tags.query.filter_by(id=c_t_db.id).delete()
            db.session.commit()

    db.session.commit()

def edit_task_template(form_dict, tid):
    template = get_task_template(tid)

    template.title=form_dict["title"]
    template.description=form_dict["body"]
    template.url=form_dict["url"]
    
    task_tag_db = Task_Template_Tags.query.filter_by(task_id=template.id).all()

    for tag in form_dict["tags"]:
        tag = get_tag(tag)

        if not tag in task_tag_db:
            task_tag = Task_Template_Tags(
                tag_id=tag.id,
                task_id=template.id
            )
            db.session.add(task_tag)
            db.session.commit()
    
    for c_t_db in task_tag_db:
        if not c_t_db in form_dict["tags"]:
            Task_Template_Tags.query.filter_by(id=c_t_db.id).delete()
            db.session.commit()

    db.session.commit()

def delete_case_template(cid):
    to_deleted = Case_Task_Template.query.filter_by(case_id=cid).all()
    for to_do in to_deleted:
        db.session.delete(to_do)
        db.session.commit()
    Case_Template_Tags.query.filter_by(case_id=cid).delete() 
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
    Task_Template_Tags.query.filter_by(task_id=tid).delete()
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
        title=case_title_fork,
        description=case_template.description,
        uuid=str(uuid.uuid4()),
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
        last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
        status_id=1,
        owner_org_id=user.org_id
    )
    db.session.add(case)
    db.session.commit()

    for c_t in Case_Template_Tags.query.filter_by(case_id=case_template.id).all():
        case_tag = Case_Tags(
            case_id=case.id,
            tag_id=c_t.tag_id
        )
        db.session.add(case_tag)
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

        for t_t in Task_Template_Tags.query.filter_by(task_id=task.id).all():
            task_tag = Task_Tags(
                task_id=t.id,
                tag_id=t_t.tag_id
            )
            db.session.add(task_tag)
            db.session.commit()
    
    return case



def core_read_json_file(case, current_user):
    if not utils.validateCaseJson(case):
        return {"message": f"Case '{case['title']}' format not okay"}
    for task in case["tasks"]:
        if not utils.validateTaskJson(task):
            return {"message": f"Task '{task['title']}' format not okay"}


    #######################
    ## Case Verification ##
    #######################

    ## Caseformat is valid
    # title
    if Case.query.filter_by(title=case["title"]).first():
        return {"message": f"Case Title '{case['title']}' already exist"}
    # deadline
    if case["deadline"]:
        try:
            loc_date = datetime.datetime.strptime(case["deadline"], "%Y-%m-%d %H:%M")
            case["deadline_date"] = loc_date.date()
            case["deadline_time"] = loc_date.time()
        except Exception as e:
            print(e)
            return {"message": f"Case '{case['title']}': deadline bad format, %Y-%m-%d %H:%M"}
    else:
        case["deadline_date"] = ""
        case["deadline_time"] = ""
    # recurring_date
    if case["recurring_date"]:
        if case["recurring_type"]:
            try:
                datetime.datetime.strptime(case["recurring_date"], "%Y-%m-%d %H:%M")
            except:
                return {"message": f"Case '{case['title']}': recurring_date bad format, %Y-%m-%d"}
        else:
            return {"message": f"Case '{case['title']}': recurring_type is missing"}
    # recurring_type
    if case["recurring_type"] and not case["recurring_date"]:
        return {"message": f"Case '{case['title']}': recurring_date is missing"}
    # uuid
    if Case.query.filter_by(uuid=case["uuid"]).first():
        case["uuid"] = str(uuid.uuid4())

    # tags
    for tag in case["tags"]:
        if not utils.check_tag(tag):
            return {"message": f"Case '{case['title']}': tag '{tag}' doesn't exist"}
        
    
    #######################
    ## Task Verification ##
    #######################

    ## Task format is valid
    for task in case["tasks"]:
        if Task.query.filter_by(uuid=task["uuid"]).first():
            task["uuid"] = str(uuid.uuid4())

        if task["deadline"]:
            try:
                loc_date = datetime.datetime.strptime(task["deadline"], "%Y-%m-%d %H:%M")
                task["deadline_date"] = loc_date.date()
                task["deadline_time"] = loc_date.time()
            except:
                return {"message": f"Task '{task['title']}': deadline bad format, %Y-%m-%d %H:%M"}
        else:
            task["deadline_date"] = ""
            task["deadline_time"] = ""

        for tag in task["tags"]:
            if not utils.check_tag(tag):
                return {"message": f"Task '{task['title']}': tag '{tag}' doesn't exist"}


    #################
    ## DB Creation ##
    ################

    ## Case creation
    case_created = case_core.create_case(case, current_user)

    ## Task creation
    for task in case["tasks"]:
        task_created = case_core.create_task(task, case_created.id, current_user)
        if task["notes"]:
            case_core.modif_note_core(task_created.id, current_user, task["notes"])

    
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