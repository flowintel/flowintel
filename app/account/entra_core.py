import datetime
import logging
import re

import msal
import requests
from flask import current_app

from .. import db
from ..db_class.db import Role, User
from ..notification import notification_core as NotifModel
from ..utils.utils import generate_api_key

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
_SCOPES = ["User.Read", "GroupMember.Read.All"]
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)
_DOMAIN_RE = re.compile(
    r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)+$'
)


def _get_msal_app():
    """Return a configured MSAL ConfidentialClientApplication."""
    tenant = current_app.config.get("ENTRA_TENANT_ID", "").strip()
    client_id = current_app.config.get("ENTRA_CLIENT_ID", "").strip()
    client_secret = current_app.config.get("ENTRA_CLIENT_SECRET", "")

    if not _UUID_RE.match(tenant) and not _DOMAIN_RE.match(tenant):
        raise RuntimeError(
            "ENTRA_TENANT_ID is not a valid UUID or domain name. "
            "Check your configuration."
        )
    if not _UUID_RE.match(client_id):
        raise RuntimeError(
            "ENTRA_CLIENT_ID is not a valid application UUID. "
            "Check your configuration."
        )
    if not client_secret:
        raise RuntimeError(
            "ENTRA_CLIENT_SECRET is empty. Check your configuration."
        )

    return msal.ConfidentialClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{tenant}",
        client_credential=client_secret,
    )


def get_auth_url(redirect_uri, state=None):
    """Return the Microsoft authorization URL to redirect the user to."""
    return _get_msal_app().get_authorization_request_url(
        scopes=_SCOPES,
        state=state,
        redirect_uri=redirect_uri,
    )


def acquire_token_by_code(code, redirect_uri):
    """Exchange an authorization code for tokens. Returns the MSAL result dict."""
    return _get_msal_app().acquire_token_by_authorization_code(
        code=code,
        scopes=_SCOPES,
        redirect_uri=redirect_uri,
    )


def _get_user_groups(access_token):
    """Return the list of group displayNames the signed-in user belongs to.

    Uses transitiveMemberOf so nested group membership is included.
    Handles paginated Graph API responses. Returns [] on any error.
    """
    groups = []
    url = f"{GRAPH_API_BASE}/me/transitiveMemberOf/microsoft.graph.group?$select=displayName"
    try:
        while url:
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if resp.status_code != 200:
                logger.warning("Graph API groups call returned %s: %s", resp.status_code, resp.text[:500])
                return []
            data = resp.json()
            groups.extend(g["displayName"] for g in data.get("value", []))
            url = data.get("@odata.nextLink")
    except Exception as exc:
        logger.warning("Graph API groups call failed: %s", exc)
        return []

    logger.debug("Entra ID group memberships for user: %s", groups)
    return groups


def get_or_create_sso_user(id_token_claims, access_token):
    """Resolve an Entra ID token to a Flowintel User, creating one if needed.

    Returns (user, None) on success or (None, error_message) on failure.
    """
    email = (
        id_token_claims.get("preferred_username")
        or id_token_claims.get("email")
        or ""
    ).lower().strip()

    if not email:
        return None, "No email address found in the Entra ID token."

    groups = _get_user_groups(access_token)

    # Priority-ordered mapping from Entra group → Flowintel role.
    # The first matching group wins, so higher-privilege groups should come first.
    # FlowintelAdmin maps to Editor initially; admins are notified to promote manually.
    cfg = current_app.config
    priority_list = [
        (cfg.get("ENTRA_GROUP_ADMIN",      "FlowintelAdmin"),      "Editor",                                True),
        (cfg.get("ENTRA_GROUP_EDITOR",     "FlowintelEditor"),     "Editor",                                False),
        (cfg.get("ENTRA_GROUP_CASE_ADMIN", "FlowintelCaseAdmin"),  cfg.get("ENTRA_ROLE_CASE_ADMIN",  "CaseAdmin"),  False),
        (cfg.get("ENTRA_GROUP_QUEUE_ADMIN","FlowintelQueueAdmin"), cfg.get("ENTRA_ROLE_QUEUE_ADMIN", "QueueAdmin"), False),
        (cfg.get("ENTRA_GROUP_QUEUER",     "FlowintelQueuer"),     cfg.get("ENTRA_ROLE_QUEUER",      "Queuer"),     False),
        (cfg.get("ENTRA_GROUP_READONLY",   "FlowintelReadOnly"),   "Read Only",                             False),
    ]

    configured_groups = [entry[0] for entry in priority_list]
    logger.info(
        "Entra ID login for '%s' — groups received: %s | checking: %s",
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

    logger.info("Entra ID login for '%s' — matched group '%s' → role '%s'", email, matched_group, matched_role_name)

    target_role = Role.query.filter_by(name=matched_role_name).first()
    if not target_role:
        return None, (
            f"Could not find Flowintel role '{matched_role_name}' in the database. "
            "Please ask an administrator to create it."
        )

    user = User.query.filter_by(email=email).first()

    if user:
        # On every login, sync the role for SSO accounts in case group membership changed.
        if user.auth_provider == "entra" and user.role_id != target_role.id:
            user.role_id = target_role.id
            db.session.commit()
        return user, None

    # Provision a new user account on first login.
    name = id_token_claims.get("name", "")
    parts = name.split(" ", 1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""
    nick = f"{email.split('@')[0]} - via EntraID"

    user = User(
        first_name=first_name,
        last_name=last_name,
        nickname=nick,
        email=email,
        role_id=target_role.id,
        api_key=generate_api_key(),
        auth_provider="entra",
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    db.session.add(user)
    db.session.commit()

    from ..admin.admin_core import create_default_org
    org = create_default_org(user)
    user.org_id = org.id
    db.session.commit()

    logger.info("Provisioned new Entra ID user: %s (role: %s)", email, target_role.name)

    if notify_admin:
        NotifModel.create_notification_for_admins(
            message=(
                f"Entra ID user '{email}' is a member of '{matched_group}' and has been "
                f"provisioned with the '{target_role.name}' role. "
                "Please promote them to Admin if appropriate."
            ),
            html_icon="fa-solid fa-user-shield",
            user_id_for_redirect=user.id,
        )

    return user, None
