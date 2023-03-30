from ..db_class.db import User
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from .form import RegistrationForm, CreateOrgForm, AddRoleForm, EditUserFrom
from . import admin_core as AdminModel
from ..decorators import admin_required

admin_blueprint = Blueprint(
    'admin',
    __name__,
    template_folder='templates',
    static_folder='static'
)


#########
# Users #
#########

@admin_blueprint.route("/")
@login_required
@admin_required
def index():
    """List all users"""
    users = AdminModel.get_all_users()

    return render_template("admin/admin_index.html", users=users)

@admin_blueprint.route("/add_user", methods=['GET','POST'])
@login_required
@admin_required
def add_user():
    """Add a new user"""
    form = RegistrationForm()

    form.role.choices = [(role.id, role.name) for role in AdminModel.get_all_roles()]
    form.org.choices = [(org.id, org.name) for org in AdminModel.get_all_orgs()]
    form.org.choices.insert(0, ("None", "--"))

    if form.validate_on_submit():
        AdminModel.add_user_core(form)
        return redirect("/admin")
    return render_template("admin/add_user.html", form=form)


@admin_blueprint.route("/edit_user/<id>", methods=['GET','POST'])
@login_required
@admin_required
def edit_user(id):
    """Edit the user"""
    form = EditUserFrom()

    form.role.choices = [(role.id, role.name) for role in AdminModel.get_all_roles()]
    form.org.choices = [(org.id, org.name) for org in AdminModel.get_all_orgs()]
    form.org.choices.insert(0, ("None", "--"))

    if form.validate_on_submit():
        AdminModel.edit_user_core(form, id)
        return redirect("/admin")
    else:
        user_modif = AdminModel.get_user(id)
        form.first_name.data = user_modif.first_name
        form.last_name.data = user_modif.last_name

    return render_template("admin/edit_user.html", form=form)


@admin_blueprint.route("/delete_user/<id>", methods=['GET','POST'])
@login_required
@admin_required
def delete_user(id):
    """Delete the user"""
    if AdminModel.delete_user_core(id):
        flash("User deleted", 'success')
    else:
        flash("User not deleted", "error")
    return redirect("/admin")


########
# Orgs #
########

@admin_blueprint.route("/orgs", methods=['GET'])
@login_required
@admin_required
def orgs():
    """List all organisations"""
    orgs = AdminModel.get_all_orgs()
    return render_template("admin/orgs.html", orgs=orgs)


@admin_blueprint.route("/add_org", methods=['GET','POST'])
@login_required
@admin_required
def add_org():
    """Add an org"""
    form = CreateOrgForm()
    if form.validate_on_submit():
        AdminModel.add_org_core(form)
        return redirect("/admin/orgs")
    return render_template("admin/add_org.html", form=form)


@admin_blueprint.route("/edit_org/<id>", methods=['GET','POST'])
@login_required
@admin_required
def edit_org(id):
    """Edit the org"""
    form = CreateOrgForm()
    if form.validate_on_submit():
        AdminModel.edit_org_core(form, id)
        return redirect("/admin/orgs")
    else:
        org = AdminModel.get_org(id)
        form.name.data = org.name
        form.description.data = org.description
        form.uuid.data = org.uuid
    return render_template("admin/add_org.html", form=form)


@admin_blueprint.route("/delete_org/<id>", methods=['GET','POST'])
@login_required
@admin_required
def delete_org(id):
    """Delete the org"""
    if AdminModel.delete_org_core(id):
        flash("Org deleted", "success")
    else:
        flash("Org not deleted", "error")
    return redirect("/admin/orgs")


#########
# Roles #
#########

@admin_blueprint.route("/roles", methods=['GET'])
@login_required
@admin_required
def roles():
    """List all roles"""
    roles = AdminModel.get_all_roles()
    return render_template("admin/roles.html", roles=roles)

@admin_blueprint.route("/add_role", methods=['GET','POST'])
@login_required
@admin_required
def add_role():
    """Add a role"""
    form = AddRoleForm()
    if form.validate_on_submit():
        AdminModel.add_role_core(form)
        return redirect("/admin/roles")
    return render_template("admin/add_role.html", form=form)


@admin_blueprint.route("/delete_role/<id>", methods=['GET','POST'])
@login_required
@admin_required
def delete_role(id):
    """Delete the role"""
    if AdminModel.delete_role_core(id):
        flash("Role deleted", "success")
    else:
        flash("Role not deleted", "error")
    return redirect("/admin/roles")
