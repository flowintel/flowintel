import datetime
import json
import uuid
from .. import db, login_manager
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import  UserMixin, AnonymousUserMixin

DATETIME_FORMAT_FULL = '%Y-%m-%d %H:%M'
CASCADE_DELETE_ORPHAN = "all, delete-orphan"
FK_TASK_ID = 'task.id'
FK_CASE_ID = 'case.id'
FK_TASK_TEMPLATE_ID = 'task__template.id'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(64), index=True)
    last_name = db.Column(db.String(64), index=True)
    nickname = db.Column(db.String(64), index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    matrix_id = db.Column(db.String, unique=True, index=True)
    role_id = db.Column(db.Integer, index=True)
    password_hash = db.Column(db.String(165))
    api_key = db.Column(db.String(60), index=True)
    org_id = db.Column(db.Integer, db.ForeignKey('org.id', ondelete="CASCADE"))
    creation_date = db.Column(db.DateTime, index=True, default=datetime.datetime.now(tz=datetime.timezone.utc))

    def is_admin(self):
        r = Role.query.get(self.role_id)
        if r and r.admin:
            return True
        return False

    def read_only(self):
        r = Role.query.get(self.role_id)
        if r and r.read_only:
            return True
        return False

    def is_org_admin(self):
        r = Role.query.get(self.role_id)
        if r and r.org_admin:
            return True
        return False

    def is_pure_org_admin(self):
        return self.is_org_admin() and not self.is_admin()

    def is_case_admin(self):
        r = Role.query.get(self.role_id)
        if r and r.case_admin:
            return True
        return False

    def is_queue_admin(self):
        r = Role.query.get(self.role_id)
        if r and r.queue_admin:
            return True
        return False

    def is_queuer(self):
        r = Role.query.get(self.role_id)
        if r and r.queuer:
            return True
        return False

    @property
    def password(self):
        raise AttributeError('`password` is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_json(self):
        return {
            "id": self.id, 
            "first_name": self.first_name, 
            "last_name": self.last_name, 
            "nickname": self.nickname,
            "email": self.email, 
            "org_id": self.org_id, 
            "role_id": self.role_id,
            "matrix_id": self.matrix_id,
            "creation_date": self.creation_date.strftime(DATETIME_FORMAT_FULL)
        }

class AnonymousUser(AnonymousUserMixin):
    def is_admin(self):
        return False

    def read_only(self):
        return True


class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    title = db.Column(db.String)
    description = db.Column(db.String)
    creation_date = db.Column(db.DateTime, index=True)
    deadline = db.Column(db.DateTime, index=True)
    last_modif = db.Column(db.DateTime, index=True)
    finish_date = db.Column(db.DateTime, index=True)
    tasks = db.relationship('Task', backref='case', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)
    files = db.relationship('File', backref='case', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN, foreign_keys='File.case_id')
    status_id = db.Column(db.Integer, index=True)
    completed = db.Column(db.Boolean, default=False)
    owner_org_id = db.Column(db.Integer, index=True)
    notif_deadline_id = db.Column(db.Integer, index=True)
    recurring_date = db.Column(db.DateTime, index=True)
    recurring_type = db.Column(db.String(30), index=True)
    nb_tasks = db.Column(db.Integer, index=True)
    notes = db.Column(db.String, nullable=True)
    hedgedoc_url = db.Column(db.String, nullable=True)
    time_required = db.Column(db.String)
    is_private = db.Column(db.Boolean, default=False, index=True)
    privileged_case = db.Column(db.Boolean, default=False, index=True)
    ticket_id = db.Column(db.String)
    is_updated_from_misp = db.Column(db.Boolean, default=False)
    computer_assistate_report = db.Column(db.String)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "creation_date": self.creation_date.strftime(DATETIME_FORMAT_FULL),
            "last_modif": self.last_modif.strftime(DATETIME_FORMAT_FULL),
            "status_id": self.status_id,
            "completed": self.completed,
            "owner_org_id": self.owner_org_id,
            "notif_deadline_id": self.notif_deadline_id,
            "recurring_type": self.recurring_type,
            "nb_tasks": self.nb_tasks,
            "notes": self.notes,
            "hedgedoc_url": self.hedgedoc_url,
            "time_required": self.time_required,
            "is_private": self.is_private,
            "privileged_case": self.privileged_case,
            "ticket_id": self.ticket_id,
            "is_updated_from_misp": self.is_updated_from_misp,
            "computer_assistate_report": self.computer_assistate_report
        }
        if self.deadline:
            json_dict["deadline"] = self.deadline.strftime(DATETIME_FORMAT_FULL)
        else:
            json_dict["deadline"] = self.deadline

        if self.finish_date:
            json_dict["finish_date"] = self.finish_date.strftime(DATETIME_FORMAT_FULL)
        else:
            json_dict["finish_date"] = self.finish_date

        if self.recurring_date:
            json_dict["recurring_date"] = self.recurring_date.strftime('%Y-%m-%d')
        else:
            json_dict["recurring_date"] = self.recurring_date

        json_dict["tags"] = [tag.to_json() for tag in Tags.query.join(Case_Tags, Case_Tags.tag_id==Tags.id).filter_by(case_id=self.id).all()]
        json_dict["clusters"] = [cluster.to_json() for cluster in Cluster.query.join(Case_Galaxy_Tags, Case_Galaxy_Tags.case_id==self.id)\
                                                    .where(Cluster.id==Case_Galaxy_Tags.cluster_id).all()]
        json_dict["connectors"] = [connector.to_json() for connector in Connector_Instance.query.join(Case_Connector_Instance, Case_Connector_Instance.instance_id==Connector_Instance.id)\
                                                    .where(Case_Connector_Instance.case_id==self.id).all()]
        
        json_dict["custom_tags"] = [custom_tag.to_json() for custom_tag in Custom_Tags.query.join(Case_Custom_Tags, Case_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                                                    .where(Case_Custom_Tags.case_id==self.id).all()]
        
        json_dict["link_to"] = [{"id": clc.id, "title": clc.title, "description": clc.description} for clc in Case.query.join(Case_Link_Case, Case_Link_Case.case_id_2==Case.id)\
                                                    .where(Case_Link_Case.case_id_1==self.id).all()]

        return json_dict
    
    def download(self):
        json_dict = {
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "recurring_type": self.recurring_type,
            "notes": self.notes,
            "time_required": self.time_required,
            "is_private": self.is_private,
            "ticket_id": self.ticket_id,
            "is_updated_from_misp": self.is_updated_from_misp,
            "computer_assistate_report": self.computer_assistate_report
        }
        if self.deadline:
            json_dict["deadline"] = self.deadline.strftime(DATETIME_FORMAT_FULL)
        else:
            json_dict["deadline"] = self.deadline

        if self.recurring_date:
            json_dict["recurring_date"] = self.recurring_date.strftime('%Y-%m-%d')
        else:
            json_dict["recurring_date"] = self.recurring_date

        json_dict["tags"] = [tag.download() for tag in Tags.query.join(Case_Tags, Case_Tags.tag_id==Tags.id).filter_by(case_id=self.id).all()]
        json_dict["clusters"] = [cluster.download() for cluster in Cluster.query.join(Case_Galaxy_Tags, Case_Galaxy_Tags.case_id==self.id)\
                                                    .where(Cluster.id==Case_Galaxy_Tags.cluster_id).all()]


        return json_dict


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    title = db.Column(db.String)
    description = db.Column(db.String, nullable=True)
    urls_tools = db.relationship('Task_Url_Tool', backref='task', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)
    external_references = db.relationship('Task_External_Reference', backref='task', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)
    notes = db.relationship('Note', backref='task', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)
    creation_date = db.Column(db.DateTime, index=True)
    deadline = db.Column(db.DateTime, index=True)
    last_modif = db.Column(db.DateTime, index=True)
    finish_date = db.Column(db.DateTime, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id', ondelete="CASCADE"))
    status_id = db.Column(db.Integer, index=True)
    completed = db.Column(db.Boolean, default=False)
    notif_deadline_id = db.Column(db.Integer, index=True)
    case_order_id = db.Column(db.Integer, index=True)
    files = db.relationship('File', backref='task', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN, foreign_keys='File.task_id')
    nb_notes = db.Column(db.Integer, index=True)
    subtasks = db.relationship('Subtask', backref='Task', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)
    time_required = db.Column(db.String)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "creation_date": self.creation_date.strftime(DATETIME_FORMAT_FULL),
            "last_modif": self.last_modif.strftime(DATETIME_FORMAT_FULL),
            "case_id": self.case_id,
            "status_id": self.status_id,
            "completed": self.completed,
            "notif_deadline_id": self.notif_deadline_id,
            "case_order_id": self.case_order_id,
            "nb_notes": self.nb_notes,
            "time_required": self.time_required
        }
        json_dict["notes"] = [note.to_json() for note in self.notes]
        json_dict["urls_tools"] = [url_tool.to_json() for url_tool in self.urls_tools]
        json_dict["external_references"] = [ext_ref.to_json() for ext_ref in self.external_references]
        if self.deadline:
            json_dict["deadline"] = self.deadline.strftime(DATETIME_FORMAT_FULL)
        else:
            json_dict["deadline"] = self.deadline

        if self.finish_date:
            json_dict["finish_date"] = self.finish_date.strftime(DATETIME_FORMAT_FULL)
        else:
            json_dict["finish_date"] = self.finish_date

        json_dict["tags"] = [tag.to_json() for tag in Tags.query.join(Task_Tags, Task_Tags.tag_id==Tags.id).filter_by(task_id=self.id).all()]
        json_dict["clusters"] = [cluster.to_json() for cluster in Cluster.query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.task_id==self.id)\
                                                    .where(Cluster.id==Task_Galaxy_Tags.cluster_id).all()]
        json_dict["galaxies"] = [galax.to_json() for galax in Galaxy.query.join(Task_Galaxy, Task_Galaxy.task_id==self.id)\
                                                    .where(Galaxy.id==Task_Galaxy.galaxy_id).all()]
        json_dict["connectors"] = [connector.to_json() for connector in Connector_Instance.query.join(Task_Connector_Instance, Task_Connector_Instance.instance_id==Connector_Instance.id)\
                                                        .where(Task_Connector_Instance.task_id==self.id).all()]
        json_dict["custom_tags"] = [custom_tag.to_json() for custom_tag in Custom_Tags.query.join(Task_Custom_Tags, Task_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                                                    .where(Task_Custom_Tags.task_id==self.id).all()]

        return json_dict
    
    def download(self):
        json_dict = {
            "uuid": self.uuid, 
            "title": self.title, 
            "description": self.description,
            "time_required": self.time_required
        }
        json_dict["notes"] = [note.download() for note in self.notes]
        if self.deadline:
            json_dict["deadline"] = self.deadline.strftime(DATETIME_FORMAT_FULL)
        else:
            json_dict["deadline"] = self.deadline

        json_dict["tags"] = [tag.download() for tag in Tags.query.join(Task_Tags, Task_Tags.tag_id==Tags.id).filter_by(task_id=self.id).all()]
        json_dict["clusters"] = [cluster.download() for cluster in Cluster.query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.task_id==self.id)\
                                                    .where(Cluster.id==Task_Galaxy_Tags.cluster_id).all()]
        
        json_dict["subtasks"] = [subtask.download() for subtask in self.subtasks]
        json_dict["urls_tools"] = [url_tool.download() for url_tool in self.urls_tools]
        json_dict["external_references"] = [ext_ref.download() for ext_ref in self.external_references]

        return json_dict
    
class Subtask(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey(FK_TASK_ID, ondelete="CASCADE"))
    completed = db.Column(db.Boolean, default=False)
    description = db.Column(db.String, nullable=True)
    task_order_id = db.Column(db.Integer, index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "task_id": self.task_id,
            "completed": self.completed,
            "description": self.description,
            "task_order_id": self.task_order_id
        }
        return json_dict
    
    def download(self):
        json_dict = {
            "task_id": self.task_id,
            "description": self.description
        }
        return json_dict


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    note = db.Column(db.String, nullable=True)
    task_id = db.Column(db.Integer, db.ForeignKey(FK_TASK_ID, ondelete="CASCADE"))
    task_order_id = db.Column(db.Integer, index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "uuid": self.uuid,
            "note": self.note,
            "task_id": self.task_id,
            "task_uuid": Task.query.get(self.task_id).uuid,
            "task_order_id": self.task_order_id
        }
        return json_dict

    def download(self):
        json_dict = {
            "uuid": self.uuid,
            "note": self.note,
            "task_uuid": Task.query.get(self.task_id).uuid
        }
        return json_dict
    
class Task_Url_Tool(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey(FK_TASK_ID, ondelete="CASCADE"))
    name = db.Column(db.String, index=True)
    uuid = db.Column(db.String(36), index=True, default=str(uuid.uuid4()))

    def to_json(self):
        json_dict = {
            "id": self.id,
            "name": self.name,
            "task_id": self.task_id,
            "task_uuid": Task.query.get(self.task_id).uuid,
            "uuid": self.uuid
        }
        return json_dict

    def download(self):
        json_dict = {
            "name": self.name,
            "task_uuid": Task.query.get(self.task_id).uuid,
            "uuid": self.uuid
        }
        return json_dict

class Task_External_Reference(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey(FK_TASK_ID, ondelete="CASCADE"))
    url = db.Column(db.String, index=True)
    uuid = db.Column(db.String(36), index=True, default=lambda: str(uuid.uuid4()))

    def to_json(self):
        json_dict = {
            "id": self.id,
            "url": self.url,
            "task_id": self.task_id,
            "task_uuid": self.task.uuid,
            "uuid": self.uuid
        }
        return json_dict

    def download(self):
        json_dict = {
            "url": self.url,
            "task_uuid": self.task.uuid,
            "uuid": self.uuid
        }
        return json_dict

class Org(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True)
    description = db.Column(db.String, nullable=True)
    uuid = db.Column(db.String(36), index=True)
    users = db.relationship('User', backref='Org', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)
    default_org = db.Column(db.Boolean, default=True)

    def owns_cases(self):
        return Case.query.filter_by(owner_org_id=self.id).count() > 0

    def has_users(self):
        return self.users.count() > 0

    def to_json(self):
        owns_cases = self.owns_cases()
        has_users = self.has_users()
        return {
            "id": self.id, 
            "name": self.name, 
            "description": self.description,
            "uuid": self.uuid,
            "default_org": self.default_org,
            "owns_cases": owns_cases,
            "has_users": has_users
        }


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True, unique=True)
    description = db.Column(db.String, nullable=True)
    admin = db.Column(db.Boolean, default=False)
    read_only = db.Column(db.Boolean, default=False)
    org_admin = db.Column(db.Boolean, default=False)
    case_admin = db.Column(db.Boolean, default=False)
    queue_admin = db.Column(db.Boolean, default=False)
    queuer = db.Column(db.Boolean, default=False)

    def to_json(self):
        return {
            "id": self.id, 
            "name": self.name,
            "description": self.description,
            "admin": self.admin,
            "read_only": self.read_only,
            "org_admin": self.org_admin,
            "case_admin": self.case_admin,
            "queue_admin": self.queue_admin,
            "queuer": self.queuer
        }

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True)
    task_id = db.Column(db.Integer, db.ForeignKey(FK_TASK_ID, ondelete="CASCADE"), nullable=True)
    case_id = db.Column(db.Integer, db.ForeignKey(FK_CASE_ID, ondelete="CASCADE"), nullable=True)
    uuid = db.Column(db.String(36), index=True, unique=True)
    upload_date = db.Column(db.DateTime, nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    file_type = db.Column(db.String(100), nullable=True)
    def to_json(self):
        return {
            "id": self.id, 
            "name": self.name,
            "task_id": self.task_id,
            "case_id": self.case_id,
            "uuid": self.uuid,
            "upload_date": self.upload_date.strftime('%Y-%m-%d %H:%M:%S') if self.upload_date else "Unknown",
            "file_size": self.file_size if self.file_size is not None else "Unknown",
            "file_type": self.file_type if self.file_type else "Unknown"
        }

class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(30), index=True, unique=True)
    bootstrap_style = db.Column(db.String(30), index=True)

    def to_json(self):
        return {
            "id": self.id, 
            "name": self.name,
            "bootstrap_style": self.bootstrap_style
        }

