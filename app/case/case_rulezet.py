"""Rulezet tab of a case: talks to the Rulezet instance linked to the case.

Every call goes through Flowintel, so the Rulezet API key never reaches the browser.
Rulezet API used (see the instance's /api/ Swagger page):
  GET  /api/config/formats                 formats with title, colour, logo (public)
  GET  /api/rule/public/searchPage         search (public, no rule id in the results)
  POST /api/rule/private/search            search with ids (needs an API key)
  GET  /api/rule/public/detail/<id>        a rule as published on Rulezet (public)
  POST /api/rule/public/validate           syntax check of a rule for a format (public). With the
                                           API key and the rule id, a YARA rule that uses other rules
                                           is compiled together with them (trusted rules only)
  POST /api/rule/private/edit/<id>         edit a rule: direct edit (its author) or edit proposal
  GET  /api/rule/public/dependencies/<id>  the rules a rule needs, and the rules that need it
An edited rule is saved in the case first; "Publish" then sends it to Rulezet.
"""
import base64
import re
import time
from urllib.parse import quote

import requests
from flask import request
from flask_login import login_required, current_user

import conf.config_module as ModuleConfig
from .case import case_blueprint, check_user_private_case
from . import common_core as CommonModel
from ..db_class.db import Rulezet_Rule, db
from ..decorators import editor_required, misp_editor_required
from ..utils.logger import flowintel_log

VERIFY_SSL = getattr(ModuleConfig, "RULEZET_VERIFY_SSL", True)
TIMEOUT = 20
MAX_CONTENT = 512 * 1024  # Rulezet refuses larger rules on /validate

_formats_cache = {}  # base url -> (time, formats)
FORMATS_TTL = 600


def _error(message, code=400, toast="danger-subtle"):
    return {"message": message, "toast_class": toast}, code


def _instance_for(case, case_instance_id):
    """The Rulezet instance linked to this case under case_instance_id, with the user's key."""
    case_instance = CommonModel.get_case_connectors_by_id(case_instance_id)
    if not case_instance or case_instance.case_id != case.id:
        return None, _error("Connector instance not found", 404)
    instance = CommonModel.get_instance(case_instance.instance_id)
    if not instance or not CommonModel.can_interact_with_case_connector(instance, current_user):
        return None, _error("Action not allowed", 403, "warning-subtle")
    connector = CommonModel.get_connector(instance.connector_id)
    if not connector or connector.name.lower() != "rulezet":
        return None, _error("This connector instance is not a Rulezet instance")
    return {
        "id": instance.id,
        "base": (instance.url or "").rstrip("/"),
        "api_key": CommonModel.get_case_connector_api_key(instance, current_user, case.id),
    }, None


def _headers(api_key=None):
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-API-KEY"] = str(api_key).strip()
    return headers


def _call(method, url, api_key=None, **kwargs):
    try:
        res = requests.request(method, url, headers=_headers(api_key), verify=VERIFY_SSL, timeout=TIMEOUT, **kwargs)
    except requests.RequestException:
        return None, _error("Could not reach Rulezet", 502)
    try:
        data = res.json()
    except ValueError:
        return None, _error(f"Rulezet returned HTTP {res.status_code}", 502)
    if res.status_code >= 400:
        msg = data.get("message") or data.get("error") if isinstance(data, dict) else None
        return None, _error(msg or f"Rulezet returned HTTP {res.status_code}", res.status_code if res.status_code < 500 else 502)
    return data, None


_LOGO_NAME = re.compile(r'^[\w.-]+\.(png|svg|webp|jpg)$', re.I)
_LOGO_TYPES = {"png": "image/png", "svg": "image/svg+xml", "webp": "image/webp", "jpg": "image/jpeg"}
MAX_LOGO = 200 * 1024


def _logo_data_url(base, logo):
    """A format logo of the Rulezet instance as a data: URL. Flowintel's content security
    policy only allows its own images, so logos are fetched here rather than by the browser."""
    if not logo or not _LOGO_NAME.match(logo):
        return None
    try:
        res = requests.get(f"{base}/static/images/formats/{logo}", verify=VERIFY_SSL, timeout=TIMEOUT)
    except requests.RequestException:
        return None
    ext = logo.rsplit(".", 1)[1].lower()
    ctype = (res.headers.get("Content-Type") or "").split(";")[0].strip()
    if res.status_code != 200 or not ctype.startswith("image/") or len(res.content) > MAX_LOGO:
        return None
    return f"data:{_LOGO_TYPES[ext]};base64,{base64.b64encode(res.content).decode()}"


_me_cache = {}  # (base, key) -> (time, rulezet user id)


