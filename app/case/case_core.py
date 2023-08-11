import os
from .. import db
from ..db_class.db import Case, Task, Task_User, User, Case_Org, Role, Org, File, Status, Task_Template, Case_Task_Template, Case_Template
from ..utils.utils import isUUID, create_upload_dir
import uuid
import bleach
import markdown
import datetime
from sqlalchemy import desc
from flask import request, send_file
from werkzeug.utils import secure_filename
from ..notification import notification_core as NotifModel
from dateutil import relativedelta
from ..tools.tools_core import create_case_from_template

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")


def get_case(cid):
    """Return a case by is id"""
    if isUUID(cid):
        case = Case.query.filter_by(uuid=cid).first()
    elif str(cid).isdigit():
        case = Case.query.get(cid)
    else:
        case = None
    return case

def get_task(tid):
    """Return a task by is id"""
    if isUUID(tid):
        case = Task.query.filter_by(uuid=tid).first()
    elif str(tid).isdigit():
        case = Task.query.get(tid)
    else:
        case = None
    return case

def get_all_cases():
    """Return all cases"""
    cases = Case.query.order_by(desc(Case.last_modif))
    return cases

def get_case_by_completed(completed):
    return Case.query.filter_by(completed=completed)

def get_case_by_title(title):
    return Case.query.filter_by(title=title).first()

def get_case_template_by_title(title):
    return Case_Template.query.filter_by(title=title).first()

def get_role(user):
    """Return role for the current user"""
    return Role.query.get(user.role_id)

def get_org(oid):
    """Return an org by is id"""
    return Org.query.get(oid)

def get_org_by_name(name):
    """Return an org by is name"""
    return Org.query.filter_by(name=name).first()

def get_org_in_case(org_id, case_id):
    return Case_Org.query.filter_by(case_id=case_id, org_id=org_id).first()


def get_file(fid):
    return File.query.get(fid)

def get_all_status():
    return Status.query.all()

def get_status(sid):
    return Status.query.get(sid).first()


def delete_case(cid, current_user):
    """Delete a case by is id"""
    case = get_case(cid)
    if case:
        # Delete all tasks in the case
        for task in case.tasks:
            delete_task(task.id)

        NotifModel.create_notification_all_orgs(f"Case: '{case.id}-{case.title}' was deleted", cid, html_icon="fa-solid fa-trash", current_user=current_user)

        Case_Org.query.filter_by(case_id=case.id).delete()
        db.session.delete(case)
        db.session.commit()
        return True
    return False

