from flask import Blueprint, request
from . import tools_core as ToolModel

from flask_restx import Api, Resource
from ..decorators import api_required

from ..utils import utils


api_importer_blueprint = Blueprint('api_importer', __name__)
api = Api(api_importer_blueprint,
        title='flowintel API', 
        description='API to manage a case management instance.', 
        version='0.1', 
        default='GenericAPI', 
        default_label='Generic flowintel API', 
        doc='/doc'
    )

    
@api.route('/')
@api.doc(description='Import a case. JSON is required')
class ImportCase(Resource):
    method_decorators = [api_required]
    # @api.doc(params={})
    def post(self):
        if request.json:
            current_user = utils.get_user_api(request.headers["X-API-KEY"])
            if type(request.json) == list:
                for case in request.json:
                    res = ToolModel.core_read_json_file(case, current_user)
                    if res:
                        return res
            else:
                res = ToolModel.core_read_json_file(request.json, current_user)
                if res:
                    return res
            return {"message": "All created"}