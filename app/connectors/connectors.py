from flask import Blueprint, render_template, redirect, request, flash
from flask_login import (
    current_user,
    login_required,
)

from .form import AddConnectorForm, AddIconForm, EditConnectorForm, EditIconForm, AddConnectorInstanceForm, EditConnectorInstanceForm
from . import connectors_core as ConnectorModel
from ..decorators import admin_required
from ..utils.utils import form_to_dict, get_module_type

connector_blueprint = Blueprint(
    'connector',
    __name__,
    template_folder='templates',
    static_folder='static'
)


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
    for connector in ConnectorModel.get_connectors():
        connector_loc = connector.to_json()
        icon_loc = ConnectorModel.get_icon(connector.icon_id)
        icon_file = ConnectorModel.get_icon_file(icon_loc.file_icon_id)
        connector_loc["icon_filename"] = icon_file.name
        connector_loc["icon_uuid"] = icon_file.uuid
        connectors_list.append(connector_loc)
    return {"connectors": connectors_list}, 200

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


@connector_blueprint.route("/<cid>/get_instances", methods=['GET'])
@login_required
def get_instances(cid):
    """List all instance for a connector"""
    connector = ConnectorModel.get_connector(cid)
    if connector:
        instance_list = list()
        for instance in connector.instances:
            if instance.global_api_key:
                loc_instance = instance.to_json()
                if ConnectorModel.get_user_instance_both(user_id=current_user.id, instance_id=instance.id):
                    loc_instance["is_user_global_api"] = True
                instance_list.append(loc_instance)
            elif ConnectorModel.get_user_instance_both(user_id=current_user.id, instance_id=instance.id):
                instance_list.append(instance.to_json())
        return {"instances": instance_list}, 200
    return {"message": "Connector not found", "toast_class": "danger-subtle"}, 404

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
def add_instance(cid):
    """Add an instance"""
    if ConnectorModel.get_connector(cid):
        form = AddConnectorInstanceForm()
        type_list = get_module_type()
        form.type_select.choices = list()
        for i in range(0, len(type_list)):
            form.type_select.choices.append((type_list[i], type_list[i]))
        form.type_select.choices.insert(0, ("None","--"))
        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            if ConnectorModel.add_connector_instance_core(cid, form_dict, current_user.id):
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
def edit_instance(cid, iid):
    """Edit an instance"""
    if ConnectorModel.get_connector(cid):
        form = EditConnectorInstanceForm()
        loc_instance = ConnectorModel.get_instance(iid)
        form.instance_id.data = iid

        type_list = get_module_type()
        form.type_select.choices = list()
        for i in range(0, len(type_list)):
            if not type_list[i] == loc_instance.type:
                form.type_select.choices.append((type_list[i], type_list[i]))
        form.type_select.choices.insert(0, ("None","--"))
        if loc_instance.type:
            form.type_select.choices.insert(0, (loc_instance.type, loc_instance.type))

        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            if not ConnectorModel.edit_connector_instance_core(iid, form_dict):
                flash("Error editing connector")
            return redirect("/connectors")
        else:
            form.name.data = loc_instance.name
            form.url.data = loc_instance.url
            form.description.data = loc_instance.description
            form.is_global_connector.data = True if loc_instance.global_api_key else False
            
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
def delete_instance(cid, iid):
    """Delete the instance"""
    if ConnectorModel.get_connector(cid):
        if ConnectorModel.get_instance(iid):
            if ConnectorModel.delete_connector_instance_core(iid):
                return {"message":"Instance deleted", "toast_class": "success-subtle"}, 200
            return {"message":"Error connector deleted", "toast_class": "danger-subtle"}, 400
        return {"message":"Instance not found", "toast_class": "danger-subtle"}, 404
    return {"message":"Connector not found", "toast_class": "danger-subtle"}, 404


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
