import datetime
import os
import msgspec
import uuid

from flask import current_app

from app.extensions import db
from app.db_class.db import session_user_id
from app.db_class.db import Cluster, Galaxy, User, Role, Org, Case_Org, Task_User, Taxonomy, Notification, Recurring_Notification, Login_Event, User_Connector_Instance, Misp_Module_Config, Misp_Module_Result
from ..utils.utils import generate_api_key


def get_all_users():
    """Return all users"""
    return User.query.all()

def get_users_by_org(org_id):
    """Return all users filtered by organisation"""
    return User.query.filter_by(org_id=org_id).all()

def user_directory_is_limited(viewer):
    return current_app.config.get('LIMIT_USER_VIEW_TO_ORG', False) and not viewer.is_admin()


def get_visible_users(viewer):
    """Scope directory queries to the authenticated viewer before selecting rows."""
    query = User.query
    if user_directory_is_limited(viewer):
        if viewer.org_id is None:
            return query.filter_by(id=viewer.id)
        return query.filter_by(org_id=viewer.org_id)
    return query


def _filter_users(query, name=None, role_type=None, role_id=None, org_id=None):
    """Filters of the users page, applied on top of the viewer's visible users.

    - `name`: case-insensitive partial match on first name, last name, nickname or email
    - `role_type`: 'admin', 'read_only' or 'editor' (neither admin nor read only)
    - `role_id`, `org_id`: one role / one organisation
    """
    if name:
        like = f"%{name}%"
        query = query.filter(db.or_(User.first_name.ilike(like), User.last_name.ilike(like),
                                    User.nickname.ilike(like), User.email.ilike(like)))
    if role_type in ("admin", "read_only", "editor"):
        roles = Role.query
        if role_type == "admin":
            roles = roles.filter(Role.admin.is_(True))
        elif role_type == "read_only":
            roles = roles.filter(Role.read_only.is_(True), Role.admin.isnot(True))
        else:
            roles = roles.filter(Role.admin.isnot(True), Role.read_only.isnot(True))
        query = query.filter(User.role_id.in_([r.id for r in roles.all()] or [-1]))
    if role_id:
        query = query.filter(User.role_id == role_id)
    if org_id:
        query = query.filter(User.org_id == org_id)
    return query


def get_users_page(page, viewer, name=None, role_type=None, role_id=None, org_id=None):
    """Return visible users by page, with the filters of _filter_users."""
    query = _filter_users(get_visible_users(viewer), name, role_type, role_id, org_id)
    query = query.order_by(db.func.lower(User.first_name), db.func.lower(User.last_name))
    return query.paginate(page=page, per_page=20, max_per_page=50)


def get_users_facets(viewer):
    """Counts for the filters of the users page, over the users the viewer can see"""
    visible = get_visible_users(viewer)
    roles = {r.id: r for r in Role.query.all()}
    by_role, by_org = {}, {}
    types = {"admin": 0, "editor": 0, "read_only": 0}
    for role_id, org_id in visible.with_entities(User.role_id, User.org_id).all():
        by_role[role_id] = by_role.get(role_id, 0) + 1
        by_org[org_id] = by_org.get(org_id, 0) + 1
        r = roles.get(role_id)
        types["admin" if r and r.admin else "read_only" if r and r.read_only else "editor"] += 1
    orgs = {o.id: o.name for o in Org.query.filter(Org.id.in_([o for o in by_org if o] or [-1])).all()}
    return {
        "total": sum(by_role.values()),
        "types": types,
        "roles": sorted([{"id": rid, "name": roles[rid].name if rid in roles else "Unknown", "count": n,
                          "kind": "admin" if rid in roles and roles[rid].admin else "read_only" if rid in roles and roles[rid].read_only else "editor"}
                         for rid, n in by_role.items()], key=lambda x: x["name"].lower()),
        "orgs": sorted([{"id": oid, "name": orgs.get(oid, "No organisation"), "count": n}
                        for oid, n in by_org.items()], key=lambda x: x["name"].lower()),
    }

def get_all_roles():
    """Return all roles"""
    return Role.query.all()

def get_all_orgs():
    """Return all organisations"""
    return Org.query.all()

def get_orgs_page(page, name=None):
    """Return organisations by page, optionally filtered by partial case-insensitive name."""
    query = Org.query
    if name:
        query = query.filter(Org.name.ilike(f"%{name}%"))
    query = query.order_by(db.func.lower(Org.name))
    return query.paginate(page=page, per_page=20, max_per_page=50)

