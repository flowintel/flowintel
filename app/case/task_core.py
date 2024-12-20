import os
import ast
import uuid
import datetime
from .. import db
from ..db_class.db import *
from ..utils.utils import create_specific_dir

from sqlalchemy import desc, and_
from flask import request, send_file
from werkzeug.utils import secure_filename
from ..notification import notification_core as NotifModel

from . import common_core as CommonModel
from ..custom_tags import custom_tags_core as CustomModel

from app.utils.utils import MODULES, MODULES_CONFIG


UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
FILE_FOLDER = os.path.join(UPLOAD_FOLDER, "files")

def reorder_tasks(case, task_order_id):
    for task_in_case in case.tasks:
        if task_in_case.case_order_id > task_order_id:
            task_in_case.case_order_id -= 1
            db.session.commit()
    case.nb_tasks -= 1
    db.session.commit()

def delete_task(tid, current_user):
    """Delete a task by is id"""
    task = CommonModel.get_task(tid)
    if task is not None:
        for file in task.files:
            try:
                os.remove(os.path.join(FILE_FOLDER, file.uuid))
            except:
                return False
            db.session.delete(file)
            db.session.commit()

        case = CommonModel.get_case(task.case_id)
        task_users = Task_User.query.where(Task_User.task_id==task.id).all()
        for task_user in task_users:
            user = User.query.get(task_user.user_id)
            NotifModel.create_notification_user(f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' was deleted", task.case_id, user_id=user.id, html_icon="fa-solid fa-trash")

        ## Move all task down if possible
        reorder_tasks(case, task.case_order_id)

        Task_Tags.query.filter_by(task_id=task.id).delete()
        Task_Galaxy_Tags.query.filter_by(task_id=task.id).delete()
        Task_User.query.filter_by(task_id=task.id).delete()
        Task_Connector_Instance.query.filter_by(task_id=task.id).delete()
        Note.query.filter_by(task_id=tid).delete()
        Task_Custom_Tags.query.filter_by(task_id=tid).delete()
        db.session.delete(task)
        CommonModel.update_last_modif(task.case_id)
        db.session.commit()

        CommonModel.save_history(case.uuid, current_user, f"Task '{task.title}' deleted")
        return True
    return False


def complete_task(tid, current_user):
    """Complete task by is id"""
    task = CommonModel.get_task(tid)
    if task is not None:
        task.completed = not task.completed

        case = CommonModel.get_case(task.case_id)
        task_users = Task_User.query.where(Task_User.task_id==task.id).all()
        if task.completed:
            task.status_id = Status.query.filter_by(name="Finished").first().id
            task.case_order_id = -1
            reorder_tasks(case, task.case_order_id)
            message = f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' completed"
        else:
            task.status_id = Status.query.filter_by(name="Created").first().id
            case.nb_tasks += 1
            task.case_order_id = case.nb_tasks
            message = f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' revived"
        for task_user in task_users:
            user = User.query.get(task_user.user_id)
            if task.completed:
                message = f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' completed"
                NotifModel.create_notification_user(message, task.case_id, user_id=user.id, html_icon="fa-solid fa-check")
            else:
                message = f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' revived"
                NotifModel.create_notification_user(message, task.case_id, user_id=user.id, html_icon="fa-solid fa-heart-circle-bolt")

        CommonModel.update_last_modif(task.case_id)
        CommonModel.update_last_modif_task(task.id)
        db.session.commit()
        CommonModel.save_history(case.uuid, current_user, f"Task '{task.title}' completed")
        return True
    return False


def create_task(form_dict, cid, current_user):
    """Add a task to the DB"""
    if "template_select" in form_dict and not 0 in form_dict["template_select"]:
        task = CommonModel.create_task_from_template(form_dict["template_select"], cid)
    else:
        deadline = CommonModel.deadline_check(form_dict["deadline_date"], form_dict["deadline_time"])

        case = CommonModel.get_case(cid)
        nb_tasks = 1
        if case.nb_tasks:
            nb_tasks = case.nb_tasks+1
        else:
            case.nb_tasks = 0

        if "completed" in form_dict:
            completed = form_dict["completed"]
        else:
            completed = False

        task = Task(
            uuid=str(uuid.uuid4()),
            title=form_dict["title"],
            description=form_dict["description"],
            url=form_dict["url"],
            creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
            last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
            deadline=deadline,
            case_id=cid,
            status_id=1,
            case_order_id=nb_tasks,
            completed=completed,
            nb_notes=0,
            time_required=form_dict["time_required"]
        )
        db.session.add(task)
        db.session.commit()

        case.nb_tasks += 1
        db.session.commit()

        for tags in form_dict["tags"]:
            tag = CommonModel.get_tag(tags)
            
            task_tag = Task_Tags(
                tag_id=tag.id,
                task_id=task.id
            )
            db.session.add(task_tag)
            db.session.commit()

        for clusters in form_dict["clusters"]:
            cluster = CommonModel.get_cluster_by_name(clusters)
            
            task_galaxy_tag = Task_Galaxy_Tags(
                cluster_id=cluster.id,
                task_id=task.id
            )
            db.session.add(task_galaxy_tag)
            db.session.commit()

        for custom_tag_name in form_dict["custom_tags"]:
            custom_tag = CustomModel.get_custom_tag_by_name(custom_tag_name)
            if custom_tag:
                task_custom_tag = Task_Custom_Tags(
                    task_id=task.id,
                    custom_tag_id=custom_tag.id
                )
                db.session.add(task_custom_tag)
                db.session.commit()

    CommonModel.update_last_modif(cid)

    case = CommonModel.get_case(cid)
    CommonModel.save_history(case.uuid, current_user, f"Task '{task.title}' Created")

    return task


def edit_task_core(form_dict, tid, current_user):
    """Edit a task to the DB"""
    task = CommonModel.get_task(tid)
    deadline = CommonModel.deadline_check(form_dict["deadline_date"], form_dict["deadline_time"])

    task.title = form_dict["title"]
    task.description=form_dict["description"]
    task.url=form_dict["url"]
    task.deadline=deadline
    task.time_required = form_dict["time_required"]

    ## Tags
    task_tag_db = CommonModel.get_task_tags(tid)
    for tags in form_dict["tags"]:
        if not tags in task_tag_db:
            tag = CommonModel.get_tag(tags)
            task_tag = Task_Tags(
                tag_id=tag.id,
                task_id=task.id
            )
            db.session.add(task_tag)
            db.session.commit()
            task_tag_db.append(tags)
    for c_t_db in task_tag_db:
        if not c_t_db in form_dict["tags"]:
            tag = CommonModel.get_tag(c_t_db)
            task_tag = CommonModel.get_task_tags_both(tid, tag.id)
            Task_Tags.query.filter_by(id=task_tag.id).delete()
            db.session.commit()

    ## Clusters
    task_cluster_db = CommonModel.get_task_clusters_uuid(tid)
    for clusters in form_dict["clusters"]:
        if not clusters in task_tag_db:
            cluster = CommonModel.get_cluster_by_uuid(clusters)
            task_tag = Task_Galaxy_Tags(
                cluster_id=cluster.id,
                task_id=task.id
            )
            db.session.add(task_tag)
            db.session.commit()
            task_cluster_db.append(clusters)
    for c_t_db in task_cluster_db:
        if not c_t_db in form_dict["clusters"]:
            cluster = CommonModel.get_cluster_by_uuid(c_t_db)
            task_cluster = CommonModel.get_task_clusters_both(tid, cluster.id)
            Task_Galaxy_Tags.query.filter_by(id=task_cluster.id).delete()
            db.session.commit()

    # Custom tags
    task_custom_tags_db = CommonModel.get_task_custom_tags_name(task.id)
    for custom_tag in form_dict["custom_tags"]:
        if not custom_tag in task_custom_tags_db:
            custom_tag_id = CustomModel.get_custom_tag_by_name(custom_tag).id
            c_t = Task_Custom_Tags(
                task_id=task.id,
                custom_tag_id=custom_tag_id
            )
            db.session.add(c_t)
            db.session.commit()
            task_custom_tags_db.append(custom_tag)
    for c_t_db in task_custom_tags_db:
        if not c_t_db in form_dict["custom_tags"]:
            custom_tag = CustomModel.get_custom_tag_by_name(c_t_db)
            task_custom_tag = CommonModel.get_task_custom_tags_both(task.id, custom_tag_id=custom_tag.id)
            Task_Custom_Tags.query.filter_by(id=task_custom_tag.id).delete()
            db.session.commit()

    CommonModel.update_last_modif(task.case_id)
    CommonModel.update_last_modif_task(task.id)
    db.session.commit()

    case = CommonModel.get_case(task.case_id)
    CommonModel.save_history(case.uuid, current_user, f"Task '{task.title}' edited")


def add_file_core(task, files_list, current_user):
    """Upload a new file"""
    create_specific_dir(UPLOAD_FOLDER)
    create_specific_dir(FILE_FOLDER)
    for file in files_list:
        if files_list[file].filename:
            uuid_loc = str(uuid.uuid4())
            filename = secure_filename(files_list[file].filename)
            try:
                file_data = request.files[file].read()
                with open(os.path.join(FILE_FOLDER, uuid_loc), "wb") as write_file:
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
            CommonModel.update_last_modif(task.case_id)
            CommonModel.update_last_modif_task(task.id)
            db.session.commit()
    case = CommonModel.get_case(task.case_id)
    CommonModel.save_history(case.uuid, current_user, f"File added for task '{task.title}'")
    return True

def modif_note_core(tid, current_user, notes, note_id):
    """Modify a note of a task to the DB"""
    task = CommonModel.get_task(tid)
    if note_id == '-1':
        note = Note(
            uuid=str(uuid.uuid4()),
            note=notes,
            task_id=tid,
            task_order_id=task.nb_notes+1
        )
        task.nb_notes += 1
        db.session.add(note)
        db.session.commit()
    else:
        note = CommonModel.get_task_note(note_id)
        if note:
            if note.task_id == int(tid):
                note.note = notes
            else:
                return {"message": f"This note is not in task {tid}"}
        else:
            return {"message": f"Note not found"}
        
    CommonModel.update_last_modif(task.case_id)
    CommonModel.update_last_modif_task(task.id)
    db.session.commit()
    case = CommonModel.get_case(task.case_id)
    CommonModel.save_history(case.uuid, current_user, f"Notes for '{task.title}' modified")
    return note

def create_note(tid, current_user):
    """Create a new empty note in the task"""
    task = CommonModel.get_task(tid)
    if task:
        note = Note(
            uuid=str(uuid.uuid4()),
            note="",
            task_id=tid,
            task_order_id=task.nb_notes+1
        )
        task.nb_notes += 1
        db.session.add(note)
        db.session.commit()

        CommonModel.update_last_modif(task.case_id)
        CommonModel.update_last_modif_task(task.id)
        db.session.commit()
        case = CommonModel.get_case(task.case_id)
        CommonModel.save_history(case.uuid, current_user, f"Notes for '{task.title}' created")
        return note
    return False

def delete_note(tid, note_id, current_user):
    """Delete note"""
    note = Note.query.get(note_id)
    if note:
        if note.task_id == int(tid):
            Note.query.filter_by(id=note_id).delete()
            db.session.commit()

            task = CommonModel.get_task(tid)
            CommonModel.update_last_modif(task.case_id)
            CommonModel.update_last_modif_task(task.id)
            db.session.commit()
            case = CommonModel.get_case(task.case_id)
            CommonModel.save_history(case.uuid, current_user, f"Notes for '{task.title}' created")
            return True
    return False

def assign_task(tid, user, current_user, flag_current_user):
    """Assign current user to a task"""
    task = CommonModel.get_task(tid)
    case = CommonModel.get_case(task.case_id)
    if task:
        if type(user) == str or type(user) == int:
            user = User.query.get(user)

        task_user = Task_User(task_id=task.id, user_id=user.id)
        if not flag_current_user:
            NotifModel.create_notification_user(f"You have been assign to: '{task.id}-{task.title}' of case '{case.id}-{case.title}'", task.case_id, user_id=user.id, html_icon="fa-solid fa-hand")
   
        if not Task_User.query.filter_by(task_id=task.id, user_id=user.id).first():
            db.session.add(task_user)
            CommonModel.update_last_modif(task.case_id)
            CommonModel.update_last_modif_task(task.id)
            db.session.commit()
            CommonModel.save_history(case.uuid, current_user, f"Task '{task.id}-{task.title}' assigned to {user.first_name} {user.last_name}")
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


def remove_assign_task(tid, user, current_user, flag_current_user):
    """Remove current user to the assignement to a task"""
    task = CommonModel.get_task(tid)
    case = CommonModel.get_case(task.case_id)
    if task:
        if type(user) == int or type(user) == str:
            user = User.query.get(user)
        task_users = Task_User.query.filter_by(task_id=task.id, user_id=user.id).all()
        if not flag_current_user:
            NotifModel.create_notification_user(f"Your assignment have been removed: '{task.id}-{task.title}' of case '{case.id}-{case.title}'", task.case_id, user_id=user.id, html_icon="fa-solid fa-handshake-slash")
        
        for task_user in task_users:
            db.session.delete(task_user)

        CommonModel.update_last_modif(task.case_id)
        CommonModel.update_last_modif_task(task.id)
        db.session.commit()
        CommonModel.save_history(case.uuid, current_user, f"Assignment '{task.title}' removed to {user.first_name} {user.last_name}")
        return True
    return False


def change_task_status(status, task, current_user):
    """Return the status of a task"""
    task.status_id = status
    CommonModel.update_last_modif(task.case_id)
    CommonModel.update_last_modif_task(task.id)
    db.session.commit()

    case = CommonModel.get_case(task.case_id)
    CommonModel.save_history(case.uuid, current_user, f"Status changed for task '{task.title}'")
    return True


def download_file(file):
    """Download a file"""
    return send_file(os.path.join(FILE_FOLDER, file.uuid), as_attachment=True, download_name=file.name)


def delete_file(file, task, current_user):
    """Delete a file"""
    try:
        os.remove(os.path.join(FILE_FOLDER, file.uuid))
    except:
        return False

    db.session.delete(file)
    db.session.commit()

    CommonModel.update_last_modif(task.case_id)
    CommonModel.update_last_modif_task(task.id)
    case = CommonModel.get_case(task.case_id)
    CommonModel.save_history(case.uuid, current_user, f"File deleted for task '{task.title}'")
    return True


def get_task_info(tasks_list, user):
    """Regroup all info on a task"""
    tasks = list()
    for task in tasks_list:
        case = CommonModel.get_case(task.case_id)
        users, is_current_user_assigned = get_users_assign_task(task.id, user)
        file_list = list()
        for file in task.files:
            file_list.append(file.to_json())
        finalTask = task.to_json()
        finalTask["users"] = users
        finalTask["is_current_user_assigned"] = is_current_user_assigned
        finalTask["files"] = file_list
        finalTask["case_title"] = case.title

        finalTask["subtasks"] = []
        cp_open=0
        for subtask in task.subtasks:
            finalTask["subtasks"].append(subtask.to_json())
            if not subtask.completed:
                cp_open += 1
        finalTask["nb_open_subtasks"] = cp_open

        tasks.append(finalTask)
    return tasks


def build_task_query(completed, tags=None, taxonomies=None, galaxies=None, clusters=None, custom_tags=None, filter=None):
    """Build a task query depending on parameters"""
    query = Task.query
    conditions = [Task.completed == completed]

    if tags or taxonomies:
        query = query.join(Task_Tags, Task_Tags.task_id == Task.id)
        query = query.join(Tags, Task_Tags.tag_id == Tags.id)
        if tags:
            conditions.append(Tags.name.in_(list(tags)))

        if taxonomies:
            query = query.join(Taxonomy, Taxonomy.id == Tags.taxonomy_id)
            conditions.append(Taxonomy.name.in_(list(taxonomies)))

    if clusters or galaxies:
        query = query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.task_id == Task.id)
        query = query.join(Cluster, Task_Galaxy_Tags.cluster_id == Cluster.id)
        if clusters:
            conditions.append(Cluster.name.in_(list(clusters)))

        if galaxies:
            query = query.join(Galaxy, Galaxy.id == Cluster.galaxy_id)
            conditions.append(Galaxy.name.in_(list(galaxies)))
    
    if custom_tags:
        query = query.join(Task_Custom_Tags, Task_Custom_Tags.task_id == Task.id)
        query = query.join(Custom_Tags, Task_Custom_Tags.custom_tag_id == Custom_Tags.id)
        conditions.append(Custom_Tags.name.in_(list(custom_tags)))

    if filter:
        query = query.order_by(desc(filter))
    
    return query.filter(and_(*conditions)).order_by(Task.case_order_id).all()

