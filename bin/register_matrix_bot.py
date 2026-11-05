#!/usr/bin/env python3
"""Register a verified existing Matrix bot by its database user ID.

Run after the is_bot migration, using the same environment as the application:
    env/bin/python bin/register_matrix_bot.py --env production --user-id 2

Identify the bot from trusted deployment records or its configured API key,
not solely from its editable name or email. This grants relay authority.
"""
import argparse
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def register_bot(user_id):
    """Mark the operator-selected account and remove its independent Admin role."""
    from app.db_class.db import Role, User
    from app.extensions import db

    user = db.session.get(User, user_id)
    if user is None:
        raise ValueError("User ID does not exist.")
    if user.auth_provider != "local":
        raise ValueError("The Matrix bot must be a dedicated local account.")
    role = Role.query.filter_by(name="Read Only").first()
    if role is None or not role.read_only or role.admin:
        raise ValueError("A non-admin Read Only role must exist before registering the bot.")
    user.is_bot = True
    user.role_id = role.id
    db.session.commit()
    return user


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--env", choices=("development", "production", "testing"))
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    if args.env:
        os.environ["FLOWINTEL_APP_ENV"] = args.env

    from app import create_app
    from sqlalchemy.exc import SQLAlchemyError

    try:
        app = create_app()
        with app.app_context():
            user = register_bot(args.user_id)
            print(f"Registered Matrix bot user {user.id} with the Read Only role. "
                  "Its API key is unchanged; requests must include MATRIX-ID.")
    except ValueError as exc:
        parser.exit(1, f"Error: {exc}\n")
    except SQLAlchemyError:
        parser.exit(1, "Error: Could not register the bot. Check the database and apply migrations first.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
