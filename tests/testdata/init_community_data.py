"""Create or delete community test data (organisations and users) via the REST API.

Requires a running Flowintel instance and an admin API key.
Roles referenced in the data file must already exist.

Usage:
    python3 tests/testdata/init_community_data.py create --api-key <key>
    python3 tests/testdata/init_community_data.py delete --api-key <key>
    python3 tests/testdata/init_community_data.py create --api-key <key> --url http://host:port
"""

import argparse
import json
import os
import sys

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "test-data-community.json")
DEFAULT_URL = "http://127.0.0.1:7006"


def _load_data():
    with open(DATA_FILE) as f:
        return json.load(f)


def _headers(api_key):
    return {"X-API-KEY": api_key, "Content-Type": "application/json"}


def _get_roles(base_url, api_key):
    """Fetch all roles and return a name-to-id mapping."""
    resp = requests.get(f"{base_url}/api/admin/roles", headers=_headers(api_key))
    resp.raise_for_status()
    return {r["name"]: r["id"] for r in resp.json()["roles"]}


def _get_orgs(base_url, api_key):
    """Fetch all organisations and return a name-to-id mapping."""
    resp = requests.get(f"{base_url}/api/admin/orgs", headers=_headers(api_key))
    resp.raise_for_status()
    return {o["name"]: o["id"] for o in resp.json()["orgs"]}


def _get_users(base_url, api_key):
    """Fetch all users and return an email-to-id mapping."""
    resp = requests.get(f"{base_url}/api/admin/users", headers=_headers(api_key))
    resp.raise_for_status()
    return {u["email"]: u["id"] for u in resp.json()["users"]}


def create(base_url, api_key):
    """Create community organisations and users from the data file."""
    data = _load_data()
    roles = _get_roles(base_url, api_key)

    # Collect all role names referenced by users
    needed_roles = set()
    for org_def in data["organisations"]:
        for u in org_def.get("users", []):
            needed_roles.add(u["role"])

    missing = needed_roles - set(roles.keys())
    if missing:
        print(f"Error: role(s) not found: {', '.join(sorted(missing))}")
        print("Create the required roles before running this script.")
        sys.exit(1)

    # Create organisations
    print("Creating organisations...")
    for org_def in data["organisations"]:
        resp = requests.post(
            f"{base_url}/api/admin/add_org",
            headers=_headers(api_key),
            json={"name": org_def["name"], "description": org_def.get("description", "")},
        )
        if resp.status_code == 201:
            print(f"  Created: {org_def['name']}")
        elif "already exists" in resp.json().get("message", "").lower():
            print(f"  Skipped (exists): {org_def['name']}")
        else:
            print(f"  Error: {org_def['name']} - {resp.json().get('message', resp.text)}")
            sys.exit(1)

    orgs = _get_orgs(base_url, api_key)

    # Create users
    print("Creating users...")
    for org_def in data["organisations"]:
        org_id = orgs.get(org_def["name"])
        if not org_id:
            print(f"  Error: organisation '{org_def['name']}' not found")
            sys.exit(1)

        for u in org_def.get("users", []):
            resp = requests.post(
                f"{base_url}/api/admin/add_user",
                headers=_headers(api_key),
                json={
                    "first_name": u["first_name"],
                    "last_name": u["last_name"],
                    "email": u["email"],
                    "password": u["password"],
                    "role": roles[u["role"]],
                    "org": org_id,
                },
            )
            name = f"{u['first_name']} {u['last_name']}"
            if resp.status_code == 201:
                print(f"  Created: {name} ({u['role']})")
            elif "already exists" in resp.json().get("message", "").lower():
                print(f"  Skipped (exists): {u['email']}")
            else:
                print(f"  Error: {u['email']} - {resp.json().get('message', resp.text)}")
                sys.exit(1)

    _print_overview(data)


def delete(base_url, api_key):
    """Delete community users and organisations listed in the data file."""
    data = _load_data()
    users = _get_users(base_url, api_key)
    orgs = _get_orgs(base_url, api_key)

    # Delete users first
    print("Deleting community test users...")
    for org_def in data["organisations"]:
        for u in org_def.get("users", []):
            user_id = users.get(u["email"])
            if not user_id:
                print(f"  Not found: {u['email']}")
                continue
            resp = requests.get(
                f"{base_url}/api/admin/delete_user/{user_id}",
                headers=_headers(api_key),
            )
            if resp.status_code == 200:
                print(f"  Deleted: {u['first_name']} {u['last_name']} ({u['email']})")
            else:
                print(f"  Error: {u['email']} - {resp.json().get('message', resp.text)}")

    # Delete organisations
    print("Deleting community test organisations...")
    for org_def in data["organisations"]:
        org_id = orgs.get(org_def["name"])
        if not org_id:
            print(f"  Not found: {org_def['name']}")
            continue
        resp = requests.get(
            f"{base_url}/api/admin/delete_org/{org_id}",
            headers=_headers(api_key),
        )
        if resp.status_code == 200:
            print(f"  Deleted: {org_def['name']}")
        else:
            print(f"  Error: {org_def['name']} - {resp.json().get('message', resp.text)}")

    print("Done.")


def _print_overview(data):
    """Print a summary table of the community data."""
    print("\n--- Community test data overview ---")
    for org_def in data["organisations"]:
        users_list = org_def.get("users", [])
        print(f"\nOrganisation: {org_def['name']}")
        print(f"  {'User':<25} {'Email':<40} {'Role'}")
        print(f"  {'-'*25} {'-'*40} {'-'*15}")
        for u in users_list:
            name = f"{u['first_name']} {u['last_name']}"
            print(f"  {name:<25} {u['email']:<40} {u['role']}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manage community test data via the Flowintel REST API"
    )
    parser.add_argument("action", choices=["create", "delete"])
    parser.add_argument("--api-key", required=True, help="Admin API key")
    parser.add_argument("--url", default=DEFAULT_URL,
                        help=f"Base URL (default: {DEFAULT_URL})")
    args = parser.parse_args()

    if args.action == "create":
        create(args.url, args.api_key)
    else:
        delete(args.url, args.api_key)
