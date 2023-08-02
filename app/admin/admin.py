from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import (
    current_user,
    login_required,
)
from .form import RegistrationForm, CreateOrgForm, AdminEditUserFrom
from . import admin_core as AdminModel
from ..decorators import admin_required
from ..utils.utils import form_to_dict

admin_blueprint = Blueprint(
    'admin',
    __name__,
    template_folder='templates',
    static_folder='static'
)


#########
# Users #
#########

@admin_blueprint.route("/users", methods=['GET'])
@login_required
def users():
    """List all users"""
    return render_template("admin/users.html")

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
        form_dict = form_to_dict(form)
        AdminModel.add_user_core(form_dict)
        return redirect("/admin/orgs")
    return render_template("admin/add_user.html", form=form)


@admin_blueprint.route("/edit_user/<uid>", methods=['GET','POST'])
@login_required
@admin_required
def edit_user(uid):
    """Edit the user"""
    form = AdminEditUserFrom()
    user_modif = AdminModel.get_user(uid)
    form.user_id.data = uid
    form.role.choices = [(role.id, role.name) for role in AdminModel.get_all_roles() if not user_modif.role_id == role.id]
    role_temp = AdminModel.get_role(user_modif.role_id)
    form.role.choices.insert(0, (role_temp.id, role_temp.name))


    form.org.choices = [(org.id, org.name) for org in AdminModel.get_all_orgs() if not user_modif.org_id == org.id]
    org_temp = AdminModel.get_org(user_modif.org_id)
    form.org.choices.insert(0, (org_temp.id, org_temp.name))
    form.org.choices.insert(1, ("None", "--"))

    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        AdminModel.admin_edit_user_core(form_dict, uid)
        return redirect("/admin/orgs")
    else:
        user_modif = AdminModel.get_user(uid)
        form.first_name.data = user_modif.first_name
        form.last_name.data = user_modif.last_name
        form.email.data = user_modif.email

    return render_template("admin/add_user.html", form=form, edit_mode=True)


@admin_blueprint.route("/delete_user/<uid>", methods=['GET','POST'])
@login_required
@admin_required
def delete_user(uid):
    """Delete the user"""
    if AdminModel.get_user(uid):
        if AdminModel.delete_user_core(uid):
            return {"message":"User deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error user deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"User not found", "toast_class": "danger-subtle"}, 404


@admin_blueprint.route("/get_users_page", methods=['GET'])
@login_required
def get_users_page():
    """Delete the user"""
    page = request.args.get('page', 1, type=int)
    users = AdminModel.get_users_page(page)
    if users:
        users_list = list()
        for user in users:
            u = user.to_json()
            r = AdminModel.get_role(user.role_id)
            u["role"] = r.name
            users_list.append(u)
        return {"users": users_list, "nb_pages": users.pages}
    return {"message": "No Users"}, 404


########
# Orgs #
########

@admin_blueprint.route("/orgs", methods=['GET', 'POST'])
@login_required
@admin_required
def orgs():
    """List all organisations"""
    form = CreateOrgForm()
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        AdminModel.add_org_core(form_dict)
        return redirect("/admin/orgs")
    return render_template("admin/orgs.html", form=form)


@admin_blueprint.route("/edit_org/<id>", methods=['GET','POST'])
@login_required
@admin_required
def edit_org(id):
    """Edit the org"""
    form = CreateOrgForm()
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        AdminModel.edit_org_core(form_dict, id)
        return redirect("/admin/orgs")
    else:
        org = AdminModel.get_org(id)
        form.name.data = org.name
        form.description.data = org.description
        form.uuid.data = org.uuid
    return render_template("admin/edit_org.html", form=form)


@admin_blueprint.route("/delete_org/<oid>", methods=['GET','POST'])
@login_required
@admin_required
def delete_org(oid):
    """Delete the org"""
    if AdminModel.get_org(oid):
        if AdminModel.delete_org_core(oid):
            return {"message":"Org deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error Org deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"Org not found", "toast_class": "danger-subtle"}, 404


@admin_blueprint.route("/get_orgs", methods=['GET','POST'])
@login_required
@admin_required
def get_orgs():
    """get all orgs"""
    page = request.args.get('page', 1, type=int)
    orgs = AdminModel.get_orgs_page(page)
    if orgs:
        orgs_list = list()
        for org in orgs:
            orgs_list.append(org.to_json())
        return {"orgs": orgs_list, "nb_pages": orgs.pages}
    return {"message": "No orgs"}


@admin_blueprint.route("/get_org_users", methods=['GET','POST'])
@login_required
@admin_required
def get_org_users():
    """get all user of an org"""
    data_dict = dict(request.args)
    users = AdminModel.get_all_user_org(data_dict["org_id"])
    if users:
        users_list = list()
        for user in users:
            u = user.to_json()
            r = AdminModel.get_role(user.role_id)
            u["role"] = r.name
            users_list.append(u)

        return {"users": users_list}
    return {"message": "No user in the org"}


