from flask import Blueprint, request
from . import admin_core as AdminModel
from . import admin_core_api as AdminModelApi

from flask_restx import Api, Resource
from ..decorators import api_required, admin_required


api_admin_blueprint = Blueprint('api_admin', __name__)
api = Api(api_admin_blueprint,
        title='flowintel API', 
        description='API to manage a case management instance.', 
        version='0.1', 
        default='GenericAPI', 
        default_label='Generic flowintel API', 
        doc='/doc'
    )


#########
# Users #
#########

@api.route('/users')
@api.doc(description='Get all users')
class GetUsers(Resource):
    method_decorators = [api_required]
    def get(self):
        users = AdminModel.get_all_users()
        return {"users": [user.to_json() for user in users]}, 200
    
@api.route('/user/<uid>')
@api.doc(description='Get a users', params={'uid': 'id of a user'})
class GetUsers(Resource):
    method_decorators = [api_required]
    def get(self, uid):
        user = AdminModel.get_user(uid)
        if user:
            return user.to_json(), 200
        return {"message": "User not found"}, 404

@api.route('/user')
@api.doc(description='Get a user by name', params={"lastname": "last name of a user"})
class GetUserName(Resource):
    method_decorators = [api_required]
    def get(self):
        if "lastname" in request.args:
            users = AdminModel.get_user_by_lastname(request.args.get("lastname"))
            return {"users": [user.to_json() for user in users]}, 200
        return {"message": "Need to pass a last name"}, 400

@api.route('/user_matrix_id')
@api.doc(description='Get a user by matrix id', params={"matrix_id": "matrix id of a user"})
class GetUserMatrix(Resource):
    method_decorators = [api_required]
    def get(self):
        if "matrix_id" in request.args:
            user = AdminModel.get_user_by_matrix_id(request.args.get("matrix_id"))
            if user:
                return user.to_json(), 200
            return {"message": "No user found for this matrix id"}
        return {"message": "Need to pass a last name"}, 400

@api.route('/add_user')
@api.doc(description='Add new user')
class AddUser(Resource):
    method_decorators = [admin_required, api_required]
    @api.doc(params={
        "first_name": "Required. First name for the user",
        "last_name": "Required. Last name for the user",
        "email": "Required. Email for the user",
        "password": "Required. Password for the user",
        "role": "Required. Role/Permission for the user",
        "org": "Organisation of the user"
        })

    def post(self):
        if request.json:
            verif_dict = AdminModelApi.verif_add_user(request.json)
            if "message" not in verif_dict:
                user = AdminModel.add_user_core(verif_dict)
                return {"message": f"User created, id: {user.id}"}, 201
            return verif_dict, 400
        return {"message": "Please give data"}, 400

                
@api.route('/edit_user/<id>')
@api.doc(description='Edit user', params={'id': 'id of a user'})
class EditUser(Resource):
    method_decorators = [admin_required, api_required]
    @api.doc(params={
        "first_name": "First name for the user",
        "last_name": "Last name for the user",
        "role": "Role/Permission for the user",
        "org": "Organisation of the user"
        })

    def post(self, id):
        if request.json:
            verif_dict = AdminModelApi.verif_edit_user(request.json, id)
            if "message" not in verif_dict:
                AdminModel.admin_edit_user_core(verif_dict, id)
                return {"message": "User edited"}, 200
            return verif_dict, 400
        return {"message": "Please give data"}, 400


@api.route('/delete_user/<id>')
@api.doc(description='Delete user' , params={'id': 'id of a user'})
class DeleteUser(Resource):
    method_decorators = [admin_required, api_required]
    def get(self, id):
        if AdminModel.get_user(id):
            if AdminModel.delete_user_core(id):
                return {"message": "User deleted"}, 200
            return {"message": "Error User deleted"}, 400
        return {"message", "User not found"}, 404


########
# Orgs #
########

@api.route('/orgs')
@api.doc(description='Get all orgs')
class GetOrgs(Resource):
    method_decorators = [api_required]
    def get(self):
        orgs = AdminModel.get_all_orgs()
        return {"orgs": [org.to_json() for org in orgs]}, 200


@api.route('/org/<oid>')
@api.doc(description='Get an org', params={'oid': 'id of an org'})
class GetOrgs(Resource):
    method_decorators = [api_required]
    def get(self, oid):
        org = AdminModel.get_org(oid)
        if org:
            return org.to_json(), 200
        return {"message", "Org not found"}, 404


@api.route('/add_org')
@api.doc(description='Add new organisation')
class AddOrg(Resource):
    method_decorators = [admin_required, api_required]
    @api.doc(params={
        "name": "Required. Name for the org",
        "description": "Description of the org",
        "uuid": "uuid of the org"
    })

    def post(self):
        if request.json:
            verif_dict = AdminModelApi.verif_add_org(request.json)
            if "message" not in verif_dict:
                org = AdminModel.add_org_core(verif_dict)
                return {"message": f"Org created: {org.id}"}, 201
            return verif_dict, 400
        return {"message": "Please give data"}, 400


@api.route('/edit_org/<id>')
@api.doc(description='Edit org', params={'oid': "id of an org"})
class EditOrg(Resource):
    method_decorators = [admin_required, api_required]
    @api.doc(params={
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

@api.route('/delete_org/<oid>')
@api.doc(description='Delete Org', params={'oid': "id of an org"})
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

@api.route('/roles')
@api.doc(description='Get all roles')
class GetRoles(Resource):
    method_decorators = [api_required]
    def get(self):
        roles = AdminModel.get_all_roles()
        return {"roles": [role.to_json() for role in roles]}, 200

