from flask import request
from . import custom_tags_core as CustomModel
from . import custom_tags_core_api as CustomModelApi

from flask_restx import Namespace, Resource
from ..decorators import api_required, editor_required
from ..utils import utils
from ..utils.logger import flowintel_log

custom_tags_ns = Namespace("custom_tags", description="Endpoints to manage custom tags")

@custom_tags_ns.route('/add', methods=['POST'])
@custom_tags_ns.doc(description='Add a new custom tag')
class AddCustomTags(Resource):
    method_decorators = [editor_required, api_required]
    @custom_tags_ns.doc(params={
        "name": "Required. Name of the tag",
        "color": "Required. Color that will represent the tag. (#ffffff)",
        "icon": "Optional. Fontawesome icon (fa-solid fa-bicycle)"
    })
    def post(self):
        user = utils.get_user_from_api(request.headers)
        if request.json:
            verif_dict = CustomModelApi.verif_add_custom_tag(request.json)
            if "message" not in verif_dict:
                custom_tag = CustomModel.add_custom_tag_core(verif_dict)
                flowintel_log("audit", 201, "API: Custom tag created", User=user.email, CustomTagId=custom_tag.id, CustomTagName=verif_dict["name"], Color=verif_dict["color"], Icon=verif_dict.get("icon"))
                return {"message": f"New custom tag created"}, 201
            return verif_dict, 400
        return {"message": "Please give data"}, 400
    
@custom_tags_ns.route('/<ctid>/delete')
@custom_tags_ns.doc(description='Delete a custom tag', params={'ctid': 'id of a custom tag'})
class DeleteCustomTag(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, ctid):
        user = utils.get_user_from_api(request.headers)
        custom_tag = CustomModel.get_custom_tag(ctid)
        if custom_tag:
            tag_name = custom_tag.name
            if CustomModel.delete_custom_tag(ctid):
                flowintel_log("audit", 200, "API: Custom tag deleted", User=user.email, CustomTagId=ctid, CustomTagName=tag_name)
                return {"message": "Custom Tag deleted"}, 200
            return {"message": "Error deleting custom tag"}, 400
        return {"message": "This custom tag doesn't exist"}, 404
    
@custom_tags_ns.route('/all')
@custom_tags_ns.doc(description='all custom tags')
class AllCustomTags(Resource):
    method_decorators = [api_required]
    def get(self):
        return [c_t.to_json() for c_t in CustomModel.get_custom_tags()], 200
    
@custom_tags_ns.route('/<ctid>/edit', methods=['POST'])
@custom_tags_ns.doc(description='Edit a custom tag')
class EditCustomTags(Resource):
    method_decorators = [editor_required, api_required]
    @custom_tags_ns.doc(params={
        "name": "Required. Name of the tag",
        "color": "Required. Color that will represent the tag. (#ffffff)",
        "icon": "Optional. Fontawesome icon (fa-solid fa-bicycle)"
    })
    def post(self, ctid):
        user = utils.get_user_from_api(request.headers)
        if request.json:
            verif_dict = CustomModelApi.verif_edit_custom_tag(request.json, ctid)
            if "message" not in verif_dict:
                if CustomModel.change_config_core(verif_dict):
                    flowintel_log("audit", 200, "API: Custom tag edited", User=user.email, CustomTagId=ctid, CustomTagName=verif_dict["custom_tag_name"], Color=verif_dict["custom_tag_color"], Icon=verif_dict.get("custom_tag_icon"))
                    return {"message": f"Custom tag edited"}, 200
                return {"message": "Custom tag not found"}, 404
            # Check if error is "not found" vs validation error
            if "not found" in verif_dict.get("message", "").lower():
                return verif_dict, 404
            return verif_dict, 400
        return {"message": "Please give data"}, 400
    
@custom_tags_ns.route('/<ctid>')
@custom_tags_ns.doc(description='Get a custom tag', params={'ctid': 'id of a custom tag'})
class GetCustomTag(Resource):
    method_decorators = [api_required]
    def get(self, ctid):
        c = CustomModel.get_custom_tag(ctid)
        if c:
            return c.to_json(), 200
        return {"message": "This custom tag doesn't exist"}, 404
    