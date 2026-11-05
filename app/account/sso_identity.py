"""Shared account resolution for the configured SSO providers."""

from app.db_class.db import User


def find_sso_user(email, provider):
    """Resolve an email only within its existing sign-in method; never auto-link."""
    user = User.query.filter_by(email=email).first()
    if user is None:
        return None, None
    if user.auth_provider != provider:
        return None, (
            "This email address conflicts with an existing account. "
            "Ask an administrator to resolve the account conflict."
        )
    return user, None
