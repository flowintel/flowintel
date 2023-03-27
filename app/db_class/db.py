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
        return {"id": self.id, "first_name": self.first_name, "last_name": self.last_name, "email": self.email, "api_key": self.api_key, "org_id": self.org_id}

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
    creation_date = db.Column(db.DateTime)
    dead_line = db.Column(db.DateTime)
    last_modif = db.Column(db.DateTime)
    tasks = db.relationship('Task', backref='case', lazy='dynamic', cascade="all, delete-orphan")
    completed = db.Column(db.Boolean, default=False)

    def to_json(self):
        json_dict = {
            "id": self.id, "uuid": self.uuid, 
            "title": self.title, "description": self.description,
            "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M'),
            "last_modif": self.last_modif.strftime('%Y-%m-%d %H:%M'),
            "completed": self.completed
        }
        if self.dead_line:
            json_dict["dead_line"] = self.dead_line.strftime('%Y-%m-%d %H:%M')
        else:
            json_dict["dead_line"] = self.dead_line

        return json_dict


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    title = db.Column(db.String(64), index=True)
    description = db.Column(db.String, nullable=True)
    url = db.Column(db.String(64), index=True)
    notes = db.Column(db.String, nullable=True)
    creation_date = db.Column(db.DateTime)
    dead_line = db.Column(db.DateTime)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id', ondelete="CASCADE"))
    completed = db.Column(db.Boolean, default=False)

    def to_json(self):
        json_dict = {
            "id": self.id, "uuid": self.uuid, 
            "title": self.title, "description": self.description,
            "url": self.url,
            "notes": self.notes,
            "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M'),
            "completed": self.completed
        }
        if self.dead_line:
            json_dict["dead_line"] = self.dead_line.strftime('%Y-%m-%d %H:%M')
        else:
            json_dict["dead_line"] = self.dead_line

        return json_dict


class Org(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), index=True)
    description = db.Column(db.String, nullable=True)
    users = db.relationship('User', backref='Org', lazy='dynamic', cascade="all, delete-orphan")

    def to_json(self):
        return {
            "id": self.id, 
            "name": self.name, 
            "description": self.description
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

class Task_User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)

class Case_Org(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer)
    org_id = db.Column(db.Integer)


login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))