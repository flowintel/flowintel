import base64
import datetime
import json
import logging
from urllib.parse import urlencode

import requests
from flask import current_app

from .. import db
from ..db_class.db import Role, User
from ..notification import notification_core as NotifModel
from ..utils.utils import generate_api_key

logger = logging.getLogger(__name__)


def _base_url():
    """Return the Keycloak base URL with no trailing slash."""
    return current_app.config.get("KEYCLOAK_BASE_URL", "").rstrip("/")


def _realm():
    return current_app.config.get("KEYCLOAK_REALM", "flowintel")


def _oidc_base():
    return f"{_base_url()}/realms/{_realm()}/protocol/openid-connect"


def get_auth_url(redirect_uri, state=None):
    """Build the Keycloak authorization URL for the Authorization Code flow."""
    params = {
        "client_id": current_app.config.get("KEYCLOAK_CLIENT_ID", ""),
        "response_type": "code",
        "scope": "openid",
        "redirect_uri": redirect_uri,
    }
    if state:
        params["state"] = state

    return f"{_oidc_base()}/auth?{urlencode(params)}"


def exchange_code(code, redirect_uri):
    """Exchange an authorization code for tokens. Returns the JSON token response."""
    resp = requests.post(
        f"{_oidc_base()}/token",
        data={
            "grant_type": "authorization_code",
            "client_id": current_app.config.get("KEYCLOAK_CLIENT_ID", ""),
            "client_secret": current_app.config.get("KEYCLOAK_CLIENT_SECRET", ""),
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=10,
    )
    if resp.status_code != 200:
        logger.warning("Keycloak token exchange failed (%s): %s", resp.status_code, resp.text[:500])
        return {"error": "token_exchange_failed", "error_description": resp.text[:200]}
    return resp.json()


def _decode_jwt_payload(token):
    """Decode the payload of a JWT without verifying the signature (back-channel token)."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def get_or_create_sso_user(token_response):
    """Resolve a Keycloak token response to a Flowintel User, creating one if needed.

    Returns (user, None) on success or (None, error_message) on failure.
    """
    id_token = token_response.get("id_token")
    if not id_token:
        return None, "No ID token in the Keycloak response."

    claims = _decode_jwt_payload(id_token)
    if not claims:
        return None, "Could not decode the Keycloak ID token."

    email = (claims.get("email") or claims.get("preferred_username") or "").lower().strip()
    if not email:
        return None, "No email address found in the Keycloak token."

    groups = claims.get("groups", [])

    cfg = current_app.config
    priority_list = [
        (cfg.get("KEYCLOAK_GROUP_ADMIN",      "FlowintelAdmin"),      "Editor",                                    True),
        (cfg.get("KEYCLOAK_GROUP_EDITOR",      "FlowintelEditor"),     "Editor",                                    False),
        (cfg.get("KEYCLOAK_GROUP_CASE_ADMIN",  "FlowintelCaseAdmin"),  cfg.get("KEYCLOAK_ROLE_CASE_ADMIN",  "CaseAdmin"),  False),
        (cfg.get("KEYCLOAK_GROUP_QUEUE_ADMIN", "FlowintelQueueAdmin"), cfg.get("KEYCLOAK_ROLE_QUEUE_ADMIN", "QueueAdmin"), False),
        (cfg.get("KEYCLOAK_GROUP_QUEUER",      "FlowintelQueuer"),     cfg.get("KEYCLOAK_ROLE_QUEUER",      "Queuer"),     False),
        (cfg.get("KEYCLOAK_GROUP_READONLY",    "FlowintelReadOnly"),   "Read Only",                                 False),
    ]

    configured_groups = [entry[0] for entry in priority_list]
    logger.info(
        "Keycloak login for '%s' — groups received: %s | checking: %s",
        email, groups, configured_groups,
    )

    matched_group = None
    matched_role_name = None
    notify_admin = False
    for group_name, role_name, should_notify in priority_list:
        if group_name in groups:
            matched_group = group_name
            matched_role_name = role_name
            notify_admin = should_notify
            break

    if not matched_group:
        return None, (
            "Your account is not a member of any Flowintel group "
            f"({', '.join(configured_groups)})."
        )

    logger.info("Keycloak login for '%s' — matched group '%s' → role '%s'", email, matched_group, matched_role_name)

    target_role = Role.query.filter_by(name=matched_role_name).first()
    if not target_role:
        return None, (
            f"Could not find Flowintel role '{matched_role_name}' in the database. "
            "Please ask an administrator to create it."
        )

    user = User.query.filter_by(email=email).first()

    if user:
        if user.auth_provider == "keycloak" and user.role_id != target_role.id:
            user.role_id = target_role.id
            db.session.commit()
        return user, None

    # Build user name from token claims, with sensible fallbacks.
    first_name = (claims.get("given_name") or "").strip()
    last_name = (claims.get("family_name") or "").strip()
    if not first_name and not last_name:
        full_name = (claims.get("name") or "").strip()
        if full_name:
            parts = full_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""
    if not first_name:
        first_name = email.split("@")[0]
    if not last_name:
        last_name = ""

    nick = f"{email.split('@')[0]} - via Keycloak"

    user = User(
        first_name=first_name,
        last_name=last_name,
        nickname=nick,
        email=email,
        role_id=target_role.id,
        api_key=generate_api_key(),
        auth_provider="keycloak",
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    db.session.add(user)
    db.session.commit()

    from ..admin.admin_core import create_default_org
    org = create_default_org(user)
    user.org_id = org.id
    db.session.commit()

    logger.info("Provisioned new Keycloak user: %s (role: %s)", email, target_role.name)

    if notify_admin:
        msg = (
            f"Keycloak user '{email}' is a member of '{matched_group}' and has been "
            f"provisioned with the '{target_role.name}' role. "
            "Please promote them to Admin if appropriate."
        )
    else:
        msg = (
            f"A new Keycloak user '{email}' has been provisioned with the "
            f"'{target_role.name}' role (group '{matched_group}'). "
            "Please review their organisation assignment."
        )
    NotifModel.create_notification_for_admins(
        message=msg,
        html_icon="fa-solid fa-user-shield",
        user_id_for_redirect=user.id,
    )

    return user, None
