from .. import db, login_manager
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import  UserMixin, AnonymousUserMixin


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(64), index=True)
    last_name = db.Column(db.String(64), index=True)
    email = db.Column(db.String(64), unique=True, index=True)
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
            "email": self.email, 
            "org_id": self.org_id, 
            "role_id": self.role_id
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
            "recurring_type": self.recurring_type
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

        return json_dict


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    title = db.Column(db.String(64), index=True)
    description = db.Column(db.String, nullable=True)
    url = db.Column(db.String(64), index=True)
    notes = db.Column(db.String, nullable=True)
    creation_date = db.Column(db.DateTime, index=True)
    deadline = db.Column(db.DateTime, index=True)
    last_modif = db.Column(db.DateTime, index=True)
    finish_date = db.Column(db.DateTime, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id', ondelete="CASCADE"))
    status_id = db.Column(db.Integer, index=True)
    completed = db.Column(db.Boolean, default=False)
    notif_deadline_id = db.Column(db.Integer, index=True)
    files = db.relationship('File', backref='task', lazy='dynamic', cascade="all, delete-orphan")

    def to_json(self):
        json_dict = {
            "id": self.id, "uuid": self.uuid, 
            "title": self.title, "description": self.description,
            "url": self.url,
            "notes": self.notes,
            "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M'),
            "last_modif": self.last_modif.strftime('%Y-%m-%d %H:%M'),
            "case_id": self.case_id,
            "status_id": self.status_id,
            "completed": self.completed,
            "notif_deadline_id": self.notif_deadline_id
        }
        if self.deadline:
            json_dict["deadline"] = self.deadline.strftime('%Y-%m-%d %H:%M')
        else:
            json_dict["deadline"] = self.deadline

        if self.finish_date:
            json_dict["finish_date"] = self.finish_date.strftime('%Y-%m-%d %H:%M')
        else:
            json_dict["finish_date"] = self.finish_date

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


class Case_Template(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    title = db.Column(db.String(64), index=True)
    description = db.Column(db.String, nullable=True)

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description
        }
    

class Task_Template(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    title = db.Column(db.String(64), index=True)
    description = db.Column(db.String, nullable=True)
    url = db.Column(db.String(64), index=True)

    def to_json(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "url": self.url
        }
    

class Case_Task_Template(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.Integer, index=True)
    task_id = db.Column(db.Integer, index=True)



login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))