from .. import db
from ..db_class.db import User, Role, Org, Case_Org
import bleach
from ..utils.utils import generate_api_key

def get_all_users():
    return User.query.all()

def get_all_roles():
    return Role.query.all()

def get_all_orgs():
    return Org.query.all()

def get_user(id):
    return User.query.get(id)


def create_default_org(user):
    org = Org(
        name = bleach.clean(f"{user.first_name} {user.last_name}"),
        description = bleach.clean(f"Org for user: {user.id}-{user.first_name} {user.last_name}")
    )
    db.session.add(org)
    db.session.commit()

    return org


def delete_default_org(user_org_id, user_first_name, user_last_name):
    org = Org.query.get(user_org_id)
    if org.name == f"{user_first_name} {user_last_name}":
        cases_orgs = Case_Org.query.filter_by(org_id=org.id)
        for case_org in cases_orgs:
            db.session.delete(case_org)
            db.session.commit()
        db.session.delete(org)
        db.session.commit()


def add_user_core(form):
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
    user = get_user(id)
    flag = False

    if not form.org.data or form.org.data == 'None':
        org = Org.query.filter_by(name=f"{user.first_name} {user.last_name}").first()
        if not org:
            org = create_default_org(user)
        org_change = str(org.id)
    else:
        prev_user_org_id = user.org_id
        prev_user_first_name = user.first_name
        prev_user_last_name = user.last_name
        org_change = form.org.data
        flag = True

    user.first_name=bleach.clean(form.first_name.data)
    user.last_name=bleach.clean(form.last_name.data)
    user.role_id = bleach.clean(form.role.data)
    user.org_id = org_change

    db.session.commit()

    if flag:
        delete_default_org(prev_user_org_id, prev_user_first_name, prev_user_last_name)


def add_org_core(form):
    org = Org(
        name = bleach.clean(form.name.data),
        description = bleach.clean(form.description.data)
    )
    db.session.add(org)
    db.session.commit()


def add_role_core(form):
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