def delete_task(tid):
    """Delete a task by is id"""
    task = get_task(tid)
    if task is not None:
        for file in task.files:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, file.uuid))
            except:
                return False
            db.session.delete(file)
            db.session.commit()

        case = get_case(task.case_id)
        task_users = Task_User.query.where(Task_User.task_id==task.id).all()
        for task_user in task_users:
            user = User.query.get(task_user.user_id)
            print(user.to_json())
            NotifModel.create_notification_user(f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' was deleted", task.case_id, user_id=user.id, html_icon="fa-solid fa-trash")

        Task_User.query.filter_by(task_id=task.id).delete()
        db.session.delete(task)
        update_last_modif(task.case_id)
        db.session.commit()
        return True
    return False


def update_last_modif(case_id):
    """Update 'last_modif' of a case"""
    case = Case.query.get(case_id)
    case.last_modif = datetime.datetime.now()
    db.session.commit()



def update_last_modif_task(task_id):
    """Update 'last_modif' of a task"""
    if task_id:
        task = Task.query.get(task_id)
        task.last_modif = datetime.datetime.now()
        db.session.commit()


def complete_case(cid, current_user):
    """Complete case by is id"""
    case = get_case(cid)
    if case is not None:
        case.completed = not case.completed
        if case.completed:
            case.status_id = Status.query.filter_by(name="Finished").first().id
            for task in case.tasks:
                complete_task(task.id)
            NotifModel.create_notification_all_orgs(f"Case: '{case.id}-{case.title}' is now completed", cid, html_icon="fa-solid fa-square-check", current_user=current_user)
        else:
            case.status_id = Status.query.filter_by(name="Created").first().id
            NotifModel.create_notification_all_orgs(f"Case: '{case.id}-{case.title}' is now revived", cid, html_icon="fa-solid fa-heart-circle-plus", current_user=current_user)

        update_last_modif(cid)
        db.session.commit()
        return True
    return False


def complete_task(tid):
    """Complete task by is id"""
    task = get_task(tid)
    if task is not None:
        task.completed = not task.completed

        case = get_case(task.case_id)
        task_users = Task_User.query.where(Task_User.task_id==task.id).all()
        if task.completed:
            task.status_id = Status.query.filter_by(name="Finished").first().id
            message = f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' completed"
        else:
            task.status_id = Status.query.filter_by(name="Created").first().id
            message = f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' revived"
        for task_user in task_users:
            user = User.query.get(task_user.user_id)
            if task.completed:
                message = f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' completed"
                NotifModel.create_notification_user(message, task.case_id, user_id=user.id, html_icon="fa-solid fa-check")
            else:
                message = f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' revived"
                NotifModel.create_notification_user(message, task.case_id, user_id=user.id, html_icon="fa-solid fa-heart-circle-bolt")

        update_last_modif(task.case_id)
        update_last_modif_task(task.id)
        db.session.commit()
        return True
    return False


def add_case_core(form_dict, user):
    """Add a case to the DB"""
    print(form_dict)
    if "template_select" in form_dict and not 0 in form_dict["template_select"]:
        if Case_Template.query.get(form_dict["template_select"]):
            case = create_case_from_template(form_dict["template_select"][0], form_dict["title_template"], user)
    else:
        deadline = deadline_check(form_dict["deadline_date"], form_dict["deadline_time"])
        case = Case(
            title=bleach.clean(form_dict["title"]),
            description=bleach.clean(form_dict["description"]),
            uuid=str(uuid.uuid4()),
            creation_date=datetime.datetime.now(),
            last_modif=datetime.datetime.now(),
            deadline=deadline,
            status_id=1,
            owner_org_id=user.org_id
        )
        
        db.session.add(case)
        db.session.commit()

        if "tasks_templates" in form_dict and not 0 in form_dict["tasks_templates"]:
            for tid in form_dict["tasks_templates"]:
                task = Task_Template.query.get(tid)
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

    # Add the current user's org to the case
    case_org = Case_Org(
        case_id=case.id, 
        org_id=user.org_id
    )

    db.session.add(case_org)
    db.session.commit()

    return case


def edit_case_core(form_dict, cid):
    """Edit a case to the DB"""
    case = get_case(cid)

    deadline = deadline_check(form_dict["deadline_date"], form_dict["deadline_time"])

    case.title = bleach.clean(form_dict["title"])
    case.description=bleach.clean(form_dict["description"])
    case.deadline=deadline

    update_last_modif(cid)
    db.session.commit()
    

def add_task_core(form_dict, cid):
    """Add a task to the DB"""
    if "template_select" in form_dict and not 0 in form_dict["template_select"]:
        template = Task_Template.query.get(form_dict["template_select"])
        task = Task(
            uuid=str(uuid.uuid4()),
            title=template.title,
            description=template.description,
            url=template.url,
            creation_date=datetime.datetime.now(),
            last_modif=datetime.datetime.now(),
            case_id=cid,
            status_id=1
        )
    else:
        deadline = deadline_check(form_dict["deadline_date"], form_dict["deadline_time"])

        task = Task(
            uuid=str(uuid.uuid4()),
            title=bleach.clean(form_dict["title"]),
            description=bleach.clean(form_dict["description"]),
            url=bleach.clean(form_dict["url"]),
            creation_date=datetime.datetime.now(),
            last_modif=datetime.datetime.now(),
            deadline=deadline,
            case_id=cid,
            status_id=1
        )

    db.session.add(task)
    db.session.commit()
    update_last_modif(cid)

    return task


def add_file_core(task, files_list):
    create_upload_dir(UPLOAD_FOLDER)
    for file in files_list:
        if files_list[file].filename:
            uuid_loc = str(uuid.uuid4())
            filename = secure_filename(files_list[file].filename)
            try:
                file_data = request.files[file].read()
                with open(os.path.join(UPLOAD_FOLDER, uuid_loc), "wb") as write_file:
                    write_file.write(file_data)
            except Exception as e:
                print(e)
                return False

            f = File(
                name=filename,
                task_id=task.id,
                uuid = uuid_loc
            )
            db.session.add(f)
            update_last_modif(task.case_id)
            update_last_modif_task(task.id)
            db.session.commit()
    return True

def edit_task_core(form_dict, tid):
    """Edit a task to the DB"""
    task = get_task(tid)
    deadline = deadline_check(form_dict["deadline_date"], form_dict["deadline_time"])

    task.title = bleach.clean(form_dict["title"])
    task.description=bleach.clean(form_dict["description"])
    task.url=bleach.clean(form_dict["url"])
    task.deadline=deadline

    update_last_modif(task.case_id)
    update_last_modif_task(task.id)
    db.session.commit()


def deadline_check(date, time):
    """Combine the date and the time if time exist"""
    deadline = None
    if date and time:
        deadline = datetime.datetime.combine(date, time)
    elif date:
        deadline = date
    
    return deadline


def modif_note_core(tid, notes):
    """Modify a noe of a task to the DB"""
    task = get_task(tid)
    if task:
        task.notes = bleach.clean(notes)
        update_last_modif(task.case_id)
        update_last_modif_task(task.id)
        db.session.commit()
        return True
    return False

def get_note_text(tid):
    """Return a text note by task's id"""
    task = get_task(tid)
    if task:
        return task.notes
    else:
        return ""

def get_note_markdown(tid):
    """Return a markdown note by task's id"""
    task = get_task(tid)
    if task:
        return markdown_notes(task.notes)
    else:
        return ""

def markdown_notes(notes):
    """Return a markdown version of a note"""
    if notes:
        return markdown.markdown(notes)
    return notes


def add_orgs_case(form_dict, cid, current_user):
    """Add orgs to case in th DB"""
    for org_id in form_dict["org_id"]:
        case_org = Case_Org(
            case_id=cid, 
            org_id=org_id
        )
        db.session.add(case_org)
        case = get_case(cid)
        NotifModel.create_notification_org(f"{get_org(org_id).name} add to case: '{case.id}-{case.title}'", cid, org_id, html_icon="fa-solid fa-sitemap", current_user=current_user)

    update_last_modif(cid)
    db.session.commit()
    return True

def get_orgs_in_case(case_id):
    """Return orgs present in a case"""
    case_org = Case_Org.query.filter_by(case_id=case_id).all()
    orgs = list()

    for c_o in case_org:
        o = Org.query.get(c_o.org_id)
        orgs.append(o.to_json())

    return orgs


def remove_org_case(case_id, org_id, current_user):
    """Remove an org from a case"""
    case_org = Case_Org.query.filter_by(case_id=case_id, org_id=org_id).first()
    if case_org:
        db.session.delete(case_org)

        case = get_case(case_id)
        NotifModel.create_notification_org(f"{get_org(org_id).name} removed from case: '{case.id}-{case.title}'", case_id, org_id, html_icon="fa-solid fa-door-open", current_user=current_user)

        update_last_modif(case_id)
        db.session.commit()
        return True
    return False


def assign_task(tid, user, flag_current_user):
    """Assign current user to a task"""
    task = get_task(tid)
    case = get_case(task.case_id)
    if task:
        if type(user) == str or type(user) == int:
            user_id = user
        else:
            user_id = user.id

        task_user = Task_User(task_id=task.id, user_id=user_id)
        if not flag_current_user:
            NotifModel.create_notification_user(f"You have been assign to: '{task.id}-{task.title}' of case '{case.id}-{case.title}'", task.case_id, user_id=user_id, html_icon="fa-solid fa-hand")
   
        if not Task_User.query.filter_by(task_id=task.id, user_id=user_id).first():
            db.session.add(task_user)
            update_last_modif(task.case_id)
            update_last_modif_task(task.id)
            db.session.commit()
            return True
        return False
    return False

def get_users_assign_task(task_id, user):
    """Return users assigned to a task"""
    task_users = Task_User.query.filter_by(task_id=task_id).all()
    users = list()
    flag = False
    for task_user in task_users:
        u = User.query.get(task_user.user_id)
        # if current user is assigned to the task
        if u.id == user.id:
            flag = True
        users.append(u.to_json())
    return users, flag


def remove_assign_task(tid, user, flag_current_user):
    """Remove current user to the assignement to a task"""
    task = get_task(tid)
    case = get_case(task.case_id)
    if task:
        if type(user) == int or type(user) == str:
            task_users = Task_User.query.filter_by(task_id=task.id, user_id=user).all()
            if not flag_current_user:
                NotifModel.create_notification_user(f"Your assignment have been removed: '{task.id}-{task.title}' of case '{case.id}-{case.title}'", task.case_id, user_id=user, html_icon="fa-solid fa-handshake-slash")
        else:
            task_users = Task_User.query.filter_by(task_id=task.id, user_id=user.id).all()
            if not flag_current_user:
                NotifModel.create_notification_user(f"Your assignment have been removed: '{task.id}-{task.title}' of case '{case.id}-{case.title}'", task.case_id, user_id=user.id, html_icon="fa-solid fa-handshake-slash")
        for task_user in task_users:
            db.session.delete(task_user)

        update_last_modif(task.case_id)
        update_last_modif_task(task.id)
        db.session.commit()
        return True
    return False


def get_present_in_case(case_id, user):
    """Return if current user is present in a case"""
    orgs_in_case = get_orgs_in_case(case_id)

    present_in_case = False
    for org in orgs_in_case:
        if org["id"] == user.org_id:
            present_in_case = True

    return present_in_case


def change_status_core(status, case):
    case.status_id = status
    update_last_modif(case.id)
    db.session.commit()

    return True


def change_status_task(status, task):
    task.status_id = status
    update_last_modif(task.case_id)
    update_last_modif_task(task.id)
    db.session.commit()

    return True


def download_file(file):
    return send_file(os.path.join(UPLOAD_FOLDER, file.uuid), as_attachment=True, download_name=file.name)


def delete_file(file):
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, file.uuid))
    except:
        return False

    db.session.delete(file)
    db.session.commit()
    return True



