import uuid
import datetime
import json
import os
from flask import current_app
from ..db_class.db import Case, Case_Org, Connector, Connector_Icon, Icon_File, Task, db
from ..db_class.db import User, Role, Org, Status
from .utils import generate_api_key
from ..case import common_core as CommonModel
from ..case.TaskCore import TaskModel

def create_admin_role():
    role = Role.query.filter_by(name="Admin").first()
    if role:
        return role
    
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
    role = Role.query.filter_by(name="Editor").first()
    if role:
        return role
    
    role = Role(
        name = "Editor",
        description = "Can edit a lot",
        admin = False,
        read_only = False
    )
    db.session.add(role)
    db.session.commit()

def create_read_only_role():
    role = Role.query.filter_by(name="Read Only").first()
    if role:
        return role
    
    role = Role(
        name = "Read Only",
        description = "Can only read",
        admin = False,
        read_only = True
    )
    db.session.add(role)
    db.session.commit()


def create_user_org(user):
    org = Org.query.filter_by(name=f"{user.first_name} {user.last_name}").first()
    if org:
        return org
    
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
    status = [("Created", "success"), ("Ongoing", "primary"), ("Recurring", "info"), ("Unavailable", "info"), ("Rejected", "danger"), ("Finished", "danger")]

    for s in status:
        existing_status = Status.query.filter_by(name=s[0]).first()
        if existing_status:
            continue
        status_db = Status(
            name=s[0],
            bootstrap_style=s[1]
        )

        db.session.add(status_db)
        db.session.commit()

def create_misp_ail_connector():
    ## MISP
    icon_file = Icon_File.query.filter_by(name="misp-icon.png").first()
    if not icon_file:
        icon_file = Icon_File(
            name = "misp-icon.png",
            uuid = "fe377a79-1950-407a-a02f-c5e1d990ca60"
        )
        db.session.add(icon_file)
        db.session.commit()
    icon_file_id = icon_file.id

    icon = Connector_Icon.query.filter_by(name="misp").first()
    if not icon:
        icon = Connector_Icon(
            name="misp",
            description="Misp icon.",
            uuid=str(uuid.uuid4()),
            file_icon_id=icon_file_id
        )
        db.session.add(icon)
        db.session.commit()

    misp_connector = Connector.query.filter_by(name="MISP").first()
    if not misp_connector:
        misp_connector = Connector(
            name="MISP",
            description="MISP connector",
            uuid=str(uuid.uuid4()),
            icon_id=icon.id
        )
        db.session.add(misp_connector)
        db.session.commit()

    ## AIL
    icon_file = Icon_File.query.filter_by(name="ail-icon.png").first()
    if not icon_file:
        icon_file = Icon_File(
            name = "ail-icon.png",
            uuid = "0f5bb2b8-9537-4c31-8d66-f5d0fd07b98a"
        )
        db.session.add(icon_file)
        db.session.commit()
    icon_file_id = icon_file.id

    icon = Connector_Icon.query.filter_by(name="ail").first()
    if not icon:
        icon = Connector_Icon(
            name="ail",
            description="Ail icon.",
            uuid=str(uuid.uuid4()),
            file_icon_id=icon_file_id
        )
        db.session.add(icon)
        db.session.commit()

    ail_connector = Connector.query.filter_by(name="Ail").first()
    if not ail_connector:
        ail_connector = Connector(
            name="Ail",
            description="Ail connector",
            uuid=str(uuid.uuid4()),
            icon_id=icon.id
        )
        db.session.add(ail_connector)
        db.session.commit()


def create_default_icon():
    icon_file = Icon_File.query.filter_by(name="lambda.png").first()
    if not icon_file:
        icon_file = Icon_File(
            name = "lambda.png",
            uuid = "76447ff6-55f7-4acf-aed7-fabc8740d9e5"
        )
        db.session.add(icon_file)
        db.session.commit()
    icon_file_id = icon_file.id

    icon = Connector_Icon.query.filter_by(name="default").first()
    if not icon:
        icon = Connector_Icon(
            name="default",
            description="Default icon. Will be placed in case that a connector have no icon.",
            uuid=str(uuid.uuid4()),
            file_icon_id=icon_file_id
        )
        db.session.add(icon)
        db.session.commit()


