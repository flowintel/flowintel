import uuid
import datetime
from ..db_class.db import Case, Case_Org, Connector, Connector_Icon, Icon_File, Task, db
from ..db_class.db import User, Role, Org, Status
from .utils import generate_api_key
from ..case import common_core as CommonModel
from ..case import task_core as TaskModel

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


def create_user_org(user):
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
        status_db = Status(
            name=s[0],
            bootstrap_style=s[1]
        )

        db.session.add(status_db)
        db.session.commit()

def create_misp_ail_connector():
    ## MISP
    icon_file = Icon_File(
        name = "misp-icon.png",
        uuid = "fe377a79-1950-407a-a02f-c5e1d990ca60"
    )
    db.session.add(icon_file)
    db.session.commit()
    icon_file_id = icon_file.id

    icon = Connector_Icon(
        name="misp",
        description="Misp icon.",
        uuid=str(uuid.uuid4()),
        file_icon_id=icon_file_id
    )
    db.session.add(icon)
    db.session.commit()

    misp_connector = Connector(
        name="MISP",
        description="MISP connector",
        uuid=str(uuid.uuid4()),
        icon_id=icon.id
    )
    db.session.add(misp_connector)
    db.session.commit()

    ## AIL
    icon_file = Icon_File(
        name = "ail-icon.png",
        uuid = "0f5bb2b8-9537-4c31-8d66-f5d0fd07b98a"
    )
    db.session.add(icon_file)
    db.session.commit()
    icon_file_id = icon_file.id

    icon = Connector_Icon(
        name="ail",
        description="Ail icon.",
        uuid=str(uuid.uuid4()),
        file_icon_id=icon_file_id
    )
    db.session.add(icon)
    db.session.commit()

    ail_connector = Connector(
        name="Ail",
        description="Ail connector",
        uuid=str(uuid.uuid4()),
        icon_id=icon.id
    )
    db.session.add(ail_connector)
    db.session.commit()


def create_default_icon():
    icon_file = Icon_File(
        name = "lambda.png",
        uuid = "76447ff6-55f7-4acf-aed7-fabc8740d9e5"
    )
    db.session.add(icon_file)
    db.session.commit()
    icon_file_id = icon_file.id

    icon = Connector_Icon(
        name="default",
        description="Default icon. Will be placed in case that a connector have no icon.",
        uuid=str(uuid.uuid4()),
        file_icon_id=icon_file_id
    )
    db.session.add(icon)
    db.session.commit()
    

def create_task(case, user, title, description):
    nb_tasks = 1
    if case.nb_tasks:
        nb_tasks = case.nb_tasks+1
    else:
        case.nb_tasks = 0

    task = Task(
        uuid=str(uuid.uuid4()),
        title=title,
        description=description,
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
        last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
        case_id=case.id,
        status_id=1,
        case_order_id=nb_tasks,
        completed=False,
        nb_notes=0
    )
    db.session.add(task)
    db.session.commit()

    case.nb_tasks += 1
    db.session.commit()

    CommonModel.update_last_modif(case.id)
    CommonModel.save_history(case.uuid, user, f"Task '{task.title}' Created")
    return task


def create_default_case(user):
    # Create a case
    case = Case(
        title="Forensic Case",
        description="Example forensic case",
        uuid=str(uuid.uuid4()),
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
        last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
        status_id=1,
        owner_org_id=user.org_id
    )
    db.session.add(case)
    db.session.commit()

    case_org = Case_Org(
        case_id=case.id, 
        org_id=user.org_id
    )
    db.session.add(case_org)
    db.session.commit()

    CommonModel.save_history(case.uuid, user, "Case Created")

    # Create tasks
    task_1 = create_task(case, user, title="Extract disk", description="Only one machine")
    task_2 = create_task(case, user, title="Create a timeline", description="The time is your ally")
    task_3 = create_task(case, user, title="Extract and analyze evtx", description="Lost in the wild Windows")
    task_4 = create_task(case, user, title="Write report", description="Boring part but do it")

    note_1 = TaskModel.create_note(task_1.id, user)
    note_2 = TaskModel.create_note(task_2.id, user)
    note_3 = TaskModel.create_note(task_3.id, user)
    note_3_1 = TaskModel.create_note(task_3.id, user)
    note_4 = TaskModel.create_note(task_4.id, user)
    TaskModel.modif_note_core(task_1.id, user, "# Important\nDon't forget to do a copy. \nNever work on original evidence.", note_1.id)
    TaskModel.modif_note_core(task_2.id, user, "# Timeline\nPlaso or mactime. Choose your side...", note_2.id)
    TaskModel.modif_note_core(task_3.id, user, "There's always a few in a Windows machine.", note_3.id)
    TaskModel.modif_note_core(task_3.id, user, "Found it...\n\n\nQuickly...", note_3_1.id)
    TaskModel.modif_note_core(task_3.id, user, "Markdown this time.", note_4.id)



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
    admin_user = User(
        first_name="admin",
        last_name="admin",
        email="admin@admin.admin",
        password="admin",
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
    user = User(
        first_name="Matrix",
        last_name="Bot",
        email="neo@admin.admin",
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

    create_default_case(admin_user)




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