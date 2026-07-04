import base64
import datetime
import logging
import uuid
import zlib
from urllib.parse import urlencode

from lxml import etree
from flask import current_app

from .. import db
from ..db_class.db import Role, User
from ..notification import notification_core as NotifModel
from ..utils.utils import generate_api_key

logger = logging.getLogger(__name__)

# SAML2 namespace map
_NS = {
    'saml':  'urn:oasis:names:tc:SAML:2.0:assertion',
    'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
}


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
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

def _local_role():
    return current_app.config.get("SIMPLESAML_ATTR_ROLE", {})


# ---------------------------------------------------------------------------
# Auth URL — HTTP-Redirect binding (deflated SAMLRequest)
# ---------------------------------------------------------------------------
def get_auth_url(acs_url: str, relay_state: str = '') -> str:
    """Build a SAML2 AuthnRequest redirect URL (HTTP-Redirect binding)."""
    authn_request = (
        f'<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
        f'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" '
        f'ID="_{uuid.uuid4().hex}" Version="2.0" '
        f'IssueInstant="{datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}" '
        f'AssertionConsumerServiceURL="{acs_url}" '
        f'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">'
        f'<saml:Issuer>{_sp_entity_id()}</saml:Issuer>'
        f'</samlp:AuthnRequest>'
    )
    deflated = zlib.compress(authn_request.encode('utf-8'))[2:-4]
    encoded = base64.b64encode(deflated).decode('utf-8')
    params = {'SAMLRequest': encoded}
    if relay_state:
        params['RelayState'] = relay_state
    return f"{_idp_sso_url()}?{urlencode(params)}"



# ---------------------------------------------------------------------------
# SAMLResponse parser
# WARNING: no signature verification — use python3-saml in production.
# ---------------------------------------------------------------------------
def _parse_saml_response(saml_response_b64: str) -> dict | None:
    """
    Decode a base64 SAMLResponse and extract identity attributes.
    Returns {'name_id': str, 'attributes': dict[str, list[str]]} or None.
    """
    try:
        xml_bytes = base64.b64decode(saml_response_b64)
        root = etree.fromstring(xml_bytes)
    except Exception as exc:
        logger.warning("Failed to decode SAMLResponse: %s", exc)
        return None

    status_code = root.find('.//samlp:StatusCode', _NS)
    if status_code is not None and 'Success' not in status_code.get('Value', ''):
        logger.warning("SAML status not Success: %s", status_code.get('Value'))
        return None

    name_id_el = root.find('.//saml:NameID', _NS)
    name_id = name_id_el.text.strip() if name_id_el is not None else ''

    attributes: dict[str, list[str]] = {}
    for attr in root.findall('.//saml:Attribute', _NS):
        attr_name = attr.get('Name', '')
        values = [
            v.text.strip()
            for v in attr.findall('saml:AttributeValue', _NS)
            if v.text
        ]
        if attr_name:
            attributes[attr_name] = values

    return {'name_id': name_id, 'attributes': attributes}


def _first(attributes: dict, key: str, default: str = '') -> str:
    """Return the first value for a given attribute key."""
    vals = attributes.get(key, [])
    return vals[0] if vals else default


# ---------------------------------------------------------------------------
# User provisioning — same group-priority logic as Keycloak core
# ---------------------------------------------------------------------------
def get_or_create_sso_user(saml_response_b64: str):
    """
    Parse a SAMLResponse from the SimpleSaml IdP and resolve/provision
    a Flowintel User. Returns (user, None) or (None, error_message).
    """
    # First get the attributes from SAML
    #
    parsed = _parse_saml_response(saml_response_b64)
    if not parsed:
        return None, "Could not decode the SAML response."

    attrs = parsed['attributes']

    email = _first(attrs, _attr_email()).lower().strip()
    if not email:
        return None, "No email address found in the SAML assertion."

    localrole   = _first(attrs, _local_role(), default="")
    
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
        + ("Please promote them to Admin if appropriate." if notify_admin
           else "Please review their organisation assignment.")
    )
    NotifModel.create_notification_for_admins(
        message=msg,
        html_icon="fa-solid fa-user-shield",
        user_id_for_redirect=user.id,
    )

    return user, None
