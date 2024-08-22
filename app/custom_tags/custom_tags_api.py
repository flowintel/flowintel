import json
from flask import Blueprint, request
from . import custom_tags_core as CustomModel
from . import custom_tags_core_api as CustomModelApi

from flask_restx import Api, Resource
from ..decorators import api_required, editor_required

api_custom_tags_blueprint = Blueprint('api_custom_tags', __name__)
api = Api(api_custom_tags_blueprint,
        title='flowintel API', 
        description='API to manage a case management instance.', 
        version='0.1', 
        default='GenericAPI', 
        default_label='Generic flowintel API', 
        doc='/doc/'
    )


@api.route('/add', methods=['POST'])
@api.doc(description='Add a new custom tag')
class AddCustomTags(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "name": "Required. Name of the tag",
        "color": "Required. Color that will represent the tag. (#ffffff)",
        "icon": "Optional. Fontawesome icon (fa-solid fa-bicycle)"
    })
    def post(self):
        if request.json:
            verif_dict = CustomModelApi.verif_add_custom_tag(request.json)
            if "message" not in verif_dict:
                CustomModel.add_custom_tag_core(verif_dict)
                return {"message": f"New custom tag created"}, 201
            return verif_dict, 400
        return {"message": "Please give data"}, 400
    
@api.route('/<ctid>/delete')
@api.doc(description='Delete a custom tag', params={'ctid': 'id of a custom tag'})
class DeleteCustomTag(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, ctid):
        if CustomModel.get_custom_tag(ctid):
            if CustomModel.delete_custom_tag(ctid):
                return {"message": "Custom Tag deleted"}, 200
            return {"message": "Error deleting custom tag"}, 400
        return {"message": "This custom tag doesn't exist"}, 404
    
@api.route('/all')
@api.doc(description='all custom tags')
class AllCustomTags(Resource):
    method_decorators = [api_required]
    def get(self):
        return [c_t.to_json() for c_t in CustomModel.get_custom_tags()], 200
    
@api.route('/<ctid>/edit', methods=['POST'])
@api.doc(description='Edit a custom tag')
class EditCustomTags(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "name": "Required. Name of the tag",
        "color": "Required. Color that will represent the tag. (#ffffff)",
        "icon": "Optional. Fontawesome icon (fa-solid fa-bicycle)"
    })
    def post(self, ctid):
        if request.json:
            verif_dict = CustomModelApi.verif_edit_custom_tag(request.json, ctid)
            if "message" not in verif_dict:
                if CustomModel.change_config_core(verif_dict):
                    return {"message": f"Custom tag edited"}, 200
                return {"message": "Custom tag not found"}, 404
            return verif_dict, 400
        return {"message": "Please give data"}, 400
    
@api.route('/<ctid>')
@api.doc(description='Get a custom tag', params={'ctid': 'id of a custom tag'})
class GetCustomTag(Resource):
    method_decorators = [api_required]
    def get(self, ctid):
        c = CustomModel.get_custom_tag(ctid)
        if c:
            return c.to_json(), 200
        return {"message": "This custom tag doesn't exist"}, 404
    