def sort_by_status_task_core(case, user, taxonomies=[], galaxies=[], tags=[], clusters=[], custom_tags=[], or_and_taxo="true", or_and_galaxies="true", completed=False, no_info=False, filter=False):
    """Sort all tasks by completed and depending of taxonomies and galaxies"""

    if tags:
        tags = ast.literal_eval(tags)
    if taxonomies:
        taxonomies = ast.literal_eval(taxonomies)

    if galaxies:
        galaxies = ast.literal_eval(galaxies)
    if clusters:
        clusters = ast.literal_eval(clusters)

    if custom_tags:
        custom_tags = ast.literal_eval(custom_tags)

    tasks = build_task_query(completed, tags, taxonomies, galaxies, clusters, custom_tags, filter)

    if tags or taxonomies or galaxies or clusters or custom_tags:
        if or_and_taxo == "false":
            glob_list = []

            for task in tasks:
                tags_db = task.to_json()["tags"]
                loc_tag = [tag["name"] for tag in tags_db]
                taxo_list = [Taxonomy.query.get(tag["taxonomy_id"]).name for tag in tags_db]

                if (not tags or all(item in loc_tag for item in tags)) and \
                (not taxonomies or all(item in taxo_list for item in taxonomies)):
                    glob_list.append(task)

            tasks = glob_list
        if or_and_galaxies == "false":
            glob_list = []

            for task in tasks:
                clusters_db = task.to_json()["clusters"]
                loc_cluster = [cluster["name"] for cluster in clusters_db]
                galaxies_list = [Galaxy.query.get(cluster["galaxy_id"]).name for cluster in clusters_db]

                if (not clusters or all(item in loc_cluster for item in clusters)) and \
                (not galaxies or all(item in galaxies_list for item in galaxies)):
                    glob_list.append(task)

            tasks = glob_list
    else:
        tasks = Task.query.filter_by(case_id=case.id, completed=completed).order_by(Task.case_order_id).all()

    if no_info:
        return tasks
    return get_task_info(tasks, user)