def create_default_case(user):
    from ..tools.tools_core import case_creation_from_importer
    
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    testdata_dir = os.path.join(app_dir, "tests", "testdata")
    
    if not os.path.exists(testdata_dir):
        return
    
    case_files = sorted([f for f in os.listdir(testdata_dir) if f.startswith("case_") and f.endswith(".json")])
    
    for filename in case_files:
        filepath = os.path.join(testdata_dir, filename)
        with open(filepath) as f:
            case_data = json.load(f)
        result = case_creation_from_importer(case_data, user)
        if result:
            print(f"  Failed: {filename} - {result.get('message', 'Unknown error')}")
        else:
            print(f"  Created: {case_data['title']}")



############
############

def create_admin():
    # Role
    role = create_admin_role()
    create_editor_role()
    create_read_only_role()

    # Default Icon
    create_default_icon()
    create_misp_ail_connector()

    # Admin user
    admin_config = current_app.config.get('INIT_ADMIN_USER')
    if not admin_config:
        raise ValueError("INIT_ADMIN_USER configuration is required but not found in config")
    
    # Validate required fields
    required_admin_fields = ['first_name', 'last_name', 'email', 'password']
    for field in required_admin_fields:
        if field not in admin_config or not admin_config[field]:
            raise ValueError(f"INIT_ADMIN_USER.{field} is required but not specified in config")
    
    admin_email = admin_config['email']
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        admin_user = User(
            first_name=admin_config['first_name'],
            last_name=admin_config['last_name'],
            email=admin_email,
            password=admin_config['password'],
            role_id=role.id,
            api_key = generate_api_key()
        )
        db.session.add(admin_user)
        db.session.commit()
    
        # Org    
        org = create_user_org(admin_user)
        admin_user.org_id = org.id
        db.session.commit()

    # Matrix bot user
    bot_config = current_app.config.get('INIT_BOT_USER')
    if not bot_config:
        raise ValueError("INIT_BOT_USER configuration is required but not found in config")
    
    # Validate required fields
    required_bot_fields = ['first_name', 'last_name', 'email']
    for field in required_bot_fields:
        if field not in bot_config or not bot_config[field]:
            raise ValueError(f"INIT_BOT_USER.{field} is required but not specified in config")
    
    bot_email = bot_config['email']
    user = User.query.filter_by(email=bot_email).first()
    if not user:
        user = User(
            first_name=bot_config['first_name'],
            last_name=bot_config['last_name'],
            email=bot_email,
            password=generate_api_key(),
            role_id=role.id,
            api_key = generate_api_key()
        )
        db.session.add(user)
        db.session.commit()
    
        # Org    
        org = create_user_org(user)
        user.org_id = org.id
        db.session.commit()

    # Status
    create_status()




def create_user_test():
    # Role
    role = create_admin_role()
    create_editor_role()
    create_read_only_role()

    # Admin user
    user = User(
        first_name="admin",
        last_name="admin",
        email="admin@admin.admin",
        password="admin",
        role_id=role.id,
        api_key = "admin_api_key"
    )
    db.session.add(user)
    db.session.commit()

    # Org
    org = create_user_org(user)
    user.org_id = org.id
    db.session.commit()

    user = User(
        first_name="editor",
        last_name="editor",
        email="editor@editor.editor",
        password="editor",
        role_id=2,
        api_key = "editor_api_key"
    )
    db.session.add(user)
    db.session.commit()
    
    # Org
    org = create_user_org(user)
    user.org_id = org.id
    db.session.commit()

    user = User(
        first_name="read",
        last_name="read",
        email="read@read.read",
        password="read",
        role_id=3,
        api_key = "read_api_key"
    )
    db.session.add(user)
    db.session.commit()
    
    # Org
    org = create_user_org(user)
    user.org_id = org.id
    db.session.commit()

    # Status
    create_status()