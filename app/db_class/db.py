from .. import db, login_manager
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import  UserMixin
import datetime


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(64), index=True)
    last_name = db.Column(db.String(64), index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    role = db.Column(db.String(64), index=True)
    password_hash = db.Column(db.String(128))

    def can(self, permissions):
        return self.role == permissions

    @property
    def password(self):
        raise AttributeError('`password` is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_json(self):
        return {"id": self.id, "first_name": self.first_name, "last_name": self.last_name, "email": self.email}


class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), index=True)
    title = db.Column(db.String(64), index=True)
    description = db.Column(db.String)
    creation_date = db.Column(db.DateTime)
    dead_line = db.Column(db.DateTime)
    last_modif = db.Column(db.DateTime)
    tasks = db.relationship('Task', backref='case', lazy='dynamic', cascade="all, delete-orphan")

    def to_json(self):
        json_dict = {
            "id": self.id, "uuid": self.uuid, 
            "title": self.title, "description": self.description,
            "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M'),
            "last_modif": self.last_modif.strftime('%Y-%m-%d %H:%M')
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
    notes = db.Column(db.String, nullable=True)
    creation_date = db.Column(db.DateTime)
    dead_line = db.Column(db.DateTime)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id', ondelete="CASCADE"))

    def to_json(self):
        json_dict = {
            "id": self.id, "uuid": self.uuid, 
            "title": self.title, "description": self.description, 
            "notes": self.notes,
            "creation_date": self.creation_date.strftime('%Y-%m-%d %H:%M')
        }
        if self.dead_line:
            json_dict["dead_line"] = self.dead_line.strftime('%Y-%m-%d %H:%M')
        else:
            json_dict["dead_line"] = self.dead_line

        return json_dict


class Case_User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)


class Task_User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))