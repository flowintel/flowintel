import os
from .. import db
from ..db_class.db import Case, Task, Task_User, User, Case_Org, Role, Org, File
from ..utils.utils import isUUID, status_list
import uuid
import bleach
import markdown
import datetime
from sqlalchemy import desc
from flask import request, send_file
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = '/home/dacru/Desktop/Git/flowintel-cm/uploads'


def get_case(id):
    """Return a case by is id"""
    if isUUID(id):
        case = Case.query.filter_by(uuid=id).first()
    elif id.isdigit():
        case = Case.query.get(id)
    else:
        case = None
    return case

def get_task(id):
    """Return a task by is id"""
    if isUUID(id):
        case = Task.query.filter_by(uuid=id).first()
    elif id.isdigit():
        case = Task.query.get(id)
    else:
        case = None
    return case

def get_all_cases():
    """Return all cases"""
    cases = Case.query.order_by(desc(Case.last_modif))
    return cases

def get_role(user):
    """Return role for the current user"""
    return Role.query.get(user.role_id)

def get_org(id):
    """Return an org by is id"""
    return Org.query.get(id)

def get_org_by_name(name):
    """Return an org by is name"""
    return Org.query.filter_by(name=name).first()

def get_org_in_case(org_id, case_id):
    return Case_Org.query.filter_by(case_id=case_id, org_id=org_id).first()


def get_file(fid):
    return File.query.get(fid)


def delete_case(id):
    """Delete a case by is id"""
    case = get_case(id)
    if case is not None:
        # Delete all tasks in the case
        for task in case.tasks:
            delete_task(task.id)

        Case_Org.query.filter_by(case_id=case.id).delete()
        db.session.delete(case)
        db.session.commit()
        return True
    return False

def delete_task(id):
    """Delete a task by is id"""
    task = get_task(id)
    if task is not None:
        for file in task.files:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, file.name))
            except:
                return False
            db.session.delete(file)
            db.session.commit()
        Task_User.query.filter_by(task_id=task.id).delete()
        db.session.delete(task)
        update_last_modif(task.case_id)
        db.session.commit()
        return True
    return False


def update_last_modif(id):
    """Update 'last_modif' of a case"""
    case = Case.query.get(id)
    case.last_modif = datetime.datetime.now()


def complete_task(id):
    """Complete task by is id"""
    task = get_task(id)
    if task is not None:
        if task.completed:
            task.completed = False
        else:
            task.completed=True
        update_last_modif(task.case_id)
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
        dead_line=dead_line
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


def edit_case_core(form_dict, id):
    """Edit a case to the DB"""
    case = get_case(id)

    dead_line = dead_line_check(form_dict["dead_line_date"], form_dict["dead_line_time"])

    case.title = bleach.clean(form_dict["title"])
    case.description=bleach.clean(form_dict["description"])
    case.dead_line=dead_line

    update_last_modif(id)
    db.session.commit()
    

def add_task_core(form_dict, id):
    """Add a task to the DB"""
    dead_line = dead_line_check(form_dict["dead_line_date"], form_dict["dead_line_time"])

    task = Task(
        uuid=str(uuid.uuid4()),
        title=bleach.clean(form_dict["title"]),
        description=bleach.clean(form_dict["description"]),
        url=bleach.clean(form_dict["url"]),
        creation_date=datetime.datetime.now(),
        dead_line=dead_line,
        case_id=id,
        status=0
    )
    db.session.add(task)
    db.session.commit()


    if form_dict["files_upload"]:
        for file in form_dict["files_upload"]["data"]:
            filename = f"({str(uuid.uuid4())}){secure_filename(file.filename)}"
            try:
                file_data = request.files[form_dict["files_upload"]["name"]].read()
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
            db.session.commit()


    update_last_modif(id)

    return task

def edit_task_core(form_dict, id):
    """Edit a task to the DB"""
    task = get_task(id)
    dead_line = dead_line_check(form_dict["dead_line_date"], form_dict["dead_line_time"])

    task.title = bleach.clean(form_dict["title"])
    task.description=bleach.clean(form_dict["description"])
    task.url=bleach.clean(form_dict["url"])
    task.dead_line=dead_line

    update_last_modif(task.case_id)
    db.session.commit()


def dead_line_check(date, time):
    """Combine the date and the time if time exist"""
    dead_line = None
    if date and time:
        dead_line = datetime.datetime.combine(date, time)
    elif date:
        dead_line = date
    
    return dead_line


def modif_note_core(id, notes):
    """Modify a noe of a task to the DB"""
    task = get_task(id)
    if task:
        task.notes = bleach.clean(notes)
        update_last_modif(task.case_id)
        db.session.commit()
        return True
    return False

def get_note_text(id):
    """Return a text note by task's id"""
    task = get_task(id)
    if task:
        return task.notes
    else:
        return ""

def get_note_markdown(id):
    """Return a markdown note by task's id"""
    task = get_task(id)
    if task:
        return markdown_notes(task.notes)
    else:
        return ""

def markdown_notes(notes):
    """Return a markdown version of a note"""
    if notes:
        return markdown.markdown(notes)
    return notes


def add_orgs_case(form_dict, id):
    """Add orgs to case in th DB"""
    for org_id in form_dict["org_id"]:
        case_org = Case_Org(
            case_id=id, 
            org_id=org_id
        )
        db.session.add(case_org)

    update_last_modif(id)
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


def remove_org_case(case_id, org_id):
    """Remove an org from a case"""
    case_org = Case_Org.query.filter_by(case_id=case_id, org_id=org_id).first()
    if case_org:
        db.session.delete(case_org)
        update_last_modif(case_id)
        db.session.commit()
        return True
    return False


def assign_task(id, user):
    """Assign current user to a task"""
    task = get_task(id)
    if task:
        # if Task_User.query.filter_by(task_id=task.id, user_id=user.id).first():
        #     return 
        task_user = Task_User(task_id=task.id, user_id=user.id)

        db.session.add(task_user)
        update_last_modif(task.case_id)
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


def remove_assign_task(id, user):
    """Remove current user to the assignement to a task"""
    task = get_task(id)
    if task:
        task_users = Task_User.query.filter_by(task_id=task.id, user_id=user.id).all()
        for task_user in task_users:
            db.session.delete(task_user)

        update_last_modif(task.case_id)
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


def change_status(status, task):
    task.status = status
    update_last_modif(task.case_id)
    db.session.commit()

    return True

def get_status():
    return status_list()


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