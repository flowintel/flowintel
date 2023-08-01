from flask import Blueprint, request
from . import admin_core as AdminModel
from . import admin_core_api as AdminModelApi

from flask_restx import Api, Resource
from ..decorators import api_required, admin_required


api_admin_blueprint = Blueprint('api_admin', __name__)
api = Api(api_admin_blueprint,
        title='Flowintel-cm API', 
        description='API to manage a case management instance.', 
        version='0.1', 
        default='GenericAPI', 
        default_label='Generic Flowintel-cm API', 
        doc='/doc'
    )


#########
# Users #
#########

@api.route('/users')
@api.doc(description='Get all users')
class GetUsers(Resource):
    method_decorators = [admin_required, api_required]
    def get(self):
        users = AdminModel.get_all_users()
        return {"users": [user.to_json() for user in users]}


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
            print(verif_dict)
            if "message" not in verif_dict:
                user = AdminModel.add_user_core(verif_dict)
                return {"message": f"User created: {user.id}"}, 400
            return verif_dict
        return {"message": "Please give data"}

                
@api.route('/edit_user/<id>')
@api.doc(description='Edit user')
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
                AdminModel.edit_user_core(verif_dict, id)
                return {"message": f"User edited"}
            return verif_dict
        return {"message": "Please give data"}


@api.route('/delete_user/<id>')
@api.doc(description='Delete user')
class DeleteUser(Resource):
    method_decorators = [admin_required, api_required]
    def get(self, id):
        if AdminModel.delete_user_core(id):
            return {"message": "User deleted"}
        return {"message": "Error User deleted"}


########
# Orgs #
########

@api.route('/orgs')
@api.doc(description='Get all orgs')
class GetOrgs(Resource):
    method_decorators = [admin_required, api_required]
    def get(self):
        orgs = AdminModel.get_all_orgs()
        return {"orgs": [org.to_json() for org in orgs]}


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
                return {"message": f"Org created: {org.id}"}
            return verif_dict
        return {"message": "Please give data"}


@api.route('/edit_org/<id>')
@api.doc(description='Edit org')
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
                return {"message": f"Org edited"}
            return verif_dict
        return {"message": "Please give data"}

@api.route('/delete_org/<id>')
@api.doc(description='Delete Org')
class DeleteOrg(Resource):
    method_decorators = [admin_required, api_required]
    def get(self, id):
        if AdminModel.delete_org_core(id):
            return {"message": "Org deleted"}
        return {"message": "Error Org deleted"}


#########
# Roles #
#########

@api.route('/roles')
@api.doc(description='Get all roles')
class GetRoles(Resource):
    method_decorators = [admin_required, api_required]
    def get(self):
        roles = AdminModel.get_all_roles()
        return {"roles": [role.to_json() for role in roles]}