def get_roles_page(page, name=None):
    """Return roles by page, optionally filtered by partial case-insensitive name."""
    query = Role.query
    if name:
        query = query.filter(Role.name.ilike(f"%{name}%"))
    return query.paginate(page=page, per_page=20, max_per_page=50)

def get_user(id):
    """Return the user"""
    return User.query.get(id)

def get_user_by_lastname(lastname, viewer):
    # Case-insensitive partial match for last name
    return get_visible_users(viewer).filter(User.last_name.ilike(f"%{lastname}%")).all()

def get_user_by_matrix_id(matrix_id, viewer):
    return get_visible_users(viewer).filter_by(matrix_id=matrix_id).first()

def get_org(id):
    """Return the org"""
    return Org.query.get(id)

def get_role(id):
    """Return the role"""
    return Role.query.get(id)

def get_all_user_org(org_id):
    """Return all users of an org"""
    return User.query.join(Org, User.org_id==Org.id).where(Org.id==org_id).all()

def get_all_user_role(role_id):
    """Return all users of a role"""
    return User.query.join(Role, User.role_id==Role.id).where(Role.id==role_id).all()


## Taxonomies
def get_taxonomies():
    return [taxo.to_json() for taxo in Taxonomy.query.all()]

def _filter_items(items, name=None, enabled=None):
    if name:
        name_l = name.lower()
        items = [i for i in items if name_l in i.get('name', '').lower()]
    if enabled == 'true':
        items = [i for i in items if not i.get('exclude', False)]
    elif enabled == 'false':
        items = [i for i in items if i.get('exclude', False)]
    return items

_SORTABLE_KEYS = {'name', 'description', 'version', 'type', 'exclude'}

def _sort_items(items, sort=None, order='asc'):
    """Sort taxonomies/galaxies on one of their fields. Unknown keys keep the DB order."""
    if sort not in _SORTABLE_KEYS:
        return items

    def key(item):
        value = item.get(sort)
        if sort == 'version':
            try:
                return (0, float(value), '')
            except (TypeError, ValueError):
                return (1, 0, str(value or ''))
        if isinstance(value, bool):
            return (0, int(value), '')
        return (0, 0, str(value or '').lower())

    return sorted(items, key=key, reverse=(order == 'desc'))

def get_nb_page_taxo(name=None, enabled=None):
    """Return number of pages for taxonomies, optionally filtered by name and enabled status."""
    taxo_list = _filter_items(get_taxonomies(), name=name, enabled=enabled)
    return int(len(taxo_list) / 25) + 1

def get_taxonomy_counts(name=None):
    taxo_list = _filter_items(get_taxonomies(), name=name)
    total = len(taxo_list)
    enabled = sum(1 for t in taxo_list if not t.get('exclude', False))
    return {"total": total, "enabled": enabled}

def get_tags(taxonomy_id):
    taxonomy = Taxonomy.query.get(taxonomy_id)
    if not taxonomy:
        return None
    return [tag.to_json() for tag in taxonomy.tags]


## Galaxies
def get_galaxies():
    return [galax.to_json() for galax in Galaxy.query.order_by('name').all()]

def get_galaxy(galaxy_id):
    return Galaxy.query.get(galaxy_id)

def get_clusters():
    return [cluster.to_json() for cluster in Cluster.query.all()]

def get_clusters_galaxy(galaxy_id):
    galaxy = get_galaxy(galaxy_id)
    if not galaxy:
        return None
    return [cluster.to_json() for cluster in galaxy.clusters]

def get_nb_page_galaxies(name=None, enabled=None):
    """Return number of pages for galaxies, optionally filtered by name and enabled status."""
    gal_list = _filter_items(get_galaxies(), name=name, enabled=enabled)
    return int(len(gal_list) / 25) + 1

def get_galaxy_counts(name=None):
    gal_list = _filter_items(get_galaxies(), name=name)
    total = len(gal_list)
    enabled = sum(1 for g in gal_list if not g.get('exclude', False))
    return {"total": total, "enabled": enabled}

def get_tags_galaxy(galaxy_id):
    galaxy = get_galaxy(galaxy_id)
    if not galaxy:
        return None
    return [cluster.tag for cluster in galaxy.clusters]

def get_tag_cluster(cluster_id):
    return Cluster.query.get(cluster_id).tag



def create_default_org(user):
    """Create a fresh default org; a user's name must never grant org membership."""
    org = Org(
        name = f"{user.first_name} {user.last_name}",
        description = f"Org for user: {user.id}-{user.first_name} {user.last_name}",
        uuid = str(uuid.uuid4()),
        default_org = True
    )
    db.session.add(org)
    db.session.commit()
    return org


