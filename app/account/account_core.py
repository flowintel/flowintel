from app.extensions import db
from app.db_class.db import User, Role, Org
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
    # SSO accounts have their identity managed externally; disallow email changes.
    if not is_sso:
        user.email=form_dict["email"]
    user.matrix_id=matrix_id
    password_changed = "password" in form_dict and form_dict["password"]
    if password_changed:
        user.password=form_dict["password"]

    db.session.commit()

    if password_changed:
        from ..admin.admin_core import _invalidate_user_sessions
        _invalidate_user_sessions(user.id)

def change_api_key(current_user: User) -> str:
    """Change the api key of the user"""
    loc_api_key = generate_api_key()
    current_user.api_key = loc_api_key
    db.session.commit()
    return loc_api_key


def _shared_case_ids(org_a, org_b):
    """Cases both organisations are part of"""
    from app.db_class.db import Case_Org
    a = {c.case_id for c in Case_Org.query.filter_by(org_id=org_a).all()}
    if org_a == org_b:
        return a
    return a & {c.case_id for c in Case_Org.query.filter_by(org_id=org_b).all()}


def get_user_card(user_id, viewer):
    """What the hover card of a user chip shows, or None when the viewer may not see this user.

    Three levels: name, nickname, organisation and open tasks for anyone who may see the user;
    email, role and account date for the same organisation; last login and sign-in method for admins.

    A user is visible to admins, to their own organisation, and to the organisations they
    share a case with: the people who already see their name in those cases. The open
    tasks are only counted in the cases the viewer can see."""
    from app.db_class.db import Task, Task_User
    user = User.query.get(user_id)
    if not user:
        return None
    is_admin = viewer.is_admin()
    shared = _shared_case_ids(viewer.org_id, user.org_id)
    if not is_admin and viewer.org_id != user.org_id and not shared:
        return None

    org = Org.query.get(user.org_id) if user.org_id else None
    role = Role.query.get(user.role_id) if user.role_id else None

    open_tasks = Task.query.join(Task_User, Task_User.task_id == Task.id) \
        .filter(Task_User.user_id == user.id, Task.completed.is_(False))
    if not is_admin:
        open_tasks = open_tasks.filter(Task.case_id.in_(shared or [-1]))

    # What anyone allowed to see the user gets: who they are and their organisation,
    # nothing that is not already visible in the cases they share
    card = {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "nickname": user.nickname,
        "org": {"id": org.id, "name": org.name} if org else None,
        "open_tasks": open_tasks.count(),
        "is_me": user.id == viewer.id,
    }
    # Contact details and role: only for the same organisation (and admins)
    if is_admin or viewer.org_id == user.org_id:
        card["email"] = user.email
        card["role"] = role.name if role else None
        card["role_admin"] = bool(role and role.admin)
        card["member_since"] = user.creation_date.strftime('%Y-%m-%d') if user.creation_date else None
    # Account activity: admins only
    if is_admin:
        card["last_login"] = user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else None
        card["auth_provider"] = user.auth_provider
    return card
