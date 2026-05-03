from flask import request
from . import admin_core as AdminModel
from . import admin_core_api as AdminModelApi

from flask_restx import Namespace, Resource, fields
from ..decorators import api_required, admin_required, admin_or_org_admin_required
from ..utils.utils import get_user_api, reload_application
from ..utils.logger import flowintel_log
from flask import current_app
from flask_login import current_user


admin_ns = Namespace("admin", description="Endpoints to manage admin actions")

# Define models for request body documentation
# Changed to use JSON body fields, instead of URL parameters
add_user_model = admin_ns.model('AddUser', {
    'first_name': fields.String(required=True, description='First name for the user'),
    'last_name': fields.String(required=True, description='Last name for the user'),
    'email': fields.String(required=True, description='Email for the user'),
    'password': fields.String(required=True, description='Password for the user'),
    'role': fields.Integer(required=True, description='Role ID (integer) for the user'),
    'org': fields.Integer(required=False, description='Organisation ID (integer) for the user')
})

edit_user_model = admin_ns.model('EditUser', {
    'first_name': fields.String(required=False, description='First name for the user'),
    'last_name': fields.String(required=False, description='Last name for the user'),
    'email': fields.String(required=False, description='Email for the user'),
    'role': fields.Integer(required=False, description='Role ID (integer) for the user'),
    'org': fields.Integer(required=False, description='Organisation ID (integer) for the user'),
    'password': fields.String(required=False, description='New password for the user (local auth only). Resets the user password.')
})

add_org_model = admin_ns.model('AddOrg', {
    'name': fields.String(required=True, description='Name for the organisation'),
    'description': fields.String(required=False, description='Description of the organisation'),
    'uuid': fields.String(required=False, description='UUID of the organisation')
})

edit_org_model = admin_ns.model('EditOrg', {
    'name': fields.String(required=False, description='Name for the organisation'),
    'description': fields.String(required=False, description='Description of the organisation'),
    'uuid': fields.String(required=False, description='UUID of the organisation')
})

add_role_model = admin_ns.model('AddRole', {
    'name': fields.String(required=True, description='Name for the role'),
    'description': fields.String(required=False, description='Description of the role'),
    'admin': fields.Boolean(required=False, description='Admin privilege'),
    'read_only': fields.Boolean(required=False, description='Read-only privilege'),
    'org_admin': fields.Boolean(required=False, description='Organisation admin privilege'),
    'case_admin': fields.Boolean(required=False, description='Case admin privilege'),
    'queue_admin': fields.Boolean(required=False, description='Queue admin privilege'),
    'queuer': fields.Boolean(required=False, description='Queuer privilege'),
    'audit_viewer': fields.Boolean(required=False, description='Audit viewer privilege'),
    'template_editor': fields.Boolean(required=False, description='Template editor privilege'),
    'misp_editor': fields.Boolean(required=False, description='MISP editor privilege'),
    'importer': fields.Boolean(required=False, description='Importer privilege'),
})



#########
# Users #
#########

@admin_ns.route('/users')
@admin_ns.doc(description='Get all users')
class GetUsers(Resource):
    method_decorators = [api_required]
    def get(self):
        user = get_user_api(request.headers["X-API-KEY"])
        
        if current_app.config.get('LIMIT_USER_VIEW_TO_ORG', False) and not user.is_admin():
            users = AdminModel.get_users_by_org(user.org_id)
        else:
            users = AdminModel.get_all_users()
        
        return {"users": [user.to_json() for user in users]}, 200
    
@admin_ns.route('/user/<uid>')
@admin_ns.doc(description='Get a users', params={'uid': 'id of a user'})
class GetUsers(Resource):
    method_decorators = [api_required]
    def get(self, uid):
        user = AdminModel.get_user(uid)
        if user:
            return user.to_json(), 200
        return {"message": "User not found"}, 404

@admin_ns.route('/user')
@admin_ns.doc(description='Get a user by name', params={"lastname": "last name of a user"})
class GetUserName(Resource):
    method_decorators = [api_required]
    def get(self):
        if "lastname" in request.args:
            users = AdminModel.get_user_by_lastname(request.args.get("lastname"))
            return {"users": [user.to_json() for user in users]}, 200
        return {"message": "Need to pass a last name"}, 400

@admin_ns.route('/user_matrix_id')
@admin_ns.doc(description='Get a user by matrix id', params={"matrix_id": "matrix id of a user"})
class GetUserMatrix(Resource):
    method_decorators = [api_required]
    def get(self):
        if "matrix_id" in request.args:
            user = AdminModel.get_user_by_matrix_id(request.args.get("matrix_id"))
            if user:
                return user.to_json(), 200
            return {"message": "No user found for this matrix id"}, 404
        return {"message": "Need to pass a matrix id"}, 400

