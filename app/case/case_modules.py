from flask import request, jsonify
from flask_login import login_required, current_user

from .case import case_blueprint, check_user_private_case
from .CaseCore import CaseModel
from . import common_core as CommonModel
from ..db_class.db import Rulezet_Rule, Case_Connector_Instance, Connector_Instance, db
from ..decorators import misp_editor_required
from ..utils.logger import flowintel_log


#############
## MODULES ##
#############

@case_blueprint.route("/get_case_modules", methods=['GET'])
@login_required
def get_case_modules():
    """Get all modules"""
    return {"modules": CommonModel.get_modules_by_case_task('case')}, 200


@case_blueprint.route("/<cid>/get_instance_module", methods=['GET'])
@login_required
def get_instance_module(cid):
    """Get all connectors instances by modules"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get instance module of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        if "module" not in request.args:
            return {"message": "Need to pass 'module'", 'toast_class': "danger-subtle"}, 400
        if "type" not in request.args:
            return {"message": "Need to pass 'type'", 'toast_class': "danger-subtle"}, 400
        module = request.args.get("module")
        type_module = request.args.get("type")
        return {"instances": CaseModel.get_instance_module_core(module, type_module, cid, current_user.id)}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/module_counts", methods=['GET'])
@login_required
def get_module_counts(cid):
    """Return counts for known module components for the case."""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get module counts of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403

        counts = {}
        try:
            counts['Rulezet'] = Rulezet_Rule.query.filter_by(case_id=case.id).count()
        except Exception:
            counts['Rulezet'] = 0

        return {"counts": counts}, 200
    return {"message": "Case Not Found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/call_module_case", methods=['GET', 'POST'])
@login_required
@misp_editor_required
def call_module_case(cid):
    """Run a module"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Call module on case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403

        if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
            flowintel_log("audit", 403, "Call module on case: Org not assigned to case", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403

        payload = request.get_json()
        case_instance_id = payload.get("case_task_instance_id")
        module = payload.get("module")
        res = CaseModel.call_module_case(module, case_instance_id, case, current_user, payload=payload)
        if res:
            res["toast_class"] = "danger-subtle"
            return jsonify(res), 400
        flowintel_log("audit", 200, "Module called on case", User=current_user.email, CaseId=cid, Module=module)
        return {"message": "Connector used", 'toast_class': "success-subtle"}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404



#############
## Rulezet ##
#############

@case_blueprint.route("/<cid>/rulezet_rules", methods=['GET'])
@login_required
def get_rulezet_rules(cid):
    """Return stored Rulezet rules for a case (optional query param `instance_id`)"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get rulezet rules of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        instance_id = request.args.get('instance_id')
        query = Rulezet_Rule.query.filter_by(case_id=case.id)
        if instance_id:
            try:
                query = query.filter_by(instance_id=int(instance_id))
            except Exception:
                pass
        rules = [r.to_json() for r in query.order_by(Rulezet_Rule.date_added.desc()).all()]
        return {"rules": rules}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/rulezet_rule_remove", methods=['POST'])
@login_required
@misp_editor_required
def remove_rulezet_rule(cid):
    """Remove a stored Rulezet rule for a case."""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Remove rulezet rule: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403

        payload = request.get_json() or {}
        rule = None

        if "id" in payload:
            try:
                rule = Rulezet_Rule.query.get(int(payload.get("id")))
            except Exception:
                rule = None

        if not rule and "uuid" in payload:
            rule = Rulezet_Rule.query.filter_by(uuid=payload.get("uuid")).first()

        if not rule and "remote_id" in payload and "instance_id" in payload:
            try:
                rule = Rulezet_Rule.query.filter_by(remote_id=str(payload.get("remote_id")), instance_id=int(payload.get("instance_id")), case_id=case.id).first()
            except Exception:
                rule = None

        if not rule:
            return {"message": "Rule not found", "toast_class": "warning-subtle"}, 404

        if rule.case_id != case.id:
            flowintel_log("audit", 403, "Remove rulezet rule: Action not allowed", User=current_user.email, CaseId=cid, RuleId=rule.id)
            return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403

        try:
            db.session.delete(rule)
            db.session.commit()
            CommonModel.update_last_modif(case.id)
            flowintel_log("audit", 200, "Rulezet rule removed", User=current_user.email, CaseId=cid, RuleId=rule.id)
            return {"message": "Rule removed", "toast_class": "success-subtle"}, 200
        except Exception:
            db.session.rollback()
            return {"message": "Error removing rule", "toast_class": "danger-subtle"}, 400

    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/remove_module_tab/<connType>", methods=['POST'])
@login_required
@misp_editor_required
def remove_module_tab(cid, connType):
    """Remove all data and connector linkages for a given connector type from a case."""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404

    if not check_user_private_case(case):
        flowintel_log("audit", 403, "Remove module tab: Permission denied", User=current_user.email, CaseId=cid)
        return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403

    if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
        flowintel_log("audit", 403, "Remove module tab: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", 'toast_class': "warning-subtle"}, 403

    # Delete module-specific data based on connector type
    if connType.upper() == 'RULEZET':
        try:
            Rulezet_Rule.query.filter_by(case_id=case.id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()

    # Remove all Case_Connector_Instance rows for this connector type from the case
    connector = CommonModel.get_connector_by_name(connType)
    if connector:
        try:
            instances_of_type = Connector_Instance.query.filter_by(connector_id=connector.id).all()
            instance_ids = [i.id for i in instances_of_type]
            if instance_ids:
                Case_Connector_Instance.query.filter(
                    Case_Connector_Instance.case_id == case.id,
                    Case_Connector_Instance.instance_id.in_(instance_ids)
                ).delete(synchronize_session=False)
                db.session.commit()
        except Exception:
            db.session.rollback()

    CommonModel.update_last_modif(case.id)
    flowintel_log("audit", 200, f"Module tab {connType} removed from case", User=current_user.email, CaseId=cid)
    return {"message": f"{connType} module removed", 'toast_class': "success-subtle"}, 200
