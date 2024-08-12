from .. import db, login_manager
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import  UserMixin, AnonymousUserMixin


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(64), index=True)
    last_name = db.Column(db.String(64), index=True)
    nickname = db.Column(db.String(64), index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    matrix_id = db.Column(db.String, unique=True, index=True)
    role_id = db.Column(db.Integer, index=True)
    password_hash = db.Column(db.String(128))
    api_key = db.Column(db.String(60), index=True)
    org_id = db.Column(db.Integer, db.ForeignKey('org.id', ondelete="CASCADE"))

    def is_admin(self):
        r = Role.query.get(self.role_id)
        if r.admin:
            return True
        return False

    def read_only(self):
        r = Role.query.get(self.role_id)
        if r.read_only:
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
            "matrix_id": self.matrix_id
        }

class AnonymousUser(AnonymousUserMixin):
    def is_admin(self):
        return False

    def read_only(self):
        return True


class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    title = db.Column(db.String(64), index=True)
    description = db.Column(db.String)
    creation_date = db.Column(db.DateTime, index=True)
    deadline = db.Column(db.DateTime, index=True)
    last_modif = db.Column(db.DateTime, index=True)
    finish_date = db.Column(db.DateTime, index=True)
    tasks = db.relationship('Task', backref='case', lazy='dynamic', cascade="all, delete-orphan")
    status_id = db.Column(db.Integer, index=True)
    completed = db.Column(db.Boolean, default=False)
    owner_org_id = db.Column(db.Integer, index=True)
    notif_deadline_id = db.Column(db.Integer, index=True)
    recurring_date = db.Column(db.DateTime, index=True)
    recurring_type = db.Column(db.String(30), index=True)
    nb_tasks = db.Column(db.Integer, index=True)
    notes = db.Column(db.String, nullable=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M'),
            "last_modif": self.last_modif.strftime('%Y-%m-%d %H:%M'),
            "status_id": self.status_id,
            "completed": self.completed,
            "owner_org_id": self.owner_org_id,
            "notif_deadline_id": self.notif_deadline_id,
            "recurring_type": self.recurring_type,
            "nb_tasks": self.nb_tasks,
            "notes": self.notes
        }
        if self.deadline:
            json_dict["deadline"] = self.deadline.strftime('%Y-%m-%d %H:%M')
        else:
            json_dict["deadline"] = self.deadline

        if self.finish_date:
            json_dict["finish_date"] = self.finish_date.strftime('%Y-%m-%d %H:%M')
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
            "notes": self.notes
        }
        if self.deadline:
            json_dict["deadline"] = self.deadline.strftime('%Y-%m-%d %H:%M')
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
    title = db.Column(db.String(64), index=True)
    description = db.Column(db.String, nullable=True)
    url = db.Column(db.String(64), index=True)
    notes = db.relationship('Note', backref='task', lazy='dynamic', cascade="all, delete-orphan")
    creation_date = db.Column(db.DateTime, index=True)
    deadline = db.Column(db.DateTime, index=True)
    last_modif = db.Column(db.DateTime, index=True)
    finish_date = db.Column(db.DateTime, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id', ondelete="CASCADE"))
    status_id = db.Column(db.Integer, index=True)
    completed = db.Column(db.Boolean, default=False)
    notif_deadline_id = db.Column(db.Integer, index=True)
    case_order_id = db.Column(db.Integer, index=True)
    files = db.relationship('File', backref='task', lazy='dynamic', cascade="all, delete-orphan")
    nb_notes = db.Column(db.Integer, index=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M'),
            "last_modif": self.last_modif.strftime('%Y-%m-%d %H:%M'),
            "case_id": self.case_id,
            "status_id": self.status_id,
            "completed": self.completed,
            "notif_deadline_id": self.notif_deadline_id,
            "case_order_id": self.case_order_id,
            "nb_notes": self.nb_notes,
        }
        json_dict["notes"] = [note.to_json() for note in self.notes]
        if self.deadline:
            json_dict["deadline"] = self.deadline.strftime('%Y-%m-%d %H:%M')
        else:
            json_dict["deadline"] = self.deadline

        if self.finish_date:
            json_dict["finish_date"] = self.finish_date.strftime('%Y-%m-%d %H:%M')
        else:
            json_dict["finish_date"] = self.finish_date

        json_dict["tags"] = [tag.to_json() for tag in Tags.query.join(Task_Tags, Task_Tags.tag_id==Tags.id).filter_by(task_id=self.id).all()]
        json_dict["clusters"] = [cluster.to_json() for cluster in Cluster.query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.task_id==self.id)\
                                                    .where(Cluster.id==Task_Galaxy_Tags.cluster_id).all()]
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
            "url": self.url
        }
        json_dict["notes"] = [note.download() for note in self.notes]
        if self.deadline:
            json_dict["deadline"] = self.deadline.strftime('%Y-%m-%d %H:%M')
        else:
            json_dict["deadline"] = self.deadline

        json_dict["tags"] = [tag.download() for tag in Tags.query.join(Task_Tags, Task_Tags.tag_id==Tags.id).filter_by(task_id=self.id).all()]
        json_dict["clusters"] = [cluster.download() for cluster in Cluster.query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.task_id==self.id)\
                                                    .where(Cluster.id==Task_Galaxy_Tags.cluster_id).all()]

        return json_dict

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    note = db.Column(db.String, nullable=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete="CASCADE"))
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

