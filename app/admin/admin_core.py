import datetime
import os
from .. import db
from ..db_class.db import Cluster, Galaxy, User, Role, Org, Case_Org, Task_User, Taxonomy
from ..utils.utils import generate_api_key
import uuid


def get_all_users():
    """Return all users"""
    return User.query.all()

def get_users_by_org(org_id):
    """Return all users filtered by organization"""
    return User.query.filter_by(org_id=org_id).all()

def get_users_page(page, org_id=None, lastname=None):
    """Return users by page, optionally filtered by org_id and/or partial lastname match.

    - `lastname` performs a case-insensitive partial match against `User.last_name`.
    """
    query = User.query
    if org_id is not None:
        query = query.filter_by(org_id=org_id)
    if lastname:
        query = query.filter(User.last_name.ilike(f"%{lastname}%"))
    return query.paginate(page=page, per_page=20, max_per_page=50)

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

def get_user_by_lastname(lastname):
    # Case-insensitive partial match for last name
    return User.query.filter(User.last_name.ilike(f"%{lastname}%")).all()

def get_user_by_matrix_id(matrix_id):
    return User.query.filter_by(matrix_id=matrix_id).first()

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

def get_nb_page_taxo(name=None):
    """Return number of pages for taxonomies, optionally filtered by name.

    Uses the same in-memory list logic as `get_taxonomies_page` so results
    remain consistent when a `name` filter is provided.
    """
    taxo_list = get_taxonomies()
    if name:
        name_l = name.lower()
        taxo_list = [t for t in taxo_list if name_l in t.get('name', '').lower()]
    return int(len(taxo_list) / 25) + 1

def get_tags(taxonomy_id):
    return [tag.to_json() for tag in Taxonomy.query.get(taxonomy_id).tags]


## Galaxies
def get_galaxies():
    return [galax.to_json() for galax in Galaxy.query.order_by('name').all()]

def get_galaxy(galaxy_id):
    return Galaxy.query.get(galaxy_id)

def get_clusters():
    return [cluster.to_json() for cluster in Cluster.query.all()]

def get_clusters_galaxy(galaxy_id):
    return [cluster.to_json() for cluster in get_galaxy(galaxy_id).clusters]

def get_nb_page_galaxies(name=None):
    """Return number of pages for galaxies, optionally filtered by name.

    Uses the same in-memory list logic as `get_galaxies_page` so results
    remain consistent when a `name` filter is provided.
    """
    gal_list = get_galaxies()
    if name:
        name_l = name.lower()
        gal_list = [g for g in gal_list if name_l in g.get('name', '').lower()]
    return int(len(gal_list) / 25) + 1

def get_tags_galaxy(galaxy_id):
    return [cluster.tag for cluster in get_galaxy(galaxy_id).clusters]

def get_tag_cluster(cluster_id):
    return Cluster.query.get(cluster_id).tag



def create_default_org(user):
    """Create a default org for a user who have no org"""
    o_d = Org.query.filter_by(name=f"{user.first_name} {user.last_name}").first()
    if not o_d:
        org = Org(
            name = f"{user.first_name} {user.last_name}",
            description = f"Org for user: {user.id}-{user.first_name} {user.last_name}",
            uuid = str(uuid.uuid4()),
            default_org = True
        )
        db.session.add(org)
        db.session.commit()

        return org
    return o_d


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
    if "password" in form_dict and form_dict["password"]:
        user.password=form_dict["password"]
    user.role_id = int(form_dict["role"])
    user.org_id = org_change

    db.session.commit()

    if flag:
        delete_default_org(prev_user_org_id)


def delete_user_core(id):
    """Delete the user to the DB"""
    user = get_user(id)
    if user:
        Task_User.query.filter_by(user_id=user.id).delete()
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
        audit_viewer = form_dict.get("audit_viewer", False)
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
        
        for case_org in Case_Org.query.filter_by(org_id=org.id):
            db.session.delete(case_org)
            db.session.commit()

        db.session.delete(org)
        db.session.commit()
        return True
    else:
        return False
    

def get_taxonomies_page(page, name=None):
    nb_taxo = 25
    taxo_list = get_taxonomies()
    if name:
        name_l = name.lower()
        taxo_list = [t for t in taxo_list if name_l in t.get('name','').lower()]

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

def get_galaxies_page(page, name=None):
    nb_galaxies = 25
    galaxies_list = get_galaxies()
    if name:
        name_l = name.lower()
        galaxies_list = [g for g in galaxies_list if name_l in g.get('name','').lower()]

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
