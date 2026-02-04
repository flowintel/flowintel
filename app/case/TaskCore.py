import os
from typing import List
import uuid
import datetime
from flask import current_app
from .. import db
from ..db_class.db import (
    Cluster, Custom_Tags, File, Note, Status, Subtask, Tags, Task,
    Task_Connector_Instance, Task_Custom_Tags, Task_Galaxy_Tags,
    Task_Tags, Task_Url_Tool, Task_User, User
)
from ..utils.utils import create_specific_dir

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from flask import request, send_file
from werkzeug.utils import secure_filename
from ..notification import notification_core as NotifModel

from . import common_core as CommonModel
from ..custom_tags import custom_tags_core as CustomModel

from app.utils.utils import get_modules_list

from .CommonAbstract import CommonAbstract
from .FilteringAbstract import FilteringAbstract


UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
FILE_FOLDER = os.path.join(UPLOAD_FOLDER, "files")

class TaskCore(CommonAbstract, FilteringAbstract):
    def get_class(self) -> Task:
        return Task
    
    def get_tags(self) -> Task_Tags:
        return Task_Tags

    def get_tag_class_id(self) -> int:
        return Task_Tags.task_id

    def get_galaxies(self) -> Task_Galaxy_Tags:
        return Task_Galaxy_Tags

    def get_galaxies_class_id(self) -> int:
        return Task_Galaxy_Tags.task_id

    def get_custom_tags(self) -> Task_Custom_Tags:
        return Task_Custom_Tags

    def get_custom_tags_class_id(self) -> int:
        return Task_Custom_Tags.task_id
    
    
    def get_assigned_tags(self, class_id) -> List:
        """Return a list of tags present in a task"""
        return [tag.name for tag in Tags.query.join(Task_Tags, Task_Tags.tag_id==Tags.id).filter_by(task_id=class_id).all()]

    def get_assigned_clusters_uuid(self, class_id) -> List:
        """Return a list of clusters uuid present in a task"""
        return [cluster.uuid for cluster in \
            Cluster.query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.cluster_id==Cluster.id)\
                .filter_by(task_id=class_id).all()]

    def get_assigned_custom_tags_name(self, class_id) -> List:
        return [c_t.name for c_t in \
            Custom_Tags.query.join(Task_Custom_Tags, Task_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                .where(Task_Custom_Tags.task_id==class_id).all()]

    def add_tag(self, tag, class_id) -> None:
        task_tag = Task_Tags(
            tag_id=tag.id,
            task_id=class_id
        )
        db.session.add(task_tag)
        db.session.commit()

    def delete_tag(self, tag, class_id) -> None:
        task_tag = CommonModel.get_task_tags_both(class_id, tag.id)
        Task_Tags.query.filter_by(id=task_tag.id).delete()
        db.session.commit()

    def add_cluster(self, cluster, class_id) -> None:
        task_galaxy_tag = Task_Galaxy_Tags(
            cluster_id=cluster.id,
            task_id=class_id
        )
        db.session.add(task_galaxy_tag)
        db.session.commit()

    def delete_cluster(self, cluster, class_id) -> None:
        task_cluster = CommonModel.get_task_clusters_both(class_id, cluster.id)
        Task_Galaxy_Tags.query.filter_by(id=task_cluster.id).delete()
        db.session.commit()

    def add_custom_tag(self, custom_tag, class_id) -> None:
        c_t = Task_Custom_Tags(
            task_id=class_id,
            custom_tag_id=custom_tag.id
        )
        db.session.add(c_t)
        db.session.commit()

    def delete_custom_tag(self, custom_tag, class_id) -> None:
        task_custom_tag = CommonModel.get_task_custom_tags_both(class_id, custom_tag_id=custom_tag.id)
        Task_Custom_Tags.query.filter_by(id=task_custom_tag.id).delete()
        db.session.commit()
    


    def update_task_time_modification(self, task, current_user, message):
        CommonModel.update_last_modif(task.case_id)
        CommonModel.update_last_modif_task(task.id)
        db.session.commit()
        case = CommonModel.get_case(task.case_id)
        CommonModel.save_history(case.uuid, current_user, message)

    def reorder_tasks(self, case, task_to_delete_id):
        # Filter out the task to delete
        remaining_tasks = [t for t in case.tasks if t.id != task_to_delete_id]

        # Sort remaining tasks by case_order_id
        remaining_tasks = sorted(remaining_tasks, key=lambda t: t.case_order_id)

        # Reassign order IDs sequentially starting from 1
        for i, task in enumerate(remaining_tasks, start=1):
            task.case_order_id = i
            
        # Commit changes to DB
        db.session.commit()

    def delete_task(self, tid, current_user, case_deleted=False):
        """Delete a task by is id"""
        task = CommonModel.get_task(tid)
        if task is not None:
            for file in task.files:
                try:
                    os.remove(os.path.join(FILE_FOLDER, file.uuid))
                except OSError:
                    return False
                db.session.delete(file)
                db.session.commit()

            case = CommonModel.get_case(task.case_id)
            if not case_deleted:
                task_users = Task_User.query.where(Task_User.task_id==task.id).all()
                for task_user in task_users:
                    user = User.query.get(task_user.user_id)
                    NotifModel.create_notification_user(f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' was deleted", task.case_id, user_id=user.id, html_icon="fa-solid fa-trash")

                ## Move all task down if possible
                self.reorder_tasks(case, task.id)

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

    def get_nb_open_tasks(self, case):
        loc_open = 0
        for task in case.tasks:
            if not task.completed:
                loc_open += 1
        return loc_open

    def complete_task(self, tid, current_user):
        """Complete task by is id"""
        task = CommonModel.get_task(tid)
        if task is not None:
            task.completed = not task.completed

            case = CommonModel.get_case(task.case_id)
            task_users = Task_User.query.where(Task_User.task_id==task.id).all()
            if task.completed:
                task.status_id = Status.query.filter_by(name="Finished").first().id
                task.finish_date = datetime.datetime.now(tz=datetime.timezone.utc)
                task.case_order_id = -1
                self.reorder_tasks(case, task.id)
            else:
                task.status_id = Status.query.filter_by(name="Created").first().id
                task.finish_date = None
                task.case_order_id = self.get_nb_open_tasks(case)
            for task_user in task_users:
                if task.completed:
                    message = f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' completed"
                    NotifModel.create_notification_user(message, task.case_id, user_id=task_user.user_id, html_icon="fa-solid fa-check")
                else:
                    message = f"Task '{task.id}-{task.title}' of case '{case.id}-{case.title}' revived"
                    NotifModel.create_notification_user(message, task.case_id, user_id=task_user.user_id, html_icon="fa-solid fa-heart-circle-bolt")

            self.update_task_time_modification(task, current_user, f"Task '{task.title}' completed")
            return True
        return False


    def create_task(self, form_dict, cid, current_user):
        """Add a task to the DB"""
        if "template_select" in form_dict and 0 not in form_dict["template_select"]:
            task = CommonModel.create_task_from_template(form_dict["template_select"], cid, current_user)
        else:
            deadline = CommonModel.deadline_check(form_dict["deadline_date"], form_dict["deadline_time"])

            case = CommonModel.get_case(cid)
            case.nb_tasks = case.nb_tasks or 0

            status_id = 1
            if case.privileged_case and current_user.is_queuer() and not current_user.is_admin() and not current_user.is_case_admin() and not current_user.is_queue_admin():
                status_id = current_app.config['TASK_REQUESTED']

            task = Task(
                uuid=str(uuid.uuid4()),
                title=form_dict["title"],
                description=form_dict["description"],
                creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
                last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
                deadline=deadline,
                case_id=cid,
                status_id=status_id,
                case_order_id=self.get_nb_open_tasks(case)+1,
                completed=form_dict.get("completed", False),
                nb_notes=0,
                time_required=form_dict["time_required"]
            )
            db.session.add(task)
            db.session.commit()

            case.nb_tasks += 1
            db.session.commit()

            for tags in form_dict["tags"]:
                tag = CommonModel.get_tag(tags)
                
                self.add_tag(tag, task.id)

            for clusters in form_dict["clusters"]:
                cluster = CommonModel.get_cluster_by_name(clusters)
                
                self.add_cluster(cluster, task.id)

            for custom_tag_name in form_dict["custom_tags"]:
                custom_tag = CustomModel.get_custom_tag_by_name(custom_tag_name)
                if custom_tag:
                    self.add_custom_tag(custom_tag, task.id)

            # Auto-assign queuer to task if they created it in a privileged case with Requested status
            if status_id == current_app.config['TASK_REQUESTED']:
                task_user = Task_User(
                    task_id=task.id,
                    user_id=current_user.id
                )
                db.session.add(task_user)
                db.session.commit()
                
                # Notify users who can approve the task (Admin, Case Admin, Queue Admin in owner org)
                NotifModel.create_notification_for_approvers(
                    message=f"New task '{task.id}-{task.title}' requested by {current_user.first_name} {current_user.last_name} in case '{case.id}-{case.title}'. You can approve or reject this task.",
                    case_id=cid,
                    org_id=case.owner_org_id,
                    html_icon="fa-solid fa-circle-exclamation"
                )

        CommonModel.update_last_modif(cid)

        case = CommonModel.get_case(cid)
        CommonModel.save_history(case.uuid, current_user, f"Task '{task.title}' Created")

        return task


    def edit_task_core(self, form_dict, tid, current_user):
        """Edit a task to the DB"""
        task = CommonModel.get_task(tid)
        deadline = CommonModel.deadline_check(form_dict["deadline_date"], form_dict["deadline_time"])

        task.title = form_dict["title"]
        task.description=form_dict["description"]
        task.deadline=deadline
        task.time_required = form_dict["time_required"]

        ## Tags
        self._edit(form_dict, tid)

        self.update_task_time_modification(task, current_user, f"Task '{task.title}' edited")
    
    def can_edit_requested_task(self, current_user):
        """Check if user can edit a task in Requested or Rejected status"""
        return current_user.is_admin() or current_user.is_case_admin() or current_user.is_queue_admin()
    
    def is_task_restricted(self, task):
        """Check if task is in a restricted status (Requested or Rejected) in a privileged case"""
        case = CommonModel.get_case(task.case_id)
        if not case:
            return False
        return case.privileged_case and task.status_id in (current_app.config['TASK_REQUESTED'], current_app.config['TASK_REJECTED'])


    def add_file_core(self, task, files_list, current_user):
        """Upload a new file"""
        create_specific_dir(UPLOAD_FOLDER)
        create_specific_dir(FILE_FOLDER)
        created_files = []
        for file in files_list:
            if files_list[file].filename:
                uuid_loc = str(uuid.uuid4())
                filename = secure_filename(files_list[file].filename)
                try:
                    file_data = request.files[file].read()
                    file_size = len(file_data)
                    with open(os.path.join(FILE_FOLDER, uuid_loc), "wb") as write_file:
                        write_file.write(file_data)
                except Exception as e:
                    print(e)
                    return None

                file_type = files_list[file].content_type if files_list[file].content_type else filename.rsplit('.', 1)[-1] if '.' in filename else 'unknown'

                f = File(
                    name=filename,
                    task_id=task.id,
                    uuid=uuid_loc,
                    upload_date=datetime.datetime.now(tz=datetime.timezone.utc),
                    file_size=file_size,
                    file_type=file_type
                )
                db.session.add(f)
                created_files.append(f)
        
        if created_files:
            self.update_task_time_modification(task, current_user, f"File added for task '{task.title}'")
        return created_files

    def modif_note_core(self, tid, current_user, notes, note_id):
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

        self.update_task_time_modification(task, current_user, f"Notes for '{task.title}' modified")
        return note

    def create_note(self, tid, current_user):
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

            self.update_task_time_modification(task, current_user, f"Notes for '{task.title}' created")
            return note
        return False

    def delete_note(self, tid, note_id, current_user):
        """Delete note"""
        note = Note.query.get(note_id)
        if note and note.task_id == int(tid):
            Note.query.filter_by(id=note_id).delete()
            db.session.commit()

            task = CommonModel.get_task(tid)
            self.update_task_time_modification(task, current_user, f"Notes for '{task.title}' deleted")
            return True
        return False

    def assign_task(self, tid, user, current_user, flag_current_user):
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
                self.update_task_time_modification(task, current_user, f"Task '{task.id}-{task.title}' assigned to {user.first_name} {user.last_name}")
                return True
            return False
        return False

    def get_users_assign_task(self, task_id, user):
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


    def remove_assign_task(self, tid, user, current_user, flag_current_user):
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

            self.update_task_time_modification(task, current_user, f"Assignment '{task.title}' removed to {user.first_name} {user.last_name}")
            return True
        return False


    def change_task_status(self, status, task, current_user):
        """Return the status of a task"""
        old_status_id = task.status_id
        task.status_id = status
        self.update_task_time_modification(task, current_user, f"Status changed for task '{task.title}'")
        
        case = CommonModel.get_case(task.case_id)
        if case and case.privileged_case:
            if status == current_app.config['TASK_APPROVED'] and old_status_id == current_app.config['TASK_REQUESTED']:
                approval_msg = f"Your task '{task.id}-{task.title}' in case '{case.id}-{case.title}' has been approved by an administrator"
                
                NotifModel.create_notification_for_approvers(
                    message=approval_msg,
                    case_id=task.case_id,
                    org_id=case.owner_org_id,
                    html_icon="fa-solid fa-circle-check"
                )
                
                task_users = Task_User.query.filter_by(task_id=task.id).all()
                for task_user in task_users:
                    NotifModel.create_notification_user(
                        message=approval_msg,
                        case_id=task.case_id,
                        user_id=task_user.user_id,
                        html_icon="fa-solid fa-circle-check"
                    )
            
            elif status == current_app.config['TASK_REJECTED'] and old_status_id == current_app.config['TASK_REQUESTED']:
                rejection_msg = f"Your task '{task.id}-{task.title}' in case '{case.id}-{case.title}' has been rejected by an administrator"
                
                NotifModel.create_notification_for_approvers(
                    message=rejection_msg,
                    case_id=task.case_id,
                    org_id=case.owner_org_id,
                    html_icon="fa-solid fa-circle-xmark"
                )
                
                task_users = Task_User.query.filter_by(task_id=task.id).all()
                for task_user in task_users:
                    NotifModel.create_notification_user(
                        message=rejection_msg,
                        case_id=task.case_id,
                        user_id=task_user.user_id,
                        html_icon="fa-solid fa-circle-xmark"
                    )
        
        return True


    def download_file(self, file):
        """Download a file"""
        return send_file(os.path.join(FILE_FOLDER, file.uuid), as_attachment=True, download_name=file.name)


    def delete_file(self, file, task, current_user):
        """Delete a file"""
        try:
            os.remove(os.path.join(FILE_FOLDER, file.uuid))
        except OSError:
            return False

        db.session.delete(file)
        db.session.commit()

        self.update_task_time_modification(task, current_user, f"File deleted for task '{task.title}'")
        return True


    def get_task_info(self, tasks_list, user):
        """Regroup all info on a task"""
        tasks = list()
        for task in tasks_list:
            case = CommonModel.get_case(task.case_id)
            users, is_current_user_assigned = self.get_users_assign_task(task.id, user)
            file_list = list()
            for file in task.files:
                file_list.append(file.to_json())
            final_task = task.to_json()
            final_task["users"] = users
            final_task["is_current_user_assigned"] = is_current_user_assigned
            final_task["files"] = file_list
            final_task["case_title"] = case.title
            
            # Set can_edit flag - for Requested/Rejected tasks, only Admin/CaseAdmin/QueueAdmin can edit
            if self.is_task_restricted(task):
                final_task["can_edit"] = self.can_edit_requested_task(user)
            else:
                final_task["can_edit"] = not user.read_only()

            final_task["subtasks"] = []
            cp_open=0
            subtasks = Subtask.query.filter_by(task_id=task.id).order_by(Subtask.task_order_id).all()
            for subtask in subtasks:
                final_task["subtasks"].append(subtask.to_json())
                if not subtask.completed:
                    cp_open += 1
            final_task["nb_open_subtasks"] = cp_open

            tasks.append(final_task)
        return tasks


    def build_task_query(self, case_id, completed, tags=None, taxonomies=None, galaxies=None, clusters=None, custom_tags=None):
        """Build a task query depending on parameters"""
        query, conditions = self._build_sort_query(completed, tags, taxonomies, galaxies, clusters, custom_tags)
        
        return query.where(Task.case_id==case_id).filter(and_(*conditions)).order_by(Task.case_order_id).all()

    def sort_tasks(self, case, user, taxonomies=[], galaxies=[], tags=[], clusters=[], custom_tags=[], or_and_taxo="true", or_and_galaxies="true", completed=False, filter=False, title_search=None):
        """Sort all tasks by completed and depending of taxonomies and galaxies"""


        if tags or taxonomies or galaxies or clusters or custom_tags:
            tasks = self.build_task_query(case.id, completed, tags, taxonomies, galaxies, clusters, custom_tags)
            tasks = self._sort(tasks, taxonomies, galaxies, tags, clusters, or_and_taxo, or_and_galaxies)
        else:
            tasks = Task.query.filter_by(case_id=case.id, completed=completed).order_by(Task.case_order_id).all()

        if filter:
            loc_list = list()
            if filter == "assigned_tasks":
                for task in tasks:
                    if Task_User.query.filter_by(task_id=task.id).first():
                        loc_list.append(task)
                tasks = loc_list

            elif filter == "my_assignment":
                for task in tasks:
                    if Task_User.query.filter_by(task_id=task.id, user_id=user.id).first():
                        task.is_current_user_assigned = True
                        loc_list.append(task)
                tasks = loc_list

            elif filter == "deadline":
                # for deadline filter, only task with a deadline defined is required
                loc = list()
                for task in tasks:
                    if getattr(task, filter):
                        loc.append(task)
                tasks = loc
            else:
                # status, last_modif, title
                tasks.sort(key=lambda x: getattr(x, filter))

            # apply title search filter if provided
            if title_search:
                ql = title_search.lower()
                tasks = [t for t in tasks if ql in getattr(t, 'title','').lower()]

            return self.get_task_info(tasks, user)

        # apply title search when no 'filter' parameter used
        if title_search:
            ql = title_search.lower()
            tasks = [t for t in tasks if ql in getattr(t, 'title','').lower()]

        return self.get_task_info(tasks, user)

    def change_order(self, case, task, request_json):
        """Change the order of tasks"""
        # Get tasks ordered by case_order_id
        tasks_list = [t for t in case.tasks if not t.completed]
        tasks = sorted(tasks_list, key=lambda t: t.case_order_id)
        target_task = None
        for t in tasks:
            if t.case_order_id == int(request_json["new-index"])+1:
                target_task = t
                break

        if target_task:

            moving_task = task

            # Find index where to insert
            target_index = tasks.index(target_task)

            # Remove the moving task from the list
            tasks.remove(moving_task)

            # Insert the task before the target
            tasks.insert(target_index, moving_task)

            # Reassign order IDs
            for i, loc_task in enumerate(tasks, start=1):
                loc_task.case_order_id = i

            db.session.commit()
            return True
        return False


    def get_task_modules(self):
        """Return modules for task only"""
        loc_list = {}
        _, res = get_modules_list()
        for module in res:
            if res[module]["config"]["case_task"] == 'task':
                loc_list[module] = res[module]
        return loc_list

    def get_instance_module_core(self, module, type_module, task_id, user_id):
        """Return a list of connectors instances for a module"""
        _, res = get_modules_list()
        if "connector" in res[module]["config"]:
            connector = CommonModel.get_connector_by_name(res[module]["config"]["connector"])
            instance_list = list()
            for instance in connector.instances:
                if CommonModel.get_user_instance_both(user_id=user_id, instance_id=instance.id) and instance.type == type_module:
                    loc_instance = instance.to_json()
                    identifier = CommonModel.get_task_connector_id(instance.id, task_id)
                    loc_instance["identifier"] = identifier.identifier if identifier else None
                    instance_list.append(loc_instance)
            return instance_list
        return []


    def call_module_task(self, module, task_instance_id, case, task, user):
        """Run a module"""
        org = CommonModel.get_org(case.owner_org_id)

        case = case.to_json()
        case["org_name"] = org.name
        case["org_uuid"] = org.uuid
        case["status"] = CommonModel.get_status(case["status_id"]).name

        task = task.to_json()
        task["status"] = CommonModel.get_status(task["status_id"]).name


        task_instance = CommonModel.get_task_connectors_by_id(task_instance_id)
        instance = CommonModel.get_instance(task_instance.instance_id)
        user_instance = CommonModel.get_user_instance_both(user.id, instance.id)

        instance = instance.to_json()
        if user_instance:
            instance["api_key"] = user_instance.api_key
        instance["identifier"] = task_instance.identifier

        #######
        # RUN #
        #######
        modules, _ = get_modules_list()
        event_uuid = modules[module].handler(instance, case, task, user)
        res = CommonModel.module_error_check(event_uuid)
        if res:
            return res
        
        ###########
        # RESULTS #
        ###########

        if not task_instance:
            tc_instance = Task_Connector_Instance(
                task_id=task["id"],
                instance_id=instance["id"],
                identifier=event_uuid
            )
            db.session.add(tc_instance)
            db.session.commit()

        elif not task_instance.identifier == event_uuid:
            task_instance.identifier = event_uuid
            db.session.commit()

        CommonModel.save_history(case["uuid"], user, f"Task Module {module} used on instances: {instance['name']}")


    def call_module_task_no_instance(self, module, task, case, current_user, user_id):
        user = User.query.get(user_id)
        modules, _ = get_modules_list()
        res = modules[module].handler(task, case, current_user, user)
        if isinstance(res, dict):
            return res
        

    ##############
    # Urls/Tools #
    ##############

    def get_url_tool(self, utid):
        return Task_Url_Tool.query.get(utid)

    def delete_url_tool(self, tid, utid, current_user):
        url_tool = self.get_url_tool(utid)
        if url_tool and url_tool.task_id == int(tid):
            db.session.delete(url_tool)
            db.session.commit()

            task = CommonModel.get_task(tid)
            self.update_task_time_modification(task, current_user, f"Url/Tool '{url_tool.name}' deleted for '{task.title}'")
            return True
        return False

    def create_url_tool(self, tid, url_tool_name, current_user):
        url_tool = Task_Url_Tool(
            name=url_tool_name,
            task_id=tid,
            uuid=str(uuid.uuid4())
        )
        db.session.add(url_tool)
        db.session.commit()

        task = CommonModel.get_task(tid)
        self.update_task_time_modification(task, current_user, f"Url/Tool '{url_tool.name}' created for '{task.title}'")
        return url_tool

    def edit_url_tool(self, tid, utid, url_tool_name, current_user):
        url_tool = self.get_url_tool(utid)
        if url_tool and url_tool.task_id == int(tid):
            url_tool.name = url_tool_name
            db.session.commit()

            task = CommonModel.get_task(tid)
            self.update_task_time_modification(task, current_user, f"Url/Tool '{url_tool.name}' edited for '{task.title}'")
            return True
        return False
    
    ############
    # Subtasks #
    ############

    def get_subtask(self, sid):
        return Subtask.query.get(sid)

    def complete_subtask(self, tid, sid, current_user):
        subtask = self.get_subtask(sid)
        if subtask and subtask.task_id == int(tid):
            subtask.completed = not subtask.completed
            db.session.commit()

            task = CommonModel.get_task(tid)
            self.update_task_time_modification(task, current_user, f"Subtask '{subtask.description}' completed for '{task.title}'")
            return True
        return False

    def delete_subtask(self, tid, sid, current_user):
        subtask = self.get_subtask(sid)
        if subtask and subtask.task_id == int(tid):
            db.session.delete(subtask)
            db.session.commit()

            task = CommonModel.get_task(tid)
            self.update_task_time_modification(task, current_user, f"Subtask '{subtask.description}' deleted for '{task.title}'")
            return True
        return False

    def create_subtask(self, tid, subtask_description, current_user):
        task = CommonModel.get_task(tid)
        cp = 0

        for _ in task.subtasks:
            cp += 1

        subtask = Subtask(
            description=subtask_description,
            task_id=tid,
            task_order_id=cp
        )
        db.session.add(subtask)
        db.session.commit()

        task = CommonModel.get_task(tid)
        self.update_task_time_modification(task, current_user, f"Subtask '{subtask.description}' created for '{task.title}'")
        return subtask

    def edit_subtask(self, tid, sid, subtask_description, current_user):
        subtask = self.get_subtask(sid)
        if subtask and subtask.task_id == int(tid):
            subtask.description = subtask_description
            db.session.commit()

            task = CommonModel.get_task(tid)
            self.update_task_time_modification(task, current_user, f"Subtask '{subtask.description}' edited for '{task.title}'")
            return True
        return False
    
    def change_order_subtask(self, task, subtask, up_down):
        """Change the order of tasks"""
        for subtask_in_task in task.subtasks:
            # A task move up, case_order_id decrease by one
            if up_down == "true":
                if subtask_in_task.task_order_id == subtask.task_order_id - 1:
                    subtask_in_task.task_order_id += 1
                    subtask.task_order_id -= 1
                    break
            else:
                if subtask_in_task.task_order_id == subtask.task_order_id + 1:
                    subtask_in_task.task_order_id -= 1
                    subtask.task_order_id += 1
                    break
        db.session.commit()

    ##############
    # Connectors #
    ##############

    def add_connector(self, tid, request_json, current_user) -> bool:
        task = CommonModel.get_task(tid)

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

            self.update_task_time_modification(task, current_user, f"Connector {instance.name} added to task {task.title}")
        return True

    def remove_connector(self, task_instance_id):
        try:
            Task_Connector_Instance.query.filter_by(id=task_instance_id).delete()
            db.session.commit()
        except SQLAlchemyError:
            return False
        return True

    def edit_connector(self, task_instance_id, request_json):
        c = Task_Connector_Instance.query.filter_by(id=task_instance_id).first()
        if c:
            c.identifier = request_json["identifier"]
            db.session.commit()
            return True
        return False
    
TaskModel = TaskCore()