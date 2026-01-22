from flask import Blueprint, jsonify, render_template, redirect, url_for, request, flash
from flask_login import (
    current_user,
    login_required,
)

from .form import RegistrationForm, CreateOrgForm, AdminEditUserFrom, CreateRoleForm
from . import admin_core as AdminModel
from ..decorators import admin_required
from ..utils.utils import form_to_dict
from ..utils.logger import flowintel_log
from ..db_class.db import User, Role

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
def add_user():
    """Add a new user"""
    if not (current_user.is_admin() or current_user.is_org_admin()):
        flash("You do not have permission to add users.", "error")
        return redirect(url_for('admin.users'))
    
    form = RegistrationForm()

    if current_user.is_pure_org_admin():
        form.role.choices = [(role.id, role.name) for role in AdminModel.get_all_roles() if not role.admin]
    else:
        form.role.choices = [(role.id, role.name) for role in AdminModel.get_all_roles()]
    
    if current_user.is_pure_org_admin():
        user_org = AdminModel.get_org(current_user.org_id)
        if not user_org:
            flash("Your organization could not be found. Please contact an administrator.", "error")
            return redirect(url_for('admin.users'))
        form.org.choices = [(user_org.id, user_org.name)]
        form.org.data = str(user_org.id)
    else:
        form.org.choices = [(org.id, org.name) for org in AdminModel.get_all_orgs()]
        form.org.choices.insert(0, ("None", "New org"))

    if form.validate_on_submit():
        if current_user.is_pure_org_admin():
            if form.org.data != str(current_user.org_id):
                flash("You can only add users to your own organization.", "error")
                return render_template("admin/add_user.html", form=form, edit_mode=False)
            
            selected_role = Role.query.get(form.role.data)
            if selected_role and selected_role.admin:
                flash("You cannot assign Admin role to users.", "error")
                return render_template("admin/add_user.html", form=form, edit_mode=False)
        
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("A user with this email address already exists.", "error")
            return render_template("admin/add_user.html", form=form, edit_mode=False)
        
        form_dict = form_to_dict(form)
        AdminModel.add_user_core(form_dict)
        flowintel_log("audit", 200, "User added", User=form.email.data, By=current_user.email)
        return redirect(url_for('admin.users'))
    return render_template("admin/add_user.html", form=form, edit_mode=False)


@admin_blueprint.route("/edit_user/<uid>", methods=['GET','POST'])
@login_required
def edit_user(uid):
    """Edit the user"""
    user_modif = AdminModel.get_user(uid)
    if not user_modif:
        flash("User not found.", "error")
        return redirect(url_for('admin.users'))
    
    if current_user.is_pure_org_admin():
        if user_modif.org_id != current_user.org_id:
            flash("You can only edit users from your own organization.", "error")
            return redirect(url_for('admin.users'))
    elif not current_user.is_admin():
        flash("You do not have permission to edit users.", "error")
        return redirect(url_for('admin.users'))
    
    form = AdminEditUserFrom()
    form.user_id.data = uid
    
    if current_user.is_pure_org_admin():
        form.role.choices = [(role.id, role.name) for role in AdminModel.get_all_roles() if not user_modif.role_id == role.id and not role.admin]
    else:
        form.role.choices = [(role.id, role.name) for role in AdminModel.get_all_roles() if not user_modif.role_id == role.id]
    
    role_temp = AdminModel.get_role(user_modif.role_id)
    if not (current_user.is_pure_org_admin() and role_temp.admin):
        form.role.choices.insert(0, (role_temp.id, role_temp.name))

    if current_user.is_pure_org_admin():
        user_org = AdminModel.get_org(current_user.org_id)
        form.org.choices = [(user_org.id, user_org.name)]
    else:
        form.org.choices = [(org.id, org.name) for org in AdminModel.get_all_orgs() if not user_modif.org_id == org.id]
        org_temp = AdminModel.get_org(user_modif.org_id)
        form.org.choices.insert(0, (org_temp.id, org_temp.name))

    if form.validate_on_submit():
        if current_user.is_pure_org_admin():
            if user_modif.org_id != current_user.org_id:
                flash("You can only edit users from your own organization.", "error")
                return redirect(url_for('admin.users'))
            if form.org.data != str(current_user.org_id):
                flash("You cannot change the organization of users.", "error")
                return render_template("admin/add_user.html", form=form, edit_mode=True)
            
            selected_role = Role.query.get(form.role.data)
            if selected_role and selected_role.admin:
                flash("You cannot assign Admin role to users.", "error")
                return render_template("admin/add_user.html", form=form, edit_mode=True)
        
        form_dict = form_to_dict(form)
        # Only include password if change_password is checked
        if not form.change_password.data:
            form_dict.pop('password', None)
            form_dict.pop('password2', None)
        flowintel_log("audit", 200, "User edited", User=user_modif.email, UserId=uid, By=current_user.email)
        AdminModel.admin_edit_user_core(form_dict, uid)
        return redirect(url_for('admin.users'))
    else:
        form.first_name.data = user_modif.first_name
        form.last_name.data = user_modif.last_name
        form.nickname.data = user_modif.nickname
        form.email.data = user_modif.email
        form.matrix_id.data = user_modif.matrix_id

    return render_template("admin/add_user.html", form=form, edit_mode=True)


