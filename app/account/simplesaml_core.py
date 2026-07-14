import datetime
import logging

from flask import current_app, Request
from onelogin.saml2.auth import OneLogin_Saml2_Auth


from .. import db
from ..db_class.db import Role, User
from ..notification import notification_core as NotifModel
from ..utils.utils import generate_api_key

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
def _saml_path():
    return current_app.config.get("SIMPLESAML_PYTHON3_SAML_PATH")

def _sp_entity_id():
    return current_app.config.get('SIMPLESAML_SP_ENTITY_ID')

def _idp_sso_url():
    return current_app.config.get('SIMPLESAML_IDP_SSO_URL')

def _attr_email():
    return current_app.config.get('SIMPLESAML_ATTR_EMAIL')

def _attr_name():
    return current_app.config.get('SIMPLESAML_ATTR_NAME')

def _attr_username():
    return current_app.config.get('SIMPLESAML_ATTR_USERNAME')

def _attr_groups():
    return current_app.config.get('SIMPLESAML_ATTR_GROUPS')

def _sync_role_on_login():
    return current_app.config.get('SIMPLESAML_SYNC_ROLE_ON_LOGIN')

def _group_admin():
    # Editor by default, Admin will be notified thanks to True argument, then Admin can promote new Admin
    return (
        current_app.config.get("SIMPLESAML_GROUP_ADMIN"),
        "Editor",
        True
    )

def _group_editor():
    return (
        current_app.config.get("SIMPLESAML_GROUP_EDITOR"),
        "Editor",
        False
    )

def _group_case_admin():
    return (
        current_app.config.get("SIMPLESAML_GROUP_CASE_ADMIN"),
        current_app.config.get("SIMPLESAML_ROLE_CASE_ADMIN"),
        False
    )

def _group_queue_admin():
    return (
        current_app.config.get("SIMPLESAML_GROUP_QUEUE_ADMIN"),
        current_app.config.get("SIMPLESAML_ROLE_QUEUE_ADMIN"),
        False
    )

def _group_queuer():
    return (
        current_app.config.get("SIMPLESAML_GROUP_QUEUER"),
        current_app.config.get("SIMPLESAML_ROLE_QUEUER"),
        False
    )

def _group_readonly():
    return (
        current_app.config.get("SIMPLESAML_GROUP_READONLY"),
        "Read Only", 
        False
    )

def _group_aliases():
    return current_app.config.get("SIMPLESAML_GROUP_ALIASES", {})


# ---------------------------------------------------------------------------
# python3-saml integration — SAMLResponse validation and Auth object setup
#
# All signature verification, InResponseTo/AuthnRequestID matching, and
# assertion parsing is delegated to the python3-saml (OneLogin) toolkit.
# See _init_saml_auth() and get_or_create_sso_user() below.
# ---------------------------------------------------------------------------
def _prepare_flask_request(req: Request) -> dict:
    """Build the request dict python3-saml uses to validate SAML messages.

    python3-saml reconstructs a "self URL" (scheme + host + port) from this
    dict and compares it against the configured ACS URL during strict
    validation. Behind a reverse proxy (e.g. Nginx terminating TLS on 443
    and forwarding to the app on an internal port), the raw request seen by
    Flask reflects the internal connection, not the public-facing one,
    causing false-positive `invalid_response` errors.

    When SIMPLESAML_TRUST_PROXY_HEADERS is enabled, scheme/host/port are
    read strictly from the X-Forwarded-* headers instead of the raw
    request, with no fallback to the raw request values. This is only
    safe if the reverse proxy unconditionally overwrites (not appends to)
    these headers for every request it forwards, otherwise a client could
    spoof them and bypass SAML's origin validation entirely. If any header
    is missing, this raises immediately rather than silently falling back,
    since a silent fallback would surface as a confusing SAML validation
    failure instead of an obvious Nginx misconfiguration.

    Args:
        req: The current Flask request object (SAML login redirect or
            ACS callback).

    Returns:
        dict: Request data in the format expected by
        `OneLogin_Saml2_Auth`, with keys 'https', 'http_host',
        'server_port', 'script_name', 'get_data', 'post_data', and
        'query_string'.

    Raises:
        RuntimeError: If SIMPLESAML_TRUST_PROXY_HEADERS is enabled but
            one or more required X-Forwarded-* headers are missing from
            the incoming request.
    """
    trusted_proxy = current_app.config.get('SIMPLESAML_TRUST_PROXY_HEADERS', False)

    if trusted_proxy:
        scheme = req.headers.get('X-Forwarded-Proto', req.scheme)
        http_host = req.headers.get('X-Forwarded-Host', req.host)
        server_port = req.headers.get('X-Forwarded-Port')
        if not all([scheme, http_host, server_port]):
            raise RuntimeError(
                "SIMPLESAML_TRUST_PROXY_HEADERS is enabled but required "
                "X-Forwarded-* headers are missing — check Nginx config."
            )
    else:
        scheme = req.scheme
        http_host = req.host
        server_port = req.environ.get('SERVER_PORT')


    return {
        'https': 'on' if scheme == 'https' else 'off',
        'http_host': http_host,
        # it comes from the incoming WSGI request environment
        # reflects the actual request the server received, including the port used on that request
        # should be provided automatically by flask dev server, wsgi server like Gunicorn or reverse proxy like Nginx
        # may need to configure Flask/Werkzeug to trust forwarded headers so scheme/host/port reflect the external request correctly.
        # potential not ideal deployment workaround: omit server_port or force HTTPS-related values when the proxy setup is stable
        'server_port': server_port,
        #
        'script_name': req.path,
        'get_data': req.args.copy(),
        'post_data': req.form.copy(),
        'query_string': req.query_string.decode('utf-8'),
    }

