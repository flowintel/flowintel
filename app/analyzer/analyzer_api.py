import json
from flask import Blueprint, request
from ..case import case_core_api as CaseModelApi
from . import analyzer_core as AnalyzerModel

from flask_restx import Api, Resource
from ..decorators import api_required, editor_required

api_analyzer_blueprint = Blueprint('api_analyzer', __name__)
api = Api(api_analyzer_blueprint,
        title='flowintel API', 
        description='API to manage a case management instance.', 
        version='0.1', 
        default='GenericAPI', 
        default_label='Generic flowintel API', 
        doc='/doc/'
    )


@api.route('/receive_result', methods=['POST'])
@api.doc(description='Receive a result from an external tool')
class ReiceveResult(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "results": "Required. Results from external tool"
    })
    def post(self):
        user = CaseModelApi.get_user_api(request.headers)
        print(request.json)
        if request.json:
            AnalyzerModel.add_pending_result(request.headers.get('Origin'), request.json["results"], user)
            return {"message": "Results receive"}, 200
        return {"message": "Please give data"}, 400
    