def delete_default_org(user_org_id):
    """Delete the default org for the user"""
    if not user_org_id:
        return False
    
    org = Org.query.get(user_org_id)
    if not org:
        return False
    
    cp = 0
    for user in org.users:
        cp += 1
    if org.default_org and not cp > 0:
        delete_org_core(org.id)
        return True
    return False


def add_user_core(form_dict):
    """Add a user to the DB"""
    matrix_id = form_dict["matrix_id"]
    if not matrix_id:
        matrix_id = None

    user = User(
        first_name=form_dict["first_name"],
        last_name=form_dict["last_name"],
        nickname=form_dict["nickname"],
        email=form_dict["email"],
        password=form_dict["password"],
        role_id = form_dict["role"],
        matrix_id=matrix_id,
        api_key = generate_api_key(),
        creation_date = datetime.datetime.now(tz=datetime.timezone.utc)
    )
    db.session.add(user)
    db.session.commit()

    if not form_dict["org"] or form_dict["org"] == "None":
        org = create_default_org(user)
        user.org_id = org.id
    else:
        loc_org = get_org(int(form_dict["org"]))
        if loc_org:
            user.org_id = loc_org.id
        else:
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
        org_change = org.id
    else:
        org_change = int(form_dict["org"])
        if not get_org(org_change).id == prev_user_org_id:
            flag = True

    user.first_name=form_dict["first_name"]
    user.last_name=form_dict["last_name"]
    user.nickname=form_dict["nickname"] or None
    user.email=form_dict["email"]
    user.matrix_id = form_dict["matrix_id"] or None  # Convert empty string to None to avoid UNIQUE constraint issues
    password_changed = "password" in form_dict and form_dict["password"] and user.auth_provider == 'local'
    if password_changed:
        user.password=form_dict["password"]
        user.api_key = generate_api_key()
    user.role_id = int(form_dict["role"])
    user.org_id = org_change

    db.session.commit()

    if password_changed:
        _invalidate_user_sessions(user.id)

    if flag:
        delete_default_org(prev_user_org_id)


def _iter_user_sessions():
    """Yield (key, data) for every stored server-side session."""
    redis_client = current_app.config.get("SESSION_REDIS")
    if not redis_client:
        return
    prefix = current_app.config.get("SESSION_KEY_PREFIX", "session:")
    decoder = msgspec.msgpack.Decoder()
    for key in redis_client.scan_iter(f"{prefix}*"):
        raw = redis_client.get(key)
        if raw is None:
            continue
        try:
            yield key, decoder.decode(raw)
        except Exception:
            continue


def _invalidate_user_sessions(user_id):
    """Remove all server-side sessions belonging to a user."""
    redis_client = current_app.config.get("SESSION_REDIS")
    if not redis_client:
        return
    for key, data in _iter_user_sessions():
        if session_user_id(data.get("_user_id")) == int(user_id):
            redis_client.delete(key)


# Idle time is (lifetime - ttl), since the TTL resets on each request.
ACTIVE_SESSION_THRESHOLD_MINUTES = 15


def list_active_user_sessions(exclude_user_id=None):
    """Return distinct users active within the threshold, optionally excluding one."""
    redis_client = current_app.config.get("SESSION_REDIS")
    if not redis_client:
        return []

    lifetime = current_app.config.get("PERMANENT_SESSION_LIFETIME") or datetime.timedelta(days=31)
    lifetime_seconds = lifetime.total_seconds()
    threshold_seconds = ACTIVE_SESSION_THRESHOLD_MINUTES * 60

    # user_id -> {"count": sessions, "idle": idle of the most recent one}
    active = {}
    for key, data in _iter_user_sessions():
        user_id = session_user_id(data.get("_user_id"))
        if not user_id or str(user_id) == str(exclude_user_id):
            continue

        ttl = redis_client.ttl(key)
        if ttl == -2:  # key expired between scan and read
            continue
        # ttl == -1 means no expiry, which we treat as just-active
        idle = 0 if ttl < 0 else max(0, lifetime_seconds - ttl)
        if idle > threshold_seconds:
            continue

        if user_id in active:
            active[user_id]["count"] += 1
            active[user_id]["idle"] = min(active[user_id]["idle"], idle)
        else:
            active[user_id] = {"count": 1, "idle": idle}

    sessions = []
    for user_id, entry in active.items():
        user = get_user(user_id)
        if not user:
            continue
        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
        sessions.append({
            "id": user.id,
            "name": name,
            "email": user.email,
            "sessions": entry["count"],
            "idle_seconds": int(entry["idle"]),
        })
    sessions.sort(key=lambda u: u["idle_seconds"])
    return sessions


