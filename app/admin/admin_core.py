from .. import db
from ..db_class.db import User, Role, Org, Case_Org, Task_User
import bleach
from ..utils.utils import generate_api_key
import uuid

def get_all_users():
    """Return all users"""
    return User.query.all()

def get_all_roles():
    """Return all roles"""
    return Role.query.all()

def get_all_orgs():
    """Return all organisations"""
    return Org.query.all()

def get_user(id):
    """Return the user"""
    return User.query.get(id)

def get_org(id):
    """Return the org"""
    return Org.query.get(id)

def get_role(id):
    """Return the role"""
    return Role.query.get(id)

def get_all_user_org(org_id):
    """Return all users of an org"""
    return User.query.join(Org, User.org_id==Org.id).where(Org.id==org_id).all()


def create_default_org(user):
    """Create a default org for a user who have no org"""
    o_d = Org.query.filter_by(name=f"{user.first_name} {user.last_name}").first()
    if not o_d:
        org = Org(
            name = bleach.clean(f"{user.first_name} {user.last_name}"),
            description = bleach.clean(f"Org for user: {user.id}-{user.first_name} {user.last_name}"),
            uuid = str(uuid.uuid4()),
            default_org = True
        )
        db.session.add(org)
        db.session.commit()

        return org
    return o_d


def delete_default_org(user_org_id):
    """Delete the default org for the user"""
    org = Org.query.get(user_org_id)
    cp = 0
    for user in org.users:
        cp += 1
    if org.default_org and not cp > 0:
        db.session.delete(org)
        db.session.commit()
        return True
    return False


def add_user_core(form_dict):
    """Add a user to the DB"""
    user = User(
        first_name=bleach.clean(form_dict["first_name"]),
        last_name=bleach.clean(form_dict["last_name"]),
        email=bleach.clean(form_dict["email"]),
        password=bleach.clean(form_dict["password"]),
        role_id = bleach.clean(form_dict["role"]),
        org_id = bleach.clean(form_dict["org"]),
        api_key = generate_api_key()
    )
    db.session.add(user)
    db.session.commit()

    if not form_dict["org"] or form_dict["org"] == "None":
        org = create_default_org(user)

        user.org_id = org.id
        db.session.commit()

    return user


def admin_edit_user_core(form_dict, id):
    """Edit the user to the DB"""
    user = get_user(id)
    prev_user_org_id = user.org_id
    flag = False

    if not form_dict["org"] or form_dict["org"] == 'None':
        org = get_org(prev_user_org_id)
        if not org.default_org:
            org = create_default_org(user)
        org_change = str(org.id)
    else:
        org_change = form_dict["org"]
        if not get_org(form_dict["org"]).id == prev_user_org_id:
            flag = True

    user.first_name=bleach.clean(form_dict["first_name"])
    user.last_name=bleach.clean(form_dict["last_name"])
    user.email=bleach.clean(form_dict["email"])
    if form_dict["password"]:
        user.password=bleach.clean(form_dict["password"])
    user.role_id = bleach.clean(form_dict["role"])
    user.org_id = org_change

    db.session.commit()

    if flag:
        delete_default_org(prev_user_org_id)


def delete_user_core(id):
    """Delete the user to the DB"""
    user = get_user(id)
    if user:
        if not delete_default_org(user.org_id):
            db.session.delete(user)
            db.session.commit()
        return True
    else:
        return False


def add_org_core(form_dict):
    """Add an org to the DB"""
    if form_dict["uuid"]:
        uuid_field = form_dict["uuid"]
    else:
        uuid_field = str(uuid.uuid4())
    org = Org(
        name = bleach.clean(form_dict["name"]),
        description = bleach.clean(form_dict["description"]),
        uuid = uuid_field,
        default_org = False
    )
    db.session.add(org)
    db.session.commit()


def edit_org_core(form_dict, id):
    """Edit the org ot the DB"""
    org = get_org(id)
    if form_dict["uuid"]:
        org.uuid = form_dict["uuid"]
    else:
        org.uuid = str(uuid.uuid4())

    org.name = bleach.clean(form_dict["name"])
    org.description = bleach.clean(form_dict["description"])
    
    db.session.commit()


def delete_org_core(id):
    """Delete the org to the DB"""
    org = get_org(id)
    if org:
        for user in org.users:
            tasks_users = Task_User.query.filter_by(user_id=user.id)
            for task_user in tasks_users:
                db.session.delete(task_user)
                db.session.commit()

        db.session.delete(org)
        db.session.commit()
        return True
    else:
        return False


def add_role_core(form_dict):
    """Add a role to the DB"""
    role = Role(
        name = bleach.clean(form_dict["name"]),
        description = bleach.clean(form_dict["description"]),
        admin = form_dict["admin"],
        read_only = form_dict["read_only"]
    )
    db.session.add(role)
    db.session.commit()

    return role


def delete_role_core(id):
    """Delete a role to the DB"""
    role = get_role(id)
    if role:
        db.session.delete(role)
        db.session.commit()
        return True
    else:
        return False
