from flask import Blueprint, request, jsonify
from ..utils.utils import get_user_from_api

from flask_restx import Api, Resource
from ..decorators import api_required, editor_required
from . import session_class as SessionModel
from . import misp_modules_core as MispModuleModel

api_analyzer_blueprint = Blueprint('api_analyzer', __name__)
api = Api(api_analyzer_blueprint,
        title='flowintel API', 
        description='API to manage a case management instance.', 
        version='0.1', 
        default='GenericAPI', 
        default_label='Generic flowintel API', 
        doc='/doc/'
    )


@api.route('/misp-modules/query', methods=['POST'])
@api.doc(description='Receive a result from an external tool')
class Query(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "query": "Required. List of queries",
        "input": "Required. Type of attributes in entry.Can be only one type",
        "modules": "Required. List of modules to run on queries"
    })
    def post(self):
        user = get_user_from_api(request.headers)
        if "query" in request.json:
            if "input" in request.json and request.json["input"]:
                if "modules" in request.json:
                    sess = SessionModel.Session_class(request.json, user)
                    sess.start()
                    SessionModel.sessions.append(sess)
                    return sess.status(), 201
                return {"message": "Need a module type"}, 400
            return {"message": "Need an input (misp attribute)"}, 400
        return {"message": "Need to type something"}, 400
    

@api.route('/misp-modules/status/<sid>', methods=['GET'])
@api.doc(description='See the status of a query', params={'sid': 'uuid of the session of query'})
class Status(Resource):
    method_decorators = [api_required]
    def get(self, sid):
        for s in SessionModel.sessions:
            if s.uuid == sid:
                return jsonify(s.status)
        if MispModuleModel.get_misp_modules_result(sid):
            return {"message": "Query is finished. /analyzer/misp-modules/result/<sid> to see the result"}
        return {"message": "Session not found."}
    
@api.route('/misp-modules/result/<sid>', methods=['GET'])
@api.doc(description='See the result of a query', params={'sid': 'uuid of the session of query'})
class Result(Resource):
    method_decorators = [api_required]
    def get(self, sid):
        res = MispModuleModel.get_misp_modules_result(sid)  
        if res:
            return res.to_json()
        return {"message": "Session not found. It may be not finished yet. /analyzer/misp-modules/status/<sid> to see the status of the query"}