def get_task_info(tasks_list, user):
    tasks = list()
    for task in tasks_list:
        case = get_case(task.case_id)
        users, is_current_user_assigned = get_users_assign_task(task.id, user)
        task.notes = markdown_notes(task.notes)
        file_list = list()
        for file in task.files:
            file_list.append(file.to_json())
        finalTask = task.to_json()
        finalTask["users"] = users
        finalTask["is_current_user_assigned"] = is_current_user_assigned
        finalTask["files"] = file_list
        finalTask["case_title"] = case.title

        tasks.append(finalTask)
    return tasks


def regroup_case_info(cases, user, nb_pages=None):
    loc = dict()
    loc["cases"] = list()
    
    for case in cases:
        present_in_case = get_present_in_case(case.id, user)
        case_loc = case.to_json()
        case_loc["present_in_case"] = present_in_case
        case_loc["current_user_permission"] = get_role(user).to_json()

        loc["cases"].append(case_loc)
    if nb_pages:
        loc["nb_pages"] = nb_pages
    else:
        try:
            loc["nb_pages"] = cases.pages
        except:
            pass

    return loc


def sort_by_ongoing_task_core(case, user):
    tasks_list = Task.query.filter_by(case_id=case.id, completed=False).all()
    return get_task_info(tasks_list, user)
    