class Task_User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)

class Case_Org(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.Integer)
    org_id = db.Column(db.Integer)
    db.UniqueConstraint('case_id', 'org_id', name="case_org")


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message = db.Column(db.String, index=True)
    is_read = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, index=True)
    case_id = db.Column(db.Integer, index=True)
    creation_date = db.Column(db.DateTime, index=True)
    for_deadline = db.Column(db.DateTime, index=True)
    read_date = db.Column(db.DateTime, index=True)
    html_icon = db.Column(db.String(60), index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "message": self.message,
            "is_read": self.is_read,
            "user_id": self.user_id,
            "case_id": self.case_id,
            "html_icon": self.html_icon,
            "creation_date": self.creation_date.strftime(DATETIME_FORMAT_FULL)
        }
        if self.read_date:
            json_dict["read_date"] = self.read_date.strftime(DATETIME_FORMAT_FULL)
        else:
            json_dict["read_date"] = self.read_date

        if self.for_deadline:
            json_dict["for_deadline"] = self.for_deadline.strftime(DATETIME_FORMAT_FULL)
        else:
            json_dict["for_deadline"] = self.for_deadline
        
        return json_dict
    
class Recurring_Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, index=True)
    case_id = db.Column(db.Integer, index=True)
    db.UniqueConstraint('case_id', 'user_id', name="recurring_notif")

    def to_json(self):
        json_dict = {
            "id": self.id,
            "user_id": self.user_id,
            "case_id": self.case_id
        }
        
        return json_dict