@admin_ns.route('/add_user')
@admin_ns.doc(description='Add new user')
class AddUser(Resource):
    method_decorators = [admin_or_org_admin_required, api_required]
    
    @admin_ns.expect(add_user_model)
    def post(self):
        if request.json:
            api_user = get_user_api(request.headers["X-API-KEY"])
            
            verif_dict = AdminModelApi.verif_add_user(request.json, api_user)
            if "message" not in verif_dict:
                user = AdminModel.add_user_core(verif_dict)
                role = AdminModel.get_role(user.role_id)
                org = AdminModel.get_org(user.org_id)
                flowintel_log("audit", 200, "User added via API", User=request.json.get('email'), UserId=user.id, Role=role.name if role else "Unknown", Organisation=org.name if org else "Unknown", By=api_user.email)
                return {"message": f"User created {user.id}", "id": user.id, "api_key": user.api_key}, 201
            return verif_dict, 400
        return {"message": "Please give data"}, 400

                
@admin_ns.route('/edit_user/<id>')
@admin_ns.doc(description='Edit user', params={'id': 'id of a user'})
class EditUser(Resource):
    method_decorators = [admin_or_org_admin_required, api_required]
    
    @admin_ns.expect(edit_user_model)
    def post(self, id):
        if request.json:
            api_user = get_user_api(request.headers["X-API-KEY"])
            
            user_to_edit = AdminModel.get_user(id)
            if not user_to_edit:
                return {"message": "User not found"}, 404
            
            if api_user.is_pure_org_admin():
                if user_to_edit.org_id != api_user.org_id:
                    return {"message": "OrgAdmin can only edit users from their own organisation"}, 403
                
                if 'org' in request.json and int(request.json['org']) != api_user.org_id:
                    return {"message": "OrgAdmin cannot move users to different organisation"}, 403
            
            verif_dict = AdminModelApi.verif_edit_user(request.json, id, api_user)
            if "message" not in verif_dict:
                AdminModel.admin_edit_user_core(verif_dict, id)
                updated_user = AdminModel.get_user(id)
                role = AdminModel.get_role(updated_user.role_id)
                org = AdminModel.get_org(updated_user.org_id)
                flowintel_log("audit", 200, "User edited via API", User=user_to_edit.email, UserId=id, Role=role.name if role else "Unknown", Organisation=org.name if org else "Unknown", By=api_user.email)
                return {"message": "User edited"}, 200
            return verif_dict, 400
        return {"message": "Please give data"}, 400


@admin_ns.route('/delete_user/<id>')
@admin_ns.doc(description='Delete user' , params={'id': 'id of a user'})
class DeleteUser(Resource):
    method_decorators = [admin_or_org_admin_required, api_required]
    def get(self, id):
        api_user = get_user_api(request.headers["X-API-KEY"])
        
        user_to_delete = AdminModel.get_user(id)
        if not user_to_delete:
            return {"message": "User not found"}, 404
        
        if user_to_delete.id == api_user.id:
            return {"message": "You cannot delete your own account"}, 403
        
        if api_user.is_pure_org_admin():
            if user_to_delete.org_id != api_user.org_id:
                return {"message": "OrgAdmin can only delete users from their own organisation"}, 403
        
        if AdminModel.delete_user_core(id):
            flowintel_log("audit", 200, "User deleted via API", User=user_to_delete.email, UserId=id, By=api_user.email)
            return {"message": "User deleted"}, 200
        return {"message": "Error deleting user"}, 400


########
# Orgs #
########

@admin_ns.route('/orgs')
@admin_ns.doc(description='Get all orgs')
class GetOrgs(Resource):
    method_decorators = [api_required]
    def get(self):
        orgs = AdminModel.get_all_orgs()
        return {"orgs": [org.to_json() for org in orgs]}, 200


@admin_ns.route('/org/<oid>')
@admin_ns.doc(description='Get an org', params={'oid': 'id of an org'})
class GetOrgs(Resource):
    method_decorators = [api_required]
    def get(self, oid):
        org = AdminModel.get_org(oid)
        if org:
            return org.to_json(), 200
        return {"message": "Org not found"}, 404


@admin_ns.route('/add_org')
@admin_ns.doc(description='Add new organisation')
class AddOrg(Resource):
    method_decorators = [admin_required, api_required]
    
    @admin_ns.expect(add_org_model)
    def post(self):
        if request.json:
            api_user = get_user_api(request.headers["X-API-KEY"])
            verif_dict = AdminModelApi.verif_add_org(request.json)
            if "message" not in verif_dict:
                org = AdminModel.add_org_core(verif_dict)
                flowintel_log("audit", 200, "Org added via API", Org=request.json.get('name'), OrgId=org.id, By=api_user.email)
                return {"message": f"Org created: {org.id}", "org_id": org.id}, 201
            return verif_dict, 400
        return {"message": "Please give data"}, 400