def sort_by_finished_task_core(case, user):
    tasks_list = Task.query.filter_by(case_id=case.id, completed=True).all()
    return get_task_info(tasks_list, user)


def sort_tasks_by_filter(case, user, completed, filter):
    if filter == "assigned_tasks":
        tasks_list = Task.query.join(Task_User,Task_User.task_id==Task.id)\
                        .where(Task.case_id==case.id, Task.completed==completed)\
                        .order_by(desc('title')).all()

    elif filter == "my_assignment":
        tasks_list = Task.query.join(Task_User,Task_User.task_id==Task.id)\
                        .where(Task_User.user_id==user.id)\
                        .where(Task.case_id==case.id, Task.completed==completed)\
                        .order_by(desc('title')).all()
        loc = list()
        for task in tasks_list:
            task.is_current_user_assigned = True
            loc.append(task)
        tasks_list = loc
    else:
        # for deadline filter, only task with a deadline defined is required
        tasks_list = Task.query.filter_by(case_id=case.id, completed=completed).order_by(desc(filter)).all()
        loc = list()
        for task in tasks_list:
            if getattr(task, filter):
                loc.append(task)
        tasks_list = loc

    return get_task_info(tasks_list, user)


def sort_by_ongoing_core(page):
    return Case.query.filter_by(completed=False).paginate(page=page, per_page=20, max_per_page=50)
    
