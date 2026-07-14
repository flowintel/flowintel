from flask import Blueprint, render_template, redirect, request, flash, abort
from flask_login import (
    current_user,
    login_required,
)

from .form import AddConnectorForm, AddIconForm, EditConnectorForm, EditIconForm, AddConnectorInstanceForm, EditConnectorInstanceForm
from . import connectors_core as ConnectorModel
from ..decorators import admin_required, misp_editor_required
from ..utils.utils import form_to_dict
from ..utils.logger import flowintel_log

connector_blueprint = Blueprint(
    'connector',
    __name__,
    template_folder='templates',
    static_folder='static'
)


def _set_instance_sharing_scope_choices(form, user):
    choices = [("personal", "Personal only")]
    if user.is_admin() or user.is_org_admin():
        choices.append(("org", "Organization-wide"))
    if user.is_admin():
        choices.append(("global", "Platform-wide"))
    form.sharing_scope.choices = choices


@connector_blueprint.route("/", methods=['GET'])
@login_required
def connectors():
    """connectors' index page"""
    return render_template("connectors/connectors.html")

@connector_blueprint.route("/connectors_icons", methods=['GET'])
@login_required
def icons():
    """connectors icons' index page"""
    return render_template("connectors/connectors_icons.html")



@connector_blueprint.route("/get_connectors", methods=['GET'])
@login_required
def get_connectors():
    """List all connectors"""
    connectors_list = list()
    connectors = ConnectorModel.get_connectors()
    connector_ids = [connector.id for connector in connectors]
    connectors_with_instances, connectors_with_links = ConnectorModel.get_connectors_flags(connector_ids)

    for connector in connectors:
        connector_loc = connector.to_json()
        icon_loc = ConnectorModel.get_icon(connector.icon_id)
        icon_file = ConnectorModel.get_icon_file(icon_loc.file_icon_id)
        connector_loc["icon_filename"] = icon_file.name
        connector_loc["icon_uuid"] = icon_file.uuid
        connector_loc["has_instances"] = connector.id in connectors_with_instances
        connector_loc["has_linked_instances"] = connector.id in connectors_with_links
        connectors_list.append(connector_loc)
    return {"connectors": connectors_list}, 200


@connector_blueprint.route("/get_connectors_page", methods=['GET'])
@login_required
def get_connectors_page():
    """Get connectors of a specific page (supports optional `name` filter)."""
    page = request.args.get('page', 1, type=int)
    name = request.args.get('name', None, type=str)
    connectors = ConnectorModel.get_connectors_page(page, name=name)
    return {"connectors": connectors}, 200


@connector_blueprint.route("/nb_page_connectors", methods=['GET'])
@login_required
def nb_page_connectors():
    """Get number of page to list all connectors (supports optional `name` filter)."""
    name = request.args.get('name', None, type=str)
    return {"nb_page": ConnectorModel.get_nb_page_connectors(name=name)}

@connector_blueprint.route("/get_icons", methods=['GET'])
@login_required
def get_icons():
    """List all icons"""
    icon_list = list()
    for icon in ConnectorModel.get_icons():
        icon_loc = icon.to_json()
        icon_file = ConnectorModel.get_icon_file(icon.file_icon_id)
        icon_loc["icon_filename"] = icon_file.name
        icon_loc["icon_uuid"] = icon_file.uuid
        icon_list.append(icon_loc)
    return {"icons": icon_list}, 200


@connector_blueprint.route("/get_icons_page", methods=['GET'])
@login_required
def get_icons_page():
    """Get icons of a specific page (supports optional `name` filter)."""
    page = request.args.get('page', 1, type=int)
    name = request.args.get('name', None, type=str)
    icons = ConnectorModel.get_icons_page(page, name=name)
    return {"icons": icons}, 200


@connector_blueprint.route("/nb_page_icons", methods=['GET'])
@login_required
def nb_page_icons():
    """Get number of page to list icons (supports optional `name` filter)."""
    name = request.args.get('name', None, type=str)
    return {"nb_page": ConnectorModel.get_nb_page_icons(name=name)}



@connector_blueprint.route("/<cid>/get_instances", methods=['GET'])
@login_required
def get_instances(cid):
    """List all instance for a connector"""
    connector = ConnectorModel.get_connector(cid)
    if connector:
        instance_list = list()
        for instance in connector.instances:
            if ConnectorModel.is_instance_visible_to_user(instance, current_user):
                loc_instance = instance.to_json()
                if ConnectorModel.get_user_instance_both(user_id=current_user.id, instance_id=instance.id):
                    loc_instance["is_user_global_api"] = True
                loc_instance["has_links"] = ConnectorModel.instance_has_links(instance.id)
                loc_instance["can_manage"] = ConnectorModel.can_user_manage_instance(instance, current_user)
                instance_list.append(loc_instance)
        return {"instances": instance_list}, 200
    return {"message": "Connector not found", "toast_class": "danger-subtle"}, 404