@admin_blueprint.route("/delete_user/<uid>", methods=['POST'])
@login_required
def delete_user(uid):
    """Delete the user"""
    user = AdminModel.get_user(uid)
    if not user:
        return {"message":"User not found", "toast_class": "danger-subtle"}, 404
    
    if user.id == current_user.id:
        return {"message":"You cannot delete your own account", "toast_class": "danger-subtle"}, 403
    
    if current_user.is_pure_org_admin():
        if user.org_id != current_user.org_id:
            return {"message":"You can only delete users from your own organization", "toast_class": "danger-subtle"}, 403
    elif not current_user.is_admin():
        return {"message":"You do not have permission to delete users", "toast_class": "danger-subtle"}, 403
    
    if AdminModel.delete_user_core(uid):
        flowintel_log("audit", 200, "User deleted", User=user.email, UserId=uid, By=current_user.email)
        return {"message":"User deleted", "toast_class": "success-subtle"}, 200
    return {"message":"Error user deleted", "toast_class": "danger-subtle"}, 400


@admin_blueprint.route("/get_users_page", methods=['GET'])
@login_required
def get_users_page():
    """Get all users page"""
    from conf.config import Config
    
    page = request.args.get('page', 1, type=int)
    
    org_id = None
    if Config.LIMIT_USER_VIEW_TO_ORG and not current_user.is_admin():
        org_id = current_user.org_id
    
    users = AdminModel.get_users_page(page, org_id=org_id)
    if users:
        users_list = list()
        for user in users:
            u = user.to_json()
            r = AdminModel.get_role(user.role_id)
            u["role"] = r.name if r else "Unknown"
            u["org_id"] = user.org_id
            org = AdminModel.get_org(user.org_id) if user.org_id else None
            u["org_name"] = org.name if org else "No Organization"
            users_list.append(u)
        return {"users": users_list, "nb_pages": users.pages}
    return {"message": "No Users"}, 404


########
# Orgs #
########

@admin_blueprint.route("/orgs", methods=['GET', 'POST'])
@login_required
def orgs():
    """List all organisations"""
    return render_template("admin/orgs.html")


#########
# Roles #
#########

@admin_blueprint.route("/roles", methods=['GET', 'POST'])
@login_required
def roles():
    """List all roles"""
    return render_template("admin/roles.html")

@admin_blueprint.route("/add_role", methods=['GET','POST'])
@login_required
@admin_required
def add_role():
    """Add a role"""
    form = CreateRoleForm()
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        AdminModel.add_role_core(form_dict)
        flowintel_log("audit", 200, "Role added", RoleName=form.name.data, Admin=form.admin.data, ReadOnly=form.read_only.data, OrgAdmin=form.org_admin.data)
        return redirect(url_for('admin.roles'))
    return render_template("admin/add_edit_role.html", form=form, edit_mode=False)

