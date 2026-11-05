#!/usr/bin/env python3
r"""Create a local Flowintel account directly in the configured database.

Example (the password is prompted for):
    env/bin/python bin/create_user.py --email admin@example.com \
        --first-name Site --last-name Admin --role Admin

The database schema must already exist. No login or API key is required.
"""

import argparse
import datetime as dt
import getpass
import os
from pathlib import Path
import sys
import uuid


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def create_user(*, first_name, last_name, email, password, role_name="Editor",
                org_id=None, nickname=None):
    """Create the user, role and personal organisation in one transaction."""
    from email_validator import validate_email
    from sqlalchemy import func

    from app.db_class.db import Org, Role, User
    from app.extensions import db
    from app.utils.utils import generate_api_key, validate_password_strength

    first_name = first_name.strip()
    last_name = last_name.strip()
    email = email.strip().lower()
    nickname = nickname.strip() if nickname else None
    for label, value in (("First name", first_name), ("Last name", last_name),
                         ("Email", email)):
        if not value or len(value) > 64:
            raise ValueError(f"{label} must be between 1 and 64 characters.")
    if nickname and len(nickname) > 64:
        raise ValueError("Nickname must be at most 64 characters.")
    validate_email(email, check_deliverability=False)
    password_error = validate_password_strength(password)
    if password_error:
        raise ValueError(password_error)

    if User.query.filter(func.lower(User.email) == email).first():
        raise ValueError(f"A user with email {email} already exists.")

    role_name = role_name.strip()
    role = Role.query.filter(func.lower(Role.name) == role_name.lower()).first()
    if role is None:
        # These are the same built-in roles used by database initialisation.
        defaults = {
            "admin": ("Admin", "All rights", True, False),
            "editor": ("Editor", "Can edit a lot", False, False),
            "read only": ("Read Only", "Can only read", False, True),
        }
        if role_name.lower() not in defaults:
            raise ValueError(f"Role {role_name!r} does not exist.")
        name, description, admin, read_only = defaults[role_name.lower()]
        role = Role(name=name, description=description, admin=admin, read_only=read_only)

    org = None
    if org_id is not None:
        org = db.session.get(Org, org_id)
        if org is None:
            raise ValueError(f"Organisation with ID {org_id} does not exist.")

    try:
        db.session.add(role)
        db.session.flush()
        user = User(
            first_name=first_name,
            last_name=last_name,
            nickname=nickname,
            email=email,
            password=password,
            role_id=role.id,
            api_key=generate_api_key(),
            auth_provider="local",
            creation_date=dt.datetime.now(dt.timezone.utc),
        )
        db.session.add(user)
        db.session.flush()
        if org is None:
            org = Org(
                name=f"{first_name} {last_name}"[:64],
                description=f"Org for user: {user.id}-{first_name} {last_name}",
                uuid=str(uuid.uuid4()),
                default_org=True,
            )
            db.session.add(org)
            db.session.flush()
        user.org_id = org.id
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return user


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True, help="Login email address")
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--nickname")
    parser.add_argument("--password", help="Password; omitted to prompt without echo")
    parser.add_argument("--role", default="Editor",
                        help="Role name (default: Editor); built-in roles are created if missing")
    parser.add_argument("--org-id", type=int,
                        help="Existing organisation ID; omitted to create a personal organisation")
    parser.add_argument("--env", choices=("development", "production", "testing"),
                        help="Override FLOWINTEL_APP_ENV (otherwise use the application configuration)")
    args = parser.parse_args(argv)

    # Match launch.sh's working directory and resolve imports when run from bin/.
    os.chdir(REPO_ROOT)
    if args.env:
        os.environ["FLOWINTEL_APP_ENV"] = args.env

    from sqlalchemy.exc import SQLAlchemyError
    from app import create_app

    try:
        password = args.password
        if password is None:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Confirm password: "):
                raise ValueError("Passwords do not match.")

        app = create_app()
        with app.app_context():
            user = create_user(
                first_name=args.first_name,
                last_name=args.last_name,
                email=args.email,
                password=password,
                role_name=args.role,
                org_id=args.org_id,
                nickname=args.nickname,
            )
            print(f"Created user {user.email} (ID: {user.id}, "
                  f"role: {args.role}, organisation ID: {user.org_id}).")
    except ValueError as exc:
        parser.exit(1, f"Error: {exc}\n")
    except SQLAlchemyError:
        # Database exceptions can include INSERT parameters such as credentials.
        parser.exit(1, "Error: Could not create user. Check the database connection, "
                    "apply any pending migrations, and check for duplicate users.\n")
    except (EOFError, KeyboardInterrupt):
        parser.exit(1, "\nUser creation cancelled.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