class Org(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True)
    description = db.Column(db.String, nullable=True)
    uuid = db.Column(db.String(36), index=True)
    users = db.relationship('User', backref='Org', lazy='dynamic', cascade="all, delete-orphan")
    default_org = db.Column(db.Boolean, default=True)

    def to_json(self):
        return {
            "id": self.id, 
            "name": self.name, 
            "description": self.description,
            "uuid": self.uuid,
            "default_org": self.default_org
        }


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True, unique=True)
    description = db.Column(db.String, nullable=True)
    admin = db.Column(db.Boolean, default=False)
    read_only = db.Column(db.Boolean, default=False)

    def to_json(self):
        return {
            "id": self.id, 
            "name": self.name,
            "description": self.description,
            "admin": self.admin,
            "read_only": self.read_only
        }

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True, unique=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete="CASCADE"))
    uuid = db.Column(db.String(36), index=True)

    def to_json(self):
        return {
            "id": self.id, 
            "name": self.name,
            "task_id": self.task_id,
            "uuid": self.uuid
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
    message = db.Column(db.String(60), index=True)
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
            "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M')
        }
        if self.read_date:
            json_dict["read_date"] = self.read_date.strftime('%Y-%m-%d %H:%M')
        else:
            json_dict["read_date"] = self.read_date

        if self.for_deadline:
            json_dict["for_deadline"] = self.for_deadline.strftime('%Y-%m-%d %H:%M')
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
    title = db.Column(db.String(64), index=True)
    description = db.Column(db.String, nullable=True)
    last_modif = db.Column(db.DateTime, index=True)

    def to_json(self):
        json_dict =  {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "last_modif": self.last_modif.strftime('%Y-%m-%d %H:%M')
        }

        json_dict["tags"] = [tag.to_json() for tag in Tags.query.join(Case_Template_Tags, Case_Template_Tags.tag_id==Tags.id).filter_by(case_id=self.id).all()]
        json_dict["clusters"] = [cluster.to_json() for cluster in Cluster.query.join(Case_Template_Galaxy_Tags, Case_Template_Galaxy_Tags.template_id==self.id)\
                                                    .where(Cluster.id==Case_Template_Galaxy_Tags.cluster_id).all()]
        json_dict["connectors"] = [connector.to_json() for connector in Connector_Instance.query.join(Case_Template_Connector_Instance, Case_Template_Connector_Instance.instance_id==Connector_Instance.id)\
                                                        .where(Case_Template_Connector_Instance.template_id==self.id).all()]
        json_dict["custom_tags"] = [custom_tag.to_json() for custom_tag in Custom_Tags.query.join(Case_Template_Custom_Tags, Case_Template_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                                                    .where(Case_Template_Custom_Tags.case_template_id==self.id).all()]


        return json_dict
    
    def download(self):
        json_dict = {
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description
        }
        json_dict["tags"] = [tag.download() for tag in Tags.query.join(Case_Template_Tags, Case_Template_Tags.tag_id==Tags.id).filter_by(case_id=self.id).all()]
        json_dict["clusters"] = [cluster.download() for cluster in Cluster.query.join(Case_Template_Galaxy_Tags, Case_Template_Galaxy_Tags.template_id==self.id)\
                                                    .where(Cluster.id==Case_Template_Galaxy_Tags.cluster_id).all()]


        return json_dict
    

class Task_Template(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    title = db.Column(db.String(64), index=True)
    description = db.Column(db.String, nullable=True)
    url = db.Column(db.String(64), index=True)
    notes = db.relationship('Note_Template', backref='task_template', lazy='dynamic', cascade="all, delete-orphan")
    nb_notes = db.Column(db.Integer, index=True)
    last_modif = db.Column(db.DateTime, index=True)

    def to_json(self):
        json_dict =  {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "nb_notes": self.nb_notes,
            "last_modif": self.last_modif.strftime('%Y-%m-%d %H:%M')
        }
        json_dict["notes"] = [note.to_json() for note in self.notes]
        json_dict["tags"] = [tag.to_json() for tag in Tags.query.join(Task_Template_Tags, Task_Template_Tags.tag_id==Tags.id).filter_by(task_id=self.id).all()]
        json_dict["clusters"] = [cluster.to_json() for cluster in Cluster.query.join(Task_Template_Galaxy_Tags, Task_Template_Galaxy_Tags.template_id==self.id)\
                                                    .where(Cluster.id==Task_Template_Galaxy_Tags.cluster_id).all()]
        json_dict["connectors"] = [connector.to_json() for connector in Connector_Instance.query.join(Task_Template_Connector_Instance, Task_Template_Connector_Instance.instance_id==Connector_Instance.id)\
                                                        .where(Task_Template_Connector_Instance.template_id==self.id).all()]
        json_dict["custom_tags"] = [custom_tag.to_json() for custom_tag in Custom_Tags.query.join(Task_Template_Custom_Tags, Task_Template_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                                                    .where(Task_Template_Custom_Tags.task_template_id==self.id).all()]

        return json_dict
    
    def download(self):
        json_dict =  {
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "url": self.url,
        }
        json_dict["notes"] = [note.to_json() for note in self.notes]
        json_dict["tags"] = [tag.download() for tag in Tags.query.join(Task_Template_Tags, Task_Template_Tags.tag_id==Tags.id).filter_by(task_id=self.id).all()]
        json_dict["clusters"] = [cluster.download() for cluster in Cluster.query.join(Task_Template_Galaxy_Tags, Task_Template_Galaxy_Tags.template_id==self.id)\
                                                    .where(Cluster.id==Task_Template_Galaxy_Tags.cluster_id).all()]

        return json_dict
    
class Note_Template(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    note = db.Column(db.String, nullable=True)
    template_id = db.Column(db.Integer, db.ForeignKey('task__template.id', ondelete="CASCADE"))
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
    

class Case_Task_Template(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.Integer, index=True)
    task_id = db.Column(db.Integer, index=True)
    case_order_id = db.Column(db.Integer, index=True)


class Taxonomy(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    exclude = db.Column(db.Boolean, default=False)
    tags = db.relationship('Tags', backref='taxonomy', lazy='dynamic', cascade="all, delete-orphan")

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "exclude": self.exclude
        }

class Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    color = db.Column(db.String)
    exclude = db.Column(db.Boolean, default=False)
    description = db.Column(db.String)
    taxonomy_id = db.Column(db.Integer, db.ForeignKey('taxonomy.id', ondelete="CASCADE"))
    cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id', ondelete="CASCADE"))

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "exclude": self.exclude,
            "description": self.description,
            "taxonomy_id": self.taxonomy_id,
            "cluster_id": self.cluster_id
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
    clusters = db.relationship('Cluster', backref='galaxy', lazy='dynamic', cascade="all, delete-orphan")

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

class Case_Template_Galaxy_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cluster_id = db.Column(db.Integer, index=True)
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
    instances = db.relationship('Connector_Instance', backref='connector', lazy='dynamic', cascade="all, delete-orphan")

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

    def to_json(self):
        json_dict = {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "uuid": self.uuid,
            "connector_id": self.connector_id,
            "type": self.type
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

class Task_Connector_Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, index=True)
    instance_id = db.Column(db.Integer, index=True)
    identifier = db.Column(db.String)

class Case_Template_Connector_Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.Integer, index=True)
    instance_id = db.Column(db.Integer, index=True)

class Task_Template_Connector_Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.Integer, index=True)
    instance_id = db.Column(db.Integer, index=True)



class User_Connector_Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, index=True)
    instance_id = db.Column(db.Integer, index=True)
    api_key = db.Column(db.String(100), index=True)


class Analyzer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True, unique=True)
    url = db.Column(db.String, index=True)
    is_active = db.Column(db.Boolean, default=True)

    def to_json(self):
        json_dict = {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "is_active": self.is_active
        }
        return json_dict
    
class Custom_Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(25), index=True, unique=True)
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

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))