def delete_user_core(id):
    """Delete the user to the DB"""
    user = get_user(id)
    if user:
        _invalidate_user_sessions(user.id)
        Task_User.query.filter_by(user_id=user.id).delete()
        Notification.query.filter_by(user_id=user.id).delete()
        Recurring_Notification.query.filter_by(user_id=user.id).delete()
        Login_Event.query.filter_by(user_id=user.id).delete()
        User_Connector_Instance.query.filter_by(user_id=user.id).delete()
        Misp_Module_Config.query.filter_by(user_id=user.id).delete()
        Misp_Module_Result.query.filter_by(user_id=user.id).delete()
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
        name = form_dict["name"],
        description = form_dict["description"],
        uuid = uuid_field,
        default_org = False
    )
    db.session.add(org)
    db.session.commit()
    return org

def add_role_core(form_dict):
    """Add a role to the DB"""
    role = Role(
        name = form_dict["name"],
        description = form_dict["description"],
        admin = form_dict.get("admin", False),
        read_only = form_dict.get("read_only", False),
        org_admin = form_dict.get("org_admin", False),
        case_admin = form_dict.get("case_admin", False),
        queue_admin = form_dict.get("queue_admin", False),
        queuer = form_dict.get("queuer", False),
        audit_viewer = form_dict.get("audit_viewer", False),
        template_editor = form_dict.get("template_editor", False),
        misp_editor = form_dict.get("misp_editor", False),
        importer = form_dict.get("importer", False)
    )
    db.session.add(role)
    db.session.commit()
    return role

def count_users_with_role(role_id):
    """Count users with a specific role"""
    return User.query.filter_by(role_id=role_id).count()

def delete_role(role_id):
    """Delete a role"""
    role = Role.query.get(role_id)
    if role:
        db.session.delete(role)
        db.session.commit()
        return True
    return False

def edit_role_core(role_id, data):
    """Edit a role"""
    role = Role.query.get(role_id)
    if role:
        if 'name' in data:
            role.name = data['name']
        if 'description' in data:
            role.description = data['description']
        role.admin = data.get("admin", False)
        role.read_only = data.get("read_only", False)
        role.org_admin = data.get("org_admin", False)
        role.case_admin = data.get("case_admin", False)
        role.queue_admin = data.get("queue_admin", False)
        role.queuer = data.get("queuer", False)
        role.audit_viewer = data.get("audit_viewer", False)
        role.template_editor = data.get("template_editor", False)
        role.misp_editor = data.get("misp_editor", False)
        role.importer = data.get("importer", False)
        db.session.commit()
        return True
    return False


def edit_org_core(form_dict, id):
    """Edit the org ot the DB"""
    org = get_org(id)
    if form_dict["uuid"]:
        org.uuid = form_dict["uuid"]
    else:
        org.uuid = str(uuid.uuid4())

    org.name = form_dict["name"]
    org.description = form_dict["description"]
    
    db.session.commit()


def delete_org_core(oid):
    """Delete the org to the DB"""
    org = get_org(oid)
    if org:
        for user in org.users:
            tasks_users = Task_User.query.filter_by(user_id=user.id)
            for task_user in tasks_users:
                db.session.delete(task_user)
                db.session.commit()
            Notification.query.filter_by(user_id=user.id).delete()
            Recurring_Notification.query.filter_by(user_id=user.id).delete()
            Login_Event.query.filter_by(user_id=user.id).delete()
            User_Connector_Instance.query.filter_by(user_id=user.id).delete()
            Misp_Module_Config.query.filter_by(user_id=user.id).delete()
            Misp_Module_Result.query.filter_by(user_id=user.id).delete()
        
        for case_org in Case_Org.query.filter_by(org_id=org.id):
            db.session.delete(case_org)
            db.session.commit()

        db.session.delete(org)
        db.session.commit()
        return True
    else:
        return False
    

def get_taxonomies_page(page, name=None, enabled=None, sort=None, order='asc'):
    nb_taxo = 25
    taxo_list = _filter_items(get_taxonomies(), name=name, enabled=enabled)
    taxo_list = _sort_items(taxo_list, sort=sort, order=order)

    to_give = nb_taxo * page
    if to_give > len(taxo_list):
        limit = len(taxo_list)
    else:
        limit = to_give
    to_start = limit - nb_taxo

    out_list = list()
    for i in range(max(0, to_start), limit):
        out_list.append(taxo_list[i])
    return out_list