def _rulezet_user_id(inst):
    """Id of the Rulezet account behind the API key of the instance (None without a key)"""
    if not inst["api_key"]:
        return None
    k = (inst["base"], inst["api_key"])
    cached = _me_cache.get(k)
    if cached and time.time() - cached[0] < FORMATS_TTL:
        return cached[1]
    data, err = _call("GET", f"{inst['base']}/api/rule/private/me", inst["api_key"])
    uid = data.get("user_id") if not err and isinstance(data, dict) else None
    _me_cache[k] = (time.time(), uid)
    return uid


def _owns(inst, detail):
    """Whether the rule (Rulezet detail) belongs to the Rulezet account of the API key"""
    me = _rulezet_user_id(inst)
    owner = (detail.get("user") or {}).get("id") if isinstance(detail, dict) else None
    return me is not None and owner is not None and str(me) == str(owner)


def _readable_case(cid):
    case = CommonModel.get_case(cid)
    if not case:
        return None, _error("Case not found", 404)
    if not check_user_private_case(case):
        return None, _error("Permission denied", 403)
    return case, None


def _writable_case(cid):
    case, err = _readable_case(cid)
    if err:
        return None, err
    if not (CommonModel.get_present_in_case(case.id, current_user) or current_user.is_admin()):
        return None, _error("Action not allowed", 403, "warning-subtle")
    return case, None


def _validate(inst, rule_format, content, remote_id=None):
    """Syntax check by Rulezet. The API key and the Rulezet id of the rule let Rulezet compile
    a rule together with the rules it references (e.g. a YARA rule using other rules)."""
    body = {"format": rule_format, "content": content}
    if remote_id and str(remote_id).isdigit():
        body["rule_id"] = int(remote_id)
    return _call("POST", f"{inst['base']}/api/rule/public/validate", inst["api_key"], json=body)


def _case_rule(case, rid):
    rule = Rulezet_Rule.query.get(rid)
    if not rule or rule.case_id != case.id or not rule.remote_id:
        return None, _error("Rule not found", 404)
    return rule, None


def _check_content(content):
    if not isinstance(content, str) or not content.strip():
        return _error("The rule is empty")
    if len(content.encode()) > MAX_CONTENT:
        return _error("Rule too large (512 KB max)")
    return None


@case_blueprint.route("/<int:cid>/rulezet/<int:ciid>/formats", methods=['GET'])
@login_required
def rulezet_formats(cid, ciid):
    """Formats known by the Rulezet instance: title, colour, logo URL, icon"""
    case, err = _readable_case(cid)
    if err:
        return err
    inst, err = _instance_for(case, ciid)
    if err:
        return err

    cached = _formats_cache.get(inst["base"])
    if cached and time.time() - cached[0] < FORMATS_TTL:
        return {"formats": cached[1]}, 200

    data, err = _call("GET", f"{inst['base']}/api/config/formats")
    if err:
        return err
    formats = []
    for f in data.get("formats", []):
        logo = f.get("logo")
        formats.append({
            "key": f.get("key"),
            "title": f.get("title") or f.get("key"),
            "color": f.get("color") or "#6C757D",
            "icon": f.get("icon") or "fa-file-code",
            "logo": _logo_data_url(inst["base"], logo),
            "rule_count": f.get("rule_count"),
            "category": f.get("category"),
        })
    _formats_cache[inst["base"]] = (time.time(), formats)
    return {"formats": formats}, 200