@connector_blueprint.route("/<cid>/instance/<iid>/cases", methods=['GET'])
@login_required
def get_instance_cases(cid, iid):
    """Get paginated cases linked to a connector instance"""
    if not ConnectorModel.get_connector(cid):
        return {"message": "Connector not found", "toast_class": "danger-subtle"}, 404
    if not ConnectorModel.get_instance(iid):
        return {"message": "Instance not found", "toast_class": "danger-subtle"}, 404
    page = request.args.get('page', 1, type=int)
    cases, total, nb_pages, private_count = ConnectorModel.get_cases_for_instance(iid, page=page, current_user=current_user)
    return {"cases": cases, "total": total, "nb_pages": nb_pages, "page": page, "private_count": private_count}, 200

@connector_blueprint.route("/add_connector", methods=['GET','POST'])
@login_required
@admin_required
def add_connector():
    """Add a connector"""
    form = AddConnectorForm()
    uuid_dict = dict()
    for icon in ConnectorModel.get_icons():
        uuid_dict[icon.id] = ConnectorModel.get_icon_file(icon.file_icon_id).uuid
    form.icon_select.choices = [(icon.id, icon.name) for icon in ConnectorModel.get_icons()]
    form.icon_select.choices.insert(0, ("None","--"))
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        ConnectorModel.add_connector_core(form_dict)
        return redirect("/connectors")
    return render_template("connectors/add_connector.html", form=form, uuid_dict=uuid_dict, edit_mode=False)


@connector_blueprint.route("/<cid>/add_instance", methods=['GET','POST'])
@login_required
@misp_editor_required
def add_instance(cid):
    """Add an instance"""
    if ConnectorModel.get_connector(cid):
        form = AddConnectorInstanceForm()
        _set_instance_sharing_scope_choices(form, current_user)
        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            sharing_scope = ConnectorModel.normalize_instance_sharing_scope(form_dict, current_user)
            if not ConnectorModel.can_user_use_sharing_scope(current_user, sharing_scope):
                flash("You are not allowed to create a connector with this sharing scope", "danger")
                return render_template("connectors/add_instance.html", form=form, edit_mode=False)
            instance = ConnectorModel.add_connector_instance_core(cid, form_dict, current_user.id)
            if instance:
                connector = ConnectorModel.get_connector(cid)
                flowintel_log(
                    "audit",
                    200,
                    "Connector instance created",
                    Connector=connector.name if connector else "Unknown",
                    ConnectorId=cid,
                    Instance=instance.name,
                    InstanceId=instance.id,
                    InstanceUrl=instance.url,
                    By=current_user.email
                )
                return redirect("/connectors")
            return render_template("connectors/add_instance.html", form=form, edit_mode=False)
        return render_template("connectors/add_instance.html", form=form, edit_mode=False)
    return render_template("404.html")


@connector_blueprint.route("/add_icons", methods=['GET','POST'])
@login_required
@admin_required
def add_icons():
    """Add an icon"""
    form = AddIconForm()
    if form.validate_on_submit():
        icon = form.icon_upload
        form_dict = form_to_dict(form)
        if not ConnectorModel.add_icon_core(form_dict, icon):
            flash("Error uploading icon")
        return redirect("/connectors/connectors_icons")
    return render_template("connectors/add_icons.html", form=form)


@connector_blueprint.route("/edit_connector/<cid>", methods=['GET','POST'])
@login_required
@admin_required
def edit_connector(cid):
    """Edit a connector"""
    form = EditConnectorForm()
    loc_connector = ConnectorModel.get_connector(cid)
    form.connector_id.data = cid

    uuid_dict = dict()
    for icon in ConnectorModel.get_icons():
        uuid_dict[icon.id] = ConnectorModel.get_icon_file(icon.file_icon_id).uuid

    loc_icon = ConnectorModel.get_icon(loc_connector.icon_id)
    form.icon_select.choices = [(icon.id, icon.name) for icon in ConnectorModel.get_icons() if not icon.id == loc_icon.id]
    form.icon_select.choices.insert(0, ("None","--"))
    form.icon_select.choices.insert(0, (loc_icon.id,loc_icon.name))
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        if not ConnectorModel.edit_connector_core(cid, form_dict):
            flash("Error editing connector")
        return redirect("/connectors")
    else:
        form.name.data = loc_connector.name
        form.description.data = loc_connector.description
        
    return render_template("connectors/add_connector.html", form=form, uuid_dict=uuid_dict, edit_mode=True)