def taxonomy_status(taxonomy_id):
    taxo = Taxonomy.query.get(taxonomy_id)
    taxo.exclude = not taxo.exclude
    db.session.commit()

def bulk_set_exclude(model, ids, exclude):
    for item_id in ids:
        item = model.query.get(item_id)
        if item:
            item.exclude = exclude
    db.session.commit()

def get_galaxies_page(page, name=None, enabled=None, sort=None, order='asc'):
    nb_galaxies = 25
    galaxies_list = _filter_items(get_galaxies(), name=name, enabled=enabled)
    galaxies_list = _sort_items(galaxies_list, sort=sort, order=order)

    to_give = nb_galaxies * page
    if to_give > len(galaxies_list):
        limit = len(galaxies_list)
    else:
        limit = to_give
    to_start = limit - nb_galaxies

    out_list = list()
    for i in range(max(0, to_start), limit):
        out_list.append(galaxies_list[i])
    return out_list

def galaxy_status(galaxy_id):
    gal = get_galaxy(galaxy_id)
    gal.exclude = not gal.exclude
    db.session.commit()


def can_see_user_stats(viewer, user):
    """Activity of a user: admins, the org admins of that user's organisation, and the user"""
    return viewer.is_admin() or viewer.id == user.id or (viewer.is_org_admin() and viewer.org_id == user.org_id)


def get_user_stats(user, viewer, weeks=12):
    """What the users page shows when a row is opened: tasks, recent work, cases, sign-ins.
    Cases and tasks are only counted in the cases the viewer can see."""
    from app.db_class.db import Task, Case
    from app.case import common_core as CommonModel

    now = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None)
    tasks = Task.query.join(Task_User, Task_User.task_id == Task.id).filter(Task_User.user_id == user.id).all()
    cases = {c.id: c for c in Case.query.filter(Case.id.in_({t.case_id for t in tasks} or {-1})).all()}
    visible = {cid for cid, c in cases.items() if CommonModel.can_view_case(c, viewer)}
    tasks = [t for t in tasks if t.case_id in visible]

    def naive(d):
        return d.replace(tzinfo=None) if d and d.tzinfo else d

    open_tasks = [t for t in tasks if not t.completed]
    overdue = [t for t in open_tasks if t.deadline and naive(t.deadline) < now]
    due_week = [t for t in open_tasks if t.deadline and now <= naive(t.deadline) <= now + datetime.timedelta(days=7)]

    # Tasks finished per week, oldest first
    start = (now - datetime.timedelta(weeks=weeks - 1)).date()
    start = start - datetime.timedelta(days=start.weekday())
    finished = [0] * weeks
    for t in tasks:
        fd = naive(t.finish_date)
        if t.completed and fd and fd.date() >= start:
            i = (fd.date() - start).days // 7
            if 0 <= i < weeks:
                finished[i] += 1

    # Cases the user works on, most recently changed first
    per_case = {}
    for t in tasks:
        e = per_case.setdefault(t.case_id, {"open": 0, "total": 0})
        e["total"] += 1
        e["open"] += 0 if t.completed else 1
    recent_cases = sorted(per_case, key=lambda cid: naive(cases[cid].last_modif) or datetime.datetime.min, reverse=True)

    # Sign-ins per day over the last 30 days
    since = now - datetime.timedelta(days=29)
    logins = [0] * 30
    for (d,) in Login_Event.query.filter(Login_Event.user_id == user.id, Login_Event.login_date >= since).with_entities(Login_Event.login_date):
        i = (naive(d).date() - since.date()).days
        if 0 <= i < 30:
            logins[i] += 1

    return {
        "tasks": {"total": len(tasks), "open": len(open_tasks), "done": len(tasks) - len(open_tasks),
                  "overdue": len(overdue), "due_week": len(due_week)},
        "finished_per_week": {"start": start.isoformat(), "counts": finished},
        "cases": {"total": len(per_case), "open": sum(1 for cid in per_case if not cases[cid].completed),
                  "recent": [{"id": cid, "title": cases[cid].title, "completed": bool(cases[cid].completed), **per_case[cid]}
                             for cid in recent_cases[:5]]},
        "overdue_tasks": [{"id": t.id, "title": t.title, "case_id": t.case_id, "deadline": naive(t.deadline).isoformat()}
                          for t in sorted(overdue, key=lambda t: naive(t.deadline))[:5]],
        "logins": {"per_day": logins, "total_30d": sum(logins),
                   "last": user.last_login.isoformat() if user.last_login else None},
        "member_since": user.creation_date.isoformat() if user.creation_date else None,
        "auth_provider": user.auth_provider,
    }
