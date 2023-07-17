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
    if case is not None:
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
                os.remove(os.path.join(UPLOAD_FOLDER, file.name))
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



def update_last_modif_task(task_id):
    """Update 'last_modif' of a task"""
    if task_id:
        task = Task.query.get(task_id)
        task.last_modif = datetime.datetime.now()


def complete_case(cid, current_user):
    """Complete case by is id"""
    case = get_case(cid)
    if case is not None:
        case.completed = not case.completed
        if case.completed:
            NotifModel.create_notification_all_orgs(f"Case: '{case.id}-{case.title}' is now completed", cid, html_icon="fa-solid fa-square-check", current_user=current_user)
        else:
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
            message = f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' completed"
        else:
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

    dead_line = dead_line_check(form_dict["dead_line_date"], form_dict["dead_line_time"])

    case = Case(
        title=bleach.clean(form_dict["title"]),
        description=bleach.clean(form_dict["description"]),
        uuid=str(uuid.uuid4()),
        creation_date=datetime.datetime.now(),
        last_modif=datetime.datetime.now(),
        dead_line=dead_line,
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

    return case


def edit_case_core(form_dict, cid):
    """Edit a case to the DB"""
    case = get_case(cid)

    dead_line = dead_line_check(form_dict["dead_line_date"], form_dict["dead_line_time"])

    case.title = bleach.clean(form_dict["title"])
    case.description=bleach.clean(form_dict["description"])
    case.dead_line=dead_line

    update_last_modif(cid)
    db.session.commit()
    

def add_task_core(form_dict, cid):
    """Add a task to the DB"""
    dead_line = dead_line_check(form_dict["dead_line_date"], form_dict["dead_line_time"])

    task = Task(
        uuid=str(uuid.uuid4()),
        title=bleach.clean(form_dict["title"]),
        description=bleach.clean(form_dict["description"]),
        url=bleach.clean(form_dict["url"]),
        creation_date=datetime.datetime.now(),
        last_modif=datetime.datetime.now(),
        dead_line=dead_line,
        case_id=cid,
        status_id=1
    )
    db.session.add(task)
    db.session.commit()

    update_last_modif(cid)

    return task


def add_file_core(task, files_list):
    create_upload_dir(UPLOAD_FOLDER)
    return_files_list = list()
    for file in files_list:
        if files_list[file].filename:
            filename = f"({str(uuid.uuid4())}){secure_filename(files_list[file].filename)}"
            try:
                file_data = request.files[file].read()
                with open(os.path.join(UPLOAD_FOLDER, filename), "wb") as write_file:
                    write_file.write(file_data)
            except Exception as e:
                print(e)
                return False

            f = File(
                name=filename,
                task_id=task.id
            )
            db.session.add(f)
            update_last_modif(task.case_id)
            update_last_modif_task(task.id)
            db.session.commit()
            return_files_list.append(f.to_json())
    return return_files_list

def edit_task_core(form_dict, tid):
    """Edit a task to the DB"""
    task = get_task(tid)
    dead_line = dead_line_check(form_dict["dead_line_date"], form_dict["dead_line_time"])

    task.title = bleach.clean(form_dict["title"])
    task.description=bleach.clean(form_dict["description"])
    task.url=bleach.clean(form_dict["url"])
    task.dead_line=dead_line

    update_last_modif(task.case_id)
    update_last_modif_task(task.id)
    db.session.commit()


def dead_line_check(date, time):
    """Combine the date and the time if time exist"""
    dead_line = None
    if date and time:
        dead_line = datetime.datetime.combine(date, time)
    elif date:
        dead_line = date
    
    return dead_line


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
        if type(user) == str:
            task_user = Task_User(task_id=task.id, user_id=user)
            if not flag_current_user:
                NotifModel.create_notification_user(f"You have been assign to: '{task.id}-{task.title}' of case '{case.id}-{case.title}'", task.case_id, user_id=user, html_icon="fa-solid fa-hand")
        else:
            task_user = Task_User(task_id=task.id, user_id=user.id)
            if not flag_current_user:
                NotifModel.create_notification_user(f"You have been assign to: '{task.id}-{task.title}' of case '{case.id}-{case.title}'", task.case_id, user_id=user.id, html_icon="fa-solid fa-hand")

        db.session.add(task_user)
        update_last_modif(task.case_id)
        update_last_modif_task(task.id)
        db.session.commit()
        return True
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
        if type(user) == int:
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


def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True, download_name=filename.split(")")[1])