@connector_blueprint.route("/<cid>/edit_instance/<iid>", methods=['GET','POST'])
@login_required
@misp_editor_required
def edit_instance(cid, iid):
    """Edit an instance"""
    if ConnectorModel.get_connector(cid):
        form = EditConnectorInstanceForm()
        loc_instance = ConnectorModel.get_instance(iid)
        if not loc_instance or not ConnectorModel.can_user_manage_instance(loc_instance, current_user):
            abort(403)
        _set_instance_sharing_scope_choices(form, current_user)
        form.instance_id.data = iid

        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            form_dict["acting_user_id"] = current_user.id
            sharing_scope = ConnectorModel.normalize_instance_sharing_scope(form_dict, current_user)
            if not ConnectorModel.can_user_use_sharing_scope(current_user, sharing_scope):
                flash("You are not allowed to save a connector with this sharing scope", "danger")
                return render_template("connectors/add_instance.html", form=form, edit_mode=True)
            if not ConnectorModel.edit_connector_instance_core(iid, form_dict):
                flash("Error editing connector")
            else:
                connector = ConnectorModel.get_connector(cid)
                updated_instance = ConnectorModel.get_instance(iid)
                flowintel_log(
                    "audit",
                    200,
                    "Connector instance edited",
                    Connector=connector.name if connector else "Unknown",
                    ConnectorId=cid,
                    Instance=updated_instance.name if updated_instance else "Unknown",
                    InstanceId=iid,
                    InstanceUrl=updated_instance.url if updated_instance else None,
                    By=current_user.email
                )
            return redirect("/connectors")
        else:
            form.name.data = loc_instance.name
            form.url.data = loc_instance.url
            form.description.data = loc_instance.description
            form.is_global_connector.data = True if loc_instance.global_api_key else False
            form.sharing_scope.data = ConnectorModel.get_instance_sharing_scope(loc_instance)
            
        return render_template("connectors/add_instance.html", form=form, edit_mode=True)
    return render_template("404.html")


@connector_blueprint.route("/edit_icon/<iid>", methods=['GET','POST'])
@login_required
@admin_required
def edit_icon(iid):
    """Edit an icon"""
    form = EditIconForm()
    loc_icon = ConnectorModel.get_icon(iid)
    icon_file = ConnectorModel.get_icon_file(loc_icon.file_icon_id)
    form.icon_id.data = iid
    if form.validate_on_submit():
        icon = form.icon_upload
        form_dict = form_to_dict(form)
        if not ConnectorModel.edit_icon_core(iid, form_dict, icon):
            flash("Error uploading icon")
        return redirect("/connectors/connectors_icons")
    else:
        form.name.data = loc_icon.name
        form.description.data = loc_icon.description
    return render_template("connectors/edit_icons.html", form=form, icon_file=icon_file.to_json())


@connector_blueprint.route("/delete_connector/<cid>", methods=['GET','POST'])
@login_required
@admin_required
def delete_connector(cid):
    """Delete the connector"""
    if ConnectorModel.get_connector(cid):
        if ConnectorModel.delete_connector_core(cid):
            return {"message":"Connector deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error connector deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"Connector not found", "toast_class": "danger-subtle"}, 404

@connector_blueprint.route("/<cid>/delete_instance/<iid>", methods=['GET','POST'])
@login_required
@misp_editor_required
def delete_instance(cid, iid):
    """Delete the instance"""
    if ConnectorModel.get_connector(cid):
        instance = ConnectorModel.get_instance(iid)
        if instance:
            if not ConnectorModel.can_user_manage_instance(instance, current_user):
                return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
            if ConnectorModel.instance_has_links(iid):
                return {"message":"Instance is linked to a case or task", "toast_class": "warning-subtle"}, 400
            if ConnectorModel.delete_connector_instance_core(iid):
                connector = ConnectorModel.get_connector(cid)
                flowintel_log(
                    "audit",
                    200,
                    "Connector instance deleted",
                    Connector=connector.name if connector else "Unknown",
                    ConnectorId=cid,
                    Instance=instance.name,
                    InstanceId=iid,
                    InstanceUrl=instance.url,
                    By=current_user.email
                )
                return {
                    "message":"Instance deleted",
                    "toast_class": "success-subtle",
                    "connector_flags": {
                        "has_instances": ConnectorModel.connector_has_instances(cid),
                        "has_linked_instances": ConnectorModel.connector_has_linked_instances(cid)
                    }
                }, 200
            return {"message":"Error connector deleted", "toast_class": "danger-subtle"}, 400
        return {"message":"Instance not found", "toast_class": "danger-subtle"}, 404
    return {"message":"Connector not found", "toast_class": "danger-subtle"}, 404


@connector_blueprint.route("/<cid>/check_connectivity/<iid>", methods=['GET'])
@login_required
def check_connectivity(cid, iid):
    """Check connectivity to a connector instance (MISP)"""
    connector = ConnectorModel.get_connector(cid)
    if not connector:
        return {"message": "Connector not found", "toast_class": "danger-subtle"}, 404
    
    instance = ConnectorModel.get_instance(iid)
    if not instance:
        return {"message": "Instance not found", "toast_class": "danger-subtle"}, 404
    
    # Only MISP connectors
    if connector.name.lower() != "misp":
        return {"message": "Connectivity check not supported for this connector type", "toast_class": "warning-subtle"}, 400
    
    result = ConnectorModel.check_misp_connectivity(instance, current_user=current_user)
    status_code = 200 if result["success"] else 400
    return result, status_code


@connector_blueprint.route("/delete_icon/<iid>", methods=['GET','POST'])
@login_required
@admin_required
def delete_icon(iid):
    """Delete the icon"""
    if ConnectorModel.get_icon(iid):
        if ConnectorModel.delete_icon_core(iid):
            return {"message":"Icon deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error Icon deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"Icon not found", "toast_class": "danger-subtle"}, 404