@case_blueprint.route("/<int:cid>/rulezet/<int:ciid>/search", methods=['GET'])
@login_required
def rulezet_search(cid, ciid):
    """Search the Rulezet instance. With an API key the results carry the rule id, so they
    can be added to the case; without one, only the public search (no ids) is available."""
    case, err = _readable_case(cid)
    if err:
        return err
    inst, err = _instance_for(case, ciid)
    if err:
        return err

    query = (request.args.get("q") or "").strip()
    rule_format = (request.args.get("format") or "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    mine = request.args.get("mine") in ("1", "true")

    if inst["api_key"]:
        body = {"search": query, "page": page, "per_page": 12, "paginate": True, "sort_by": "newest",
                "fields": ["id", "uuid", "title", "description", "author", "format", "version",
                           "creation_date", "last_modif", "vote_up", "vote_down", "cve_id", "to_string"]}
        if rule_format:
            body["rule_type"] = rule_format
        if mine:
            body["mine"] = True
        data, err = _call("POST", f"{inst['base']}/api/rule/private/search", inst["api_key"], json=body)
        if err:
            return err
        rules = data.get("rules", [])
        return {"rules": rules, "total": data.get("total", len(rules)), "page": data.get("page", page),
                "pages": data.get("pages", 1), "can_add": True}, 200

    if mine:
        return _error("Add an API key to the connector to list your own rules", 400, "warning-subtle")
    params = {"search": query, "page": page, "per_page": 12, "sort_by": "newest"}
    if rule_format:
        params["rule_type"] = rule_format
    data, err = _call("GET", f"{inst['base']}/api/rule/public/searchPage", params=params)
    if err:
        return err
    return {"rules": data.get("results", []), "total": data.get("total_rules_found", 0), "page": page,
            "pages": data.get("total_pages", 1), "can_add": False}, 200


@case_blueprint.route("/<int:cid>/rulezet/<int:ciid>/validate", methods=['POST'])
@login_required
def rulezet_validate(cid, ciid):
    """Syntax check of a rule by the Rulezet instance: {format, content, rule_id?} -> {valid, errors, warnings}.
    rule_id (a rule of the case) lets Rulezet resolve the other rules it references."""
    case, err = _readable_case(cid)
    if err:
        return err
    inst, err = _instance_for(case, ciid)
    if err:
        return err
    payload = request.get_json(silent=True) or {}
    rule_format, content = payload.get("format"), payload.get("content")
    if not rule_format or not isinstance(content, str) or not content.strip():
        return _error("Need a format and a content")
    if len(content.encode()) > MAX_CONTENT:
        return _error("Rule too large to be checked (512 KB max)")
    remote_id = None
    if payload.get("rule_id"):
        rule = Rulezet_Rule.query.get(payload.get("rule_id"))
        if rule and rule.case_id == case.id:
            remote_id = rule.remote_id
    data, err = _validate(inst, rule_format, content, remote_id)
    if err:
        return err
    return {"valid": bool(data.get("valid")), "errors": data.get("errors") or [],
            "warnings": data.get("warnings") or []}, 200


@case_blueprint.route("/<int:cid>/rulezet/<int:ciid>/rule/<int:rid>/remote", methods=['GET'])
@login_required
def rulezet_remote_rule(cid, ciid, rid):
    """The rule as currently published on Rulezet: details, and whether it changed since it
    was added to the case"""
    case, err = _readable_case(cid)
    if err:
        return err
    inst, err = _instance_for(case, ciid)
    if err:
        return err
    rule = Rulezet_Rule.query.get(rid)
    if not rule or rule.case_id != case.id or not rule.remote_id:
        return _error("Rule not found", 404)
    data, err = _call("GET", f"{inst['base']}/api/rule/public/detail/{quote(str(rule.remote_id), safe='')}")
    if err:
        return err
    remote_content = (data.get("to_string") or "").strip()
    local = (rule.content or "").strip()
    base = (rule.base_content if rule.base_content is not None else rule.content or "").strip()
    local_changed = local != base           # edited in Flowintel since it was taken
    remote_changed = remote_content != base  # updated on Rulezet since it was taken
    return {
        "remote": {
            "id": data.get("id"),
            "title": data.get("title"),
            "version": data.get("version"),
            "source": data.get("source"),
            "license": data.get("license"),
            # "cve_ids" is the list (recent Rulezet), "cve_id" the raw stored string (older ones)
            "cve_id": data.get("cve_ids") if isinstance(data.get("cve_ids"), list) else (data.get("cve_id") or ""),
            "tags": data.get("tags") or [],
            "attacks": data.get("attacks") or [],
            "last_modif": data.get("last_modif"),
            "original_uuid": data.get("original_uuid"),
            "user": data.get("user"),
            "url": f"{inst['base']}/rule/detail_rule/{data.get('id')}",
            "edit_url": f"{inst['base']}/rule/edit_rule/{data.get('id')}",
        },
        "changed": remote_content != local,
        # the author of the rule on Rulezet may edit it directly, others propose a change
        "owner": _owns(inst, data),
        "has_key": bool(inst["api_key"]),
        "remote_content": data.get("to_string") or "",
        "local_changed": local_changed,
        "remote_changed": remote_changed,
        # both sides changed: a resync would drop the edits made in Flowintel
        "conflict": local_changed and remote_changed and remote_content != local,
    }, 200


@case_blueprint.route("/<int:cid>/rulezet/<int:ciid>/rule/<int:rid>/save", methods=['POST'])
@login_required
@editor_required
@misp_editor_required
def rulezet_save_rule(cid, ciid, rid):
    """Save an edited rule in the case, once Rulezet says its syntax is valid (Rulezet is not changed)"""
    case, err = _writable_case(cid)
    if err:
        return err
    inst, err = _instance_for(case, ciid)
    if err:
        return err
    rule, err = _case_rule(case, rid)
    if err:
        return err
    content = (request.get_json(silent=True) or {}).get("content")
    err = _check_content(content)
    if err:
        return err

    data, err = _validate(inst, rule.format, content, rule.remote_id)
    if err:
        return err
    if not data.get("valid"):
        return {"message": "The rule is not valid, it was not saved", "toast_class": "warning-subtle",
                "errors": data.get("errors") or [], "warnings": data.get("warnings") or []}, 400

    rule.content = content
    db.session.commit()
    CommonModel.update_last_modif(case.id)
    CommonModel.save_history(case.uuid, current_user, f"Rulezet rule '{rule.title}' edited")
    flowintel_log("audit", 200, "Rulezet rule edited", User=current_user.email, CaseId=case.id, RuleId=rule.id)
    return {"message": "Rule saved", "toast_class": "success-subtle", "rule": rule.to_json(),
            "warnings": data.get("warnings") or []}, 200


@case_blueprint.route("/<int:cid>/rulezet/<int:ciid>/rule/<int:rid>/publish", methods=['POST'])
@login_required
@editor_required
@misp_editor_required
def rulezet_publish_rule(cid, ciid, rid):
    """Send an edited rule to Rulezet: {content, mode: "edit"|"proposal", message, base_last_modif}.
    Rulezet decides with the API key: its author may edit the rule directly, anyone else (or
    mode "proposal") creates an edit proposal for the author to review."""
    case, err = _writable_case(cid)
    if err:
        return err
    inst, err = _instance_for(case, ciid)
    if err:
        return err
    if not inst["api_key"]:
        return _error("Add an API key to the Rulezet connector to send changes to Rulezet", 400, "warning-subtle")
    rule, err = _case_rule(case, rid)
    if err:
        return err
    payload = request.get_json(silent=True) or {}
    content = payload.get("content")
    err = _check_content(content)
    if err:
        return err
    mode = "edit" if payload.get("mode") == "edit" else "proposal"
    body = {"content": content, "mode": mode, "message": str(payload.get("message") or "")[:2000]}
    if payload.get("base_last_modif"):
        body["base_last_modif"] = str(payload["base_last_modif"])

    try:
        res = requests.post(f"{inst['base']}/api/rule/private/edit/{quote(str(rule.remote_id), safe='')}",
                            headers=_headers(inst["api_key"]), json=body, verify=VERIFY_SSL, timeout=TIMEOUT)
        data = res.json()
    except (requests.RequestException, ValueError):
        return _error("Could not reach Rulezet", 502)
    if res.status_code >= 400 or not data.get("success"):
        # 409: the rule changed on Rulezet since it was read, or the same proposal is already open
        return {"message": data.get("message") or f"Rulezet returned HTTP {res.status_code}",
                "toast_class": "warning-subtle", "conflict": res.status_code == 409,
                "current_version": data.get("current_version")}, res.status_code if res.status_code < 500 else 502

    # The case keeps the content sent. After a direct edit it is the Rulezet version too.
    rule.content = content
    if data.get("mode") == "edit":
        rule.base_content = content
        if data.get("version"):
            rule.version = str(data["version"])
        what = "edited on Rulezet"
    else:
        what = "proposed as a change on Rulezet"
    db.session.commit()
    CommonModel.update_last_modif(case.id)
    CommonModel.save_history(case.uuid, current_user, f"Rulezet rule '{rule.title}' {what}")
    flowintel_log("audit", 200, f"Rulezet rule {what}", User=current_user.email, CaseId=case.id, RuleId=rule.id)
    return {"message": "Rule updated on Rulezet" if data.get("mode") == "edit" else "Change proposed to the author on Rulezet",
            "toast_class": "success-subtle", "mode": data.get("mode"), "url": data.get("url"),
            "rule": rule.to_json()}, 200


@case_blueprint.route("/<int:cid>/rulezet/<int:ciid>/rule/<int:rid>/dependencies", methods=['GET'])
@login_required
def rulezet_rule_dependencies(cid, ciid, rid):
    """Rules this rule needs on Rulezet (e.g. YARA rules used in its condition), and the ones
    that need it, each with whether it is already in the case"""
    case, err = _readable_case(cid)
    if err:
        return err
    inst, err = _instance_for(case, ciid)
    if err:
        return err
    rule, err = _case_rule(case, rid)
    if err:
        return err
    data, err = _call("GET", f"{inst['base']}/api/rule/public/dependencies/{quote(str(rule.remote_id), safe='')}")
    if err:
        return err
    in_case = {str(r.remote_id) for r in Rulezet_Rule.query.filter_by(case_id=case.id, instance_id=rule.instance_id).all()}
    keep = ("id", "uuid", "title", "format", "depth", "via", "version")
    def rows(items):
        return [{**{k: d.get(k) for k in keep}, "in_case": str(d.get("id")) in in_case} for d in items or []]
    return {"requires": rows(data.get("requires")), "required_by": rows(data.get("required_by")),
            "install_order": data.get("install_order") or [], "truncated": bool(data.get("truncated"))}, 200