def sort_tasks_by_filter(case, user, filter, taxonomies=[], galaxies=[], tags=[], clusters=[], custom_tags=[], or_and_taxo="true", or_and_galaxies="true", completed=False):
    """Sort all tasks by a filter and taxonomies and galaxies"""
    tasks_list = sort_by_status_task_core(case, user, taxonomies, galaxies, tags, clusters, custom_tags, or_and_taxo, or_and_galaxies, completed, no_info=True, filter=filter)

    loc_list = list()
    if filter == "assigned_tasks":
        for task in tasks_list:
            if Task_User.query.filter_by(task_id=task.id).first():
                loc_list.append(task)
        tasks_list = loc_list

    elif filter == "my_assignment":
        for task in tasks_list:
            if Task_User.query.filter_by(task_id=task.id, user_id=user.id).first():
                task.is_current_user_assigned = True
                loc_list.append(task)
        tasks_list = loc_list

    elif filter == "deadline":
        # for deadline filter, only task with a deadline defined is required
        loc = list()
        for task in tasks_list:
            if getattr(task, filter):
                loc.append(task)
        tasks_list = loc
    else:
        # status, last_modif, title
        tasks_list.sort(key=lambda x: getattr(x, filter))

    return get_task_info(tasks_list, user)


def change_order(case, task, up_down):
    """Change the order of tasks"""
    for task_in_case in case.tasks:
        # A task move up, case_order_id decrease by one
        if up_down == "true":
            if task_in_case.case_order_id == task.case_order_id - 1:
                task_in_case.case_order_id += 1
                task.case_order_id -= 1
                break
        else:
            if task_in_case.case_order_id == task.case_order_id + 1:
                task_in_case.case_order_id -= 1
                task.case_order_id += 1
                break
    db.session.commit()