def _init_saml_auth(req: Request) -> OneLogin_Saml2_Auth:
    """
    Initialize a python3-saml Auth object for the current Flask request.

    If SIMPLESAML_PYTHON3_SAML_PATH is configured, python3-saml loads
    settings.json and advanced_settings.json from that directory automatically,
    along with any certificate files located there.
    """
    saml_path = _saml_path()
    prepared = _prepare_flask_request(req)
    if saml_path:
        return OneLogin_Saml2_Auth(prepared, custom_base_path=saml_path)
    return OneLogin_Saml2_Auth(prepared)

def _first(attributes: dict, key: str, default: str = '') -> str:
    """Return the first value for a given attribute key."""
    vals = attributes.get(key, [])
    return vals[0] if vals else default


# ---------------------------------------------------------------------------
# User provisioning — same group-priority logic as Keycloak core
# ---------------------------------------------------------------------------
def get_or_create_sso_user(auth: OneLogin_Saml2_Auth) -> tuple[User | None, str | None]:
    """
    Resolve/Provision a Flowintel user from a validated python3-saml auth object.
    Returns (user, None) or (None, error_message).
    """
    # First get the attributes from SAML
    #
    attrs = auth.get_attributes()
    email = _first(attrs, _attr_email()).lower().strip()
    if not email:
        return None, "No email address found in the SAML assertion."

    raw_groups = attrs.get(_attr_groups(), [])
    aliases = _group_aliases()
    groups = [aliases.get(group, group) for group in raw_groups]

    full_name = _first(attrs, _attr_name())
    username  = _first(attrs, _attr_username(), default=email.split('@')[0])

    # Which role stays on top if present in multiple groups mapping different privilege roles
    priority_list = [
        _group_admin(),
        _group_case_admin(),
        _group_queue_admin(),
        _group_editor(),
        _group_queuer(),
        _group_readonly(),
    ]

    configured_groups = [e[0] for e in priority_list]
    logger.info(
        "SimpleSAML login for '%s' — raw groups: %s | aliased groups: %s | checking: %s",
        email, raw_groups, groups, configured_groups,
    )

    # Define the user role based on defined mapping
    matched_group = matched_role_name = None
    notify_admin = False
    for group_name, role_name, should_notify in priority_list:
        # The idea is to break once the first group is encountered in the list -> highest priority by design
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

    logger.info(
        "SimpleSAML login for '%s' — matched group '%s' → role '%s'",
        email, matched_group, matched_role_name,
    )

    target_role = Role.query.filter_by(name=matched_role_name).first()
    if not target_role:
        return None, (
            f"Could not find Flowintel role '{matched_role_name}' in the database. "
            "Please ask an administrator to create it."
        )

    user = User.query.filter_by(email=email).first()

    if user:
        # Sync role if it drifted (group membership change)
        if (
            user.auth_provider == "simplesaml" and 
            user.role_id != target_role.id and
            _sync_role_on_login()
            ):
            user.role_id = target_role.id
            db.session.commit()
        return user, None

    # Name: single 'cn' field split on first space
    if full_name:
        parts = full_name.split(' ', maxsplit=1)
        first_name = parts[0]
        last_name  = parts[1] if len(parts) > 1 else ''
    else:
        # Graceful fallback if cn is absent
        first_name = email.split('@')[0]
        last_name  = ''

    # Username from Organisation SimpleSaml OID (for nickname, login is always email in Flowintel)
    nick = f"{username} - via SimpleSAML"

    user = User(
        first_name=first_name,
        last_name=last_name,
        nickname=nick,
        email=email,
        role_id=target_role.id,
        api_key=generate_api_key(),
        auth_provider="simplesaml",
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    db.session.add(user)
    db.session.commit()

    from ..admin.admin_core import create_default_org
    org = create_default_org(user)
    user.org_id = org.id
    db.session.commit()

    logger.info("Provisioned new SimpleSAML user: %s (role: %s)", email, target_role.name)

    msg = (
        f"SimpleSAML user '{email}' (login: {username}) is a member of '{matched_group}' "
        f"and has been provisioned with the '{target_role.name}' role. "
        + (
            "Please promote them to Admin if appropriate."
            if notify_admin else
            "Please review their organisation assignment."
        )
    )
    NotifModel.create_notification_for_admins(
        message=msg,
        html_icon="fa-solid fa-user-shield",
        user_id_for_redirect=user.id,
    )

    return user, None