def sort_by_finished_core(page):
    return Case.query.filter_by(completed=True).paginate(page=page, per_page=20, max_per_page=50)


def sort_by_filter(completed, filter, page): 
    cases = Case.query.filter_by(completed=completed).order_by(desc(filter)).paginate(page=page, per_page=20, max_per_page=50)
    # for deadline filter, only case with a deadline defined is required
    loc = list()
    for case in cases:
        if getattr(case, filter):
            loc.append(case)
    return loc, cases.pages

def get_all_users_core(case):
    return Org.query.join(Case_Org, Case_Org.case_id==case.id).where(Case_Org.org_id==Org.id).all()

def fork_case_core(cid, case_title_fork, user):
    case_title_stored = get_case_by_title(case_title_fork)
    if case_title_stored:
        return {"message": "Error, title already exist"}
    case = get_case(cid)

    case_json = case.to_json()
    case_json["title"] = case_title_fork

    if case.deadline:
        case_json["deadline_date"] = datetime.datetime.strptime(case_json["deadline"].split(" ")[0], "%Y-%m-%d").date()
        case_json["deadline_time"] = datetime.datetime.strptime(case_json["deadline"].split(" ")[1], "%H:%M").time()
    else:
        case_json["deadline_date"] = None
        case_json["deadline_time"] = None

    new_case = add_case_core(case_json, user)

    for task in case.tasks:
        task_json = task.to_json()
        if task.deadline:
            task_json["deadline_date"] = datetime.datetime.strptime(task_json["deadline"].split(" ")[0], "%Y-%m-%d").date()
            task_json["deadline_time"] = datetime.datetime.strptime(task_json["deadline"].split(" ")[1], "%H:%M").time()
        else:
            task_json["deadline_date"] = None
            task_json["deadline_time"] = None

        add_task_core(task_json, new_case.id)
    return new_case


def create_template_from_case(cid, case_title_template):
    if Case_Template.query.filter_by(title=case_title_template).first():
        return {"message": "Error, title already exist"}
    
    case = get_case(cid)
    new_template = Case_Template(
        uuid=str(uuid.uuid4()),
        title=case_title_template,
        description=case.description
    )
    db.session.add(new_template)
    db.session.commit()

    for task in case.tasks:
        task_exist = Task_Template.query.filter_by(title=task.title).first()
        if not task_exist:
            task_template = Task_Template(
                uuid=str(uuid.uuid4()),
                title=task.title,
                description=task.description,
                url=task.url
            )
            db.session.add(task_template)
            db.session.commit()

            case_task_template = Case_Task_Template(
                    case_id=new_template.id,
                    task_id=task_template.id
                )
            db.session.add(case_task_template)
            db.session.commit()
        else:
            case_task_template = Case_Task_Template(
                    case_id=new_template.id,
                    task_id=task_exist.id
                )
            db.session.add(case_task_template)
            db.session.commit()

    return new_template


def change_recurring(form_dict, cid):
    case = get_case(cid)
    if "once" in form_dict and form_dict["once"]:
        case.recurring_type = "once"
        case.recurring_date = form_dict["once"]
    elif "daily" in form_dict and form_dict["daily"]:
        case.recurring_type = "daily"
    elif "weekly" in form_dict and form_dict["weekly"]:
        case.recurring_type = "weekly"
        case.recurring_date = datetime.datetime.today() + datetime.timedelta(
            days=(form_dict["weekly"].weekday() - datetime.datetime.today().weekday() + 7)
            )
    elif "monthly" in form_dict and form_dict["monthly"]:
        case.recurring_type = "monthly"
        if form_dict["monthly"].date()<datetime.datetime.today().date():
            case.recurring_date = form_dict["monthly"] + relativedelta.relativedelta(months=1)
        else:
            case.recurring_date = form_dict["monthly"]

    db.session.commit()
    return

def notify_user(task, user_id):
    case = get_case(task.case_id)
    message = f"Notify for task '{task.id}-{task.title}' of case '{case.id}-{case.title}'"
    NotifModel.create_notification_user(message, task.case_id, user_id=user_id, html_icon="fa-solid fa-bell")
    return True