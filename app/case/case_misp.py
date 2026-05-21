from flask import request, jsonify
from flask_login import login_required, current_user

from .case import case_blueprint, check_user_private_case
from .CaseCore import CaseModel
from . import common_core as CommonModel
from ..connectors import connectors_core as ConnectorsModel
from ..connectors import connectors_core as ConnectorModel
from ..db_class.db import Task, Task_Misp_Object, Misp_Object_Instance_Uuid, Misp_Attribute_Instance_Uuid, Case_Timeline_Event, db
from ..decorators import editor_required, misp_editor_required
from ..utils.logger import flowintel_log
from ..utils.utils import get_object_templates
from functools import lru_cache


###############
# MISP Object #
###############

@case_blueprint.route("/<int:cid>/get_case_misp_object", methods=['GET'])
@login_required
def get_case_misp_object(cid):
    """Get case list of misp object"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get MISP objects of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        misp_object = CaseModel.get_misp_object_by_case(cid)
        loc_object = list()
        for object in misp_object:
            loc_attr_list = list()
            for attribute in object.attributes:
                res = CaseModel.check_correlation_attr(cid, attribute)
                loc_attr = attribute.to_json()
                loc_attr["correlation_list"] = res
                loc_attr_list.append(loc_attr)

            # Collect synced instance info for badge display
            synced_instances = []
            for uuid_row in Misp_Object_Instance_Uuid.query.filter_by(misp_object_id=object.id, case_id=int(cid)).all():
                inst = CommonModel.get_instance(uuid_row.instance_id)
                synced_instances.append({
                    "instance_id": uuid_row.instance_id,
                    "instance_name": inst.name if inst else str(uuid_row.instance_id),
                    "instance_url": inst.url if inst else None,
                    "object_uuid": uuid_row.object_instance_uuid
                })

            loc_object.append({
                "object_name": object.name,
                "attributes": loc_attr_list,
                "object_id": object.id,
                "object_uuid": object.template_uuid,
                "object_creation_date": object.creation_date.strftime('%Y-%m-%d %H:%M'),
                "object_last_modif": object.last_modif.strftime('%Y-%m-%d %H:%M'),
                "synced_instances": synced_instances,
                # Mark whether this object already has a timeline event
                "is_imported": True if Case_Timeline_Event.query.filter_by(case_id=int(cid), misp_object_id=object.id).first() else False
                ,
                # Tasks assigned to this object
                "tasks": [
                    {"id": t.task_id, "title": (Task.query.get(t.task_id).title if Task.query.get(t.task_id) else None)}
                    for t in Task_Misp_Object.query.filter_by(misp_object_id=object.id).all()
                ]
            })
        return {"misp-object": loc_object}
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<int:cid>/get_correlation_attr/<int:aid>", methods=['GET'])
@login_required
def get_correlation_attr(cid, aid):
    case = CommonModel.get_case(cid)
    if not case:
        return {"correlation_list": []}, 200
    if not check_user_private_case(case):
        return {"correlation_list": []}, 200
    attribute = CaseModel.get_misp_attribute(aid)
    res = CaseModel.check_correlation_attr(cid, attribute)
    return {"correlation_list": res}, 200


@case_blueprint.route("/get_misp_object", methods=['GET'])
@login_required
def get_misp_object():
    """Get list of misp object"""
    return {"misp-object": get_object_templates()}, 200


@case_blueprint.route("/get_misp_attribute_types", methods=['GET'])
@login_required
def get_misp_attribute_types():
    """Return list of MISP attribute types (for frontend dropdowns)"""
    # Return the cached canonical types. Use ?force=1 to rebuild cache.
    force = request.args.get('force', '').lower() in ('1', 'true', 'yes')
    if force:
        try:
            _build_misp_attribute_types.cache_clear()
        except Exception:
            pass
    try:
        types = list(_build_misp_attribute_types())
        return jsonify({"types": types}), 200
    except Exception as e:
        flowintel_log('error', 500, 'Failed to build attribute types from templates', error=str(e))
        return jsonify({"types": []}), 200


@lru_cache(maxsize=1)
def _build_misp_attribute_types():
    """Construct and cache the canonical list of attribute types from templates."""
    templates = get_object_templates()
    types_set = set()
    for tpl in templates:
        for attr in tpl.get('attributes', []):
            ma = attr.get('misp_attribute')
            if not ma:
                continue
            if isinstance(ma, (list, tuple)):
                for t in ma:
                    types_set.add(t)
            else:
                types_set.add(ma)
    return tuple(sorted(types_set))


@case_blueprint.route("/<cid>/create_misp_object", methods=['POST'])
@login_required
@editor_required
def create_misp_object(cid):
    """Create misp object"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "object-template" in request.json:
                if "attributes" in request.json:
                    CaseModel.create_misp_object(cid, request.json, current_user)
                    flowintel_log("audit", 200, "MISP object created", User=current_user.email, CaseId=cid, ObjectTemplate=request.json["object-template"])
                    return {"message": "Object created", "toast_class": "success-subtle"}, 200
                return {"message": "Need to pass 'attributes'", "toast_class": "warning-subtle"}, 400
            return {"message": "Need to pass 'object-template'", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Create MISP object: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/delete_object/<oid>", methods=['GET'])
@login_required
@editor_required
def delete_object(cid, oid):
    """Delete an object from case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.delete_object(cid, oid, current_user):
                flowintel_log("audit", 200, "MISP object deleted", User=current_user.email, CaseId=cid, ObjectId=oid)
                return {"message": "Object deleted", "toast_class": "success-subtle"}, 200
            return {"message": "Object not found in this case", "toast_class": "warning-subtle"}, 404
        flowintel_log("audit", 403, "Delete MISP object: Action not allowed", User=current_user.email, CaseId=cid, ObjectId=oid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/add_attributes/<oid>", methods=['POST'])
@login_required
@editor_required
def add_attributes(cid, oid):
    """Add attributes to an existing object"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "object-template" in request.json:
                if "attributes" in request.json:
                    if CaseModel.add_attributes_object(cid, oid, request.json):
                        flowintel_log("audit", 200, "Attributes added to MISP object", User=current_user.email, CaseId=cid, ObjectId=oid)
                        return {"message": "Receive", "toast_class": "success-subtle"}, 200
                    return {"message": "Object not found in this case", "toast_class": "warning-subtle"}, 404
                return {"message": "Need to pass 'attributes'", "toast_class": "warning-subtle"}, 400
            return {"message": "Need to pass 'object-template'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/misp_object/<oid>/edit_attr/<aid>", methods=['POST'])
@login_required
@editor_required
def edit_attr(cid, oid, aid):
    """Edit misp object"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "value" in request.json:
                if "type" in request.json:
                    flowintel_log("audit", 200, "Edit attribute of MISP object", User=current_user.email, CaseId=cid, ObjectId=oid, AttributeId=aid)
                    return CaseModel.edit_attr(cid, oid, aid, request.json)
                return {"message": "Need to pass 'value'", "toast_class": "warning-subtle"}, 400
            return {"message": "Need to pass 'type'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/misp_object/<oid>/delete_attribute/<aid>", methods=['GET'])
@login_required
@editor_required
def delete_attribute(cid, oid, aid):
    """Delete an object from case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            flowintel_log("audit", 200, "Delete attribute of MISP object", User=current_user.email, CaseId=cid, ObjectId=oid, AttributeId=aid)
            return CaseModel.delete_attribute(cid, oid, aid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/nb_objects", methods=['GET'])
@login_required
def nb_objects(cid):
    """Return nb of misp objects"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get number of MISP objects of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        return {"nb_objects": len(CaseModel.get_misp_object_by_case(cid))}, 200
    return {"message": "Case not found"}, 404


@case_blueprint.route("/<int:cid>/misp_object/<int:oid>/set_tasks", methods=['POST'])
@login_required
@editor_required
def set_misp_object_tasks(cid, oid):
    """Assign tasks to a MISP object (replace current assignments)."""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404
    if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
        flowintel_log("audit", 403, "Set MISP object tasks: Action not allowed", User=current_user.email, CaseId=cid, ObjectId=oid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403

    misp_object = CaseModel.get_misp_object(oid)
    if not misp_object or int(misp_object.case_id) != int(cid):
        return {"message": "Object not found in this case", "toast_class": "warning-subtle"}, 404

    task_ids = request.json.get('task_ids', []) if request.is_json else []
    if not isinstance(task_ids, list):
        return {"message": "task_ids must be a list", "toast_class": "warning-subtle"}, 400

    # Normalize and validate tasks
    valid_new_ids = set()
    for tid in task_ids:
        try:
            tid_int = int(tid)
        except Exception:
            continue
        t = Task.query.get(tid_int)
        if t and int(t.case_id) == int(cid):
            valid_new_ids.add(tid_int)

    # Current assignments
    existing_links = Task_Misp_Object.query.filter_by(misp_object_id=oid).all()
    existing_ids = set([l.task_id for l in existing_links])

    to_add = valid_new_ids - existing_ids
    to_remove = existing_ids - valid_new_ids

    try:
        for tid in to_add:
            link = Task_Misp_Object(task_id=tid, misp_object_id=oid)
            db.session.add(link)
        if to_remove:
            Task_Misp_Object.query.filter(Task_Misp_Object.misp_object_id == oid, Task_Misp_Object.task_id.in_(list(to_remove))).delete(synchronize_session=False)
        db.session.commit()

        CommonModel.save_history(case.uuid, current_user, f"Updated tasks for MISP object {misp_object.id}")
        CommonModel.update_last_modif(cid)
        return {"message": "Tasks updated", "toast_class": "success-subtle"}, 200
    except Exception:
        db.session.rollback()
        return {"message": "Error updating tasks", "toast_class": "danger-subtle"}, 500


##############################
# Standalone MISP Attributes #
##############################

@case_blueprint.route("/<int:cid>/get_case_misp_attributes", methods=['GET'])
@login_required
def get_case_misp_attributes(cid):
    case = CommonModel.get_case(cid)
    if not case or not check_user_private_case(case):
        return {"message": "No case found", "toast_class": "warning-subtle"}, 404
    attrs = CaseModel.get_standalone_attributes_by_case(cid)
    result = []
    for attr in attrs:
        loc = attr.to_json()
        loc["correlation_list"] = CaseModel.check_correlation_attr(cid, attr)
        loc["synced_instances"] = []
        synced = Misp_Attribute_Instance_Uuid.query.filter_by(misp_attribute_id=attr.id, case_id=cid).all()
        for s in synced:
            loc["synced_instances"].append({
                "instance_id": s.instance_id,
                "uuid": s.attribute_instance_uuid
            })
        result.append(loc)
    return jsonify({"attributes": result})


@case_blueprint.route("/<int:cid>/create_misp_attribute", methods=['POST'])
@login_required
@editor_required
@misp_editor_required
def create_misp_attribute(cid):
    case = CommonModel.get_case(cid)
    if not case or not check_user_private_case(case):
        return {"message": "No case found", "toast_class": "warning-subtle"}, 404
    data = request.get_json()
    if not data:
        return {"message": "No data provided", "toast_class": "warning-subtle"}, 400
    if not data.get("value"):
        return {"message": "Value is required", "toast_class": "warning-subtle"}, 400
    if not data.get("type"):
        return {"message": "Type is required", "toast_class": "warning-subtle"}, 400
    attr = CaseModel.create_standalone_attribute(cid, data, current_user)
    return {"message": "Attribute created", "toast_class": "success-subtle", "attribute": attr.to_json()}, 201


@case_blueprint.route("/<int:cid>/misp_attribute/<int:aid>/edit_misp_attribute", methods=['POST'])
@login_required
@editor_required
@misp_editor_required
def edit_misp_attribute(cid, aid):
    case = CommonModel.get_case(cid)
    if not case or not check_user_private_case(case):
        return {"message": "No case found", "toast_class": "warning-subtle"}, 404
    data = request.get_json()
    if not data:
        return {"message": "No data provided", "toast_class": "warning-subtle"}, 400
    result, status = CaseModel.edit_standalone_attr(cid, aid, data)
    return result, status


@case_blueprint.route("/<int:cid>/misp_attribute/<int:aid>/delete_misp_attribute", methods=['GET'])
@login_required
@editor_required
@misp_editor_required
def delete_misp_attribute(cid, aid):
    case = CommonModel.get_case(cid)
    if not case or not check_user_private_case(case):
        return {"message": "No case found", "toast_class": "warning-subtle"}, 404
    result, status = CaseModel.delete_standalone_attr(cid, aid)
    return result, status


############
# Timeline #
############

@case_blueprint.route("/<int:cid>/get_timeline_events", methods=['GET'])
@login_required
def get_timeline_events(cid):
    """Get all timeline events for a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        events = CaseModel.get_timeline_events(cid)
        return {"events": [e.to_json() for e in events]}, 200
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<int:cid>/create_timeline_event", methods=['POST'])
@login_required
@editor_required
def create_timeline_event(cid):
    """Create a new timeline event"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "date_text" in request.json and "description" in request.json:
                misp_object_id = request.json.get("misp_object_id")
                event = CaseModel.create_timeline_event(
                    cid, request.json["date_text"], request.json["description"],
                    misp_object_id, current_user
                )
                return {"message": "Event created", "toast_class": "success-subtle", "event": event.to_json()}, 200
            return {"message": "Need 'date_text' and 'description'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<int:cid>/edit_timeline_event/<int:eid>", methods=['POST'])
@login_required
@editor_required
def edit_timeline_event(cid, eid):
    """Edit a timeline event"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "date_text" in request.json and "description" in request.json:
                event = CaseModel.edit_timeline_event(
                    eid, request.json["date_text"], request.json["description"], current_user
                )
                if event:
                    return {"message": "Event updated", "toast_class": "success-subtle", "event": event.to_json()}, 200
                return {"message": "Event not found", "toast_class": "warning-subtle"}, 404
            return {"message": "Need 'date_text' and 'description'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<int:cid>/delete_timeline_event/<int:eid>", methods=['GET'])
@login_required
@editor_required
def delete_timeline_event(cid, eid):
    """Delete a timeline event"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.delete_timeline_event(cid, eid, current_user):
                return {"message": "Event deleted", "toast_class": "success-subtle"}, 200
            return {"message": "Event not found", "toast_class": "warning-subtle"}, 404
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<int:cid>/import_misp_to_timeline", methods=['POST'])
@login_required
@editor_required
def import_misp_to_timeline(cid):
    """Import MISP objects into the timeline"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            data = request.get_json(silent=True) or {}
            object_ids = data.get('object_ids', None)
            if object_ids is not None and not isinstance(object_ids, list):
                return {"message": "'object_ids' must be a list", "toast_class": "warning-subtle"}, 400
            count = CaseModel.import_misp_objects_to_timeline(cid, current_user, object_ids)
            return {"message": f"{count} MISP object(s) imported to timeline", "toast_class": "success-subtle"}, 200
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


#####################
# Timeline  - Graph #
#####################

@case_blueprint.route("/<int:cid>/get_timeline_graph", methods=['GET'])
@login_required
def get_timeline_graph(cid):
    """Get all timeline events and links for graph view"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        events = CaseModel.get_timeline_events(cid)
        links = CaseModel.get_timeline_event_links(cid)
        return {
            "events": [e.to_json() for e in events],
            "links": [l.to_json() for l in links]
        }, 200
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<int:cid>/create_timeline_event_link", methods=['POST'])
@login_required
@editor_required
def create_timeline_event_link(cid):
    """Create a link between two timeline events"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "source_event_id" in request.json and "target_event_id" in request.json:
                link = CaseModel.create_timeline_event_link(
                    cid,
                    request.json["source_event_id"],
                    request.json["target_event_id"],
                    request.json.get("label", ""),
                    current_user
                )
                return {"message": "Link created", "toast_class": "success-subtle", "link": link.to_json()}, 200
            return {"message": "Need 'source_event_id' and 'target_event_id'", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<int:cid>/edit_timeline_event_link/<int:lid>", methods=['POST'])
@login_required
@editor_required
def edit_timeline_event_link(cid, lid):
    """Edit a timeline event link label"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            link = CaseModel.edit_timeline_event_link(lid, request.json.get("label", ""), current_user)
            if link:
                return {"message": "Link updated", "toast_class": "success-subtle", "link": link.to_json()}, 200
            return {"message": "Link not found", "toast_class": "warning-subtle"}, 404
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<int:cid>/delete_timeline_event_link/<int:lid>", methods=['GET'])
@login_required
@editor_required
def delete_timeline_event_link(cid, lid):
    """Delete a timeline event link"""
    case = CommonModel.get_case(cid)
    if case:
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.delete_timeline_event_link(cid, lid, current_user):
                return {"message": "Link deleted", "toast_class": "success-subtle"}, 200
            return {"message": "Link not found", "toast_class": "warning-subtle"}, 404
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


#############
# Connector #
#############

@case_blueprint.route("/<cid>/get_case_connectors", methods=['GET', 'POST'])
@login_required
@misp_editor_required
def get_case_connectors(cid):
    """Get all connectors for a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get connectors of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        instance_list = list()
        misp_connector = CommonModel.get_connector_by_name("MISP")
        for case_connector in CommonModel.get_case_connectors(cid, current_user):
            is_misp_connector = False
            if misp_connector:
                connect_instance = CommonModel.get_instance(case_connector.instance_id)
                if connect_instance and connect_instance.connector_id == misp_connector.id:
                    is_misp_connector = True
            instance_list.append({
                "case_task_instance_id": case_connector.id,
                "details": CommonModel.get_instance_with_icon(case_connector.instance_id),
                "identifier": case_connector.identifier,
                "is_updating_case": case_connector.is_updating_case,
                "is_misp_connector": is_misp_connector,
                "last_sync": case_connector.last_sync.strftime('%Y-%m-%d %H:%M') if case_connector.last_sync else None
            })
        return {"case_connectors": instance_list}, 200
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/add_connector", methods=['POST'])
@login_required
@misp_editor_required
def add_connector(cid):
    """Add MISP Connector"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "connectors" in request.json and CaseModel.add_connector(cid, request.json, current_user):
                flowintel_log("audit", 200, "Connector added to case", User=current_user.email, CaseId=cid)
                return {"message": "Connector added successfully", "toast_class": "success-subtle"}, 200
            return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Add connector to case: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/connectors/<ciid>/remove_connector", methods=['GET'])
@login_required
@misp_editor_required
def remove_connector(cid, ciid):
    """Remove a connector from case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.remove_connector(ciid):
                flowintel_log("audit", 200, "Connector removed from case", User=current_user.email, CaseId=cid, ConnectorInstanceId=ciid)
                return {"message": "Connector removed", 'toast_class': "success-subtle"}, 200
            return {"message": "Something went wrong", 'toast_class': "danger-subtle"}, 400
        flowintel_log("audit", 403, "Remove connector from case: Action not allowed", User=current_user.email, CaseId=cid, ConnectorInstanceId=ciid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/connectors/<ciid>/edit_connector", methods=['POST'])
@login_required
@misp_editor_required
def edit_connector(cid, ciid):
    """Edit Connector"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "identifier" in request.json:
                if CaseModel.edit_connector(ciid, request.json):
                    flowintel_log("audit", 200, "Connector edited", User=current_user.email, CaseId=cid, ConnectorInstanceId=ciid)
                    return {"message": "Connector edited successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Error editing connector", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Edit connector: Action not allowed", User=current_user.email, CaseId=cid, ConnectorInstanceId=ciid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<int:cid>/connectors/<int:ciid>/misp_objects_preview", methods=['GET'])
@login_required
@misp_editor_required
def misp_objects_preview(cid, ciid):
    """Fetch the list of MISP objects from the remote event for a connector (preview before sync)."""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404
    if not check_user_private_case(case):
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403

    case_instance = CommonModel.get_case_connectors_by_id(ciid)
    if not case_instance or case_instance.case_id != int(cid):
        return {"message": "Connector not found", "toast_class": "danger-subtle"}, 404
    if not case_instance.identifier:
        return {"message": "No identifier set for this connector", "toast_class": "warning-subtle"}, 400

    loc_instance = CommonModel.get_instance(case_instance.instance_id)
    if not loc_instance:
        return {"message": "Connector instance not found", "toast_class": "danger-subtle"}, 404

    user_instance = CommonModel.get_user_instance_both(current_user.id, loc_instance.id)
    api_key = loc_instance.global_api_key or (user_instance.api_key if user_instance else None)
    if not api_key:
        return {"message": "No API key configured for this connector", "toast_class": "warning-subtle"}, 400

    objects, error = ConnectorsModel.misp_get_event_objects(loc_instance, api_key, case_instance.identifier)
    if error:
        return {"message": error["message"], "toast_class": error["toast_class"]}, error["status"]
    return {"objects": objects.get("objects", []), "standalone_attributes": objects.get("standalone_attributes", [])}, 200


@case_blueprint.route("/<int:cid>/connectors/<int:ciid>/sync_logs", methods=['GET'])
@login_required
@misp_editor_required
def get_sync_logs(cid, ciid):
    """Get sync history for a connector instance."""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404
    if not check_user_private_case(case):
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403

    case_instance = CommonModel.get_case_connectors_by_id(ciid)
    if not case_instance or case_instance.case_id != int(cid):
        return {"message": "Connector not found", "toast_class": "danger-subtle"}, 404

    return {"sync_logs": ConnectorsModel.get_connector_sync_logs(cid, ciid)}, 200


@case_blueprint.route("/<int:cid>/connectors/<int:ciid>/import_event_report", methods=['POST'])
@login_required
@misp_editor_required
def import_event_report(cid, ciid):
    """Fetch MISP event reports and import them as a case note."""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404
    if not check_user_private_case(case):
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
    if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403

    case_instance = CommonModel.get_case_connectors_by_id(ciid)
    if not case_instance or case_instance.case_id != int(cid):
        return {"message": "Connector not found", "toast_class": "danger-subtle"}, 404
    if not case_instance.identifier:
        return {"message": "No identifier set for this connector", "toast_class": "warning-subtle"}, 400

    loc_instance = CommonModel.get_instance(case_instance.instance_id)
    if not loc_instance:
        return {"message": "Connector instance not found", "toast_class": "danger-subtle"}, 404

    user_instance = CommonModel.get_user_instance_both(current_user.id, loc_instance.id)
    api_key = loc_instance.global_api_key or (user_instance.api_key if user_instance else None)
    if not api_key:
        return {"message": "No API key configured for this connector", "toast_class": "warning-subtle"}, 400

    note_content, error = ConnectorsModel.misp_get_event_reports(loc_instance, api_key, case_instance.identifier)
    if error:
        return {"message": error["message"], "toast_class": error["toast_class"]}, error["status"]

    existing = case.notes or ""
    separator = "\n\n---\n\n" if existing.strip() else ""
    CaseModel.modify_note_core(cid, current_user, existing + separator + note_content)
    flowintel_log("audit", 200, "MISP event report imported as case note", User=current_user.email, CaseId=cid)
    return {"message": "Report(s) imported as case note", "toast_class": "success-subtle"}, 200


@case_blueprint.route("/<int:cid>/misp_object/<int:oid>/link_remote", methods=['POST'])
@login_required
@misp_editor_required
def link_remote_misp_object(cid, oid):
    """Manually link a local MISP object to a remote object UUID on a specific connector instance."""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404
    if not check_user_private_case(case):
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
    if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403

    data = request.get_json(silent=True) or {}
    instance_id = data.get("instance_id")
    remote_uuid = data.get("remote_uuid", "").strip()
    if not instance_id or not remote_uuid:
        return {"message": "Need 'instance_id' and 'remote_uuid'", "toast_class": "warning-subtle"}, 400

    loc_object = CaseModel.get_misp_object(oid)
    if not loc_object or loc_object.case_id != int(cid):
        return {"message": "Object not found", "toast_class": "danger-subtle"}, 404

    # Enforce one link per object — remove all existing links before creating the new one
    Misp_Object_Instance_Uuid.query.filter_by(misp_object_id=oid, case_id=int(cid)).delete()
    link = Misp_Object_Instance_Uuid(
        instance_id=int(instance_id),
        misp_object_id=oid,
        object_instance_uuid=remote_uuid,
        case_id=int(cid)
    )
    db.session.add(link)
    db.session.commit()
    flowintel_log("audit", 200, f"Linked local object {oid} to remote UUID {remote_uuid}", User=current_user.email, CaseId=cid)
    return {"message": "Object linked to remote MISP object", "toast_class": "success-subtle"}, 200


@case_blueprint.route("/<int:cid>/misp_object/<int:oid>/unlink_remote/<int:instance_id>", methods=['DELETE'])
@login_required
@misp_editor_required
def unlink_remote_misp_object(cid, oid, instance_id):
    """Remove the link between a local MISP object and a remote object on a connector instance."""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404
    if not check_user_private_case(case):
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
    if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403

    link = Misp_Object_Instance_Uuid.query.filter_by(
        misp_object_id=oid, instance_id=int(instance_id), case_id=int(cid)
    ).first()
    if not link:
        return {"message": "Link not found", "toast_class": "warning-subtle"}, 404

    db.session.delete(link)
    db.session.commit()
    flowintel_log("audit", 200, f"Unlinked local object {oid} from instance {instance_id}", User=current_user.email, CaseId=cid)
    return {"message": "Link removed", "toast_class": "success-subtle"}, 200


@case_blueprint.route("/<cid>/connectors/<ciid>/search_in_misp", methods=['POST'])
@login_required
@misp_editor_required
def search_in_misp_case(cid, ciid):
    """Search attributes in MISP using a receive_from MISP connector attached to a case."""
    if not CommonModel.get_case(cid):
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404
    if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
        flowintel_log("audit", 403, "Search in MISP: Action not allowed", User=current_user.email, CaseId=cid, ConnectorInstanceId=ciid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403

    case_connector = CommonModel.get_case_connectors_by_id(ciid)
    if not case_connector or str(case_connector.case_id) != str(cid):
        return {"message": "Connector not attached to this case", "toast_class": "warning-subtle"}, 404

    instance = CommonModel.get_instance(case_connector.instance_id)
    misp_connector = CommonModel.get_connector_by_name("MISP")
    if not instance or not misp_connector or instance.connector_id != misp_connector.id:
        return {"message": "Connector is not a MISP connector", "toast_class": "warning-subtle"}, 400

    query = ((request.json or {}).get("query") or "").strip()
    if not query:
        return {"message": "Search query is required", "toast_class": "warning-subtle"}, 400

    res = ConnectorModel.search_misp_attributes(instance, current_user, query)
    if not res.get("success"):
        flowintel_log("audit", 400, f"Search in MISP failed: {res.get('message')}", User=current_user.email, CaseId=cid, ConnectorInstanceId=ciid)
        return {"message": res.get("message", "MISP search failed"), "toast_class": "danger-subtle"}, 400

    flowintel_log("audit", 200, "Searched attributes in MISP", User=current_user.email, CaseId=cid, ConnectorInstanceId=ciid, Query=query)
    return {"results": res["results"]}, 200


@case_blueprint.route("/<cid>/append_note_case", methods=['POST'])
@login_required
@editor_required
def append_note_case(cid):
    """Append text to the case note (used by Search-in-MISP results)."""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404
    if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
        flowintel_log("audit", 403, "Append note: Org not assigned to case", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403

    notes = (request.json or {}).get("notes")
    if not notes:
        return {"message": "Key 'notes' missing", "toast_class": "warning-subtle"}, 400
    if CaseModel.append_note_core(cid, current_user, notes):
        flowintel_log("audit", 200, "Note appended", User=current_user.email, CaseId=cid)
        return {"notes": case.notes, "message": "Note appended", "toast_class": "success-subtle"}, 200
    return {"message": "Error appending note", "toast_class": "danger-subtle"}, 400