def get_task_modules():
    """Return modules for task only"""
    loc_list = {}
    for module in MODULES_CONFIG:
        if MODULES_CONFIG[module]["config"]["case_task"] == 'task':
            loc_list[module] = MODULES_CONFIG[module]
    return loc_list

def get_instance_module_core(module, type_module, task_id, user_id):
    """Return a list of connectors instances for a module"""
    if "connector" in MODULES_CONFIG[module]["config"]:
        connector = CommonModel.get_connector_by_name(MODULES_CONFIG[module]["config"]["connector"])
        instance_list = list()
        for instance in connector.instances:
            if CommonModel.get_user_instance_both(user_id=user_id, instance_id=instance.id):
                if instance.type==type_module:
                    loc_instance = instance.to_json()
                    identifier = CommonModel.get_task_connector_id(instance.id, task_id)
                    if identifier:
                        loc_id = identifier.identifier
                    else:
                        loc_id = None
                    loc_instance["identifier"] = loc_id
                    instance_list.append(loc_instance)
        return instance_list
    return []


def call_module_task(module, instance_id, case, task, user):
    """Run a module"""
    org = CommonModel.get_org(case.owner_org_id)

    case = case.to_json()
    case["org_name"] = org.name
    case["org_uuid"] = org.uuid
    case["status"] = CommonModel.get_status(case["status_id"]).name

    task = task.to_json()
    task["status"] = CommonModel.get_status(task["status_id"]).name


    instance = CommonModel.get_instance(instance_id)
    user_instance = CommonModel.get_user_instance_both(user.id, instance.id)
    task_instance_id = CommonModel.get_task_connector_id(instance.id, task["id"])

    instance = instance.to_json()
    if user_instance:
        instance["api_key"] = user_instance.api_key
    instance["identifier"] = task_instance_id.identifier

    #######
    # RUN #
    #######
    event_id = MODULES[module].handler(instance, case, task, user)
    res = CommonModel.module_error_check(event_id)
    if res:
        return res
    
    ###########
    # RESULTS #
    ###########

    if not task_instance_id:
        tc_instance = Task_Connector_Instance(
            task_id=task["id"],
            instance_id=instance["id"],
            identifier=event_id
        )
        db.session.add(tc_instance)
        db.session.commit()

    elif not task_instance_id.identifier == event_id:
        task_instance_id.identifier = event_id
        db.session.commit()

    CommonModel.save_history(case.uuid, user, f"Task Module {module} used on instances: {instance['name']}")


