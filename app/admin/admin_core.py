import os
from .. import db
from ..db_class.db import Cluster, Connector_Icon, Galaxy, Icon_File, User, Role, Org, Case_Org, Task_User, Taxonomy, Connector
from ..utils.utils import generate_api_key
import uuid
from werkzeug.utils import secure_filename

ICON_FOLDER = os.path.join(os.getcwd(), "app", "static", "icons")

def get_all_users():
    """Return all users"""
    return User.query.all()

def get_users_page(page):
    """Return all users by page"""
    return User.query.paginate(page=page, per_page=20, max_per_page=50)

def get_all_roles():
    """Return all roles"""
    return Role.query.all()

def get_all_orgs():
    """Return all organisations"""
    return Org.query.all()

def get_orgs_page(page):
    """Return all organisations by page"""
    return Org.query.paginate(page=page, per_page=20, max_per_page=50)

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


## Taxonomies
def get_taxonomies():
    return [taxo.to_json() for taxo in Taxonomy.query.all()]

def get_nb_page_taxo():
    return int(len(get_taxonomies())/25)+1

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

def get_nb_page_galaxies():
    return int(len(get_galaxies()) / 25) + 1

def get_tags_galaxy(galaxy_id):
    return [cluster.tag for cluster in get_galaxy(galaxy_id).clusters]

def get_tag_cluster(cluster_id):
    return Cluster.query.get(cluster_id).tag


## Connectors
def get_connectors():
    """Return all connectors"""
    return Connector.query.all()

def get_connector(cid):
    """Return a connector"""
    return Connector.query.get(cid)

def get_icons():
    """Return all icons"""
    return Connector_Icon.query.all()

def get_icon(iid):
    """Return an icon"""
    return Connector_Icon.query.get(iid)

def get_default_icon():
    """Return teh default icon"""
    return Connector_Icon.query.filter_by(name="default").first()

def get_icon_file(file_id):
    """Return a file"""
    return Icon_File.query.get(file_id)


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
        first_name=form_dict["first_name"],
        last_name=form_dict["last_name"],
        email=form_dict["email"],
        password=form_dict["password"],
        role_id = form_dict["role"],
        org_id = form_dict["org"],
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

    user.first_name=form_dict["first_name"]
    user.last_name=form_dict["last_name"]
    user.email=form_dict["email"]
    if "password" in form_dict:
        user.password=form_dict["password"]
    user.role_id = form_dict["role"]
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
        name = form_dict["name"],
        description = form_dict["description"],
        uuid = uuid_field,
        default_org = False
    )
    db.session.add(org)
    db.session.commit()
    return org


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
    

def get_taxonomies_page(page):
    nb_taxo = 25
    to_give = nb_taxo * page
    taxo_list = get_taxonomies()
    
    if to_give > len(taxo_list):
        limit = len(taxo_list)
    else:
        limit = to_give
    to_start = limit - nb_taxo

    out_list = list()
    for i in range(to_start, limit):
        out_list.append(taxo_list[i])
    return out_list

def taxonomy_status(taxonomy_id):
    taxo = Taxonomy.query.get(taxonomy_id)
    taxo.exclude = not taxo.exclude
    db.session.commit()

def get_galaxies_page(page):
    nb_galaxies = 25
    to_give = nb_galaxies * page
    galaxies_list = get_galaxies()
    
    if to_give > len(galaxies_list):
        limit = len(galaxies_list)
    else:
        limit = to_give
    to_start = limit - nb_galaxies

    out_list = list()
    for i in range(to_start, limit):
        out_list.append(galaxies_list[i])
    return out_list

def galaxy_status(galaxy_id):
    gal = get_galaxy(galaxy_id)
    gal.exclude = not gal.exclude
    db.session.commit()


def add_connector_core(form_dict):
    if not form_dict["icon_select"] or form_dict["icon_select"] == "None":
        icon_id = get_default_icon().id
    else:
        icon_id = form_dict["icon_select"]

    connector = Connector(
        name=form_dict["name"],
        description=form_dict["description"],
        url=form_dict["url"],
        uuid=str(uuid.uuid4()),
        icon_id=icon_id
    )
    db.session.add(connector)
    db.session.commit()
    return True


def add_icon_file(icon):
    uuid_loc = str(uuid.uuid4())
    try:
        with open(os.path.join(ICON_FOLDER, uuid_loc), "wb") as write_icon:
            write_icon.write(icon.data.read())
    except Exception as e:
        print(e)
        return False
    
    icon_file = Icon_File(
        name = secure_filename(icon.data.filename),
        uuid = uuid_loc
    )
    db.session.add(icon_file)
    db.session.commit()
    return icon_file.id

def add_icon_core(form_dict, icon):
    icon_file_id = add_icon_file(icon)
    
    icon = Connector_Icon(
        name = form_dict["name"],
        description = form_dict["description"],
        uuid = str(uuid.uuid4()),
        file_icon_id = icon_file_id
    )
    db.session.add(icon)
    db.session.commit()

    return True


def edit_connector_core(cid, form_dict):
    connector_db = get_connector(cid)
    if connector_db:
        if not form_dict["icon_select"] or form_dict["icon_select"] == "None":
            icon_id = get_default_icon().id
        else:
            icon_id = form_dict["icon_select"]
        connector_db.name = form_dict["name"]
        connector_db.url = form_dict["url"]
        connector_db.description = form_dict["description"]
        connector_db.icon_id = icon_id

        db.session.add(connector_db)
        db.session.commit()
        return True
    return False


def edit_icon_core(iid, form_dict, icon):
    icon_db = get_icon(iid)
    if icon_db:
        if icon.data:
            if not delete_icon_file(icon_db.file_icon_id):
                return False
            icon_db.file_icon_id = add_icon_file(icon)

        icon_db.name = form_dict["name"]
        icon_db.description = form_dict["description"]
        db.session.commit()
        return True
    return False


def delete_connector_core(cid):
    connector = get_connector(cid)
    db.session.delete(connector)
    db.session.commit()
    return True


def delete_icon_file(file_icon_id):
    """Delete an icon from disk from table Icon_File"""
    icon_file = get_icon_file(file_icon_id)

    try:
        os.remove(os.path.join(ICON_FOLDER, icon_file.uuid))
    except:
        return False
    
    db.session.delete(icon_file)
    db.session.commit()
    return True


def delete_icon_core(iid):
    """Delete the icon from the DB"""
    icon = get_icon(iid)
    if icon:
        if not delete_icon_file(icon.file_icon_id):
            return False

        default_icon = get_default_icon()
        for connector in Connector.query.filter_by(icon_id=icon.id).all():
            connector.icon_id = default_icon.id
            db.session.commit()

        db.session.delete(icon)
        db.session.commit()
        
        return True
    else:
        return False