@admin_ns.route('/edit_org/<id>')
@admin_ns.doc(description='Edit org', params={'id': "id of an org"})
class EditOrg(Resource):
    method_decorators = [admin_required, api_required]
    
    @admin_ns.expect(edit_org_model)
    def post(self, id):
        if request.json:
            api_user = get_user_api(request.headers["X-API-KEY"])
            org = AdminModel.get_org(id)
            if not org:
                return {"message": "Org not found"}, 404
            
            verif_dict = AdminModelApi.verif_edit_org(request.json, id)
            if "message" not in verif_dict:
                AdminModel.edit_org_core(verif_dict, id)
                flowintel_log("audit", 200, "Org edited via API", Org=verif_dict.get('name'), OrgId=id, By=api_user.email)
                return {"message": f"Org edited"}, 200
            return verif_dict, 400
        return {"message": "Please give data"}, 400

@admin_ns.route('/delete_org/<oid>')
@admin_ns.doc(description='Delete Org', params={'oid': "id of an org"})
class DeleteOrg(Resource):
    method_decorators = [admin_required, api_required]
    def get(self, oid):
        api_user = get_user_api(request.headers["X-API-KEY"])
        org = AdminModel.get_org(oid)
        if not org:
            return {"message": "Org not found"}, 404

        reasons = []
        if org.has_users():
            reasons.append("has users")
        if org.owns_cases():
            reasons.append("owns cases")
        if reasons:
            reason_str = " and ".join(reasons)
            flowintel_log("audit", 403, "Org deletion prevented: " + reason_str, OrgId=oid, OrgName=org.name, By=api_user.email)
            return {"message": "Cannot delete organisation that " + reason_str}, 403

        if AdminModel.delete_org_core(oid):
            flowintel_log("audit", 200, "Org deleted via API", OrgId=oid, By=api_user.email)
            return {"message": "Org deleted"}, 200
        return {"message": "Error deleting org"}, 400


#########
# Roles #
#########

@admin_ns.route('/roles')
@admin_ns.doc(description='Get all roles')
class GetRoles(Resource):
    method_decorators = [api_required]
    def get(self):
        roles = AdminModel.get_all_roles()
        return {"roles": [role.to_json() for role in roles]}, 200


@admin_ns.route('/add_role')
@admin_ns.doc(description='Add new role')
class AddRole(Resource):
    method_decorators = [admin_required, api_required]

    @admin_ns.expect(add_role_model)
    def post(self):
        if request.json:
            api_user = get_user_api(request.headers["X-API-KEY"])
            verif_dict = AdminModelApi.verif_add_role(request.json)
            if "message" not in verif_dict:
                role = AdminModel.add_role_core(verif_dict)
                flowintel_log("audit", 200, "Role added via API", Role=role.name, RoleId=role.id, By=api_user.email)
                return {"message": f"Role created: {role.id}", "role_id": role.id}, 201
            return verif_dict, 400
        return {"message": "Please give data"}, 400


@admin_ns.route('/delete_role/<rid>')
@admin_ns.doc(description='Delete role', params={'rid': 'id of a role'})
class DeleteRole(Resource):
    method_decorators = [admin_required, api_required]
    def get(self, rid):
        api_user = get_user_api(request.headers["X-API-KEY"])
        role_id = int(rid)

        if role_id in current_app.config['SYSTEM_ROLES']:
            return {"message": "Cannot delete system role"}, 400

        role = AdminModel.get_role(role_id)
        if not role:
            return {"message": "Role not found"}, 404

        users_count = AdminModel.count_users_with_role(role_id)
        if users_count > 0:
            return {"message": f"Cannot delete role: {users_count} user(s) still assigned"}, 400

        role_name = role.name
        if AdminModel.delete_role(role_id):
            flowintel_log("audit", 200, "Role deleted via API", RoleId=role_id, RoleName=role_name, By=api_user.email)
            return {"message": "Role deleted"}, 200
        return {"message": "Error deleting role"}, 400


##########
# Reload #
##########

@admin_ns.route('/reload')
@admin_ns.doc(description='Gracefully reload application workers to pick up config.py changes')
class ReloadApplication(Resource):
    method_decorators = [api_required]
    def post(self):
        api_user = get_user_api(request.headers["X-API-KEY"])
        if not api_user.is_admin():
            return {"message": "Admin required"}, 403

        ok, message, status = reload_application()
        if not ok:
            return {"message": message}, status

        flowintel_log("audit", 200, "Application reload requested via API", By=api_user.email)
        return {"message": message}, status