def call_module_task_no_instance(module, task, case, current_user, user_id):
    user = User.query.get(user_id)
    res = MODULES[module].handler(task, case, current_user, user)
    if isinstance(res, dict):
        return res


def get_subtask(sid):
    return Subtask.query.get(sid)

def complete_subtask(tid, sid, current_user):
    subtask = get_subtask(sid)
    if subtask:
        if subtask.task_id == int(tid):
            subtask.completed = not subtask.completed
            db.session.commit()

            task = CommonModel.get_task(tid)
            CommonModel.update_last_modif(task.case_id)
            CommonModel.update_last_modif_task(task.id)
            db.session.commit()
            case = CommonModel.get_case(task.case_id)
            CommonModel.save_history(case.uuid, current_user, f"Subtask '{subtask.description}' completed for '{task.title}'")
            return True
    return False

def delete_subtask(tid, sid, current_user):
    subtask = get_subtask(sid)
    if subtask:
        if subtask.task_id == int(tid):
            db.session.delete(subtask)
            db.session.commit()

            task = CommonModel.get_task(tid)
            CommonModel.update_last_modif(task.case_id)
            CommonModel.update_last_modif_task(task.id)
            db.session.commit()
            case = CommonModel.get_case(task.case_id)
            CommonModel.save_history(case.uuid, current_user, f"Subtask '{subtask.description}' deleted for '{task.title}'")
            return True
    return False

