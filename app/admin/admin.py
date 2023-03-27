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



@admin_blueprint.route("/")
@login_required
@admin_required
def index():
    users = AdminModel.get_all_users()

    return render_template("admin/admin_index.html", users=users)

@admin_blueprint.route("/add_user", methods=['GET','POST'])
@login_required
@admin_required
def add_user():
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


@admin_blueprint.route("/orgs", methods=['GET'])
@login_required
@admin_required
def orgs():
    orgs = AdminModel.get_all_orgs()
    return render_template("admin/orgs.html", orgs=orgs)


@admin_blueprint.route("/add_org", methods=['GET','POST'])
@login_required
@admin_required
def add_org():
    form = CreateOrgForm()
    if form.validate_on_submit():
        AdminModel.add_org_core(form)
        return redirect("/admin/orgs")
    return render_template("admin/add_org.html", form=form)


@admin_blueprint.route("/roles", methods=['GET'])
@login_required
@admin_required
def roles():
    roles = AdminModel.get_all_roles()
    return render_template("admin/roles.html", roles=roles)

@admin_blueprint.route("/add_role", methods=['GET','POST'])
@login_required
@admin_required
def add_role():
    form = AddRoleForm()
    if form.validate_on_submit():
        AdminModel.add_role_core(form)
        return redirect("/admin/roles")
    return render_template("admin/add_role.html", form=form)