from .. import db
from ..db_class.db import User, Role, Org
from ..utils.utils import generate_api_key

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



def edit_user_core(form_dict, id, is_sso=False):
    """Edit the user to the DB"""

    matrix_id = form_dict["matrix_id"]
    if not matrix_id:
        matrix_id = None

    user = get_user(id)

    user.first_name=form_dict["first_name"]
    user.last_name=form_dict["last_name"]
    user.nickname=form_dict["nickname"]
    # SSO accounts have their identity managed by Entra ID; disallow email changes.
    if not is_sso:
        user.email=form_dict["email"]
    user.matrix_id=matrix_id
    if "password" in form_dict and form_dict["password"]:
        user.password=form_dict["password"]

    db.session.commit()

def change_api_key(current_user: User) -> str:
    """Change the api key of the user"""
    loc_api_key = generate_api_key()
    current_user.api_key = loc_api_key
    db.session.commit()
    return loc_api_key