def create_subtask(tid, subtask_description, current_user):
    subtask = Subtask(
        description=subtask_description,
        task_id=tid
    )
    db.session.add(subtask)
    db.session.commit()

    task = CommonModel.get_task(tid)
    CommonModel.update_last_modif(task.case_id)
    CommonModel.update_last_modif_task(task.id)
    db.session.commit()
    case = CommonModel.get_case(task.case_id)
    CommonModel.save_history(case.uuid, current_user, f"Subtask '{subtask.description}' deleted for '{task.title}'")
    return subtask

def edit_subtask(tid, sid, subtask_description, current_user):
    subtask = get_subtask(sid)
    if subtask:
        if subtask.task_id == int(tid):
            subtask.description = subtask_description
            db.session.commit()

            task = CommonModel.get_task(tid)
            CommonModel.update_last_modif(task.case_id)
            CommonModel.update_last_modif_task(task.id)
            db.session.commit()
            case = CommonModel.get_case(task.case_id)
            CommonModel.save_history(case.uuid, current_user, f"Subtask '{subtask.description}' deleted for '{task.title}'")
            return True
    return False


def add_connector(tid, request_json, current_user) -> bool:
    task = CommonModel.get_task(tid)
    case = CommonModel.get_case(task.case_id)

    for connector in request_json["connectors"]:
        instance = CommonModel.get_instance_by_name(connector["name"])
        if "identifier" in connector: loc_identfier = connector["identifier"]
        else: loc_identfier = ""
        c = Task_Connector_Instance(
            task_id=tid,
            instance_id=instance.id,
            identifier=loc_identfier
        )
        db.session.add(c)
        db.session.commit()

        CommonModel.update_last_modif(task.case_id)
        CommonModel.update_last_modif_task(task.id)
        db.session.commit()
        
        CommonModel.save_history(case.uuid, current_user, f"Connector {instance.name} added to task {task.title}")
    return True

def remove_connector(task_id, instance_id):
    try:
        Task_Connector_Instance.query.filter_by(task_id=task_id, instance_id=instance_id).delete()
        db.session.commit()
    except:
        return False
    return True

def edit_connector(task_id, instance_id, request_json):
    c = Task_Connector_Instance.query.filter_by(task_id=task_id, instance_id=instance_id).first()
    if c:
        c.identifier = request_json["identifier"]
        db.session.commit()
        return True
    return False
