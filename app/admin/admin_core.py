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
    if org.default_org:
        cases_orgs = Case_Org.query.filter_by(org_id=org.id)
        for case_org in cases_orgs:
            db.session.delete(case_org)
            db.session.commit()
        db.session.delete(org)
        db.session.commit()
        return True
    return False


def add_user_core(form):
    """Add a user to the DB"""
    user = User(
        first_name=bleach.clean(form.first_name.data),
        last_name=bleach.clean(form.last_name.data),
        email=bleach.clean(form.email.data),
        password=bleach.clean(form.password.data),
        role_id = bleach.clean(form.role.data),
        org_id = bleach.clean(form.org.data),
        api_key = generate_api_key()
    )
    db.session.add(user)
    db.session.commit()

    if form.org.data == "None":
        org = create_default_org(user)

        user.org_id = org.id
        db.session.commit()


def edit_user_core(form, id):
    """Edit the user to the DB"""
    user = get_user(id)
    prev_user_org_id = user.org_id
    flag = False

    if not form.org.data or form.org.data == 'None':
        org = get_org(prev_user_org_id)
        if not org.default_org:
            org = create_default_org(user)
        org_change = str(org.id)
    else:
        org_change = form.org.data
        if not get_org(form.org.data).id == prev_user_org_id:
            flag = True

    user.first_name=bleach.clean(form.first_name.data)
    user.last_name=bleach.clean(form.last_name.data)
    user.role_id = bleach.clean(form.role.data)
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


def add_org_core(form):
    """Add an org to the DB"""
    if form.uuid.data:
        uuid_field = form.uuid.data
    else:
        uuid_field = str(uuid.uuid4())
    org = Org(
        name = bleach.clean(form.name.data),
        description = bleach.clean(form.description.data),
        uuid = uuid_field,
        default_org = False
    )
    db.session.add(org)
    db.session.commit()


def edit_org_core(form, id):
    """Edit the org ot the DB"""
    org = get_org(id)
    if form.uuid.data:
        org.uuid = form.uuid.data
    else:
        org.uuid = str(uuid.uuid4())

    org.name = bleach.clean(form.name.data)
    org.description = bleach.clean(form.description.data)
    
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


def add_role_core(form):
    """Add a role to the DB"""
    role = Role(
        name = bleach.clean(form.name.data),
        description = bleach.clean(form.description.data),
        admin = form.admin.data,
        create_case = form.create_case.data,
        create_task = form.create_task.data,
        remove_case = form.remove_case.data,
        remove_task = form.remove_task.data,
        take_task = form.take_task.data,
        edit_case = form.edit_case.data,
        edit_task = form.edit_task.data,
        edit_task_note = form.edit_task_note.data
    )
    db.session.add(role)
    db.session.commit()


def delete_role_core(id):
    """Delete a role to the DB"""
    role = get_role(id)
    if role:
        db.session.delete(role)
        db.session.commit()
        return True
    else:
        return False
