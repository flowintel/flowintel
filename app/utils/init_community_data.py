"""Community test case import and deletion.

Organisations and users are managed via the REST API using
tests/testdata/init_community_data.py.  This module handles test *cases*
which require direct database access through the application context.
"""

import json
import os
import random
import string
import uuid as uuid_mod

from ..db_class.db import Case, Task_User, User, Org, db

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

DATA_FILE = os.path.join(_APP_ROOT, "tests", "testdata", "test-data-community.json")
TESTDATA_DIR = os.path.join(_APP_ROOT, "tests", "testdata")

_CASE_TAG = "[community-test-case]"


def _load_data():
    with open(DATA_FILE) as f:
        return json.load(f)


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
        case_data["title"] = f"{prefix} {case_data['title']}"
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
    from ..case.CaseCore import CaseModel

    cases = Case.query.filter(Case.description.like(f"{_CASE_TAG}%")).all()
    if not cases:
        print("No community test cases found.")
        return

    admin_user = User.query.filter_by(role_id=1).first()
    if not admin_user:
        print("Error: no admin user found.")
        return

    case_model = CaseModel()
    print(f"Deleting {len(cases)} community test case(s)...")
    for case in cases:
        title = case.title
        case_model.delete_case(case.id, admin_user)
        print(f"  Deleted: {title}")

    print("Done.")


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
