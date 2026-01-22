from flask import request
from . import admin_core as AdminModel
from . import admin_core_api as AdminModelApi

from flask_restx import Namespace, Resource
from ..decorators import api_required, admin_required, admin_or_org_admin_required
from ..utils.utils import get_user_api
from flask import current_app
from flask_login import current_user


admin_ns = Namespace("admin", description="Endpoints to manage admin actions")


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
            return {"message": "No user found for this matrix id"}
        return {"message": "Need to pass a last name"}, 400

@admin_ns.route('/add_user')
@admin_ns.doc(description='Add new user')
class AddUser(Resource):
    method_decorators = [admin_or_org_admin_required, api_required]
    @admin_ns.doc(params={
        "first_name": "Required. First name for the user",
        "last_name": "Required. Last name for the user",
        "email": "Required. Email for the user",
        "password": "Required. Password for the user",
        "role": "Required. Role/Permission for the user",
        "org": "Organisation of the user"
        })

    def post(self):
        if request.json:
            api_user = get_user_api(request.headers["X-API-KEY"])
            
            if api_user.is_org_admin() and not api_user.is_admin():
                if 'org' not in request.json or int(request.json['org']) != api_user.org_id:
                    return {"message": "OrgAdmin can only add users to their own organization"}, 403
            
            verif_dict = AdminModelApi.verif_add_user(request.json, api_user)
            if "message" not in verif_dict:
                user = AdminModel.add_user_core(verif_dict)
                return {"message": f"User created {user.id}", "id": user.id}, 201
            return verif_dict, 400
        return {"message": "Please give data"}, 400

                
@admin_ns.route('/edit_user/<id>')
@admin_ns.doc(description='Edit user', params={'id': 'id of a user'})
class EditUser(Resource):
    method_decorators = [admin_or_org_admin_required, api_required]
    @admin_ns.doc(params={
        "first_name": "First name for the user",
        "last_name": "Last name for the user",
        "role": "Role/Permission for the user",
        "org": "Organisation of the user"
        })

    def post(self, id):
        if request.json:
            api_user = get_user_api(request.headers["X-API-KEY"])
            
            user_to_edit = AdminModel.get_user(id)
            if not user_to_edit:
                return {"message": "User not found"}, 404
            
            if api_user.is_org_admin() and not api_user.is_admin():
                if user_to_edit.org_id != api_user.org_id:
                    return {"message": "OrgAdmin can only edit users from their own organization"}, 403
                
                if 'org' in request.json and int(request.json['org']) != api_user.org_id:
                    return {"message": "OrgAdmin cannot move users to different organization"}, 403
            
            verif_dict = AdminModelApi.verif_edit_user(request.json, id, api_user)
            if "message" not in verif_dict:
                AdminModel.admin_edit_user_core(verif_dict, id)
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
        
        if api_user.is_org_admin() and not api_user.is_admin():
            if user_to_delete.org_id != api_user.org_id:
                return {"message": "OrgAdmin can only delete users from their own organization"}, 403
        
        if AdminModel.delete_user_core(id):
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
        return {"message", "Org not found"}, 404


@admin_ns.route('/add_org')
@admin_ns.doc(description='Add new organisation')
class AddOrg(Resource):
    method_decorators = [admin_required, api_required]
    @admin_ns.doc(params={
        "name": "Required. Name for the org",
        "description": "Description of the org",
        "uuid": "uuid of the org"
    })

    def post(self):
        if request.json:
            verif_dict = AdminModelApi.verif_add_org(request.json)
            if "message" not in verif_dict:
                org = AdminModel.add_org_core(verif_dict)
                return {"message": f"Org created: {org.id}", "org_id": org.id}, 201
            return verif_dict, 400
        return {"message": "Please give data"}, 400


@admin_ns.route('/edit_org/<id>')
@admin_ns.doc(description='Edit org', params={'id': "id of an org"})
class EditOrg(Resource):
    method_decorators = [admin_required, api_required]
    @admin_ns.doc(params={
        "name": "Name for the org",
        "description": "Description of the org",
        "uuid": "uuid of the org"
        })

    def post(self, id):
        if request.json:
            verif_dict = AdminModelApi.verif_edit_org(request.json, id)
            if "message" not in verif_dict:
                AdminModel.edit_org_core(verif_dict, id)
                return {"message": f"Org edited"}, 200
            return verif_dict, 400
        return {"message": "Please give data"}, 400

@admin_ns.route('/delete_org/<oid>')
@admin_ns.doc(description='Delete Org', params={'oid': "id of an org"})
class DeleteOrg(Resource):
    method_decorators = [admin_required, api_required]
    def get(self, oid):
        if AdminModel.get_org(oid):
            if AdminModel.delete_org_core(oid):
                return {"message": "Org deleted"}, 200
            return {"message": "Error Org deleted"}, 400
        return {"message": "Org not found"}, 404


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

