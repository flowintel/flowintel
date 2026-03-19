"""Create or delete community test data from tests/testdata/test-data-community.json."""

import json
import os
import random
import string
import uuid as uuid_mod

from ..db_class.db import (
    Case, Case_Org, Case_Tags, Case_Galaxy_Tags, Case_Connector_Instance,
    Case_Custom_Tags, Case_Link_Case, Case_Misp_Object, Case_Note_Template_Model,
    Note, Recurring_Notification, Task, Task_Tags, Task_Galaxy_Tags, Task_Galaxy,
    Task_User, Task_Connector_Instance, Task_Custom_Tags,
    User, Role, Org, db,
)
from .utils import generate_api_key

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

DATA_FILE = os.path.join(_APP_ROOT, "tests", "testdata", "test-data-community.json")
TESTDATA_DIR = os.path.join(_APP_ROOT, "tests", "testdata")
HISTORY_DIR = os.environ.get("HISTORY_DIR", "history")

# Marker so we can identify community-created records later
_TAG = "[community-test-data]"
_CASE_TAG = "[community-test-case]"


def _load_data():
    with open(DATA_FILE) as f:
        return json.load(f)


def _find_role(name):
    """Look up a role by name, falling back to built-in roles."""
    return Role.query.filter_by(name=name).first()


def create_community_test_data():
    data = _load_data()

    # Roles
    print("Creating roles...")
    for r in data["roles"]:
        existing = Role.query.filter_by(name=r["name"]).first()
        if existing:
            print(f"  Skipped (exists): {r['name']}")
            continue
        perms = r.get("permissions", {})
        role = Role(
            name=r["name"],
            description=r.get("description", ""),
            admin=perms.get("admin", False),
            read_only=perms.get("read_only", False),
            org_admin=perms.get("org_admin", False),
            case_admin=perms.get("case_admin", False),
            queue_admin=perms.get("queue_admin", False),
            queuer=perms.get("queuer", False),
            audit_viewer=perms.get("audit_viewer", False),
            template_editor=perms.get("template_editor", False),
            misp_editor=perms.get("misp_editor", False),
            importer=perms.get("importer", False),
        )
        db.session.add(role)
        db.session.commit()
        print(f"  Created: {r['name']}")

    # Organisations and users
    print("Creating organisations and users...")
    for org_def in data["organisations"]:
        org = Org.query.filter_by(name=org_def["name"]).first()
        if not org:
            org = Org(
                name=org_def["name"],
                description=f'{_TAG} {org_def.get("description", "")}',
                uuid=str(uuid_mod.uuid4()),
                default_org=False,
            )
            db.session.add(org)
            db.session.commit()
            print(f"  Organisation created: {org_def['name']}")
        else:
            print(f"  Organisation exists: {org_def['name']}")

        for u in org_def.get("users", []):
            existing = User.query.filter_by(email=u["email"]).first()
            if existing:
                print(f"    Skipped (exists): {u['email']}")
                continue

            role = _find_role(u["role"])
            if not role:
                print(f"    Error: role '{u['role']}' not found, skipping {u['email']}")
                continue

            user = User(
                first_name=u["first_name"],
                last_name=u["last_name"],
                email=u["email"],
                password=u["password"],
                role_id=role.id,
                org_id=org.id,
                api_key=generate_api_key(),
            )
            db.session.add(user)
            db.session.commit()
            print(f"    User created: {u['first_name']} {u['last_name']} ({u['role']})")

    # Overview
    _print_overview(data)


def delete_community_test_data():
    data = _load_data()

    # Collect all emails and org names from the JSON
    emails = []
    org_names = []
    for org_def in data["organisations"]:
        org_names.append(org_def["name"])
        for u in org_def.get("users", []):
            emails.append(u["email"])

    # Delete users
    print("Deleting community test users...")
    for email in emails:
        user = User.query.filter_by(email=email).first()
        if user:
            print(f"  Deleted user: {user.first_name} {user.last_name} ({email})")
            db.session.delete(user)
        else:
            print(f"  Not found: {email}")
    db.session.commit()

    # Delete organisations
    print("Deleting community test organisations...")
    for name in org_names:
        org = Org.query.filter_by(name=name).first()
        if org:
            print(f"  Deleted organisation: {name}")
            db.session.delete(org)
        else:
            print(f"  Not found: {name}")
    db.session.commit()

    # Delete roles (only those defined in the JSON, skip built-in ones)
    role_names = [r["name"] for r in data["roles"]]
    print("Deleting community test roles...")
    for name in role_names:
        role = Role.query.filter_by(name=name).first()
        if role:
            # Only delete if no other users reference this role
            remaining = User.query.filter_by(role_id=role.id).count()
            if remaining > 0:
                print(f"  Kept (still in use by {remaining} user(s)): {name}")
            else:
                print(f"  Deleted role: {name}")
                db.session.delete(role)
        else:
            print(f"  Not found: {name}")
    db.session.commit()

    print("Done.")


def _print_overview(data):
    print("\n--- Community test data overview ---")
    role_names = [r["name"] for r in data["roles"]]
    print(f"Roles: {', '.join(role_names)}")
    for org_def in data["organisations"]:
        users = org_def.get("users", [])
        print(f"\nOrganisation: {org_def['name']}")
        print(f"  {'User':<25} {'Email':<40} {'Role'}")
        print(f"  {'-'*25} {'-'*40} {'-'*15}")
        for u in users:
            name = f"{u['first_name']} {u['last_name']}"
            print(f"  {name:<25} {u['email']:<40} {u['role']}")
    print()


# --- Test cases ---

def _random_prefix():
    return "TC-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))


