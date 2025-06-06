from .. import db
from ..db_class.db import User, Role, Org

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



def edit_user_core(form_dict, id):
    """Edit the user to the DB"""

    matrix_id = form_dict["matrix_id"]
    if not matrix_id:
        matrix_id = None

    user = get_user(id)

    user.first_name=form_dict["first_name"]
    user.last_name=form_dict["last_name"]
    user.nickname=form_dict["nickname"]
    user.email=form_dict["email"]
    user.matrix_id=matrix_id

    db.session.commit()