def delete_file(file):
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, file.name))
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


def regroup_case_info(cases, user):
    loc = dict()
    loc["cases"] = list()
    
    for case in cases:
        present_in_case = get_present_in_case(case.id, user)
        case_loc = case.to_json()
        case_loc["present_in_case"] = present_in_case
        case_loc["current_user_permission"] = get_role(user).to_json()

        loc["cases"].append(case_loc)

    return loc


def sort_by_ongoing_task_core(case, user):
    tasks_list = Task.query.filter_by(case_id=case.id, completed=False).all()
    return get_task_info(tasks_list, user)
    
def sort_by_finished_task_core(case, user):
    tasks_list = Task.query.filter_by(case_id=case.id, completed=True).all()
    return get_task_info(tasks_list, user)


def sort_tasks_by_filter(case, user, completed, filter):
    if filter == "assigned_tasks":
        final_tasks = list()
        tasks_list_query = Task.query.filter_by(case_id=case.id, completed=completed).all()
        for task in tasks_list_query:
            users, _ = get_users_assign_task(task.id, user)
            if users:
                task.len_u = len(users)
            else:
                task.len_u = 0
            final_tasks.append(task)
        tasks_list = sorted(final_tasks, key=lambda t: t.len_u)

    elif filter == "my_assignment":
        final_tasks = list()
        tasks_list_query = Task.query.filter_by(case_id=case.id, completed=completed).all()
        for task in tasks_list_query:
            _, is_current_user_assigned = get_users_assign_task(task.id, user)
            task.is_current_user_assigned = is_current_user_assigned
            final_tasks.append(task)
        tasks_list = sorted(final_tasks, key=lambda t: t.is_current_user_assigned)

    else:
        tasks_list = Task.query.filter_by(case_id=case.id, completed=completed).order_by(desc(filter)).all()

    return get_task_info(tasks_list, user)


def sort_by_ongoing_core():
    return Case.query.filter_by(completed=False).all()
    
def sort_by_finished_core():
    return Case.query.filter_by(completed=True).all()


def sort_by_filter(completed, filter): 
    return Case.query.filter_by(completed=completed).order_by(desc(filter)).all()


def my_assignment_sort_by_status(user, completed):
    return Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==user.id, Task.completed==completed).all()


def my_assignment_sort_by_filter(user, completed, filter):
    return Task.query.join(Task_User, Task_User.task_id==Task.id).where(Task_User.user_id==user.id, Task.completed==completed).order_by(desc(filter)).all()


def get_all_users_core(case):
    return Org.query.join(Case_Org, Case_Org.case_id==case.id).where(Case_Org.org_id==Org.id).all()


def fork_case_core(cid, case_title_fork, user):
    case_title_stored = get_case_by_title(case_title_fork)
    if case_title_stored:
        return {"message": "Error, title already exist"}
    case = get_case(cid)

    case_json = case.to_json()
    case_json["title"] = case_title_fork

    if case.dead_line:
        case_json["dead_line_date"] = datetime.datetime.strptime(case_json["dead_line"].split(" ")[0], "%Y-%m-%d").date()
        case_json["dead_line_time"] = datetime.datetime.strptime(case_json["dead_line"].split(" ")[1], "%H:%M").time()
    else:
        case_json["dead_line_date"] = None
        case_json["dead_line_time"] = None

    new_case = add_case_core(case_json, user)

    for task in case.tasks:
        task_json = task.to_json()
        if task.dead_line:
            task_json["dead_line_date"] = datetime.datetime.strptime(task_json["dead_line"].split(" ")[0], "%Y-%m-%d").date()
            task_json["dead_line_time"] = datetime.datetime.strptime(task_json["dead_line"].split(" ")[1], "%H:%M").time()
        else:
            task_json["dead_line_date"] = None
            task_json["dead_line_time"] = None

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