def _get_community_orgs():
    """Return Org objects for every organisation in the community JSON."""
    data = _load_data()
    orgs = []
    for org_def in data["organisations"]:
        org = Org.query.filter_by(name=org_def["name"]).first()
        if org:
            orgs.append(org)
    return orgs


def _get_community_assignees():
    """Return User objects with Queuer or QueueAdmin role from community orgs."""
    data = _load_data()
    emails = []
    for org_def in data["organisations"]:
        for u in org_def.get("users", []):
            if u["role"] in ("Queuer", "QueueAdmin"):
                emails.append(u["email"])
    users = []
    for email in emails:
        user = User.query.filter_by(email=email).first()
        if user:
            users.append(user)
    return users


def create_community_test_cases():
    from ..tools.tools_core import case_creation_from_importer

    community_orgs = _get_community_orgs()
    if not community_orgs:
        print("Error: no community organisations found. Run --test_data_community first.")
        return

    assignees = _get_community_assignees()
    if not assignees:
        print("Warning: no Queuer/QueueAdmin users found; tasks will not be assigned.")

    # Pick a community user to act as the creator
    creator_user = User.query.filter(User.org_id.in_([o.id for o in community_orgs])).first()
    if not creator_user:
        print("Error: no community users found.")
        return

    case_files = sorted(
        f for f in os.listdir(TESTDATA_DIR)
        if f.startswith("case_") and f.endswith(".json")
    )
    if not case_files:
        print("No case files found in tests/testdata/.")
        return

    created_cases = []

    print("Importing test cases...")
    for filename in case_files:
        filepath = os.path.join(TESTDATA_DIR, filename)
        with open(filepath) as f:
            case_data = json.load(f)

        # Randomise title and UUID so re-runs work
        prefix = _random_prefix()
        original_title = case_data["title"]
        case_data["title"] = f"{prefix} {original_title}"
        case_data["uuid"] = str(uuid_mod.uuid4())
        for task in case_data.get("tasks", []):
            task["uuid"] = str(uuid_mod.uuid4())

        # Mark the description so we can find these cases later for deletion
        desc = case_data.get("description") or ""
        case_data["description"] = f"{_CASE_TAG} {desc}"

        # Assign a random community org to the creator for this case
        chosen_org = random.choice(community_orgs)
        original_org_id = creator_user.org_id
        creator_user.org_id = chosen_org.id
        db.session.commit()

        result = case_creation_from_importer(case_data, creator_user)

        # Restore the creator's original org
        creator_user.org_id = original_org_id
        db.session.commit()

        if result:
            print(f"  Failed: {filename} - {result.get('message', 'Unknown error')}")
            continue

        case = Case.query.filter_by(title=case_data["title"]).first()
        if not case:
            print(f"  Failed: {filename} - case not found after import")
            continue

        print(f"  Created: {case_data['title']} (org: {chosen_org.name})")

        # Assign community Queuer/QueueAdmin users to each task
        if assignees:
            for task in case.tasks:
                user = random.choice(assignees)
                if not Task_User.query.filter_by(task_id=task.id, user_id=user.id).first():
                    db.session.add(Task_User(task_id=task.id, user_id=user.id))
                    print(f"    Task '{task.title}' assigned to {user.first_name} {user.last_name}")
            db.session.commit()

        created_cases.append((case, chosen_org))

    # Overview
    _print_case_overview(created_cases)


def delete_community_test_cases():
    cases = Case.query.filter(Case.description.like(f"{_CASE_TAG}%")).all()
    if not cases:
        print("No community test cases found.")
        return

    print(f"Deleting {len(cases)} community test case(s)...")
    for case in cases:
        _delete_case_and_relations(case)
        print(f"  Deleted: {case.title}")

    db.session.commit()
    print("Done.")


def _delete_case_and_relations(case):
    """Remove a case and all its related records."""
    # Task-level cleanup
    for task in case.tasks:
        Task_Tags.query.filter_by(task_id=task.id).delete()
        Task_Galaxy_Tags.query.filter_by(task_id=task.id).delete()
        Task_Galaxy.query.filter_by(task_id=task.id).delete()
        Task_User.query.filter_by(task_id=task.id).delete()
        Task_Connector_Instance.query.filter_by(task_id=task.id).delete()
        Task_Custom_Tags.query.filter_by(task_id=task.id).delete()
        Note.query.filter_by(task_id=task.id).delete()

    # Case-level cleanup
    Case_Tags.query.filter_by(case_id=case.id).delete()
    Case_Galaxy_Tags.query.filter_by(case_id=case.id).delete()
    Case_Org.query.filter_by(case_id=case.id).delete()
    Case_Connector_Instance.query.filter_by(case_id=case.id).delete()
    Case_Custom_Tags.query.filter_by(case_id=case.id).delete()
    Case_Link_Case.query.filter_by(case_id_1=case.id).delete()
    Case_Link_Case.query.filter_by(case_id_2=case.id).delete()
    Case_Misp_Object.query.filter_by(case_id=case.id).delete()
    Recurring_Notification.query.filter_by(case_id=case.id).delete()
    Case_Note_Template_Model.query.filter_by(case_id=case.id).delete()

    # History file
    history_path = os.path.join(HISTORY_DIR, str(case.uuid))
    if os.path.isfile(history_path):
        os.remove(history_path)

    db.session.delete(case)


def _print_case_overview(created_cases):
    if not created_cases:
        return
    print(f"\n--- Community test cases overview ---")
    print(f"  {'Case title':<45} {'Organisation':<25} {'Tasks'}")
    print(f"  {'-'*45} {'-'*25} {'-'*6}")
    for case, org in created_cases:
        task_count = case.tasks.count()
        print(f"  {case.title:<45} {org.name:<25} {task_count}")
    print()
