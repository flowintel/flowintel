from ..db_class.db import db
from ..db_class.db import User, Role, Org, Status
from .utils import generate_api_key
import uuid

def create_admin_role():
    role = Role(
        name = "Admin",
        description = "All rights",
        admin = True,
        read_only = False
    )
    db.session.add(role)
    db.session.commit()
    return role

def create_editor_role():
    role = Role(
        name = "Editor",
        description = "Can edit a lot",
        admin = False,
        read_only = False
    )
    db.session.add(role)
    db.session.commit()

def create_read_only_role():
    role = Role(
        name = "Read Only",
        description = "Can only read",
        admin = False,
        read_only = True
    )
    db.session.add(role)
    db.session.commit()


def create_admin_org(user):
    org = Org(
        name = f"{user.first_name} {user.last_name}",
        description = f"Org for user: {user.id}-{user.first_name} {user.last_name}",
        uuid = str(uuid.uuid4()),
        default_org = True
    )
    db.session.add(org)
    db.session.commit()

    return org


def create_status():
    status = [("Created", "success"), ("On going", "primary"), ("Scheduled", "warning"), ("Finished", "danger")]

    for s in status:
        status_db = Status(
            name=s[0],
            bootstrap_style=s[1]
        )

        db.session.add(status_db)
        db.session.commit()
    

def create_admin():
    # Role
    role = create_admin_role()
    create_editor_role()
    create_read_only_role()

    # Admin user
    user = User(
        first_name="admin",
        last_name="admin",
        email="admin@admin.com",
        password="admin",
        role_id=role.id,
        api_key = generate_api_key()
    )
    db.session.add(user)
    db.session.commit()
    
    # Org    
    org = create_admin_org(user)
    user.org_id = org.id
    db.session.commit()

    # Status
    create_status()