@admin_blueprint.route("/edit_role/<id>", methods=['POST'])
@login_required
@admin_required
def edit_role(id):
    """Edit a role"""
    from conf.config import Config
    
    if int(id) in Config.SYSTEM_ROLES:
        return {"message": "Cannot edit system role", "toast_class": "danger-subtle"}, 400
    
    data = request.get_json()
    if AdminModel.edit_role_core(id, data):
        role_name = data.get('name', 'N/A')
        flowintel_log("audit", 200, "Role edited", RoleId=id, RoleName=role_name, Description=data.get('description'), Admin=data.get('admin'), ReadOnly=data.get('read_only'), OrgAdmin=data.get('org_admin'))
        return {"message": "Role updated", "toast_class": "success-subtle"}, 200
    return {"message": "Error updating role", "toast_class": "danger-subtle"}, 400

@admin_blueprint.route("/delete_role/<id>", methods=['POST'])
@login_required
@admin_required
def delete_role(id):
    """Delete a role"""
    from conf.config import Config
    
    if int(id) in Config.SYSTEM_ROLES:
        return {"message": "Cannot delete system role", "toast_class": "danger-subtle"}, 400
    
    users_count = AdminModel.count_users_with_role(id)
    if users_count > 0:
        msg = "Cannot delete role. {} user(s) are associated with this role".format(users_count)
        return {"message": msg, "toast_class": "danger-subtle"}, 400
    
    role = AdminModel.get_role(id)
    role_name = role.name if role else "Unknown"
    if AdminModel.delete_role(id):
        flowintel_log("audit", 200, "Role deleted", RoleId=id, RoleName=role_name)
        return {"message": "Role deleted", "toast_class": "success-subtle"}, 200
    return {"message": "Error deleting role", "toast_class": "danger-subtle"}, 400


@admin_blueprint.route("/add_org", methods=['GET','POST'])
@login_required
@admin_required
def add_org():
    """Add the org"""
    form = CreateOrgForm()
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        AdminModel.add_org_core(form_dict)
        flowintel_log("audit", 200, "Org added", Org=form.name.data)
        return redirect(url_for('admin.orgs'))
    return render_template("admin/add_edit_org.html", form=form, edit_mode=False)


@admin_blueprint.route("/edit_org/<id>", methods=['GET','POST'])
@login_required
@admin_required
def edit_org(id):
    """Edit the org"""
    form = CreateOrgForm()
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        AdminModel.edit_org_core(form_dict, id)
        flowintel_log("audit", 200, "Org edited", Org=form.name.data, OrgId=id)
        return redirect(url_for('admin.orgs'))
    else:
        org = AdminModel.get_org(id)
        form.org_id.data = org.id
        form.name.data = org.name
        form.description.data = org.description
        form.uuid.data = org.uuid
    return render_template("admin/add_edit_org.html", form=form, edit_mode=True)