class Case_Template(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    title = db.Column(db.String, index=True)
    description = db.Column(db.String, nullable=True)
    last_modif = db.Column(db.DateTime, index=True)
    time_required = db.Column(db.String)
    notes = db.Column(db.String, nullable=True)

    def to_json(self):
        json_dict =  {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "last_modif": self.last_modif.strftime(DATETIME_FORMAT_FULL),
            "time_required": self.time_required,
            "notes": self.notes
        }

        json_dict["tags"] = [tag.to_json() for tag in Tags.query.join(Case_Template_Tags, Case_Template_Tags.tag_id==Tags.id).filter_by(case_id=self.id).all()]
        json_dict["clusters"] = [cluster.to_json() for cluster in Cluster.query.join(Case_Template_Galaxy_Tags, Case_Template_Galaxy_Tags.template_id==self.id)\
                                                    .where(Cluster.id==Case_Template_Galaxy_Tags.cluster_id).all()]
        json_dict["custom_tags"] = [custom_tag.to_json() for custom_tag in Custom_Tags.query.join(Case_Template_Custom_Tags, Case_Template_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                                                    .where(Case_Template_Custom_Tags.case_template_id==self.id).all()]
        json_dict["connector_instances"] = [connector_instance.to_json() for connector_instance in Case_Template_Connector_Instance.query.filter(Case_Template_Connector_Instance.case_template_id==self.id).all()]

        return json_dict
    
    def download(self):
        json_dict = {
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "time_required": self.time_required,
            "notes": self.notes
        }
        json_dict["tags"] = [tag.download() for tag in Tags.query.join(Case_Template_Tags, Case_Template_Tags.tag_id==Tags.id).filter_by(case_id=self.id).all()]
        json_dict["clusters"] = [cluster.download() for cluster in Cluster.query.join(Case_Template_Galaxy_Tags, Case_Template_Galaxy_Tags.template_id==self.id)\
                                                    .where(Cluster.id==Case_Template_Galaxy_Tags.cluster_id).all()]


        return json_dict
    

class Task_Template(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    title = db.Column(db.String, index=True)
    description = db.Column(db.String, nullable=True)
    urls_tools = db.relationship('Task_Template_Url_Tool', backref='task', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)
    notes = db.relationship('Note_Template', backref='task_template', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)
    nb_notes = db.Column(db.Integer, index=True)
    last_modif = db.Column(db.DateTime, index=True)
    subtasks = db.relationship('Subtask_Template', backref='task_template', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)
    time_required = db.Column(db.String)

    def to_json(self):
        json_dict =  {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "nb_notes": self.nb_notes,
            "last_modif": self.last_modif.strftime(DATETIME_FORMAT_FULL),
            "time_required": self.time_required
        }
        json_dict["notes"] = [note.to_json() for note in self.notes]
        json_dict["urls_tools"] = [url_tool.to_json() for url_tool in self.urls_tools]
        json_dict["tags"] = [tag.to_json() for tag in Tags.query.join(Task_Template_Tags, Task_Template_Tags.tag_id==Tags.id).filter_by(task_id=self.id).all()]
        json_dict["clusters"] = [cluster.to_json() for cluster in Cluster.query.join(Task_Template_Galaxy_Tags, Task_Template_Galaxy_Tags.template_id==self.id)\
                                                    .where(Cluster.id==Task_Template_Galaxy_Tags.cluster_id).all()]
        json_dict["galaxies"] = [galax.to_json() for galax in Galaxy.query.join(Task_Template_Galaxy, Task_Template_Galaxy.template_id==self.id)\
                                                    .where(Galaxy.id==Task_Template_Galaxy.galaxy_id).all()]
        json_dict["custom_tags"] = [custom_tag.to_json() for custom_tag in Custom_Tags.query.join(Task_Template_Custom_Tags, Task_Template_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                                                    .where(Task_Template_Custom_Tags.task_template_id==self.id).all()]

        return json_dict
    
    def download(self):
        json_dict =  {
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "time_required": self.time_required
        }
        json_dict["notes"] = [note.download() for note in self.notes]
        json_dict["subtasks"] = [subtask.download() for subtask in self.subtasks]
        json_dict["urls_tools"] = [url_tool.download() for url_tool in self.urls_tools]
        json_dict["tags"] = [tag.download() for tag in Tags.query.join(Task_Template_Tags, Task_Template_Tags.tag_id==Tags.id).filter_by(task_id=self.id).all()]
        json_dict["clusters"] = [cluster.download() for cluster in Cluster.query.join(Task_Template_Galaxy_Tags, Task_Template_Galaxy_Tags.template_id==self.id)\
                                                    .where(Cluster.id==Task_Template_Galaxy_Tags.cluster_id).all()]

        return json_dict
    
class Subtask_Template(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.Integer, db.ForeignKey(FK_TASK_TEMPLATE_ID, ondelete="CASCADE"))
    completed = db.Column(db.Boolean, default=False)
    description = db.Column(db.String, nullable=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "template_id": self.template_id,
            "completed": self.completed,
            "description": self.description
        }
        return json_dict
    
    def download(self):
        json_dict = {
            "description": self.description
        }
        return json_dict
    
class Note_Template(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    note = db.Column(db.String, nullable=True)
    template_id = db.Column(db.Integer, db.ForeignKey(FK_TASK_TEMPLATE_ID, ondelete="CASCADE"))
    template_order_id = db.Column(db.Integer, index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "uuid": self.uuid,
            "note": self.note,
            "template_id": self.template_id,
            "template_uuid": Task_Template.query.get(self.template_id).uuid,
            "template_order_id": self.template_order_id
        }
        return json_dict
    
    def download(self):
        json_dict = {
            "note": self.note,
            "template_uuid": Task_Template.query.get(self.template_id).uuid,
        }
        return json_dict
    
class Task_Template_Url_Tool(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey(FK_TASK_TEMPLATE_ID, ondelete="CASCADE"))
    name = db.Column(db.String, index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "name": self.name,
            "task_id": self.task_id,
        }
        return json_dict

    def download(self):
        json_dict = {
            "name": self.name
        }
        return json_dict
    

class Case_Task_Template(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.Integer, index=True)
    task_id = db.Column(db.Integer, index=True)
    case_order_id = db.Column(db.Integer, index=True)


class Taxonomy(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    exclude = db.Column(db.Boolean, default=False)
    tags = db.relationship('Tags', backref='taxonomy', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)
    version = db.Column(db.String(15))

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "name": self.name,
            "description": self.description,
            "exclude": self.exclude,
            "version": self.version
        }

class Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    name = db.Column(db.String)
    color = db.Column(db.String)
    exclude = db.Column(db.Boolean, default=False)
    description = db.Column(db.String)
    taxonomy_id = db.Column(db.Integer, db.ForeignKey('taxonomy.id', ondelete="CASCADE"))

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "name": self.name,
            "color": self.color,
            "exclude": self.exclude,
            "description": self.description,
            "taxonomy_id": self.taxonomy_id
        }
    
    def download(self):
        return self.name

class Case_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tag_id = db.Column(db.Integer, index=True)
    case_id = db.Column(db.Integer, index=True)

class Task_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tag_id = db.Column(db.Integer, index=True)
    task_id = db.Column(db.Integer, index=True)

class Case_Template_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tag_id = db.Column(db.Integer, index=True)
    case_id = db.Column(db.Integer, index=True)

class Task_Template_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tag_id = db.Column(db.Integer, index=True)
    task_id = db.Column(db.Integer, index=True)


class Galaxy(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    uuid = db.Column(db.String(36), index=True)
    version = db.Column(db.Integer, index=True)
    description = db.Column(db.String)
    icon = db.Column(db.String)
    type = db.Column(db.String)
    exclude = db.Column(db.Boolean, default=False)
    clusters = db.relationship('Cluster', backref='galaxy', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "name": self.name,
            "uuid": self.uuid,
            "version": self.version,
            "description": self.description,
            "icon": self.icon,
            "exclude": self.exclude,
            "type": self.type
        }
        return json_dict

class Cluster(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    uuid = db.Column(db.String(36), index=True)
    version = db.Column(db.Integer, index=True)
    description = db.Column(db.String)
    meta = db.Column(db.String)
    exclude = db.Column(db.Boolean, default=False)
    tag = db.Column(db.String)
    galaxy_id = db.Column(db.Integer, db.ForeignKey('galaxy.id', ondelete="CASCADE"))

    def to_json(self):
        json_dict = {
            "id": self.id,
            "name": self.name,
            "uuid": self.uuid,
            "version": self.version,
            "description": self.description,
            "meta": self.meta,
            "exclude": self.exclude,
            "galaxy_id": self.galaxy_id,
            "tag": self.tag
        }
        json_dict["icon"] = Galaxy.query.get(self.galaxy_id).icon
        return json_dict
    
    def download(self):
        json_dict = {
            "name": self.name,
            "uuid": self.uuid,
            "version": self.version,
            "description": self.description,
            "meta": self.meta,
            "tag": self.tag
        }
        return json_dict
    

class Case_Galaxy_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cluster_id = db.Column(db.Integer, index=True)
    case_id = db.Column(db.Integer, index=True)

class Task_Galaxy_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cluster_id = db.Column(db.Integer, index=True)
    task_id = db.Column(db.Integer, index=True)

class Task_Galaxy(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    galaxy_id = db.Column(db.Integer, index=True)
    task_id = db.Column(db.Integer, index=True)

class Case_Template_Galaxy_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cluster_id = db.Column(db.Integer, index=True)
    template_id = db.Column(db.Integer, index=True)

class Task_Template_Galaxy(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    galaxy_id = db.Column(db.Integer, index=True)
    template_id = db.Column(db.Integer, index=True)

class Task_Template_Galaxy_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cluster_id = db.Column(db.Integer, index=True)
    template_id = db.Column(db.Integer, index=True)


class Connector(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True)
    description = db.Column(db.String)
    uuid = db.Column(db.String(36), index=True)
    icon_id = db.Column(db.Integer, index=True)
    instances = db.relationship('Connector_Instance', backref='connector', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "uuid": self.uuid,
            "icon_id": self.icon_id
        }
        return json_dict
    
class Connector_Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True)
    url = db.Column(db.String(64), index=True)
    description = db.Column(db.String)
    uuid = db.Column(db.String(36), index=True)
    type = db.Column(db.String(36), index=True)
    connector_id = db.Column(db.Integer, db.ForeignKey('connector.id', ondelete="CASCADE"))
    global_api_key = db.Column(db.String(100), index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "uuid": self.uuid,
            "connector_id": self.connector_id,
            "type": self.type,
            "global_api_key": True if self.global_api_key else False
        }
        return json_dict

class Connector_Icon(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True, unique=True)
    description = db.Column(db.String)
    uuid = db.Column(db.String(36), index=True)
    file_icon_id = db.Column(db.Integer, index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "uuid": self.uuid,
            "file_icon_id": self.file_icon_id
        }
        return json_dict

class Icon_File(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True, unique=True)
    uuid = db.Column(db.String(36), index=True)

    def to_json(self):
        return {
            "id": self.id, 
            "name": self.name,
            "uuid": self.uuid
        }


class Case_Connector_Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.Integer, index=True)
    instance_id = db.Column(db.Integer, index=True)
    identifier = db.Column(db.String)
    is_updating_case = db.Column(db.Boolean, default=False)


class Case_Template_Connector_Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_template_id = db.Column(db.Integer, index=True)
    connector_instance_id = db.Column(db.Integer, index=True)
    identifier = db.Column(db.String)

    def to_json(self):
        return {
            "id": self.id, 
            "case_template_id": self.case_template_id,
            "instance": Connector_Instance.query.filter_by(id=self.connector_instance_id).first().to_json(),
            "identifier": self.identifier
        }


class Task_Connector_Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, index=True)
    instance_id = db.Column(db.Integer, index=True)
    identifier = db.Column(db.String)


class User_Connector_Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, index=True)
    instance_id = db.Column(db.Integer, index=True)
    api_key = db.Column(db.String(100), index=True)


class Misp_Module(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, index=True, unique=True)
    description = db.Column(db.String)
    input_attr = db.Column(db.String)
    version = db.Column(db.String(15))

    def to_json(self):
        json_dict = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "input_attr": self.input_attr,
            "version": self.version
        }
        return json_dict
    

class Misp_Module_Result(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True, unique=True)
    modules_list = db.Column(db.String)
    query_enter = db.Column(db.String)
    input_query = db.Column(db.String)
    result=db.Column(db.String)
    nb_errors = db.Column(db.Integer, index=True)
    query_date = db.Column(db.DateTime, index=True)
    user_id = db.Column(db.Integer, index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "uuid": self.uuid,
            "modules": json.loads(self.modules_list),
            "query_enter": json.loads(self.query_enter),
            "input_query": self.input_query,
            "result": json.loads(self.result),
            "nb_errors": self.nb_errors,
            "query_date": self.query_date.strftime(DATETIME_FORMAT_FULL),
            "user_id": self.user_id
        }
        return json_dict
    
    def history_json(self):
        json_dict = {
            "uuid": self.uuid,
            "modules": json.loads(self.modules_list),
            "query": json.loads(self.query_enter),
            "input": self.input_query,
            "query_date": self.query_date.strftime(DATETIME_FORMAT_FULL)
        }
        return json_dict
    

class Configurable_Fields(db.Model):
    """List of elements configurable for modules (api_key,url,...)"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, index=True, unique=True)

class Misp_Module_Config(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_id = db.Column(db.Integer, index=True)
    config_id = db.Column(db.Integer, index=True)
    user_id = db.Column(db.Integer, index=True)
    value = db.Column(db.String, index=True)



    
class Custom_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, index=True, unique=True)
    color = db.Column(db.String(20), index=True)
    icon = db.Column(db.String, index=True, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "icon": self.icon,
            "is_active": self.is_active
        }
        return json_dict
        
class Case_Custom_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.Integer, index=True)
    custom_tag_id = db.Column(db.Integer, index=True)

class Task_Custom_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, index=True)
    custom_tag_id = db.Column(db.Integer, index=True)

class Case_Template_Custom_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_template_id = db.Column(db.Integer, index=True)
    custom_tag_id = db.Column(db.Integer, index=True)

class Task_Template_Custom_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_template_id = db.Column(db.Integer, index=True)
    custom_tag_id = db.Column(db.Integer, index=True)

class Case_Link_Case(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id_1 = db.Column(db.Integer, index=True)
    case_id_2 = db.Column(db.Integer, index=True)


class Case_Misp_Object(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.Integer, index=True)
    template_uuid = db.Column(db.String(36), index=True)
    name = db.Column(db.String)
    creation_date = db.Column(db.DateTime, index=True, default=datetime.datetime.now(tz=datetime.timezone.utc))
    last_modif = db.Column(db.DateTime, index=True, default=datetime.datetime.now(tz=datetime.timezone.utc))
    attributes = db.relationship('Misp_Attribute', backref='Case_Misp_Object', lazy='dynamic', cascade=CASCADE_DELETE_ORPHAN)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "case_id": self.case_id,
            "template_uuid": self.template_uuid,
            "name": self.name,
            "creation_date": self.creation_date.strftime(DATETIME_FORMAT_FULL),
            "last_modif": self.last_modif.strftime(DATETIME_FORMAT_FULL)
        }
        return json_dict
    
    def download(self):
        json_dict = {
            "template_uuid": self.template_uuid,
            "name": self.name
        }
        json_dict["attributes"] = [attr.download() for attr in self.attributes]
        return json_dict

class Misp_Attribute(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_misp_object_id = db.Column(db.Integer, db.ForeignKey('case__misp__object.id', ondelete="CASCADE"))
    value = db.Column(db.String, index=True)
    type = db.Column(db.String, index=True)
    object_relation = db.Column(db.String, index=True)
    first_seen = db.Column(db.DateTime, index=True)
    last_seen = db.Column(db.DateTime, index=True)
    comment = db.Column(db.String, nullable=True)
    ids_flag = db.Column(db.Boolean)
    creation_date = db.Column(db.DateTime, index=True, default=datetime.datetime.now(tz=datetime.timezone.utc))
    last_modif = db.Column(db.DateTime, index=True, default=datetime.datetime.now(tz=datetime.timezone.utc))
    disable_correlation = db.Column(db.Boolean, default=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "case_misp_object_id": self.case_misp_object_id,
            "value": self.value,
            "type": self.type,
            "object_relation": self.object_relation,
            "first_seen": self.first_seen, # Added to the dict here in case of empty
            "last_seen": self.last_seen,   # Added to the dict here in case of empty
            "comment": self.comment,
            "ids_flag": self.ids_flag,
            "creation_date": self.creation_date.strftime(DATETIME_FORMAT_FULL),
            "last_modif": self.last_modif.strftime(DATETIME_FORMAT_FULL),
            "disable_correlation": self.disable_correlation
        }

        if self.first_seen:
            json_dict["first_seen"] = self.first_seen.strftime(DATETIME_FORMAT_FULL)
        if self.last_seen:
            json_dict["last_seen"] = self.last_seen.strftime(DATETIME_FORMAT_FULL)

        return json_dict
    
    def download(self):
        json_dict = {
            "value": self.value,
            "type": self.type,
            "object_relation": self.object_relation,
            "first_seen": self.first_seen, # Added to the dict here in case of empty
            "last_seen": self.last_seen,   # Added to the dict here in case of empty
            "comment": self.comment,
            "ids_flag": self.ids_flag,
            "disable_correlation": self.disable_correlation
        }

        if self.first_seen:
            json_dict["first_seen"] = self.first_seen.strftime('%Y-%m-%dT%H:%M')
        if self.last_seen:
            json_dict["last_seen"] = self.last_seen.strftime('%Y-%m-%dT%H:%M')

        return json_dict

class Misp_Object_Instance_Uuid(db.Model):
    # UUID of an object on a misp instance
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    instance_id = db.Column(db.Integer, index=True)
    misp_object_id = db.Column(db.Integer, index=True)
    object_instance_uuid = db.Column(db.String(36), index=True)
    case_id = db.Column(db.Integer, index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "misp_object_id": self.misp_object_id,
            "instance_id": self.instance_id,
            "object_instance_uuid": self.object_instance_uuid,
            "case_id": self.case_id
        }

        return json_dict
    
class Misp_Attribute_Instance_Uuid(db.Model):
    # UUID of an attribute on a misp instance
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    instance_id = db.Column(db.Integer, index=True)
    misp_attribute_id = db.Column(db.Integer, index=True)
    attribute_instance_uuid = db.Column(db.String(36), index=True)
    case_id = db.Column(db.Integer, index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "misp_attribute_id": self.misp_attribute_id,
            "instance_id": self.instance_id,
            "attribute_instance_uuid": self.attribute_instance_uuid,
            "case_id": self.case_id
        }

        return json_dict
    

class Note_Template_Model(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True, default=str(uuid.uuid4()))
    author = db.Column(db.Integer, index=True)
    title = db.Column(db.String)
    description = db.Column(db.String)
    content = db.Column(db.String)
    params = db.Column(db.JSON)
    creation_date = db.Column(db.DateTime, index=True, default=datetime.datetime.now(tz=datetime.timezone.utc))
    last_modif = db.Column(db.DateTime, index=True, default=datetime.datetime.now(tz=datetime.timezone.utc), onupdate=datetime.datetime.now(tz=datetime.timezone.utc))
    version = db.Column(db.Integer, index=True) # Keep an history of all version so case with old version can keep there notes
    # Will change the version only if params have changes
    # Stay in same version if content change without adding or modifying params

    def to_json(self):
        json_dict = {
            "id": self.id,
            "uuid": self.uuid,
            "author": self.author,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "version": self.version,
            "creation_date": self.creation_date.strftime(DATETIME_FORMAT_FULL),
            "last_modif": self.last_modif.strftime(DATETIME_FORMAT_FULL),
            "params": self.params
        }

        return json_dict

class Case_Note_Template_Model(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.Integer, index=True)
    note_template_id = db.Column(db.Integer, index=True)
    values = db.Column(db.JSON)
    content = db.Column(db.String)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "case_id": self.case_id,
            "note_template_id": self.note_template_id,
            "values": self.values,
            "content": self.content
        }

        return json_dict

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))