@admin_blueprint.route("/delete_org/<oid>", methods=['POST'])
@login_required
@admin_required
def delete_org(oid):
    """Delete the org"""
    if AdminModel.get_org(oid):
        if AdminModel.delete_org_core(oid):
            flowintel_log("audit", 200, "Org deleted", OrgId=oid)
            return {"message":"Org deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error Org deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"Org not found", "toast_class": "danger-subtle"}, 404


@admin_blueprint.route("/get_orgs", methods=['GET','POST'])
@login_required
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
def get_org_users():
    """get all user of an org"""
    from conf.config import Config
    
    data_dict = dict(request.args)
    requested_org_id = int(data_dict["org_id"])
    
    if Config.LIMIT_USER_VIEW_TO_ORG and not current_user.is_admin():
        if requested_org_id != current_user.org_id:
            return {"users": []}, 403
    
    users = AdminModel.get_all_user_org(requested_org_id)
    if users:
        users_list = list()
        for user in users:
            u = user.to_json()
            r = AdminModel.get_role(user.role_id)
            u["role"] = r.name
            users_list.append(u)

        return {"users": users_list}
    return {"message": "No user in the org"}


@admin_blueprint.route("/get_roles", methods=['GET','POST'])
@login_required
def get_roles():
    """get all roles"""
    page = request.args.get('page', 1, type=int)
    roles = AdminModel.get_roles_page(page)
    if roles:
        roles_list = list()
        for role in roles:
            role_dict = role.to_json()
            role_dict["user_count"] = AdminModel.count_users_with_role(role.id)
            roles_list.append(role_dict)
        return {"roles": roles_list, "nb_pages": roles.pages}
    return {"message": "No roles"}


@admin_blueprint.route("/get_role_users", methods=['GET','POST'])
@login_required
def get_role_users():
    """get all user of a role"""
    data_dict = dict(request.args)
    users = AdminModel.get_all_user_role(data_dict["role_id"])
    if users:
        users_list = list()
        for user in users:
            u = user.to_json()
            o = AdminModel.get_org(user.org_id)
            u["org"] = o.name
            users_list.append(u)

        return {"users": users_list}
    return {"message": "No user with this role"}



##############
# Taxonomies #
##############

@admin_blueprint.route("/taxonomies", methods=['GET'])
@login_required
def taxonomies():
    """Taxonomies' index page"""
    return render_template("admin/taxonomies.html")


@admin_blueprint.route("/get_taxonomies", methods=['GET'])
@login_required
def get_taxonomies():
    """List all taxonomies"""
    return {"taxonomies": AdminModel.get_taxonomies()}

@admin_blueprint.route("/get_taxonomies_page", methods=['GET'])
@login_required
def get_taxonomies_page():
    """Get taxonomies of a specific page"""
    page = request.args.get('page', 1, type=int)
    return {"taxonomies": AdminModel.get_taxonomies_page(page)}

@admin_blueprint.route("/nb_page_taxo", methods=['GET'])
@login_required
def nb_page_taxo():
    """Get number of page to list all taxonomies"""
    return {"nb_page": AdminModel.get_nb_page_taxo()}

@admin_blueprint.route("/get_tags", methods=['GET'])
@login_required
def get_tags():
    """Get tags of a taxonomy"""
    taxonomy = request.args.get('taxonomy')
    tags = AdminModel.get_tags(taxonomy)
    tags.sort(key=lambda x: x["name"])
    return {"tags": tags}

@admin_blueprint.route("/taxonomy_status", methods=['GET'])
@login_required
@admin_required
def taxonomy_status():
    """Active or deactive a taxonomy"""
    taxonomy_id = request.args.get('taxonomy', type=int)
    AdminModel.taxonomy_status(taxonomy_id)
    return {"message":"Taxonomy changed", "toast_class": "success-subtle"}, 200



############
# Galaxies #
############

@admin_blueprint.route("/galaxies", methods=['GET'])
@login_required
def galaxies():
    """Galaxies' index page"""
    return render_template("admin/galaxies.html")


@admin_blueprint.route("/get_galaxies", methods=['GET'])
@login_required
def get_galaxies():
    """List all galaxies"""
    return {"galaxies": AdminModel.get_galaxies()}

@admin_blueprint.route("/get_galaxies_page", methods=['GET'])
@login_required
def get_galaxies_page():
    """Get galaxies of a specific page"""
    page = request.args.get('page', 1, type=int)
    gal = AdminModel.get_galaxies_page(page)
    return {"galaxies": gal}

@admin_blueprint.route("/nb_page_galaxies", methods=['GET'])
@login_required
def nb_page_galaxies():
    """Get number of page to list all galaxies"""
    return {"nb_page": AdminModel.get_nb_page_galaxies()}

@admin_blueprint.route("/get_tags_galaxy", methods=['GET'])
@login_required
def get_tags_galaxy():
    """Get tags of a galaxy"""
    galaxy = request.args.get('galaxy')
    tags = AdminModel.get_tags_galaxy(galaxy)
    return {"tags": tags}


@admin_blueprint.route("/get_clusters", methods=['GET'])
@login_required
def get_clusters():
    """Get clusers of a galaxy"""
    galaxy_id = request.args.get('galaxy')
    clusters = AdminModel.get_clusters_galaxy(galaxy_id)
    clusters.sort(key=lambda x: x["name"])
    return jsonify({"clusters": clusters})

@admin_blueprint.route("/galaxy_status", methods=['GET'])
@login_required
@admin_required
def galaxy_status():
    """Active or deactive a galaxy"""
    galaxy_id = request.args.get('galaxy', type=int)
    AdminModel.galaxy_status(galaxy_id)
    return {"message":"Galaxy changed", "toast_class": "success-subtle"}, 200
